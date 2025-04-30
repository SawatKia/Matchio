# src\processors\transaction_matcher.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Set, Optional
import logging
from pathlib import Path
import os
import time
import itertools # Import for combinations

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
                 purchase_tolerance: float = 50.0,
                 expected_column_mappings: Dict = None) -> None:
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
            expected_column_mappings: Dictionary containing column mappings for report generation
        """
        # Create copies to avoid modifying the original dataframes passed in
        self.statement_df = statement_df.copy() if statement_df is not None else pd.DataFrame()
        self.sale_df = sale_df.copy() if sale_df is not None else pd.DataFrame()
        self.purchase_df = purchase_df.copy() if purchase_df is not None else pd.DataFrame()
        self.withholding_df = withholding_df.copy() if withholding_df is not None else pd.DataFrame()

        self.max_credit_days = max_credit_days
        self.sale_tolerance = sale_tolerance
        self.purchase_tolerance = purchase_tolerance
        self.column_mappings = expected_column_mappings or {} # Use empty dict if None

        # Sets to keep track of matched invoices (to avoid reuse)
        self.matched_sale_indexes: Set[int] = set()
        self.matched_purchase_indexes: Set[int] = set()
        self.matched_withholding_indexes: Set[int] = set()

        # Results for matched transactions
        self.matched_deposits: List[Dict] = []
        self.matched_withdrawals: List[Dict] = []

        # Add attributes to store counts for summary logging
        self.total_statement_entries = 0
        self.matched_statement_entries = 0
        self.unmatched_statement_entries = 0

        # Keep original index to ensure reports maintain original order if needed before sorting
        self.statement_df['original_index'] = self.statement_df.index
        self.sale_df['original_index'] = self.sale_df.index
        self.purchase_df['original_index'] = self.purchase_df.index
        self.withholding_df['original_index'] = self.withholding_df.index

        # Prepare data - handle potential errors
        try:
            self._prepare_data()
        except Exception as e:
            logger.error(f"Error during data preparation: {e}")
            # Depending on the error, decide if matching can proceed.
            # For now, we'll let it proceed, but matching might fail if data is bad.


    def _prepare_data(self) -> None:
        """Prepare the dataframes for matching"""
        logger.info("Preparing data for matching")

        # Define expected column names in the *processed* dataframes
        statement_cols = self.column_mappings.get('statement', {})
        sale_cols = self.column_mappings.get('sale_tax_report', {})
        purchase_cols = self.column_mappings.get('purchase_tax_report', {})
        withholding_cols = self.column_mappings.get('withholding_tax_report', {})

        # Ensure datetime columns are properly formatted and handle errors
        for df_name, df, date_col_en in [
            ('statement', self.statement_df, 'datetime'),
            ('sale', self.sale_df, 'date_of_sale_invoice'),
            ('purchase', self.purchase_df, 'date_of_purchase_invoice'),
            ('withholding', self.withholding_df, 'paid_date')
        ]:
            date_col = date_col_en # Use English name as column name in the *processed* DF
            if df is not None and not df.empty and date_col in df.columns:
                try:
                    # Attempt conversion, coercing errors to NaT (Not a Time)
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                    if df[date_col].isnull().any():
                         logger.warning(f"Found invalid date entries in {date_col} column of {df_name}_df after conversion.")
                    # logger.debug(f"Converted {date_col} in {df_name}_df to datetime")
                except Exception as e:
                    logger.error(f"Error converting {date_col} in {df_name}_df to datetime: {e}")

        # Ensure numeric columns are properly formatted and handle errors
        for df_name, df, num_cols_en in [
            ('statement', self.statement_df, ['amount', 'balance']),
            ('sale', self.sale_df, ['product_value', 'vat', 'total_amount', 'withholding_tax', 'net_amount']),
            ('purchase', self.purchase_df, ['product_value', 'vat', 'total_amount']),
            ('withholding', self.withholding_df, ['amount', 'withholding_tax', 'paid_amount'])
        ]:
             num_cols = num_cols_en # Use English names
             if df is not None and not df.empty:
                 for col in num_cols:
                     if col in df.columns:
                         try:
                             # Attempt conversion, coercing errors to NaN
                             # Ensure values are strings before replacing commas
                             df[col] = df[col].astype(str).str.replace(',', '', regex=False)
                             df[col] = pd.to_numeric(df[col], errors='coerce')
                             if df[col].isnull().any():
                                  logger.warning(f"Found invalid numeric entries in {col} column of {df_name}_df after conversion.")
                             # logger.debug(f"Converted {col} in {df_name}_df to numeric")
                         except Exception as e:
                             logger.error(f"Error converting {col} in {df_name}_df to numeric: {e}")

        # Ensure object columns are treated as strings
        # This helps preserve leading zeros in IDs and other text fields
        for df_name, df in [('statement', self.statement_df), ('sale', self.sale_df),
                           ('purchase', self.purchase_df), ('withholding', self.withholding_df)]:
            if df is not None and not df.empty:
                for col in df.columns:
                    # Check if the column dtype is 'object'
                    if df[col].dtype == 'object':
                        try:
                            df[col] = df[col].astype(str)
                            # logger.debug(f"Converted '{col}' in {df_name}_df to string")
                        except Exception as e:
                            logger.error(f"Error converting '{col}' in {df_name}_df to string: {e}")

        # Add matched status columns if they don't exist
        if 'matched' not in self.sale_df.columns:
            self.sale_df['matched'] = False # Use boolean
        else: # Ensure it's boolean True/False
             self.sale_df['matched'] = self.sale_df['matched'].astype(str).str.lower() == 'true'

        if 'matched' not in self.purchase_df.columns:
            self.purchase_df['matched'] = False # Use boolean
        else: # Ensure it's boolean True/False
             self.purchase_df['matched'] = self.purchase_df['matched'].astype(str).str.lower() == 'true'

        if 'matched' not in self.withholding_df.columns:
            self.withholding_df['matched'] = False # Use boolean
        else: # Ensure it's boolean True/False
             self.withholding_df['matched'] = self.withholding_df['matched'].astype(str).str.lower() == 'true'


        # Convert boolean isDeposit to actual boolean
        if 'isDeposit' in self.statement_df.columns:
            # Handle potential non-boolean string values like 'True', 'False', 'เงินฝาก', 'เงินถอน'
            # Assuming 'True' or 'เงินฝาก' means True
            self.statement_df['isDeposit'] = self.statement_df['isDeposit'].astype(str).str.lower().apply(lambda x: x == 'true' or x == 'เงินฝาก')
        else:
             logger.warning("Statement dataframe is missing 'isDeposit' column. Cannot proceed with matching.")
             self.statement_df = pd.DataFrame() # Clear statement_df if crucial column is missing
             return


        # Sort bank statement by date
        if not self.statement_df.empty and 'datetime' in self.statement_df.columns:
             self.statement_df = self.statement_df.sort_values(by='datetime').reset_index(drop=True) # Reset index after sort


        # Log info after preparation
        logger.debug(f"Prepared statement_df: {len(self.statement_df)} entries")
        logger.debug(f"Prepared sale_df: {len(self.sale_df)} entries")
        logger.debug(f"Prepared purchase_df: {len(self.purchase_df)} entries")
        logger.debug(f"Prepared withholding_df: {len(self.withholding_df)} entries")

    def _find_candidate_sales(self,
                              deposit_date: datetime,
                              deposit_amount: float) -> pd.DataFrame:
        """
        Find candidate sale invoices for a deposit within date window and tolerance.

        Args:
            deposit_date: Date of the deposit
            deposit_amount: Amount of the deposit

        Returns:
            DataFrame slice of candidate sale invoices (unmatched)
        """
        try:
            # Filter sales that aren't already matched
            unmatched_sales = self.sale_df[~self.sale_df['matched']].copy()

            if unmatched_sales.empty:
                 return unmatched_sales # Return empty if no unmatched sales

            # Filter by date range
            # Invoice date should be within max_credit_days before or after deposit date
            # Note: The requirement specifically said "Invoice date and paid date can differ, but they should not exceed a 30-day credit. The paid date can be either before or after the invoice date."
            # This implies the _payment_ date (deposit_date) must be within 30 days of the invoice date.
            # So, invoice_date must be between deposit_date - 30 days and deposit_date + 30 days.
            date_filter = (unmatched_sales['date_of_sale_invoice'] >= (deposit_date - timedelta(days=self.max_credit_days))) & \
                          (unmatched_sales['date_of_sale_invoice'] <= (deposit_date + timedelta(days=self.max_credit_days)))

            candidates = unmatched_sales[date_filter].copy()

            if candidates.empty:
                 return candidates

            # Filter by amount (initial rough filter)
            # Amount must be somewhat close to deposit_amount or a fraction of it for combinations
            # A simple check is if the amount is within a larger range, e.g., deposit_amount * 2 or within deposit_amount + tolerance.
            # Let's refine the amount check: filter candidates whose net_amount is within a reasonable range, say 0 to deposit_amount + sale_tolerance.
            # This allows for single matches or invoices that are part of a combination summing up to the deposit amount.
            amount_filter = (candidates['net_amount'] >= 0) & (candidates['net_amount'] <= (deposit_amount + self.sale_tolerance))

            candidates = candidates[amount_filter].copy()

            # logger.debug(f"Found {len(candidates)} sales candidates for deposit {deposit_amount}")
            return candidates
        except Exception as e:
            logger.error(f"Exception: {e}")
            return pd.DataFrame()

    def _find_candidate_withholdings(self,
                                     deposit_date: datetime,
                                     deposit_amount: float) -> pd.DataFrame:
        """
        Find candidate withholding tax entries for a deposit within date window and tolerance.

        Args:
            deposit_date: Date of the deposit
            deposit_amount: Amount of the deposit

        Returns:
            DataFrame slice of candidate withholding tax entries (unmatched)
        """
        try:
            # Filter withholdings that aren't already matched
            unmatched_withholdings = self.withholding_df[~self.withholding_df['matched']].copy()

            if unmatched_withholdings.empty:
                return unmatched_withholdings

            # Filter by date - stricter date match requested (within 3 days)(+ or - days)
            date_filter = (unmatched_withholdings['paid_date'] >= (deposit_date - timedelta(days=3))) & \
                          (unmatched_withholdings['paid_date'] <= (deposit_date + timedelta(days=3)))

            candidates = unmatched_withholdings[date_filter].copy()

            if candidates.empty:
                return candidates

            # Filter by amount (within tolerance)
            amount_filter = abs(candidates['paid_amount'] - deposit_amount) <= self.sale_tolerance

            candidates = candidates[amount_filter].copy()

            # logger.debug(f"Found {len(candidates)} withholding candidates for deposit {deposit_amount}")
            return candidates
        except Exception as e:
            logger.error(f"Exception in finding candidate withholdings: {e}")
            return pd.DataFrame()

    def _find_candidate_purchases(self,
                                 withdrawal_date: datetime,
                                 withdrawal_amount: float) -> pd.DataFrame:
        """
        Find candidate purchase invoices for a withdrawal within date window and tolerance.

        Args:
            withdrawal_date: Date of the withdrawal
            withdrawal_amount: Amount of the withdrawal

        Returns:
            List of indices of candidate purchase invoices
        """
        try:
            # Filter purchases that aren't already matched
            unmatched_purchases = self.purchase_df[~self.purchase_df['matched']].copy()

            if unmatched_purchases.empty:
                return unmatched_purchases

            # Filter by date range (withdrawal_date >= invoice_date and diff <= max_credit_days)
            date_filter = (unmatched_purchases['date_of_purchase_invoice'] <= withdrawal_date) & \
                          ((withdrawal_date - unmatched_purchases['date_of_purchase_invoice']).dt.days <= self.max_credit_days)

            candidates = unmatched_purchases[date_filter].copy()

            if candidates.empty:
                return candidates

            # Filter by amount (within tolerance)
            amount_filter = abs(candidates['total_amount'] - withdrawal_amount) <= self.purchase_tolerance

            candidates = candidates[amount_filter].copy()

            # logger.debug(f"Found {len(candidates)} purchase candidates for withdrawal {withdrawal_amount}")
            return candidates
        except Exception as e:
            logger.error(f"Exception in finding candidate purchases: {e}")
            return pd.DataFrame()

    def _find_sale_combinations(self,
                               company_sales_candidates: pd.DataFrame,
                               deposit_amount: float) -> Optional[List[int]]:
        """
        Find a combination of sales from a single company that sums to deposit amount within tolerance.
        Prioritizes smaller combinations.

        Args:
            company_sales_candidates: DataFrame slice of candidate sales for a specific company
            deposit_amount: Amount of the deposit

        Returns:
            List of indices of sale invoices that sum to deposit amount, or None if no combination found.
        """
        try:
            if company_sales_candidates.empty:
                return None

            # Sort candidates by net_amount descending? Or ascending? Descending might find larger invoices first.
            # Let's try sorting by date descending to find recent invoices first.
            company_sales_candidates = company_sales_candidates.sort_values(by='date_of_sale_invoice', ascending=False).copy()

            # Try combinations up to size 3 (a practical limit)
            for combo_size in range(1, min(4, len(company_sales_candidates) + 1)):
                for indices in itertools.combinations(company_sales_candidates.index, combo_size):
                    current_combination_sales = company_sales_candidates.loc[list(indices)]
                    total_amount = current_combination_sales['net_amount'].sum()

                    if abs(total_amount - deposit_amount) <= self.sale_tolerance:
                        logger.debug(f"  - Found combination match (size {combo_size}) for deposit {deposit_amount}: Indices {list(indices)}, Sum {total_amount:.2f}")
                        return list(indices) # Return the indices of the matched combination

            return None # No combination found within the tolerance and size limit
        except Exception as e:
            logger.error(f"Exception: {e}")
            return None

    def _match_deposit(self, statement_idx: int) -> Dict:
        """
        Match a deposit with sale invoices and/or withholding entries.

        Args:
            statement_idx: Index of the deposit in statement_df

        Returns:
            Dictionary with matching information
        """
        try:
            deposit_row = self.statement_df.loc[statement_idx] # Use .loc as index might not be 0-based after sort
            deposit_date = deposit_row['datetime']
            deposit_amount = float(deposit_row['amount']) # Ensure float

            matched_info = {
                'statement_idx': statement_idx,
                'deposit_date': deposit_date,
                'deposit_amount': deposit_amount,
                'matched_sales_indices': [], # Store indices
                'matched_withholdings_indices': [], # Store indices
                'companies': set(),
                'total_matched_amount': 0.0,
                'difference': deposit_amount,  # Initialize with full amount
                'is_matched': False,
                'match_type': 'None' # 'Sale', 'Withholding', 'Sale+Withholding', 'Combination Sale'
            }

            logger.debug(f"Attempting to match deposit: statement_idx={statement_idx}, Date={deposit_date.strftime('%y-%m-%d')}, Amount={deposit_amount:.2f}")

            # --- Strategy: Prioritize matches ---
            # 1. Look for single exact/tolerance match in Sales
            # 2. Look for combination match in Sales (same company)
            # 3. Look for single exact/tolerance match in Withholding (as a fallback if sales are missing or don't match)

            candidate_sales = self._find_candidate_sales(deposit_date, deposit_amount)

            # Filter sales candidates by company to prepare for combination matching
            sales_candidates_by_company = {}
            if not candidate_sales.empty:
                for company_name, group in candidate_sales.groupby('company_name'):
                    sales_candidates_by_company[company_name] = group.copy() # Use copy to avoid SettingWithCopyWarning

            # --- Attempt 1: Single Sale Match ---
            single_sale_match_found = False
            if not candidate_sales.empty:
                for idx, sale_row in candidate_sales.iterrows():
                    sale_amount = float(sale_row['net_amount'])
                    if abs(sale_amount - deposit_amount) <= self.sale_tolerance:
                        # Found a potential single sale match
                        if idx not in self.matched_sale_indexes: # Ensure it's not already matched elsewhere
                            self.matched_sale_indexes.add(idx)
                            self.sale_df.loc[idx, 'matched'] = True # Use .loc for index assignment

                            matched_info['matched_sales_indices'].append(idx)
                            matched_info['companies'].add(str(sale_row['company_name']))
                            matched_info['total_matched_amount'] = sale_amount
                            matched_info['difference'] = deposit_amount - sale_amount
                            matched_info['is_matched'] = True
                            matched_info['match_type'] = 'Sale (Single)'

                            logger.debug(f"  - Found single sale match: Index={idx}, Invoice='{sale_row['sale_invoice_tax_number']}', Amount={sale_amount:.2f}")
                            single_sale_match_found = True
                            break # Stop after finding the first single match

            # --- Attempt 2: Sale Combination Match (if no single match found) ---
            if not single_sale_match_found and not candidate_sales.empty:
                for company_name, company_candidates in sales_candidates_by_company.items():
                    # Filter out candidates already matched in the single-match attempt (shouldn't happen with the check above, but good practice)
                    eligible_company_candidates = company_candidates[~company_candidates.index.isin(self.matched_sale_indexes)].copy()

                    matched_indices = self._find_sale_combinations(eligible_company_candidates, deposit_amount)

                    if matched_indices:
                        # Found a combination match
                        total_amount = 0.0
                        for idx in matched_indices:
                             if idx not in self.matched_sale_indexes: # Double check, though _find_sale_combinations should use eligible ones
                                self.matched_sale_indexes.add(idx)
                                self.sale_df.loc[idx, 'matched'] = True # Use .loc
                                matched_info['matched_sales_indices'].append(idx)
                                total_amount += float(self.sale_df.loc[idx, 'net_amount'])

                        matched_info['companies'].add(str(company_name))
                        matched_info['total_matched_amount'] = total_amount
                        matched_info['difference'] = deposit_amount - total_amount
                        matched_info['is_matched'] = True
                        matched_info['match_type'] = 'Sale (Combination)'

                        logger.debug(f"  - Found combination sale match for company '{company_name}': Indices={matched_info['matched_sales_indices']}, Sum={matched_info['total_matched_amount']:.2f}")
                        break # Stop after finding the first combination match for any company

            # --- Attempt 3: Withholding Match (as a fallback or confirmation) ---
            # If a Sale match (single or combination) was found, try to find a *confirming* withholding match from the same company.
            # If *no* Sale match was found, try to match against Withholding *directly* as a fallback.

            candidate_withholdings = self._find_candidate_withholdings(deposit_date, deposit_amount)

            if not candidate_withholdings.empty:
                 for with_idx, with_row in candidate_withholdings.iterrows():
                     if with_idx in self.matched_withholding_indexes: # Ensure not already matched
                         continue

                     with_amount = float(with_row['paid_amount'])

                     # Check if it's a potential match (within tolerance, already filtered by date)
                     if abs(with_amount - deposit_amount) <= self.sale_tolerance:
                         # This withholding entry is a candidate

                         if matched_info['is_matched']:
                             # A Sale match was already found. Is this withholding entry from one of the matched companies?
                             with_company = str(with_row['company_name']).strip()
                             with_tax_id = str(with_row['tax_id']).strip()

                             # Check if the withholding company/tax ID matches any of the matched sales' company/tax ID
                             company_match_found = False
                             for sale_idx in matched_info['matched_sales_indices']:
                                 sale_row = self.sale_df.loc[sale_idx]
                                 sale_company = str(sale_row['company_name']).strip()
                                 sale_tax_id = str(sale_row['company_tax_id']).strip()
                                 # Allow matching either by name or tax ID
                                 if (with_company and with_company == sale_company) or \
                                    (with_tax_id and with_tax_id == sale_tax_id):
                                     company_match_found = True
                                     break # Found a matching company for this withholding

                             if company_match_found:
                                # Found a confirming withholding match
                                self.matched_withholding_indexes.add(with_idx)
                                self.withholding_df.loc[with_idx, 'matched'] = True # Use .loc
                                matched_info['matched_withholdings_indices'].append(with_idx)
                                # Add company if not already added (e.g., from sale)
                                if with_company:
                                     matched_info['companies'].add(with_company)
                                # No need to update total_matched_amount or difference if a sale match was primary
                                matched_info['match_type'] = matched_info.get('match_type', 'Sale') + '+Withholding' # Indicate confirmation
                                logger.debug(f"  - Found confirming withholding match: Index={with_idx}, Company='{with_row['company_name']}', Amount={with_amount:.2f}")
                                # Keep looking for other confirming withholdings if multiple sales were matched?
                                # For simplicity, let's just take the first confirming withholding for now.
                                break

                         else:
                             # No Sale match was found. This withholding entry is a potential *fallback* match.
                             # Treat this as the primary match if it's within tolerance and date range (already filtered)
                             self.matched_withholding_indexes.add(with_idx)
                             self.withholding_df.loc[with_idx, 'matched'] = True # Use .loc

                             matched_info['matched_withholdings_indices'].append(with_idx)
                             matched_info['companies'].add(str(with_row['company_name']))
                             matched_info['total_matched_amount'] = with_amount
                             matched_info['difference'] = deposit_amount - with_amount
                             matched_info['is_matched'] = True
                             matched_info['match_type'] = 'Withholding (Fallback)'

                             logger.debug(f"  - Found fallback withholding match: Index={with_idx}, Company='{with_row['company_name']}', Amount={with_amount:.2f}")
                             # If we match via withholding fallback, we stop looking for sales for this deposit
                             return matched_info # Return immediately after fallback match

            # Final check if any match was found
            if not matched_info['is_matched']:
                 logger.debug(f"  - No match found for deposit on {deposit_date.strftime('%y-%m-%d')} for amount {deposit_amount:.2f}")
            else:
                 logger.debug(f"  - Deposit matched: Type='{matched_info['match_type']}', Matched Amount={matched_info['total_matched_amount']:.2f}, Diff={matched_info['difference']:.2f}")

            return matched_info
        except Exception as e:
            logger.error(f"Exception in matching deposit: {e}")
            return {
                'statement_idx': statement_idx,
                'deposit_date': None,
                'deposit_amount': None,
                'matched_sales_indices': [],
                'matched_withholdings_indices': [],
                'companies': set(),
                'total_matched_amount': 0.0,
                'difference': 0.0,
                'is_matched': False,
                'match_type': 'Error'
            }

    def _match_withdrawal(self, statement_idx: int) -> Dict:
        """
        Match a withdrawal with purchase invoices.

        Args:
            withdrawal_idx: Index of the withdrawal in statement_df

        Returns:
            Dictionary with matching information
        """
        withdrawal_row = self.statement_df.loc[statement_idx] # Use .loc
        withdrawal_date = withdrawal_row['datetime']
        withdrawal_amount = abs(float(withdrawal_row['amount']))  # Ensure positive float

        matched_info = {
            'statement_idx': statement_idx,
            'withdrawal_date': withdrawal_date,
            'withdrawal_amount': withdrawal_amount,
            'matched_purchases_indices': [], # Store indices
            'companies': set(),
            'total_matched_amount': 0.0,
            'difference': withdrawal_amount,  # Initialize with full amount
            'is_matched': False,
            'match_type': 'None'
        }

        logger.debug(f"Attempting to match withdrawal: statement_idx={statement_idx}, Date={withdrawal_date.strftime('%y-%m-%d')}, Amount={withdrawal_amount:.2f}")

        candidate_purchases = self._find_candidate_purchases(withdrawal_date, withdrawal_amount)

        # Look for single matches first (most common)
        if not candidate_purchases.empty:
            # Sort candidates by date descending to find recent purchases first
            candidate_purchases = candidate_purchases.sort_values(by='date_of_purchase_invoice', ascending=False)

            for idx, purchase_row in candidate_purchases.iterrows():
                purchase_amount = float(purchase_row['total_amount'])

                # Check if this is a match within tolerance
                if abs(purchase_amount - withdrawal_amount) <= self.purchase_tolerance:
                     # Found a potential single purchase match
                     if idx not in self.matched_purchase_indexes: # Ensure it's not already matched elsewhere
                         self.matched_purchase_indexes.add(idx)
                         self.purchase_df.loc[idx, 'matched'] = True # Use .loc

                         matched_info['matched_purchases_indices'].append(idx)
                         matched_info['companies'].add(str(purchase_row['company_name']))
                         matched_info['total_matched_amount'] = purchase_amount
                         matched_info['difference'] = withdrawal_amount - purchase_amount
                         matched_info['is_matched'] = True
                         matched_info['match_type'] = 'Purchase (Single)'

                         logger.debug(f"  - Found single purchase match: Index={idx}, Invoice='{purchase_row['purchase_invoice_id']}', Amount={purchase_amount:.2f}")
                         return matched_info # Return after finding the first single match


        # Note: Combinations for purchases are not explicitly requested, only for sales.
        # If combination matching for purchases was needed, a similar logic to _find_sale_combinations
        # would be implemented here, but using 'total_amount' and purchase_tolerance.
        # Sticking to single match as per requirement.


        # No match found
        if not matched_info['is_matched']:
            logger.debug(f"  - No match found for withdrawal on {withdrawal_date.strftime('%y-%m-%d')} for amount {withdrawal_amount:.2f}")

        return matched_info


    def match_transactions(self) -> None:
        """Match all transactions in the statement with invoices"""
        logger.info(f"Starting transaction matching process (max_credit_days={self.max_credit_days}, sale_tolerance={self.sale_tolerance}, purchase_tolerance={self.purchase_tolerance})")

        if self.statement_df.empty:
            logger.warning("Statement dataframe is empty. Skipping matching.")
            return
        if self.sale_df.empty and self.purchase_df.empty and self.withholding_df.empty:
             logger.warning("All invoice/tax dataframes are empty. Skipping matching.")
             return

        # Iterate through statement entries
        # We process in order of statement date, which was sorted in _prepare_data
        for idx in self.statement_df.index: # zero-indexed
            try:
                row = self.statement_df.loc[idx]
                if row['isDeposit']:
                    match_result = self._match_deposit(idx)
                    # Append all deposits to the results list, mark if matched
                    self.matched_deposits.append(match_result)
                    if match_result['is_matched']:
                         self.matched_statement_entries += 1
                else: # isWithdrawal
                    match_result = self._match_withdrawal(idx)
                     # Append all withdrawals to the results list, mark if matched
                    self.matched_withdrawals.append(match_result)
                    if match_result['is_matched']:
                         self.matched_statement_entries += 1
            except Exception as e:
                logger.error(f"Error processing statement entry at index {idx}: {e}")
                # Decide if to continue or stop on error. Continuing for robustness.

        self.total_statement_entries = len(self.statement_df)
        self.unmatched_statement_entries = self.total_statement_entries - self.matched_statement_entries

        logger.info(f"Transaction matching completed.")

        logger.info(f"Summary:")
        logger.info(f" - Total statement entries: {self.total_statement_entries}")
        matched_pct = (self.matched_statement_entries/self.total_statement_entries * 100) if self.total_statement_entries > 0 else 0.0
        unmatched_pct = (self.unmatched_statement_entries/self.total_statement_entries * 100) if self.total_statement_entries > 0 else 0.0
        logger.info(f" - Matched statement entries: {self.matched_statement_entries} ({matched_pct:.1f}%)")
        logger.info(f" - Unmatched statement entries: {self.unmatched_statement_entries} ({unmatched_pct:.1f}%)")
        
        # Log matched counts and percentages
        sale_matched = len(self.matched_sale_indexes)
        sale_total = len(self.sale_df) if not self.sale_df.empty else 0
        sale_unmatched = sale_total - sale_matched
        sale_matched_pct = (sale_matched/sale_total * 100) if sale_total > 0 else 0
        sale_unmatched_pct = (sale_unmatched/sale_total * 100) if sale_total > 0 else 0
        
        purchase_matched = len(self.matched_purchase_indexes)
        purchase_total = len(self.purchase_df) if not self.purchase_df.empty else 0
        purchase_unmatched = purchase_total - purchase_matched
        purchase_matched_pct = (purchase_matched/purchase_total * 100) if purchase_total > 0 else 0
        purchase_unmatched_pct = (purchase_unmatched/purchase_total * 100) if purchase_total > 0 else 0
        
        withholding_matched = len(self.matched_withholding_indexes)
        withholding_total = len(self.withholding_df) if not self.withholding_df.empty else 0
        withholding_unmatched = withholding_total - withholding_matched
        withholding_matched_pct = (withholding_matched/withholding_total * 100) if withholding_total > 0 else 0
        withholding_unmatched_pct = (withholding_unmatched/withholding_total * 100) if withholding_total > 0 else 0

        logger.info(f" - Sale invoices: {sale_matched}/{sale_total} matched ({sale_matched_pct:.1f}%), {sale_unmatched} unmatched ({sale_unmatched_pct:.1f}%)")
        logger.info(f" - Purchase invoices: {purchase_matched}/{purchase_total} matched ({purchase_matched_pct:.1f}%), {purchase_unmatched} unmatched ({purchase_unmatched_pct:.1f}%)")
        logger.info(f" - Withholding entries: {withholding_matched}/{withholding_total} matched ({withholding_matched_pct:.1f}%), {withholding_unmatched} unmatched ({withholding_unmatched_pct:.1f}%)")


    def _get_thai_col_name(self, report_type: str, english_name: str) -> str:
        """Helper to get Thai column name from mappings"""
        return self.column_mappings.get(report_type, {}).get(english_name, english_name)

    def generate_transaction_match_report(self) -> pd.DataFrame:
        """
        Generate a report of matched transactions (deposits and withdrawals).

        Returns:
            DataFrame containing transaction match information.
            Includes both matched deposits and withdrawals, sorted by statement date.
        """
        start_time = time.time()
        logger.info("Generating transaction match report...")

        match_rows = []

        # Combine matched deposits and withdrawals for sorting
        # Iterate through all statement entries in their original order
        # Sort by original_index to maintain original file order before final date sort
        statement_sorted_by_original_index = self.statement_df.sort_values(by='original_index').reset_index(drop=True)

        for statement_idx, statement_row in statement_sorted_by_original_index.iterrows():
            original_statement_index = statement_row.get('original_index', statement_idx)
            is_deposit = statement_row['isDeposit']
            txn_date = statement_row['datetime']
            txn_amount = float(statement_row['amount'])

            # Find the corresponding match info if it exists
            match_info = None
            if is_deposit:
                # Search in matched_deposits
                for match in self.matched_deposits:
                    # Use original_index for lookup as statement_df might be re-indexed after sorting
                    if self.statement_df.loc[match['statement_idx']].get('original_index', match['statement_idx']) == original_statement_index:
                         match_info = match
                         break
            else: # isWithdrawal
                # Search in matched_withdrawals
                for match in self.matched_withdrawals:
                    # Use original_index for lookup
                    if self.statement_df.loc[match['statement_idx']].get('original_index', match['statement_idx']) == original_statement_index:
                         match_info = match
                         break

            # Populate report row
            row_data = {
                self._get_thai_col_name('transaction_match_report', 'original_statement_index'): original_statement_index,
                self._get_thai_col_name('transaction_match_report', 'transaction_type'): 'เงินฝาก' if is_deposit else 'เงินถอน',
                self._get_thai_col_name('transaction_match_report', 'transaction_date'): txn_date,
                self._get_thai_col_name('transaction_match_report', 'withdrawal_amount'): txn_amount if not is_deposit else 0.0,
                self._get_thai_col_name('transaction_match_report', 'deposit_amount'): txn_amount if is_deposit else 0.0,
                self._get_thai_col_name('transaction_match_report', 'matched_companies'): "",
                self._get_thai_col_name('transaction_match_report', 'sale_tax_ids'): "",
                self._get_thai_col_name('transaction_match_report', 'sale_invoice_numbers'): "",
                self._get_thai_col_name('transaction_match_report', 'purchase_tax_ids'): "",
                self._get_thai_col_name('transaction_match_report', 'purchase_invoice_numbers'): "",
                self._get_thai_col_name('transaction_match_report', 'withholding_paid_dates'): "",
                self._get_thai_col_name('transaction_match_report', 'total_matched_amount'): 0.0,
                self._get_thai_col_name('transaction_match_report', 'difference'): txn_amount, # Initialize difference with full amount
                self._get_thai_col_name('transaction_match_report', 'match_type'): "Unmatched",
            }

            if match_info:
                row_data[self._get_thai_col_name('transaction_match_report', 'matched_companies')] = " , ".join(sorted(list(match_info.get('companies', set()))))
                row_data[self._get_thai_col_name('transaction_match_report', 'total_matched_amount')] = match_info['total_matched_amount']
                row_data[self._get_thai_col_name('transaction_match_report', 'difference')] = match_info['difference']
                row_data[self._get_thai_col_name('transaction_match_report', 'match_type')] = match_info['match_type']

                if is_deposit:
                    # Populate sale and withholding details for deposits
                    sale_invoice_tax_numbers = []
                    sale_tax_ids = []
                    for sale_idx in match_info.get('matched_sales_indices', []):
                         if sale_idx in self.sale_df.index:
                            sale_row = self.sale_df.loc[sale_idx]
                            sale_invoice_tax_numbers.append(str(sale_row.get('sale_invoice_tax_number', 'N/A')))
                            sale_tax_ids.append(str(sale_row.get('company_tax_id', 'N/A')))
                    row_data[self._get_thai_col_name('transaction_match_report', 'sale_tax_ids')] = " , ".join(sale_tax_ids)
                    row_data[self._get_thai_col_name('transaction_match_report', 'sale_invoice_numbers')] = " , ".join(sale_invoice_tax_numbers)

                    withholding_paid_dates = []
                    for with_idx in match_info.get('matched_withholdings_indices', []):
                         if with_idx in self.withholding_df.index:
                             with_row = self.withholding_df.loc[with_idx]
                             paid_date = with_row.get('paid_date')
                             withholding_paid_dates.append(paid_date.strftime('%y-%m-%d') if pd.notna(paid_date) else "")
                    row_data[self._get_thai_col_name('transaction_match_report', 'withholding_paid_dates')] = " , ".join(withholding_paid_dates)

                else: # isWithdrawal
                    # Populate purchase details for withdrawals
                    purchase_invoice_ids = []
                    purchase_tax_ids = []
                    for purchase_idx in match_info.get('matched_purchases_indices', []):
                         if purchase_idx in self.purchase_df.index:
                            purchase_row = self.purchase_df.loc[purchase_idx]
                            purchase_invoice_ids.append(str(purchase_row.get('purchase_invoice_id', 'N/A')))
                            purchase_tax_ids.append(str(purchase_row.get('company_tax_id', 'N/A')))
                    row_data[self._get_thai_col_name('transaction_match_report', 'purchase_tax_ids')] = " , ".join(purchase_tax_ids)
                    row_data[self._get_thai_col_name('transaction_match_report', 'purchase_invoice_numbers')] = " , ".join(purchase_invoice_ids)


            match_rows.append(row_data)

        if not match_rows:
            logger.warning("No matches found for transaction report")
            # Return an empty DataFrame with expected columns
            thai_cols = [
                self._get_thai_col_name('transaction_match_report', 'original_statement_index'),
                self._get_thai_col_name('transaction_match_report', 'transaction_type'),
                self._get_thai_col_name('transaction_match_report', 'transaction_date'),
                self._get_thai_col_name('transaction_match_report', 'withdrawal_amount'),
                self._get_thai_col_name('transaction_match_report', 'deposit_amount'),
                self._get_thai_col_name('transaction_match_report', 'matched_companies'),
                self._get_thai_col_name('transaction_match_report', 'sale_tax_ids'),
                self._get_thai_col_name('transaction_match_report', 'sale_invoice_numbers'),
                self._get_thai_col_name('transaction_match_report', 'purchase_tax_ids'),
                self._get_thai_col_name('transaction_match_report', 'purchase_invoice_numbers'),
                self._get_thai_col_name('transaction_match_report', 'withholding_paid_dates'),
                self._get_thai_col_name('transaction_match_report', 'total_matched_amount'),
                self._get_thai_col_name('transaction_match_report', 'difference'),
                self._get_thai_col_name('transaction_match_report', 'match_type'),
            ]
            return pd.DataFrame(columns=thai_cols)


        match_df = pd.DataFrame(match_rows)

        # Convert date column to datetime *before* saving so save_dataframe can format it
        date_col_thai = self._get_thai_col_name('transaction_match_report', 'transaction_date')
        if date_col_thai in match_df.columns:
             # Convert back to datetime objects temporarily for sorting
             try:
                 match_df[date_col_thai] = pd.to_datetime(match_df[date_col_thai], errors='coerce')
             except Exception as e:
                 logger.error(f"Error converting {date_col_thai} column to datetime: {e}")
                 # Return empty DF with expected columns
                 return pd.DataFrame(columns=thai_cols)
             # Sort by date
             match_df = match_df.sort_values(by=date_col_thai).reset_index(drop=True)
             # Dates will be formatted to 'yy-mm-dd' by save_dataframe

        elapsed_time = time.time() - start_time
        logger.info(f"Transaction match report generated in {elapsed_time:.2f} seconds.")
        return match_df

    def generate_sale_match_report(self) -> pd.DataFrame:
        """
        Generate a report of sale invoices with match status.

        Returns:
            DataFrame containing sale invoice match information (matched/unmatched),
            sorted by invoice date.
        """
        start_time = time.time()
        logger.info("Generating sale match status report...")

        if self.sale_df.empty:
            logger.warning("Sale dataframe is empty. Cannot generate sale match report.")
            # Return an empty DataFrame with expected columns
            thai_cols = [
                self._get_thai_col_name('sale_tax_report', 'order_number'),
                self._get_thai_col_name('sale_tax_report', 'date_of_sale_invoice'),
                self._get_thai_col_name('sale_tax_report', 'sale_invoice_tax_number'),
                self._get_thai_col_name('sale_tax_report', 'company_name'),
                self._get_thai_col_name('sale_tax_report', 'company_tax_id'),
                self._get_thai_col_name('sale_tax_report', 'product_value'),
                self._get_thai_col_name('sale_tax_report', 'vat'),
                self._get_thai_col_name('sale_tax_report', 'total_amount'),
                self._get_thai_col_name('sale_tax_report', 'withholding_tax'),
                self._get_thai_col_name('sale_tax_report', 'net_amount'),
                self._get_thai_col_name('sale_tax_report', 'matched'),
                self._get_thai_col_name('sale_tax_report', 'days_outstanding'), # Keep original column if present
            ]
            return pd.DataFrame(columns=thai_cols)


        # Create a copy to work on
        sale_report = self.sale_df.copy()

        # Map boolean 'matched' status to Thai strings
        sale_report[self._get_thai_col_name('sale_tax_report', 'matched')] = sale_report['matched'].map({True: 'ใช่', False: 'ไม่'})

        # Add original index back for sorting based on original file order if needed,
        # but requirement is to sort by date. Let's keep original_index for reference.
        sale_report[self._get_thai_col_name('sale_tax_report', 'original_index')] = sale_report['original_index']


        # Select and rename columns using the mappings
        thai_cols_mapping = {v: k for k, v in self.column_mappings.get('sale_tax_report', {}).items()} # Invert mapping for easy renaming
        # Add 'matched' and 'original_index' which might not be in the original mapping
        thai_cols_mapping[self._get_thai_col_name('sale_tax_report', 'matched')] = 'matched_status_thai'
        thai_cols_mapping[self._get_thai_col_name('sale_tax_report', 'original_index')] = 'original_index'


        # Build the report DataFrame with Thai columns directly
        report_data = {}
        for eng_col, thai_col in self.column_mappings.get('sale_tax_report', {}).items():
             if eng_col in sale_report.columns:
                 report_data[thai_col] = sale_report[eng_col]
             else:
                 logger.warning(f"Sale report: English column '{eng_col}' not found in processed sale_df.")
                 report_data[thai_col] = None # Add empty column if missing

        # Add the 'matched' status and original index columns
        report_data[self._get_thai_col_name('sale_tax_report', 'matched')] = sale_report[self._get_thai_col_name('sale_tax_report', 'matched')]
        report_data[self._get_thai_col_name('sale_tax_report', 'original_index')] = sale_report[self._get_thai_col_name('sale_tax_report', 'original_index')]

        # Include 'days_outstanding' if it exists in the original sale_df
        days_outstanding_col = self._get_thai_col_name('sale_tax_report', 'days_outstanding')
        if 'days_outstanding' in sale_report.columns:
            report_data[days_outstanding_col] = sale_report['days_outstanding']
        else:
             logger.warning("Sale report: English column 'days_outstanding' not found in processed sale_df.")
             report_data[days_outstanding_col] = None


        final_report = pd.DataFrame(report_data)

        # Ensure correct dtypes before sorting and saving
        # Date column must be datetime for sorting and save_dataframe formatting
        date_col_thai = self._get_thai_col_name('sale_tax_report', 'date_of_sale_invoice')
        if date_col_thai in final_report.columns:
            try:
                final_report[date_col_thai] = pd.to_datetime(final_report[date_col_thai], errors='coerce')
            except Exception as e:
                logger.error(f"Error converting {date_col_thai} column to datetime: {e}")
                # Return empty DF with expected columns
                return pd.DataFrame(columns=thai_cols)

        # Numeric columns should be numeric for rounding by save_dataframe
        numeric_cols_thai = [
             self._get_thai_col_name('sale_tax_report', 'product_value'),
             self._get_thai_col_name('sale_tax_report', 'vat'),
             self._get_thai_col_name('sale_tax_report', 'total_amount'),
             self._get_thai_col_name('sale_tax_report', 'withholding_tax'),
             self._get_thai_col_name('sale_tax_report', 'net_amount'),
        ]
        for col in numeric_cols_thai:
             if col in final_report.columns:
                  try:
                      final_report[col] = pd.to_numeric(final_report[col], errors='coerce')
                  except Exception as e:
                      logger.error(f"Error converting {col} column to numeric: {e}")
                      # Return empty DF with expected columns
                      return pd.DataFrame(columns=thai_cols)


        # Sort by date
        if date_col_thai in final_report.columns:
            final_report = final_report.sort_values(by=date_col_thai).reset_index(drop=True)

        elapsed_time = time.time() - start_time
        logger.info(f"Sale match status report generated in {elapsed_time:.2f} seconds.")
        return final_report

    def generate_purchase_match_report(self) -> pd.DataFrame:
        """
        Generate a report of purchase invoices with match status.

        Returns:
            DataFrame containing purchase invoice match information (matched/unmatched),
            sorted by invoice date.
        """
        start_time = time.time()
        logger.info("Generating purchase match status report...")

        if self.purchase_df.empty:
            logger.warning("Purchase dataframe is empty. Cannot generate purchase match report.")
            # Return an empty DataFrame with expected columns
            thai_cols = [
                self._get_thai_col_name('purchase_tax_report', 'order_number'),
                self._get_thai_col_name('purchase_tax_report', 'date_of_purchase_invoice'),
                self._get_thai_col_name('purchase_tax_report', 'purchase_invoice_tax_number'),
                self._get_thai_col_name('purchase_tax_report', 'purchase_invoice_id'),
                self._get_thai_col_name('purchase_tax_report', 'company_name'),
                self._get_thai_col_name('purchase_tax_report', 'company_tax_id'),
                self._get_thai_col_name('purchase_tax_report', 'product_value'),
                self._get_thai_col_name('purchase_tax_report', 'vat'),
                self._get_thai_col_name('purchase_tax_report', 'total_amount'),
                self._get_thai_col_name('purchase_tax_report', 'matched'),
            ]
            return pd.DataFrame(columns=thai_cols)


        # Create a copy to work on
        purchase_report = self.purchase_df.copy()

        # Map boolean 'matched' status to Thai strings
        purchase_report[self._get_thai_col_name('purchase_tax_report', 'matched')] = purchase_report['matched'].map({True: 'ใช่', False: 'ไม่'})

        # Add original index back for reference
        purchase_report[self._get_thai_col_name('purchase_tax_report', 'original_index')] = purchase_report['original_index']


        # Build the report DataFrame with Thai columns directly
        report_data = {}
        for eng_col, thai_col in self.column_mappings.get('purchase_tax_report', {}).items():
             if eng_col in purchase_report.columns:
                 report_data[thai_col] = purchase_report[eng_col]
             else:
                 logger.warning(f"Purchase report: English column '{eng_col}' not found in processed purchase_df.")
                 report_data[thai_col] = None # Add empty column if missing

        # Add the 'matched' status and original index columns
        report_data[self._get_thai_col_name('purchase_tax_report', 'matched')] = purchase_report[self._get_thai_col_name('purchase_tax_report', 'matched')]
        report_data[self._get_thai_col_name('purchase_tax_report', 'original_index')] = purchase_report[self._get_thai_col_name('purchase_tax_report', 'original_index')]


        final_report = pd.DataFrame(report_data)


        # Ensure correct dtypes before sorting and saving
        # Date column must be datetime for sorting and save_dataframe formatting
        date_col_thai = self._get_thai_col_name('purchase_tax_report', 'date_of_purchase_invoice')
        if date_col_thai in final_report.columns:
            try:
                final_report[date_col_thai] = pd.to_datetime(final_report[date_col_thai], errors='coerce')
            except Exception as e:
                logger.error(f"Error converting {date_col_thai} column to datetime: {e}")
                # Return empty DF with expected columns
                return pd.DataFrame(columns=thai_cols)


        # Numeric columns should be numeric for rounding by save_dataframe
        numeric_cols_thai = [
             self._get_thai_col_name('purchase_tax_report', 'product_value'),
             self._get_thai_col_name('purchase_tax_report', 'vat'),
             self._get_thai_col_name('purchase_tax_report', 'total_amount'),
        ]
        for col in numeric_cols_thai:
             if col in final_report.columns:
                  try:
                      final_report[col] = pd.to_numeric(final_report[col], errors='coerce')
                  except Exception as e:
                      logger.error(f"Error converting {col} column to numeric: {e}")
                      # Return empty DF with expected columns
                      return pd.DataFrame(columns=thai_cols)


        # Sort by date
        if date_col_thai in final_report.columns:
            try:
                final_report = final_report.sort_values(by=date_col_thai).reset_index(drop=True)
            except Exception as e:
                logger.error(f"Error sorting by {date_col_thai}: {e}")
                # Return empty DF with expected columns
                return pd.DataFrame(columns=thai_cols)

        elapsed_time = time.time() - start_time
        logger.info(f"Purchase match status report generated in {elapsed_time:.2f} seconds.")
        return final_report

    def generate_withholding_match_report(self) -> pd.DataFrame:
        """
        Generate a report of withholding tax entries with match status.

        Returns:
            DataFrame containing withholding tax match information (matched/unmatched),
            sorted by paid date.
        """
        start_time = time.time()
        logger.info("Generating withholding match status report...")

        if self.withholding_df.empty:
            logger.warning("Withholding dataframe is empty. Cannot generate withholding match report.")
             # Return an empty DataFrame with expected columns
            thai_cols = [
                self._get_thai_col_name('withholding_tax_report', 'paid_date'),
                self._get_thai_col_name('withholding_tax_report', 'company_name'),
                self._get_thai_col_name('withholding_tax_report', 'tax_id'),
                self._get_thai_col_name('withholding_tax_report', 'amount'),
                self._get_thai_col_name('withholding_tax_report', 'withholding_tax'),
                self._get_thai_col_name('withholding_tax_report', 'paid_amount'),
                self._get_thai_col_name('withholding_tax_report', 'matched'),
                self._get_thai_col_name('withholding_tax_report', 'days_since_payment'), # Keep original column if present
            ]
            return pd.DataFrame(columns=thai_cols)


        # Create a copy to work on
        withholding_report = self.withholding_df.copy()

        # Map boolean 'matched' status to Thai strings
        withholding_report[self._get_thai_col_name('withholding_tax_report', 'matched')] = withholding_report['matched'].map({True: 'ใช่', False: 'ไม่'})

        # Add original index back for reference
        withholding_report[self._get_thai_col_name('withholding_tax_report', 'original_index')] = withholding_report['original_index']


        # Build the report DataFrame with Thai columns directly
        report_data = {}
        for eng_col, thai_col in self.column_mappings.get('withholding_tax_report', {}).items():
             if eng_col in withholding_report.columns:
                 report_data[thai_col] = withholding_report[eng_col]
             else:
                 logger.warning(f"Withholding report: English column '{eng_col}' not found in processed withholding_df.")
                 report_data[thai_col] = None # Add empty column if missing

        # Add the 'matched' status and original index columns
        report_data[self._get_thai_col_name('withholding_tax_report', 'matched')] = withholding_report[self._get_thai_col_name('withholding_tax_report', 'matched')]
        report_data[self._get_thai_col_name('withholding_tax_report', 'original_index')] = withholding_report[self._get_thai_col_name('withholding_tax_report', 'original_index')]

        # Include 'days_since_payment' if it exists in the original withholding_df
        days_col_thai = self._get_thai_col_name('withholding_tax_report', 'days_since_payment')
        if 'days_since_payment' in withholding_report.columns:
            report_data[days_col_thai] = withholding_report['days_since_payment']
        else:
             logger.warning("Withholding report: English column 'days_since_payment' not found in processed withholding_df.")
             report_data[days_col_thai] = None


        final_report = pd.DataFrame(report_data)


        # Ensure correct dtypes before sorting and saving
        # Date column must be datetime for sorting and save_dataframe formatting
        date_col_thai = self._get_thai_col_name('withholding_tax_report', 'paid_date')
        if date_col_thai in final_report.columns:
            try:
                final_report[date_col_thai] = pd.to_datetime(final_report[date_col_thai], errors='coerce')
            except Exception as e:
                logger.error(f"Error converting {date_col_thai} column to datetime: {e}")
                # Return empty DF with expected columns
                return pd.DataFrame(columns=thai_cols)


        # Numeric columns should be numeric for rounding by save_dataframe
        numeric_cols_thai = [
             self._get_thai_col_name('withholding_tax_report', 'amount'),
             self._get_thai_col_name('withholding_tax_report', 'withholding_tax'),
             self._get_thai_col_name('withholding_tax_report', 'paid_amount'),
        ]
        for col in numeric_cols_thai:
             if col in final_report.columns:
                  try:
                      final_report[col] = pd.to_numeric(final_report[col], errors='coerce')
                  except Exception as e:
                      logger.error(f"Error converting {col} column to numeric: {e}")
                      # Return empty DF with expected columns
                      return pd.DataFrame(columns=thai_cols)


        # Sort by date
        if date_col_thai in final_report.columns:
            try:
                final_report = final_report.sort_values(by=date_col_thai).reset_index(drop=True)
            except Exception as e:
                logger.error(f"Error sorting by {date_col_thai}: {e}")
                # Return empty DF with expected columns
                return pd.DataFrame(columns=thai_cols)

        elapsed_time = time.time() - start_time
        logger.info(f"Withholding match status report generated in {elapsed_time:.2f} seconds.")
        return final_report


# Define transaction match report columns using English names internally, map to Thai in report generation
TransactionMatcher.TRANSACTION_REPORT_COLS_MAP = {
    'original_statement_index': 'ลำดับเดิม Statement', # Added for reference
    'transaction_type': 'ประเภทรายการ',
    'transaction_date': 'วันที่ทำรายการ',
    'withdrawal_amount': 'จำนวนเงินถอน', # Updated column
    'deposit_amount': 'จำนวนเงินฝาก', # Updated column
    'matched_companies': 'บริษัทที่จับคู่',
    'sale_tax_ids': 'เลขประจำตัวผู้เสียภาษี (ขาย)',
    'sale_invoice_numbers': 'เลขที่ใบกำกับภาษี (ขาย)',
    'purchase_tax_ids': 'เลขประจำตัวผู้เสียภาษี (ซื้อ)',
    'purchase_invoice_numbers': 'เลขที่ใบกำกับภาษี/เอกสาร (ซื้อ)',
    'withholding_paid_dates': 'วันที่จ่าย (ภงด)',
    'total_matched_amount': 'ยอดใบแจ้งหนี้ที่จับคู่รวม',
    'difference': 'ส่วนต่าง',
    'match_type': 'ประเภทการจับคู่', # Added for debugging/analysis
}

# Add transaction_match_report mapping to EXPECTED_COLUMN_MAPPINGS conceptually
# This is just a conceptual mapping used within TransactionMatcher, not required in main.py CONFIG

