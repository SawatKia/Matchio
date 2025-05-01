# src\main.py
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, Dict
import time
import os # Import os for path joining

from utils import initialize_logging, get_logger, FileManager, CONFIG, EXPECTED_COLUMN_MAPPINGS
from processors import ReportProcess, Reports, TransactionMatcher 
# from gui import ApplicationGUI 

# Get the pre-configured logger
logger = get_logger()

# Add mapping for the output transaction match report columns
# This mapping is used internally by TransactionMatcher for report generation
EXPECTED_COLUMN_MAPPINGS['transaction_match_report'] = TransactionMatcher.TRANSACTION_REPORT_COLS_MAP

report_processor = None 
transaction_matcher = None 
#FIXME - move the main process to app.py and use the GUI class to run the app
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
        logger.info("ReportProcess initialized")

        # TransactionMatcher will be initialized in 'matching' step after data is loaded

        logger.info("All Services initialization phase completed")
    except Exception as error:
        logger.error(f'Error initializing services: {error}')

# process(loading, cleaning, add headers, invalid value, formatting) invoices data  purchasing report
def process_purchase_report() -> Optional[pd.DataFrame]:
    """Process the purchase tax report."""
    logger.info(f"\033[1;36mProcessing purchase tax report...\033[0m")
    result = None

    try:
        # Process purchase tax report using the global instance
        if report_processor:
             result = report_processor.process_purchase_tax_report(
                 CONFIG['csv_exported_purchase_tax_report']
             )

             if result is not None:
                 logger.info(f"Purchase tax report processed successfully with {len(result)} records")
             else:
                 logger.warning("Purchase tax report processing returned None.")

        else:
            logger.error("ReportProcess is not initialized.")


    except FileNotFoundError as e:
        logger.error(f"Purchase tax report file not found: {e}")
    except Exception as e:
        logger.error(f"Error processing purchase tax report: {e}", exc_info=True) 
    finally:
        logger.info("=" * 100)

    return result

