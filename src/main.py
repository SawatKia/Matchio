# src\main.py
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple
import time

from utils import initialize_logging, get_logger, fg, bg, style
from processors import ReportProcess, Reports
from gui import ApplicationGUI


# Get the pre-configured logger
logger = get_logger()

CONFIG = {
    'csv_exported_purchase_tax_report': r'data/inputs/ภาษีซื้อ-ทรัพยเจิรญ67.csv', # r for non-ascii text
    'csv_exported_sales_tax_report': r'data/inputs/ภาษีขาย-ทรัพย์เจริญ67.csv',
    'excel_Withholding_tax_report': r'data/inputs/ขาย1-9-ทรัพย์.xlsx',
    'excel_statement': 'data/inputs/20250319195146_merged_manual.xlsx',
    'output_dir': 'data/output',
    'matching_credit_days': 30,
    'matching_tolerance_percent': 0.1,
}

EXPECTED_COLUMN_MAPPINGS = {
    # report_name: {
    #     column_name_en: 'column_name_th',
    #     ...
    # },
    # ...
    'purchase_tax_report': {
        'order_number': 'ลำดับ',
        'date_of_purchase_invoice': 'วัน/เดือน/ปี',
        'purchase_invoice_tax_number': 'เลขที่ใบกำกับภาษี',
        'purchase_invoice_id': 'เลขที่เอกสาร',
        'company_name': 'ชื่อผู้ซื้อสินค้า/ผู้รับบริการ',
        'company_tax_id': 'เลขประจำตัวผู้เสียภาษี',
        'product_value': 'มูลค่าสินค้า',
        'vat': 'ภาษีมูลค่าเพิ่ม',
        'total_amount': 'จำนวนเงิน'
    },
    'sale_tax_report': {
        'order_number': 'ลำดับ',
        'date_of_sale_invoice': 'วัน/เดือน/ปี',
        'sale_invoice_tax_number': 'เลขที่ใบกำกับภาษี',
        'company_name': 'ชื่อผู้ซื้อสินค้า/ผู้รับบริการ',
        'company_tax_id': 'เลขประจำตัวผู้เสียภาษี',
        'product_value': 'มูลค่าสินค้า',
        'vat': 'ภาษีมูลค่าเพิ่ม',
        'total_amount': 'จำนวนเงิน',
        'withholding_tax': 'หัก 3%',
        'net_amount': 'คงเหลือ',
        'matched': 'จับคู่แล้ว',
        'days_outstanding': 'จำนวนวันที่ค้างชำระ',
    },
    'withholding_tax_report': {
        'paid_date': 'ว/ด/ป',
        'company_name': 'ชื่อผู้หักภาษี',
        'tax_id': 'เลขประจำตัวผู้เสียภาษี',
        'amount': 'จำนวนเงิน',
        'withholding_tax': 'หัก ณ ที่จ่าย',
        'paid_amount': 'ยอดโอน',
        'days_since_payment': 'จำนวนวันนับจากชำระ',
    },
    'statement': {
        'datetime': 'วันที่และเวลา',
        'amount': 'จำนวนเงิน',
        'isDeposit': 'การฝากเงิน?',
        'balance': 'ยอดคงเหลือ',
        'page': 'หน้าที่'
    }
}

report_processor = None

# init services eg: Gemini, EasyOcr, ...
def initialize_services() -> None:
    try:
        logger.info("Initializing services")
        
        # Initialize OCR processor if needed
        # Implement OCR initialization here if needed
        
        
        # Initialize Gemini if needed
        # Implement Gemini initialization here if needed
        
        # Initialize report processor singleton with configuration
        global report_processor

        # Create Reports TypedDict instance
        report_paths = Reports(
            purchase=CONFIG['csv_exported_purchase_tax_report'],
            sale=CONFIG['csv_exported_sales_tax_report'],
            withholding_tax=CONFIG['excel_Withholding_tax_report'],
            statement=CONFIG['excel_statement']
        )
        report_processor = ReportProcess(report_paths, EXPECTED_COLUMN_MAPPINGS)
        logger.info("All Services initialized successfully")
    except Exception as error:
        logger.error(f'Error initializing services: {error}')

# process(loading, cleaning, add headers, invalid value, formatting) invoices data  purchasing report
def process_purchase_report() -> Optional[pd.DataFrame]:
    """Process the purchase tax report."""
    logger.info("\033[1;36mProcessing purchase tax report...\033[0m")
    result = None
    
    try:
        # Ensure report processor is initialized
        if report_processor is None:
            initialize_services()
            
        # Process purchase tax report
        result = report_processor.process_purchase_tax_report(
            CONFIG['csv_exported_purchase_tax_report']
        )
        
        if result is not None:
            logger.info(f"Purchase tax report processed successfully with {len(result)} records")
        
    except FileNotFoundError as e:
        logger.error(f"Purchase tax report file not found: {e}")
    except Exception as e:
        logger.error(f"Error processing purchase tax report: {e}")
    finally:
        # logger.info("\033[1;32m=\033[0m"*100)
        logger.info("=" * 100)
        
    return result

