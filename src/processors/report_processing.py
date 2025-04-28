# src\processors\report_processing.py
import pandas as pd
import os
import io
import json
from typing import Optional, Dict, Any, TypedDict, List
from tabulate import tabulate


from utils import get_logger, FileManager, DataFrameCleaner

# Get the pre-configured logger
logger = get_logger()

class Reports(TypedDict):
    purchase: str
    sale: str
    withholding_tax: str
    statement: str

class ReportProcess:
    """
    A singleton class for report processing (class to loading, removing excess column, add headers,
    cleaning(na/nan/null rows), handle invalid value, formatting value) 
    invoices data both purchasing and sale report, the withholding tax report, and the statement file
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """
        Implement singleton pattern to ensure only one instance exists
        """
        if cls._instance is None:
            logger.debug("Creating new ReportProcess instance")
            cls._instance = super(ReportProcess, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self, reports_path: Reports, column_mapping: dict):
        """
        Initialize the report processor with file paths and column mappings
        
        Args:
            reports_path: Dictionary containing paths to various reports
            column_mapping: Dictionary mapping expected columns for each report type
        """
        # Only initialize once
        if getattr(self, '_initialized', False):
            logger.debug("ReportProcess already initialized, skipping initialization")
            return
            
        try:
            # Store filepaths using Reports TypedDict structure
            self.reports_filepath = {
                "purchase": reports_path['purchase'],
                "sale": {
                    "report": reports_path['sale'],
                    "withholding_tax": reports_path['withholding_tax']
                },
                "statement": reports_path['statement']
            }
            logger.debug(f"Reports filepaths: {json.dumps(self.reports_filepath, ensure_ascii=False, indent=4)}")

            self.EXPECTED_COLUMNS = column_mapping
            logger.debug(f"Expected columns: {json.dumps(self.EXPECTED_COLUMNS, ensure_ascii=False, indent=4)}")

            self.report_name = {
                "purchase": list(self.EXPECTED_COLUMNS.keys())[0],
                "sale": list(self.EXPECTED_COLUMNS.keys())[1],
                "withholding_tax": list(self.EXPECTED_COLUMNS.keys())[2],
                "statement": list(self.EXPECTED_COLUMNS.keys())[3]
            }
            logger.debug(f"Report names: {json.dumps(self.report_name, ensure_ascii=False, indent=4)}")

            self._initialized = True
            logger.info("ReportProcess initialized successfully")
        except AttributeError as e:
            logger.error(f"Invalid reports_path structure: {e}")
            raise ValueError(f"Invalid reports_path structure: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize ReportProcess: {e}")
            raise

    def _validate_file_path(self, file_path: str, default_path: str = None) -> str:
        """
        Validate file path and use default if necessary
        
        Args:
            file_path: Path to validate
            default_path: Default path to use if file_path is None
            
        Returns:
            Validated file path
        """
        try:
            if file_path is None:
                if default_path:
                    logger.warning(f"File path not provided, defaulting to: {default_path}")
                    file_path = default_path
                else:
                    raise ValueError("No file path provided and no default path available")
            return file_path
        except Exception as e:
            logger.error(f"Error validating file path: {e}")
            raise

    def _validate_columns(self, df: pd.DataFrame, expected_columns: List[str]) -> pd.DataFrame:
        """
        Validate that DataFrame has expected columns, rename if needed
        
        Args:
            df: DataFrame to validate
            expected_columns: Dictionary mapping expected column names
            
        Returns:
            DataFrame with validated columns
        """
        try:
            logger.info("Validating DataFrame columns")
            
            if not expected_columns:
                raise KeyError("Expected columns for 'purchase_tax_report' are not defined.")
            logger.debug(f"DataFrame columns: {df.columns}")
            logger.debug(f"\033[1;31m<\033[0m Expected columns: {expected_columns}::{type(expected_columns)}")

            added_columns = []
            # Check if actual columns are fewer than expected columns
            logger.debug(f"verifying condition if {len(df.columns)} < {len(expected_columns)}")
            if len(df.columns) < len(expected_columns):
                logger.warning("Actual columns are fewer than expected columns. Adding missing columns with default placeholders.")
                
                for col in expected_columns[len(df.columns):]:
                    if col == "matched":
                        df[col] = 'false'
                    elif col == "days_outstanding" or col == "days_since_payment":
                        df[col] = 0
                    else:
                        df[col] = 1111
                    logger.warning(f"Added {df[col].unique()} value to column: '{col}' ")
                    added_columns.append(col)
            columns_match = pd.Index(df.columns).equals(pd.Index(expected_columns))
            logger.debug(f"All columns match?: {columns_match}")
            if not columns_match:
                logger.warning("DataFrame columns do not match expected columns. Resetting the columns.")
                df.columns = expected_columns
                logger.debug(f"Set DataFrame columns: {df.columns}")
            ReportProcess._log_dataframe_sample(df, 10)

            logger.info("DataFrame columns validated successfully")
            return df, added_columns
        except Exception as e:
            logger.error(f"Error validating columns: {e}")
            raise
    
    @staticmethod
    def _log_dataframe_sample(df: pd.DataFrame, rows: int = 5):
        buffer = io.StringIO()
        df.info(buf=buffer)
        info_str = buffer.getvalue()
        logger.debug(f"Dataframe info:\n{info_str}")
        logger.debug(f"Dataframe first {rows} rows: \n{tabulate(df.head(rows), headers='keys', tablefmt='simple_outline', disable_numparse=True)}")

    def _calculate_new_columns(self, df: pd.DataFrame, report_name: str, columns: List[str]) -> pd.DataFrame:
        try:
            if columns is None:
                logger.error("No columns provided for calculation")
                raise ValueError("No columns provided for calculation")
            
            logger.info(f"Calculating {columns} which are new columns for {report_name}")

            if report_name == self.report_name.get('purchase'):
                logger.info(f"Calculating new columns of {self.report_name.get('purchase')} ")
                df['total_amount'] = df['product_value'] + df['vat']

            elif report_name == self.report_name.get('sale'):
                logger.info(f"Calculating new columns of{self.report_name.get('sale')} ")
                df['total_amount'] = df['product_value'] + df['vat']
                df['withholding_tax'] = df['total_amount'] * 0.03  # Example calculation
                df['net_amount'] = df['total_amount'] - df['withholding_tax']

            elif report_name == self.report_name.get('withholding_tax'):
                logger.info(f"Calculating new columns of {self.report_name.get('withholding_tax')}")
                df['paid_amount'] = df['amount'] * 1.07 - df['withholding_tax']

            logger.info(f"Calculating new columns sucessfully")
            self._log_dataframe_sample(df, 10)
            df = DataFrameCleaner.convert_numeric_columns(df)

            
            return df
        except Exception as e:
            logger.error(f"Error calculating new columns for {report_name}: {e}")
            raise

    def _clean_dataframe(self, df: pd.DataFrame, report_name: str) -> pd.DataFrame:
        """Clean DataFrame using DataFrameCleaner"""
        try:

            logger.info(f"Cleaning {report_name} DataFrame")
            if report_name == self.report_name.get('purchase'):
                cleaned_df, stats = DataFrameCleaner.clean_purchase_dataframe(df)
            elif report_name == self.report_name.get('sale'):
                cleaned_df, stats = DataFrameCleaner.clean_sale_dataframe(df)
            elif report_name == self.report_name.get('withholding_tax'):
                cleaned_df, stats = DataFrameCleaner.clean_withholding_tax_dataframe(df)
            elif report_name == self.report_name.get('statement'):
                cleaned_df, stats = DataFrameCleaner.clean_statement_dataframe(df)
            else:
                raise ValueError(f"Invalid report type: {report_name}")
            ReportProcess._log_dataframe_sample(cleaned_df, 10)
            
            if report_name not in list(self.report_name.values()):
                raise ValueError(f"Invalid report type: {report_name}, should be one of {list(self.report_name.values())}")

            # validate and set column names if it not have any
            cleaned_df, added_columns = self._validate_columns(cleaned_df, list(self.EXPECTED_COLUMNS.get(report_name).keys()))

            #calculate another columns
            calculated_df = self._calculate_new_columns(cleaned_df, report_name, added_columns)

            logger.debug(f"Cleaning stats for {report_name}: {stats}")
            # set column names by call the new method with the report type

            ReportProcess._log_dataframe_sample(calculated_df, 50)
            return calculated_df
            
        except Exception as e:
            logger.error(f"Error cleaning {report_name} DataFrame: {e}")
            raise

    def process_purchase_tax_report(self, csv_filepath: str = None) -> pd.DataFrame:
        """
        Process the purchase tax report and return a DataFrame. steps:
        1. read the CSV file
        2. cleaning by handle na, null, another invalid values properly 
        3. formatting values if needs
        4. fill missing values, columns(headers)
        5. calculate the new columns
        
        Args:
            csv_filepath: Path to CSV file, uses default if None
            
        Returns:
            Processed DataFrame
        """
        try:
            # 1. read the CSV file
            # Validate and get file path
            csv_filepath = self._validate_file_path(
                csv_filepath, 
                default_path=self.reports_filepath["purchase"]
            )
            logger.info(f"Processing purchase tax report from file: {csv_filepath}")
            
            # Check if file exists
            if not FileManager.ensure_file_exists(csv_filepath):
                raise FileNotFoundError(f"CSV file not found: {csv_filepath}")
                
            # Load CSV file using FileManager
            df = FileManager.load_csv_to_dataframe(csv_filepath)
            if df is None:
                raise ValueError(f"Failed to load CSV file: {csv_filepath}")
            logger.info("CSV file loaded successfully")
            ReportProcess._log_dataframe_sample(df, 10)

            # 2. cleaning by handle na, null, another invalid values properly
            # Clean data
            df = self._clean_dataframe(df, self.report_name.get('purchase'))
            
            # 3. formatting values if needs
            # 4. fill missing values, columns(headers)
            
            logger.info("Purchase tax report processed successfully")
            return df
            
        except FileNotFoundError as e:
            logger.error(f"Purchase tax report file not found: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid value in purchase tax report: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing purchase tax report: {e}")
            raise

    def process_sale_tax_report(self, csv_filepath: str = None) -> pd.DataFrame:
        """
        Process the sale tax report and return a DataFrame. steps:
        1. read the CSV file
        2. cleaning by handle na, null, another invalid values properly 
        3. formatting values if needs
        4. fill missing values, columns(headers)
        5. calculate the new columns
        
        Args:
            csv_filepath: Path to CSV file, uses default if None
            
        Returns:
            Processed DataFrame
        """
        try:
            # 1. read the CSV file
            # Validate and get file path
            csv_filepath = self._validate_file_path(
                csv_filepath, 
                default_path=self.reports_filepath["sale"]["report"]
            )
            logger.info(f"Processing sale tax report from file: {csv_filepath}")
            
            # Check if file exists
            if not FileManager.ensure_file_exists(csv_filepath):
                raise FileNotFoundError(f"CSV file not found: {csv_filepath}")
                
            # Load CSV file using FileManager
            df = FileManager.load_csv_to_dataframe(csv_filepath)
            if df is None:
                raise ValueError(f"Failed to load CSV file: {csv_filepath}")
            logger.info("CSV file loaded successfully")
            ReportProcess._log_dataframe_sample(df, 10)
            
            # 2. cleaning by handle na, null, another invalid values properly
            df = self._clean_dataframe(df, self.report_name.get('sale'))
            # 3. formatting values if needs
            # 4. fill missing values, columns(headers)
            # 5. calculate the new columns
            
            logger.info("Sale tax report processed successfully")
            return df
            
        except FileNotFoundError as e:
            logger.error(f"Sale tax report file not found: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid value in sale tax report: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing sale tax report: {e}")
            raise
    
    def process_withholding_tax_report(self, excel_filepath: str = None, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        Process the withholding tax report and return a DataFrame. steps:
        1. read the CSV file
        2. cleaning by handle na, null, another invalid values properly 
        3. formatting values if needs
        4. fill missing values, columns(headers)
        5. calculate the new columns
        
        Args:
            excel_filepath: Path to Excel file, uses default if None
            sheet_name: Name of sheet to load, uses default if None
            
        Returns:
            Processed DataFrame
        """
        try:
            # 1. read the CSV file
            # Validate and get file path
            excel_filepath = self._validate_file_path(
                excel_filepath, 
                default_path=self.reports_filepath["sale"]["withholding_tax"]
            )
            logger.info(f"Processing withholding tax report from file: {excel_filepath}")
            
            # Set default sheet name if not provided
            if sheet_name is None:
                sheet_name = r"หัก ณ ที่จ่าย"  # r for non-ascii text
                logger.warning(f"Sheet name not provided, default to: {sheet_name}")
            
            # Check if file exists
            if not FileManager.ensure_file_exists(excel_filepath):
                raise FileNotFoundError(f"Excel file not found: {excel_filepath}")
                
            # Load Excel file using FileManager
            df = FileManager.load_excel_to_dataframe(excel_filepath, sheet_name)
            if df is None:
                raise ValueError(f"Failed to load Excel file: {excel_filepath}")
            logger.info("EXCEL file loaded successfully")
            ReportProcess._log_dataframe_sample(df, 10)
            
            # Validate columns
            expected_columns = self.EXPECTED_COLUMNS.get('excel_Withholding_tax_report', {})
            logger.debug(f"Expected columns: {expected_columns}")

            # 2. cleaning by handle na, null, another invalid values properly
            df = self._clean_dataframe(df, self.report_name.get('withholding_tax'))
            # 3. formatting values if needs
            # 4. fill missing values, columns(headers)
            # 5. calculate the new columns
            
            logger.info("Withholding tax report processed successfully")
            return df
            
        except FileNotFoundError as e:
            logger.error(f"Withholding tax report file not found: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid value in withholding tax report: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing withholding tax report: {e}")
            raise

    def process_statement(self, excel_filepath: str = None, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        Process the statement file and return a DataFrame. steps:
        1. read the CSV file
        2. cleaning by handle na, null, another invalid values properly 
        3. formatting values if needs
        4. fill missing values, columns(headers)
        
        Args:
            excel_filepath: Path to Excel file, uses default if None
            sheet_name: Name of sheet to load, uses default if None
            
        Returns:
            Processed DataFrame
        """
        try:
            # 1. read the CSV file
            # Validate and get file path
            excel_filepath = self._validate_file_path(
                excel_filepath, 
                default_path=self.reports_filepath["statement"]
            )
            logger.info(f"Processing statement from file: {excel_filepath}")
            
            # Set default sheet name if not provided
            if sheet_name is None:
                sheet_name = r"Sheet1"  # Excel default sheet name
                logger.warning(f"Sheet name not provided, default to: {sheet_name}")
            
            # Check if file exists
            if not FileManager.ensure_file_exists(excel_filepath):
                raise FileNotFoundError(f"Excel file not found: {excel_filepath}")
                
            # Load Excel file using FileManager
            df = FileManager.load_excel_to_dataframe(excel_filepath, sheet_name)
            if df is None:
                raise ValueError(f"Failed to load Excel file: {excel_filepath}")
            logger.info("EXCEL file loaded successfully")
            ReportProcess._log_dataframe_sample(df, 10)
            
            # Validate columns
            expected_columns = self.EXPECTED_COLUMNS.get('statement', {})
            logger.debug(f"Expected columns: {expected_columns}")

            # 2. cleaning by handle na, null, another invalid values properly
            df = self._clean_dataframe(df, self.report_name.get('statement'))
            # 3. formatting values if needs
            # 4. fill missing values, columns(headers)
            
            logger.info("Statement processed successfully")
            return df
            
        except FileNotFoundError as e:
            logger.error(f"Statement file not found: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid value in statement: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing statement: {e}")
            raise