# process(loading, cleaning, add headers, invalid value, formatting) invoices data both sale and withholding tax report
def process_sale_reports() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Process both the sale tax and withholding tax reports."""
    logger.info(f"\033[1;36mProcessing sale reports...\033[0m")

    sale_df = None
    withholding_df = None

    try:
        if report_processor:
            logger.debug(f"\033[1;36mProcessing sale tax report\033[0m")
            # Process sale tax report
            sale_df = report_processor.process_sale_tax_report(
                CONFIG['csv_exported_sales_tax_report']
            )

            if sale_df is not None:
                 logger.info(f"Sale tax report processed successfully with {len(sale_df)} records")
            else:
                 logger.warning("Sale tax report processing returned None.")

        else:
             logger.error("ReportProcess is not initialized.")

    except FileNotFoundError as e:
        logger.error(f"Sale tax report file not found: {e}")
    except Exception as e:
        logger.error(f"Error processing sale tax report: {e}", exc_info=True)
    finally:
        logger.info("=" * 100)

    try:
        if report_processor:
            logger.debug(f"\033[1;36mprocessing withholding tax report\033[0m")
            # Process withholding tax report
            withholding_df = report_processor.process_withholding_tax_report(
                CONFIG['excel_Withholding_tax_report']
            )

            if withholding_df is not None:
                logger.info(f"Withholding tax report processed successfully with {len(withholding_df)} records")
            else:
                logger.warning("Withholding tax report processing returned None.")

        else:
             logger.error("ReportProcess is not initialized.")

    except FileNotFoundError as e:
        logger.error(f"Withholding tax report file not found: {e}")
    except Exception as e:
        logger.error(f"Error processing withholding tax report: {e}", exc_info=True)
    finally:
        logger.info("=" * 100)

    return (sale_df, withholding_df)

# process(loading, cleaning, add headers, invalid value, formatting) statements
def process_statements() -> Optional[pd.DataFrame]:
    """Process the bank statement file."""
    logger.info(f"\033[1;36mProcessing statements...\033[0m")
    result = None

    try:
        if report_processor:
            # Process statement file
            result = report_processor.process_statement(
                CONFIG['excel_statement']
            )

            if result is not None:
                logger.info(f"Statement processed successfully with {len(result)} records")
            else:
                 logger.warning("Statement processing returned None.")

        else:
             logger.error("ReportProcess is not initialized.")

    except FileNotFoundError as e:
        logger.error(f"Statement file not found: {e}")
    except Exception as e:
        logger.error(f"Error processing statement: {e}", exc_info=True)
    finally:
        logger.info("=" * 100)

    return result

# process all report files
def process_report_files() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Process all report files."""
    logger.info(f"Starting overall report processing...")
    purchase_df = process_purchase_report()
    sale_df, withholding_df = process_sale_reports()
    statement_df = process_statements()

    # Log each DataFrame name first, then its info
    logger.debug("purchase_df:")
    if report_processor:
        report_processor._log_dataframe_sample(purchase_df)
    else:
        logger.warning("ReportProcess not initialized, cannot log dataframe sample.")

    logger.debug("sale_df:")
    if report_processor:
       report_processor._log_dataframe_sample(sale_df)
    else:
        logger.warning("ReportProcess not initialized, cannot log dataframe sample.")

    logger.debug("withholding_df:")
    if report_processor:
       report_processor._log_dataframe_sample(withholding_df)
    else:
        logger.warning("ReportProcess not initialized, cannot log dataframe sample.")

    logger.debug("statement_df:")
    if report_processor:
        report_processor._log_dataframe_sample(statement_df)
    else:
        logger.warning("ReportProcess not initialized, cannot log dataframe sample.")


    logger.info(f"Overall report processing finished.")
    logger.info("=" * 100)

    return (purchase_df, sale_df, withholding_df, statement_df)