# process(loading, cleaning, add headers, invalid value, formatting) invoices data both sale and withholding tax report
def process_sale_reports() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Process both the sale tax and withholding tax reports."""
    logger.info("\033[1;36mProcessing sale reports...\033[0m")
    
    sale_df = None
    withholding_df = None
    
    try:
        # Ensure report processor is initialized
        if report_processor is None:
            initialize_services()
        logger.debug("\033[1;36mProcessing sale tax report\033[0m")
        # Process sale tax report
        sale_df = report_processor.process_sale_tax_report(
            CONFIG['csv_exported_sales_tax_report']
        )
        logger.info(f"Sale tax report processed successfully with {len(sale_df)} records")
    except FileNotFoundError as e:
        logger.error(f"Sale tax report file not found: {e}")
    except Exception as e:
        logger.error(f"Error processing sale tax report: {e}")
    finally:
        # logger.info("\033[1;32m=\033[0m"*100)
        logger.info("=" * 100)
    
    try:
        logger.debug("\033[1;36mprocessing withholding tax report\033[0m")
        # Process withholding tax report
        withholding_df = report_processor.process_withholding_tax_report(
            CONFIG['excel_Withholding_tax_report']
        )
        logger.info(f"Withholding tax report processed successfully with {len(withholding_df)} records")
    except FileNotFoundError as e:
        logger.error(f"Withholding tax report file not found: {e}")
    except Exception as e:
        logger.error(f"Error processing withholding tax report: {e}")
    finally:
        # logger.info("\033[1;32m=\033[0m"*100)
        logger.info("=" * 100)
    
    return (sale_df, withholding_df)

# process(loading, cleaning, add headers, invalid value, formatting) statements
def process_statements() -> Optional[pd.DataFrame]:
    """Process the bank statement file."""
    logger.info("\033[1;36mProcessing statements...\033[0m")
    result = None
    
    try:
        # Ensure report processor is initialized
        if report_processor is None:
            initialize_services()
            
        # Process statement file
        result = report_processor.process_statement(
            CONFIG['excel_statement']
        )
        
        if result is not None:
            logger.info(f"Statement processed successfully with {len(result)} records")
        
    except FileNotFoundError as e:
        logger.error(f"Statement file not found: {e}")
    except Exception as e:
        logger.error(f"Error processing statement: {e}")
    finally:
        # logger.info("\033[1;32m=\033[0m"*100)
        logger.info("=" * 100)
        
    return result

# matching
def matching(sale_df: Optional[pd.DataFrame], statement_df: Optional[pd.DataFrame]) -> None:
    """Match sale invoices with bank statement entries."""
    logger.info("\033[1;36mMatching invoices with statements...\033[0m")
    
    try:
        # Check if required dataframes are available
        if sale_df is None:
            logger.error("Cannot perform matching: Sale tax report is missing")
            return
            
        if statement_df is None:
            logger.error("Cannot perform matching: Statement is missing")
            return
            
        # TODO: Implement matching algorithm
        # Use CONFIG['matching_credit_days'] and CONFIG['matching_tolerance_percent'] 
        
        logger.info("Matching completed successfully")
        # logger.info("\033[1;32m=\033[0m"*100)
        logger.info("=" * 100)
    except Exception as e:
        logger.error(f"Error during matching process: {e}")

def process_report_files() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Process all report files."""
    purchase_df = process_purchase_report()
    sale_df, withholding_df = process_sale_reports()
    statement_df = process_statements()

    # Log each DataFrame name first, then its info
    logger.debug("purchase_df:")
    ReportProcess._log_dataframe_sample(purchase_df)
    
    logger.debug("sale_df:")
    ReportProcess._log_dataframe_sample(sale_df)
    
    logger.debug("withholding_df:")
    ReportProcess._log_dataframe_sample(withholding_df)
    
    logger.debug("statement_df:")
    ReportProcess._log_dataframe_sample(statement_df)
    
    return (purchase_df, sale_df, withholding_df, statement_df)

def main():
    """Main function to run the application."""
    logger.info("Application started")
    
    try:
        start_time = time.time()
        # Initialize all services
        initialize_services()
        
        # Process all reports
        purchase_df, sale_df, withholding_df, statement_df = process_report_files()
        
        processd_time = time.time() - start_time
        logger.info(f"Processing report completed in \033[1;36m{processd_time:.2f}\033[0m seconds")
        logger.info("=" * 100)
        
        # Perform matching
        if sale_df is not None and statement_df is not None:
            matching(sale_df, statement_df)
        end_time = time.time() - start_time
        matching_elapsed_time = end_time - processd_time
        logger.info(f"Matching completed in \033[1;36m{end_time:.2f}\033[0m seconds (\033[1;36m{matching_elapsed_time:.2f}\033[0m seconds after processing)")
        
        # Launch GUI if needed
        # app = ApplicationGUI()
        # app.mainloop()
        
        logger.info("Application finished successfully")
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        logger.info("Application finished with errors")


if __name__ == "__main__":
    main()