# src\app.py
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, Dict
import time
import os

from utils import initialize_logging, get_logger, FileManager, CONFIG, EXPECTED_COLUMN_MAPPINGS
from processors import ReportProcess, Reports, TransactionMatcher 
from gui import ApplicationGUI

# Get the pre-configured logger
logger = get_logger()

# Add mapping for the output transaction match report columns
# This mapping is used internally by TransactionMatcher for report generation
EXPECTED_COLUMN_MAPPINGS['transaction_match_report'] = TransactionMatcher.TRANSACTION_REPORT_COLS_MAP

class Application:
    def __init__(self):
        self.report_processor = None
        self.transaction_matcher = None
        self.purchase_df = None
        self.sale_df = None
        self.withholding_df = None
        self.statement_df = None
        self.reports_generated = False
        
        # Initialize logging immediately
        initialize_logging()
        logger.info("Application initialized")

    def initialize_services(self) -> None:
        """Initialize all required services."""
        try:
            logger.info("Initializing services")

            # Initialize OCR processor if needed
            # Implement OCR initialization here if needed

            # Initialize Gemini if needed
            # Implement Gemini initialization here if needed

            # Initialize report processor singleton with configuration
            # Create Reports TypedDict instance
            report_paths = Reports(
                purchase=CONFIG['csv_exported_purchase_tax_report'],
                sale=CONFIG['csv_exported_sales_tax_report'],
                withholding_tax=CONFIG['excel_Withholding_tax_report'],
                statement=CONFIG['excel_statement']
            )
            self.report_processor = ReportProcess(report_paths, EXPECTED_COLUMN_MAPPINGS)
            logger.info("ReportProcess initialized")

            # TransactionMatcher will be initialized in 'matching' step after data is loaded

            logger.info("All Services initialization phase completed")
        except Exception as error:
            logger.error(f'Error initializing services: {error}')

    def process_purchase_report(self) -> Optional[pd.DataFrame]:
        """Process the purchase tax report."""
        logger.info(f"\033[1;36mProcessing purchase tax report...\033[0m")
        result = None

        try:
            # Process purchase tax report using the instance
            if self.report_processor:
                result = self.report_processor.process_purchase_tax_report(
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

    def process_sale_reports(self) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Process both the sale tax and withholding tax reports."""
        logger.info(f"\033[1;36mProcessing sale reports...\033[0m")

        sale_df = None
        withholding_df = None

        try:
            if self.report_processor:
                logger.debug(f"\033[1;36mProcessing sale tax report\033[0m")
                # Process sale tax report
                sale_df = self.report_processor.process_sale_tax_report(
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
            if self.report_processor:
                logger.debug(f"\033[1;36mprocessing withholding tax report\033[0m")
                # Process withholding tax report
                withholding_df = self.report_processor.process_withholding_tax_report(
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

    def process_statements(self) -> Optional[pd.DataFrame]:
        """Process the bank statement file."""
        logger.info(f"\033[1;36mProcessing statements...\033[0m")
        result = None

        try:
            if self.report_processor:
                # Process statement file
                result = self.report_processor.process_statement(
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

    def process_report_files(self, progress_callback=None) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Process all report files."""
        logger.info(f"Starting overall report processing...")
        progress_callback("purchase", 1, 4)
        self.purchase_df = self.process_purchase_report()
        progress_callback("sale", 3, 4)
        self.sale_df, self.withholding_df = self.process_sale_reports()
        progress_callback("statement", 4, 4)
        self.statement_df = self.process_statements()

        # Log each DataFrame name first, then its info
        logger.debug("purchase_df:")
        if self.report_processor:
            self.report_processor._log_dataframe_sample(self.purchase_df)
        else:
            logger.warning("ReportProcess not initialized, cannot log dataframe sample.")

        logger.debug("sale_df:")
        if self.report_processor:
            self.report_processor._log_dataframe_sample(self.sale_df)
        else:
            logger.warning("ReportProcess not initialized, cannot log dataframe sample.")

        logger.debug("withholding_df:")
        if self.report_processor:
            self.report_processor._log_dataframe_sample(self.withholding_df)
        else:
            logger.warning("ReportProcess not initialized, cannot log dataframe sample.")

        logger.debug("statement_df:")
        if self.report_processor:
            self.report_processor._log_dataframe_sample(self.statement_df)
        else:
            logger.warning("ReportProcess not initialized, cannot log dataframe sample.")

        logger.info(f"Overall report processing finished.")
        logger.info("=" * 100)

        return (self.purchase_df, self.sale_df, self.withholding_df, self.statement_df)

    def perform_matching_and_generate_reports(self, progress_callback = None) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Performs transaction matching and generates match status reports.
        
        Args:
            progress_callback: Optional callback function(current, total) for progress updates

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
            if self.statement_df is None or self.statement_df.empty:
                logger.error("Statement data is missing or empty. Cannot perform matching.")
                return None, None, None, None
            if (self.sale_df is None or self.sale_df.empty) and \
               (self.purchase_df is None or self.purchase_df.empty) and \
               (self.withholding_df is None or self.withholding_df.empty):
                logger.warning("All invoice and withholding dataframes are missing or empty. Matching will likely find no matches.")
                # We can still instantiate the matcher, it will just find nothing.

            # Instantiate TransactionMatcher
            self.transaction_matcher = TransactionMatcher(
                statement_df=self.statement_df,
                sale_df=self.sale_df,
                purchase_df=self.purchase_df,
                withholding_df=self.withholding_df,
                max_credit_days=CONFIG.get('matching_credit_days', 30),
                sale_tolerance=CONFIG.get('matching_sale_tolerance', 1000.0),
                purchase_tolerance=CONFIG.get('matching_purchase_tolerance', 50.0),
                expected_column_mappings=EXPECTED_COLUMN_MAPPINGS, # Pass mappings for report generation
                progress_callback=progress_callback # Pass the progress callback function
            )

            # Perform matching
            self.transaction_matcher.match_transactions()

            # Generate reports
            transaction_match_report_df = self.transaction_matcher.generate_transaction_match_report()
            sale_match_report_df = self.transaction_matcher.generate_sale_match_report()
            purchase_match_report_df = self.transaction_matcher.generate_purchase_match_report()
            withholding_match_report_df = self.transaction_matcher.generate_withholding_match_report()

            self.reports_generated = True
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

    def save_reports(self, report_dfs) -> None:
        """Saves the generated report dataframes to CSV files."""
        logger.info("\033[1;36mSaving reports to CSV...\033[0m")
        transaction_match_report_df, sale_match_report_df, purchase_match_report_df, withholding_match_report_df = report_dfs
                
        try:
            if transaction_match_report_df is not None and not transaction_match_report_df.empty:
                FileManager.save_dataframe(transaction_match_report_df, Path(CONFIG['output_dir']) / "รายงานการจับคู่รายการบัญชี.csv")

            if sale_match_report_df is not None and not sale_match_report_df.empty:
                FileManager.save_dataframe(sale_match_report_df, Path(CONFIG['output_dir']) / "รายงานสถานะการจับคู่ใบแจ้งหนี้ขาย.csv")

            if purchase_match_report_df is not None and not purchase_match_report_df.empty:
                FileManager.save_dataframe(purchase_match_report_df, Path(CONFIG['output_dir']) / "รายงานสถานะการจับคู่ใบแจ้งหนี้ซื้อ.csv")

            if withholding_match_report_df is not None and not withholding_match_report_df.empty:
                FileManager.save_dataframe(withholding_match_report_df, Path(CONFIG['output_dir']) / "รายงานสถานะการจับคู่ภาษีหัก ณ ที่จ่าย.csv")

            logger.info("Report saving completed.")
        except Exception as e:
            logger.error(f"Error saving reports: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            logger.info("=" * 100)

    def run_cli(self):
        """Run the application in CLI mode without GUI."""
        start_time = time.time()
        logger.info("Running application in CLI mode")
        
        try:
            # Initialize all services
            self.initialize_services()

            # Process all reports
            self.process_report_files()

            processd_time = time.time() - start_time
            logger.info(f"Processing reports completed in \033[1;36m{processd_time:.2f}\033[0m seconds")
            logger.info("=" * 100)

            # Perform matching and generate reports
            report_dfs = self.perform_matching_and_generate_reports()

            # Save the generated reports
            self.save_reports(report_dfs)

            end_time = time.time() - start_time
            logger.info(f"Total application execution time: \033[1;36m{end_time:.2f}\033[0m seconds")
            logger.info("Application finished successfully")
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.info("Application finished with errors")

    def run_gui(self):
        """Run the application with GUI."""
        logger.info("Starting application with GUI")
        
        # Initialize services first
        self.initialize_services()
        
        # Create the GUI instance and pass a reference to this application
        app = ApplicationGUI(self)
        app.mainloop()


def main():
    """Entry point for the application."""
    import sys
    app = Application()
    
    # Check for any command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # Run in CLI mode if specified
        app.run_cli()
    else:
        # Default to GUI mode
        app.run_gui()


if __name__ == "__main__":
    main()