# matching - MODIFIED TO USE TransactionMatcher and generate/save reports
def perform_matching_and_generate_reports(
    purchase_df: Optional[pd.DataFrame],
    sale_df: Optional[pd.DataFrame],
    withholding_df: Optional[pd.DataFrame],
    statement_df: Optional[pd.DataFrame],
    config: Dict,
    column_mappings: Dict
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Performs transaction matching and generates match status reports.

    Args:
        purchase_df: Processed purchase DataFrame.
        sale_df: Processed sale DataFrame.
        withholding_df: Processed withholding DataFrame.
        statement_df: Processed statement DataFrame.
        config: Application configuration dictionary.
        column_mappings: Dictionary containing column mappings.

    Returns:
        A tuple containing the generated report DataFrames:
        (transaction_match_report_df, sale_match_report_df, purchase_match_report_df, withholding_match_report_df)
    """
    logger.info("\033[1;36mStarting matching and report generation...\033[0m")
    match_start_time = time.time()

    transaction_match_report_df = None
    sale_match_report_df = None
    purchase_match_report_df = None
    withholding_match_report_df = None

    try:
        # Check if essential data is available
        if statement_df is None or statement_df.empty:
            logger.error("Statement data is missing or empty. Cannot perform matching.")
            return None, None, None, None
        if (sale_df is None or sale_df.empty) and \
           (purchase_df is None or purchase_df.empty) and \
           (withholding_df is None or withholding_df.empty):
            logger.warning("All invoice and withholding dataframes are missing or empty. Matching will likely find no matches.")
            # We can still instantiate the matcher, it will just find nothing.

        # Instantiate TransactionMatcher
        matcher = TransactionMatcher(
            statement_df=statement_df,
            sale_df=sale_df,
            purchase_df=purchase_df,
            withholding_df=withholding_df,
            max_credit_days=config.get('matching_credit_days', 30),
            sale_tolerance=config.get('matching_sale_tolerance', 1000.0),
            purchase_tolerance=config.get('matching_purchase_tolerance', 50.0),
            expected_column_mappings=column_mappings # Pass mappings for report generation
        )

        # Perform matching
        matcher.match_transactions()

        # Generate reports
        transaction_match_report_df = matcher.generate_transaction_match_report()
        sale_match_report_df = matcher.generate_sale_match_report()
        purchase_match_report_df = matcher.generate_purchase_match_report()
        withholding_match_report_df = matcher.generate_withholding_match_report()


        logger.info("Matching and report generation completed successfully.")

    except Exception as e:
        logger.error(f"Error during matching or report generation: {e}")
        import traceback
        logger.error(traceback.format_exc())

    finally:
        match_elapsed_time = time.time() - match_start_time
        logger.info(f"Matching and report generation took \033[1;36m{match_elapsed_time:.2f}\033[0m seconds.")
        logger.info("=" * 100)

    return (transaction_match_report_df, sale_match_report_df, purchase_match_report_df, withholding_match_report_df)

def save_reports(
    output_dir: str,
    transaction_match_report_df: Optional[pd.DataFrame],
    sale_match_report_df: Optional[pd.DataFrame],
    purchase_match_report_df: Optional[pd.DataFrame],
    withholding_match_report_df: Optional[pd.DataFrame]
) -> None:
    """Saves the generated report dataframes to CSV files."""
    logger.info("\033[1;36mSaving reports to CSV...\033[0m")
    try:
        if transaction_match_report_df is not None and not transaction_match_report_df.empty:
            FileManager.save_dataframe(transaction_match_report_df, Path(output_dir) / "รายงานการจับคู่รายการบัญชี.csv")

        if sale_match_report_df is not None and not sale_match_report_df.empty:
             FileManager.save_dataframe(sale_match_report_df, Path(output_dir) / "รายงานสถานะการจับคู่ใบแจ้งหนี้ขาย.csv")

        if purchase_match_report_df is not None and not purchase_match_report_df.empty:
             FileManager.save_dataframe(purchase_match_report_df, Path(output_dir) / "รายงานสถานะการจับคู่ใบแจ้งหนี้ซื้อ.csv")

        if withholding_match_report_df is not None and not withholding_match_report_df.empty:
             FileManager.save_dataframe(withholding_match_report_df, Path(output_dir) / "รายงานสถานะการจับคู่ภาษีหัก ณ ที่จ่าย.csv")

        logger.info("Report saving completed.")
    except Exception as e:
        logger.error(f"Error saving reports: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
         logger.info("=" * 100)


def main():
    """Main function to run the application."""
    initialize_logging() # Ensure logging is initialized early
    logger.info("Application started")

    start_time = time.time()

    try:
        # Initialize all services (including report processor with mappings)
        initialize_services()

        # Process all reports
        # process_report_files already logs DataFrame info and sample
        purchase_df, sale_df, withholding_df, statement_df = process_report_files()

        processd_time = time.time() - start_time
        logger.info(f"Processing reports completed in \033[1;36m{processd_time:.2f}\033[0m seconds")
        logger.info("=" * 100)

        # Perform matching and generate reports
        report_dfs = perform_matching_and_generate_reports(
            purchase_df,
            sale_df,
            withholding_df,
            statement_df,
            CONFIG,
            EXPECTED_COLUMN_MAPPINGS # Pass mappings
        )

        # Save the generated reports
        save_reports(CONFIG['output_dir'], *report_dfs)

        end_time = time.time() - start_time
        logger.info(f"Total application execution time: \033[1;36m{end_time:.2f}\033[0m seconds")

        #FIXME - finish GUI implementation
        # Launch GUI if needed
        # app = ApplicationGUI()
        # app.mainloop()

        logger.info("Application finished successfully")

    except Exception as e:
        logger.error(f"Application error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.info("Application finished with errors")


if __name__ == "__main__":
    main()