# src\processors\transaction_matcher.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Set, Optional
import logging
from pathlib import Path
import os

from utils import get_logger, FileManager

logger = get_logger()

class TransactionMatcher:
    """
    Class to match bank statement transactions with sales and purchase invoices.
    The main goal is to identify which invoices in the sale_df and purchase_df match with the deposits and withdrawals in the statement_df, 
    while using withholding_df as additional confirmation information.
    1. Matches deposits in the statement_df with invoices in sale_df and withholding_df
    2. Matches withdrawals in the statement_df with invoices in purchase_df
    3. Handles special cases like multiple invoices being paid at once or small differences in amounts
    4. Ensures matched invoices aren't reused
    5. Formats and saves the results in Thai with proper date formatting
    """
    
    def __init__(self, 
                 statement_df: pd.DataFrame,
                 sale_df: pd.DataFrame,
                 purchase_df: pd.DataFrame,
                 withholding_df: pd.DataFrame,
                 max_credit_days: int = 30,
                 sale_tolerance: float = 1000.0,
                 purchase_tolerance: float = 50.0) -> None:
        """
        Initialize the transaction matcher
        
        Args:
            statement_df: DataFrame containing bank statement entries
            sale_df: DataFrame containing sale invoices
            purchase_df: DataFrame containing purchase invoices
            withholding_df: DataFrame containing withholding tax entries
            max_credit_days: Maximum number of days between invoice and payment
            sale_tolerance: Maximum allowed difference in sale transaction amounts
            purchase_tolerance: Maximum allowed difference in purchase transaction amounts
        """
        self.statement_df = statement_df.copy()
        self.sale_df = sale_df.copy()
        self.purchase_df = purchase_df.copy()
        self.withholding_df = withholding_df.copy()
        
        self.max_credit_days = max_credit_days
        self.sale_tolerance = sale_tolerance
        self.purchase_tolerance = purchase_tolerance
        
        # Sets to keep track of matched invoices (to avoid reuse)
        self.matched_sale_indexes = set()
        self.matched_purchase_indexes = set()
        self.matched_withholding_indexes = set()
        
        # Results for matched transactions
        self.matched_deposits = []
        self.matched_withdrawals = []
        
        # Prepare data
        self._prepare_data()
        
    def _prepare_data(self) -> None:
        """Prepare the dataframes for matching"""
        logger.info("Preparing data for matching")
        
        # Ensure datetime columns are properly formatted
        for df, date_col in [(self.statement_df, 'datetime'), 
                             (self.sale_df, 'date_of_sale_invoice'),
                             (self.purchase_df, 'date_of_purchase_invoice'),
                             (self.withholding_df, 'paid_date')]:
            if date_col in df.columns:
                if df[date_col].dtype != 'datetime64[ns]':
                    try:
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                        logger.debug(f"Converted {date_col} to datetime")
                    except Exception as e:
                        logger.error(f"Error converting {date_col} to datetime: {e}")
        
        # Add matched status columns if they don't exist
        if 'matched' not in self.sale_df.columns:
            self.sale_df['matched'] = 'false'
        if 'matched' not in self.purchase_df.columns:
            self.purchase_df['matched'] = 'false'
        if 'matched' not in self.withholding_df.columns:
            self.withholding_df['matched'] = 'false'
        
        # Sort bank statement by date
        self.statement_df = self.statement_df.sort_values(by='datetime')
        
        # Prepare unique IDs for easier matching
        self.sale_df['invoice_id'] = self.sale_df['sale_invoice_tax_number'].astype(str)
        
        # Convert boolean isDeposit to actual boolean
        if 'isDeposit' in self.statement_df.columns:
            self.statement_df['isDeposit'] = (self.statement_df['isDeposit'].astype(str).str.lower() == 'true')
            
        logger.debug(f"Prepared statement_df: {len(self.statement_df)} entries")
        logger.debug(f"Prepared sale_df: {len(self.sale_df)} entries")
        logger.debug(f"Prepared purchase_df: {len(self.purchase_df)} entries")
        logger.debug(f"Prepared withholding_df: {len(self.withholding_df)} entries")
        
    def _find_candidate_sales(self, 
                              deposit_date: datetime, 
                              deposit_amount: float) -> List[int]:
        """
        Find candidate sale invoices for a deposit
        
        Args:
            deposit_date: Date of the deposit
            deposit_amount: Amount of the deposit
            
        Returns:
            List of indices of candidate sale invoices
        """
        # Filter sales by date range and that aren't already matched
        candidate_indexes = []
        
        for idx, row in self.sale_df.iterrows():
            if idx in self.matched_sale_indexes:
                continue
                
            invoice_date = row['date_of_sale_invoice']
            if pd.isna(invoice_date):
                continue
                
            # Check date range (max_credit_days before or after)
            date_diff = abs((deposit_date - invoice_date).days)
            if date_diff > self.max_credit_days:
                continue
                
            # Check amount (with tolerance)
            net_amount = float(row['net_amount'])
            if abs(net_amount - deposit_amount) <= self.sale_tolerance:
                candidate_indexes.append(idx)
                
        return candidate_indexes
    
    def _find_candidate_withholdings(self, 
                                     deposit_date: datetime, 
                                     deposit_amount: float) -> List[int]:
        """
        Find candidate withholding tax entries for a deposit
        
        Args:
            deposit_date: Date of the deposit
            deposit_amount: Amount of the deposit
            
        Returns:
            List of indices of candidate withholding tax entries
        """
        # Filter withholdings by date and that aren't already matched
        candidate_indexes = []
        
        for idx, row in self.withholding_df.iterrows():
            if idx in self.matched_withholding_indexes:
                continue
                
            paid_date = row['paid_date']
            if pd.isna(paid_date):
                continue
                
            # For withholding, we want a close date match
            date_diff = abs((deposit_date - paid_date).days)
            if date_diff > 3:  # Be more strict with date matching for withholding
                continue
                
            # Check amount (with tolerance)
            paid_amount = float(row['paid_amount'])
            if abs(paid_amount - deposit_amount) <= self.sale_tolerance:
                candidate_indexes.append(idx)
                
        return candidate_indexes
    
    def _find_candidate_purchases(self, 
                                 withdrawal_date: datetime, 
                                 withdrawal_amount: float) -> List[int]:
        """
        Find candidate purchase invoices for a withdrawal
        
        Args:
            withdrawal_date: Date of the withdrawal
            withdrawal_amount: Amount of the withdrawal
            
        Returns:
            List of indices of candidate purchase invoices
        """
        # Filter purchases by date range and that aren't already matched
        candidate_indexes = []
        
        for idx, row in self.purchase_df.iterrows():
            if idx in self.matched_purchase_indexes:
                continue
                
            invoice_date = row['date_of_purchase_invoice']
            if pd.isna(invoice_date):
                continue
                
            # Check that withdrawal is not before purchase and within credit days
            if withdrawal_date < invoice_date:
                continue
                
            date_diff = (withdrawal_date - invoice_date).days
            if date_diff > self.max_credit_days:
                continue
                
            # Check amount (with tolerance)
            total_amount = float(row['total_amount'])
            if abs(total_amount - withdrawal_amount) <= self.purchase_tolerance:
                candidate_indexes.append(idx)
                
        return candidate_indexes
        
    def _find_sale_combinations(self, 
                               company_sales: pd.DataFrame, 
                               deposit_amount: float) -> List[List[int]]:
        """
        Find combinations of sales from the same company that sum to deposit amount
        
        Args:
            company_sales: DataFrame containing sales from a single company
            deposit_amount: Amount of the deposit
            
        Returns:
            List of lists of sale indices that sum to deposit amount
        """
        # Simple cases first: exact match or match within tolerance
        valid_combinations = []
        
        # Try single invoice match
        for idx, row in company_sales.iterrows():
            if idx in self.matched_sale_indexes:
                continue
            
            if abs(float(row['net_amount']) - deposit_amount) <= self.sale_tolerance:
                valid_combinations.append([idx])
        
        # If we have single invoice matches, no need to try combinations
        if valid_combinations:
            return valid_combinations
            
        # Try combinations of invoices
        # This is a subset sum problem, which can be complex for large datasets
        # We'll use a greedy approach for simplicity
        remaining_sales = company_sales[~company_sales.index.isin(self.matched_sale_indexes)].copy()
        
        # Try pairs of invoices (most common case)
        for i, row1 in remaining_sales.iterrows():
            for j, row2 in remaining_sales.iterrows():
                if i >= j:  # Avoid duplicates and self-pairs
                    continue
                    
                sum_amount = float(row1['net_amount']) + float(row2['net_amount'])
                if abs(sum_amount - deposit_amount) <= self.sale_tolerance:
                    valid_combinations.append([i, j])
        
        # If we have pairs, return them
        if valid_combinations:
            return valid_combinations
            
        # For simplicity, we won't go beyond pairs in this implementation
        # More sophisticated algorithms would be needed for larger combinations
        
        return valid_combinations
        
    def _match_deposit(self, deposit_idx: int) -> Dict:
        """
        Match a deposit with sale invoices
        
        Args:
            deposit_idx: Index of the deposit in statement_df
            
        Returns:
            Dictionary with matching information
        """
        deposit_row = self.statement_df.iloc[deposit_idx]
        deposit_date = deposit_row['datetime']
        deposit_amount = float(deposit_row['amount'])
        
        logger.debug(f"Matching deposit: {deposit_date} amount: {deposit_amount}")
        
        # First try to find exact matches in sales
        candidate_sales = self._find_candidate_sales(deposit_date, deposit_amount)
        
        matched_info = {
            'statement_idx': deposit_idx,
            'deposit_date': deposit_date,
            'deposit_amount': deposit_amount,
            'matched_sales': [],
            'matched_withholdings': [],
            'companies': set(),
            'total_matched_amount': 0.0,
            'difference': deposit_amount,  # Initialize with full amount
            'is_matched': False
        }
        
        # Check for single invoice matches first
        for sale_idx in candidate_sales:
            sale_row = self.sale_df.loc[sale_idx]
            sale_amount = float(sale_row['net_amount'])
            
            # Check if this is an exact match
            if abs(sale_amount - deposit_amount) <= self.sale_tolerance:
                # Mark this sale as matched
                self.matched_sale_indexes.add(sale_idx)
                self.sale_df.at[sale_idx, 'matched'] = 'true'
                
                matched_info['matched_sales'].append(sale_idx)
                matched_info['companies'].add(str(sale_row['company_name']))
                matched_info['total_matched_amount'] += sale_amount
                matched_info['difference'] = deposit_amount - sale_amount
                matched_info['is_matched'] = True
                
                logger.debug(f"Found exact sale match: Invoice {sale_row['sale_invoice_tax_number']}, Amount: {sale_amount}")
                
                # Try to find matching withholding entry for confirmation
                for with_idx, with_row in self.withholding_df.iterrows():
                    if with_idx in self.matched_withholding_indexes:
                        continue
                        
                    # Check if company matches
                    if str(with_row['company_name']).strip() != str(sale_row['company_name']).strip() and \
                       str(with_row['tax_id']).strip() != str(sale_row['company_tax_id']).strip():
                        continue
                        
                    # Check if date is close
                    with_date = with_row['paid_date']
                    if pd.isna(with_date):
                        continue
                        
                    date_diff = abs((deposit_date - with_date).days)
                    if date_diff > 3:  # Be more strict with date matching for withholding
                        continue
                        
                    # Check if amounts match
                    with_amount = float(with_row['paid_amount'])
                    if abs(with_amount - sale_amount) <= self.sale_tolerance:
                        # Mark this withholding as matched
                        self.matched_withholding_indexes.add(with_idx)
                        self.withholding_df.at[with_idx, 'matched'] = 'true'
                        matched_info['matched_withholdings'].append(with_idx)
                        logger.debug(f"Found matching withholding: Company {with_row['company_name']}, Amount: {with_amount}")
                        break
                
                # If we found a match, we can return
                return matched_info
                
        # If no single invoice match, try company grouping
        # Group sales by company
        unmatched_sales = self.sale_df[~self.sale_df.index.isin(self.matched_sale_indexes)]
        companies = unmatched_sales['company_name'].unique()
        
        for company in companies:
            company_sales = unmatched_sales[unmatched_sales['company_name'] == company]
            
            # Find combinations of invoices that match the deposit amount
            combinations = self._find_sale_combinations(company_sales, deposit_amount)
            
            if combinations:
                # Take the first valid combination (can be enhanced for better selection)
                for sale_indices in combinations:
                    sale_rows = [self.sale_df.loc[idx] for idx in sale_indices]
                    total_amount = sum(float(row['net_amount']) for row in sale_rows)
                    
                    # Mark all these sales as matched
                    for sale_idx in sale_indices:
                        self.matched_sale_indexes.add(sale_idx)
                        self.sale_df.at[sale_idx, 'matched'] = 'true'
                        matched_info['matched_sales'].append(sale_idx)
                    
                    matched_info['companies'].add(str(company))
                    matched_info['total_matched_amount'] = total_amount
                    matched_info['difference'] = deposit_amount - total_amount
                    matched_info['is_matched'] = True
                    
                    logger.debug(f"Found company {company} combination match: {len(sale_indices)} invoices, Total: {total_amount}")
                    
                    # Try to find matching withholding entry
                    # Same approach as above, but for company group
                    
                    # If we found a match, return
                    return matched_info
                    
        # If no match in sales, try withholding as fallback
        if not matched_info['is_matched']:
            candidate_withholdings = self._find_candidate_withholdings(deposit_date, deposit_amount)
            
            for with_idx in candidate_withholdings:
                with_row = self.withholding_df.loc[with_idx]
                with_amount = float(with_row['paid_amount'])
                
                # This is a potential match from withholding
                self.matched_withholding_indexes.add(with_idx)
                self.withholding_df.at[with_idx, 'matched'] = 'true'
                
                matched_info['matched_withholdings'].append(with_idx)
                matched_info['companies'].add(str(with_row['company_name']))
                matched_info['total_matched_amount'] = with_amount
                matched_info['difference'] = deposit_amount - with_amount
                matched_info['is_matched'] = True
                
                logger.debug(f"Found withholding match: Company {with_row['company_name']}, Amount: {with_amount}")
                return matched_info
                
        # No match found
        logger.debug(f"No match found for deposit on {deposit_date} for amount {deposit_amount}")
        return matched_info
    
    def _match_withdrawal(self, withdrawal_idx: int) -> Dict:
        """
        Match a withdrawal with purchase invoices
        
        Args:
            withdrawal_idx: Index of the withdrawal in statement_df
            
        Returns:
            Dictionary with matching information
        """
        withdrawal_row = self.statement_df.iloc[withdrawal_idx]
        withdrawal_date = withdrawal_row['datetime']
        withdrawal_amount = abs(float(withdrawal_row['amount']))  # Ensure positive
        
        logger.debug(f"Matching withdrawal: {withdrawal_date} amount: {withdrawal_amount}")
        
        # Find candidate purchases
        candidate_purchases = self._find_candidate_purchases(withdrawal_date, withdrawal_amount)
        
        matched_info = {
            'statement_idx': withdrawal_idx,
            'withdrawal_date': withdrawal_date,
            'withdrawal_amount': withdrawal_amount,
            'matched_purchases': [],
            'companies': set(),
            'total_matched_amount': 0.0,
            'difference': withdrawal_amount,  # Initialize with full amount
            'is_matched': False
        }
        
        # Check for matches
        for purchase_idx in candidate_purchases:
            purchase_row = self.purchase_df.loc[purchase_idx]
            purchase_amount = float(purchase_row['total_amount'])
            
            # Check if this is a good match
            if abs(purchase_amount - withdrawal_amount) <= self.purchase_tolerance:
                # Mark this purchase as matched
                self.matched_purchase_indexes.add(purchase_idx)
                self.purchase_df.at[purchase_idx, 'matched'] = 'true'
                
                matched_info['matched_purchases'].append(purchase_idx)
                matched_info['companies'].add(str(purchase_row['company_name']))
                matched_info['total_matched_amount'] = purchase_amount
                matched_info['difference'] = withdrawal_amount - purchase_amount
                matched_info['is_matched'] = True
                
                logger.debug(f"Found purchase match: Invoice {purchase_row['purchase_invoice_id']}, Amount: {purchase_amount}")
                return matched_info
                
        # No match found
        logger.debug(f"No match found for withdrawal on {withdrawal_date} for amount {withdrawal_amount}")
        return matched_info
    
    def match_transactions(self) -> None:
        """Match all transactions in the statement with invoices"""
        logger.info(f"Starting transaction matching process")
        
        # Process deposits first
        deposit_count = len(self.statement_df[self.statement_df['isDeposit'] == True])
        logger.info(f"Processing {deposit_count} deposits")
        
        for idx, row in self.statement_df[self.statement_df['isDeposit'] == True].iterrows():
            match_result = self._match_deposit(idx)
            if match_result['is_matched']:
                self.matched_deposits.append(match_result)
                
        # Then process withdrawals
        withdrawal_count = len(self.statement_df[self.statement_df['isDeposit'] == False])
        logger.info(f"Processing {withdrawal_count} withdrawals")
        
        for idx, row in self.statement_df[self.statement_df['isDeposit'] == False].iterrows():
            match_result = self._match_withdrawal(idx)
            if match_result['is_matched']:
                self.matched_withdrawals.append(match_result)
                
        logger.info(f"Matched {len(self.matched_deposits)} deposits and {len(self.matched_withdrawals)} withdrawals")
        logger.info(f"Matched {len(self.matched_sale_indexes)} sale invoices")
        logger.info(f"Matched {len(self.matched_purchase_indexes)} purchase invoices")
        logger.info(f"Matched {len(self.matched_withholding_indexes)} withholding entries")
    
    def generate_transaction_match_report(self) -> pd.DataFrame:
        """
        Generate a report of matched transactions
        
        Returns:
            DataFrame containing transaction match information
        """
        logger.info("Generating transaction match report")
        
        match_rows = []
        
        # Process matched deposits
        for match in self.matched_deposits:
            deposit_date = match['deposit_date']
            deposit_amount = match['deposit_amount']
            companies = " | ".join(match['companies'])
            
            # Get sale invoice details
            sale_invoices = []
            sale_tax_ids = []
            for sale_idx in match['matched_sales']:
                sale_row = self.sale_df.loc[sale_idx]
                sale_invoices.append(str(sale_row['sale_invoice_tax_number']))
                sale_tax_ids.append(str(sale_row['company_tax_id']))
                
            # Combine invoice numbers and tax IDs
            sale_invoice_str = " | ".join(sale_invoices) if sale_invoices else ""
            sale_tax_id_str = " | ".join(sale_tax_ids) if sale_tax_ids else ""
            
            # Get withholding details
            with_dates = []
            for with_idx in match['matched_withholdings']:
                with_row = self.withholding_df.loc[with_idx]
                with_dates.append(with_row['paid_date'].strftime('%d-%m-%y') if not pd.isna(with_row['paid_date']) else "")
                
            with_date_str = " | ".join(with_dates) if with_dates else ""
            
            match_rows.append({
                'ประเภทรายการ': 'เงินฝาก',
                'วันที่ทำรายการ': deposit_date.strftime('%d-%m-%y'),
                'จำนวนเงิน': round(deposit_amount, 2),
                'บริษัท': companies,
                'รหัสประจำตัวผู้เสียภาษี': sale_tax_id_str,
                'เลขที่ใบกำกับภาษี': sale_invoice_str,
                'วันที่จ่าย': with_date_str,
                'จำนวนเงินที่จับคู่': round(match['total_matched_amount'], 2),
                'ส่วนต่าง': round(match['difference'], 2)
            })
            
        # Process matched withdrawals
        for match in self.matched_withdrawals:
            withdrawal_date = match['withdrawal_date']
            withdrawal_amount = match['withdrawal_amount']
            companies = " | ".join(match['companies'])
            
            # Get purchase invoice details
            purchase_invoices = []
            purchase_tax_ids = []
            for purchase_idx in match['matched_purchases']:
                purchase_row = self.purchase_df.loc[purchase_idx]
                purchase_invoices.append(str(purchase_row['purchase_invoice_id']))
                purchase_tax_ids.append(str(purchase_row['company_tax_id']))
                
            # Combine invoice numbers and tax IDs
            purchase_invoice_str = " | ".join(purchase_invoices) if purchase_invoices else ""
            purchase_tax_id_str = " | ".join(purchase_tax_ids) if purchase_tax_ids else ""
            
            match_rows.append({
                'ประเภทรายการ': 'เงินถอน',
                'วันที่ทำรายการ': withdrawal_date.strftime('%d-%m-%y'),
                'จำนวนเงิน': round(withdrawal_amount, 2),
                'บริษัท': companies,
                'รหัสประจำตัวผู้เสียภาษี': purchase_tax_id_str,
                'เลขที่ใบกำกับภาษี': purchase_invoice_str,
                'วันที่จ่าย': '',  # Not applicable for withdrawals
                'จำนวนเงินที่จับคู่': round(match['total_matched_amount'], 2),
                'ส่วนต่าง': round(match['difference'], 2)
            })
            
        if not match_rows:
            logger.warning("No matches found for transaction report")
            return pd.DataFrame()
            
        match_df = pd.DataFrame(match_rows)
        logger.debug(f"Generated transaction match report with {len(match_df)} rows")
        return match_df
        
    def generate_sale_match_report(self) -> pd.DataFrame:
        """
        Generate a report of sale invoices with match status
        
        Returns:
            DataFrame containing sale invoice match information
        """
        logger.info("Generating sale match report")
        
        # Create a copy of the sale dataframe with additional columns for Thai names
        sale_report = self.sale_df.copy()
        
        # Format datetime column
        if 'date_of_sale_invoice' in sale_report.columns:
            sale_report['วันที่ใบกำกับภาษี'] = sale_report['date_of_sale_invoice'].apply(
                lambda x: x.strftime('%d-%m-%y') if not pd.isna(x) else ""
            )
        
        # Rename columns and format numbers
        sale_report['ลำดับ'] = sale_report['order_number']
        sale_report['เลขที่ใบกำกับภาษี'] = sale_report['sale_invoice_tax_number']
        sale_report['ชื่อบริษัท'] = sale_report['company_name']
        sale_report['เลขประจำตัวผู้เสียภาษี'] = sale_report['company_tax_id']
        sale_report['มูลค่าสินค้า'] = sale_report['product_value'].apply(lambda x: round(float(x), 2))
        sale_report['ภาษีมูลค่าเพิ่ม'] = sale_report['vat'].apply(lambda x: round(float(x), 2))
        sale_report['จำนวนเงิน'] = sale_report['total_amount'].apply(lambda x: round(float(x), 2))
        sale_report['หัก 3%'] = sale_report['withholding_tax'].apply(lambda x: round(float(x), 2))
        sale_report['คงเหลือ'] = sale_report['net_amount'].apply(lambda x: round(float(x), 2))
        sale_report['จับคู่แล้ว'] = sale_report['matched'].map({'true': 'ใช่', 'false': 'ไม่'})
        
        # Keep only Thai columns
        thai_columns = [
            'ลำดับ', 'วันที่ใบกำกับภาษี', 'เลขที่ใบกำกับภาษี', 'ชื่อบริษัท',
            'เลขประจำตัวผู้เสียภาษี', 'มูลค่าสินค้า', 'ภาษีมูลค่าเพิ่ม', 'จำนวนเงิน',
            'หัก 3%', 'คงเหลือ', 'จับคู่แล้ว'
        ]
        
        final_report = sale_report[thai_columns]
        logger.debug(f"Generated sale match report with {len(final_report)} rows")
        return final_report
        
    def generate_purchase_match_report(self) -> pd.DataFrame:
        """
        Generate a report of purchase invoices with match status
        
        Returns:
            DataFrame containing purchase invoice match information
        """
        logger.info("Generating purchase match report")
        
        # Create a copy of the purchase dataframe with additional columns for Thai names
        purchase_report = self.purchase_df.copy()
        
        # Format datetime column
        if 'date_of_purchase_invoice' in purchase_report.columns:
            purchase_report['วันที่ใบกำกับภาษี'] = purchase_report['date_of_purchase_invoice'].apply(
                lambda x: x.strftime('%d-%m-%y') if not pd.isna(x) else ""
            )
        
        # Rename columns and format numbers
        purchase_report['ลำดับ'] = purchase_report['order_number']
        purchase_report['เลขที่ใบกำกับภาษี'] = purchase_report['purchase_invoice_tax_number']
        purchase_report['เลขที่เอกสาร'] = purchase_report['purchase_invoice_id']
        purchase_report['ชื่อบริษัท'] = purchase_report['company_name']
        purchase_report['เลขประจำตัวผู้เสียภาษี'] = purchase_report['company_tax_id']
        purchase_report['มูลค่าสินค้า'] = purchase_report['product_value'].apply(lambda x: round(float(x), 2))
        purchase_report['ภาษีมูลค่าเพิ่ม'] = purchase_report['vat'].apply(lambda x: round(float(x), 2))
        purchase_report['จำนวนเงิน'] = purchase_report['total_amount'].apply(lambda x: round(float(x), 2))
        purchase_report['จับคู่แล้ว'] = purchase_report['matched'].map({'true': 'ใช่', 'false': 'ไม่'})
        
        # Keep only Thai columns
        thai_columns = [
            'ลำดับ', 'วันที่ใบกำกับภาษี', 'เลขที่ใบกำกับภาษี', 'เลขที่เอกสาร', 'ชื่อบริษัท',
            'เลขประจำตัวผู้เสียภาษี', 'มูลค่าสินค้า', 'ภาษีมูลค่าเพิ่ม', 'จำนวนเงิน',
            'จับคู่แล้ว'
        ]