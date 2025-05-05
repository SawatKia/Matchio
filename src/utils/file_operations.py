# src\utils\file_operations.py
import pandas as pd
import os
from re import match
from io import StringIO
from pathlib import Path
from typing import List, Optional

from utils import get_logger

logger = get_logger()

class FileManager:
    """Handles file operations for saving/loading data"""
    
    @staticmethod
    def ensure_directory_exists(file_path: str) -> None:
        """
        Ensure directory exists for file path
        
        Args:
            file_path: Path to file
        """
        try:
            directory = os.path.dirname(os.path.abspath(file_path))
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
        except PermissionError as e:
            logger.error(f"Permission denied when creating directory: {directory}. Error: {e}")
            raise
        except OSError as e:
            logger.error(f"OS error when creating directory: {directory}. Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to ensure directory exists: {directory}. Error: {e}")
            raise
    
    @staticmethod
    def ensure_file_exists(file_path: str) -> bool:
        """
        Check if file exists and log the result
        
        Args:
            file_path: Path to file
            
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            directory = os.path.dirname(file_path)
            if os.path.isdir(directory):
                # logger.debug(f"Directory contents: {os.listdir(directory)}")
                pass
            file_exists = Path(file_path).exists()
            if file_exists:
                logger.debug(f"File exists in directory: {directory}")
            if file_exists:
                logger.debug(f"File exists: {file_path}")
            else:
                logger.warning(f"File does not exist: {file_path}")
            return file_exists
        except PermissionError as e:
            logger.error(f"Permission denied when checking if file exists: {file_path}. Error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking if file exists: {file_path}. Error: {e}")
            return False
    
    @staticmethod
    def save_text(data: str, file_path: str, encoding: str = 'utf-8') -> None:
        """
        Save text data to file
        
        Args:
            data: Text data to save
            file_path: Path to save file
            encoding: File encoding
        """
        try:
            FileManager.ensure_directory_exists(file_path)
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(data)
            logger.info(f"Saved text data to {file_path}")
        except PermissionError as e:
            logger.error(f"Permission denied when saving text to {file_path}. Error: {e}")
            raise
        except UnicodeEncodeError as e:
            logger.error(f"Encoding error when saving text to {file_path}. Try a different encoding. Error: {e}")
            raise
        except IOError as e:
            logger.error(f"IO error when saving text to {file_path}. Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to save text data to {file_path}. Error: {e}")
            raise
    
    @staticmethod
    def save_dataframe(df: pd.DataFrame, file_path: str) -> None:
        """
        Save DataFrame to CSV, formatting datetime columns to yy-mm-dd
        and numeric columns to 2 decimal places.

        Args:
            df: DataFrame to save
            file_path: Path to save CSV
        """
        try:
            FileManager.ensure_directory_exists(file_path)

            buffer = StringIO()
            df.info(buf=buffer)
            info_str = buffer.getvalue()
            logger.debug(f"Dataframe info:\n{info_str}")

            df = df.copy()  # Work on a copy to avoid modifying original
        
            # Store original column types
            original_types = df.dtypes.to_dict()
            
            # Format datetime columns
            for column in df.select_dtypes(include=['datetime']):
                logger.info(f"Formatting datetime column: {column}")
                df[column] = df[column].apply(lambda x: x.strftime('%y-%m-%d %H:%M') 
                    if pd.notna(x) and x.time() != pd.Timestamp('00:00').time() 
                    else x.strftime('%y-%m-%d'))

            # Format float columns
            for column in df.select_dtypes(include=['float']):
                logger.info(f"Formatting float column: {column}")
                df[column] = df[column].apply(lambda x: f'{x:.2f}' if pd.notna(x) else '')

            # Format only original object columns
            for column, dtype in original_types.items():
                if dtype == 'object':
                    logger.info(f"Formatting object column: {column}")
                    df[column] = (df[column].astype(str)
                                .str.replace(r'\s+', ' ', regex=True)
                                .str.strip()
                                .apply(lambda x: f"'{x}" if pd.notna(x) and len(str(x)) > 0 else x))

            if Path(file_path).suffix == '.csv':
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            elif Path(file_path).suffix == '.xlsx':
                df.to_excel(file_path, index=False, encoding='utf-8-sig', engine='xlsxwriter')
                
            logger.info(f"Saved DataFrame to {file_path}")
            logger.debug(f"{'='*50}")
        except PermissionError as e:
            logger.error(f"Permission denied when saving DataFrame to {file_path}. Error: {e}")
            raise
        except AttributeError as e:
            logger.error(f"Attribute error when formatting datetime columns. Error: {e}")
            raise
        except ValueError as e:
            logger.error(f"Value error when saving DataFrame to {file_path}. Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to save DataFrame to {file_path}. Error: {e}")
            raise
    
    @staticmethod
    def load_csv_to_dataframe(file_path: str, encoding: str = "utf-8", fallback_to_express_format: bool = True) -> Optional[pd.DataFrame]:
        """
        Load DataFrame from CSV with fallback to Express format if standard loading fails
        
        Args:
            file_path: Path to CSV file
            encoding: File encoding for standard CSV (default: utf-8)
            fallback_to_express_format: Whether to attempt loading as Express format if standard loading fails
            
        Returns:
            DataFrame or None if file doesn't exist or loading fails
        """
        df = None
        try:
            if not FileManager.ensure_file_exists(file_path):
                logger.warning(f"File does not exist: {file_path}")
                return None
                
            logger.info(f"Attempting to load standard CSV from {file_path}")
            df = pd.read_csv(file_path, encoding=encoding, dtype=str)
            df.info()
            logger.debug(f"loaded dataframe:\n{df.head(20)}")
            return df
        except UnicodeDecodeError as e:
            logger.warning(f"Unicode decode error. Try a different encoding. Error: {e}")
            if fallback_to_express_format:
                try:
                    logger.info(f"Attempting to load as Express format due to encoding error")
                    df = FileManager.load_express_format_csv(file_path)
                    return df
                except Exception as fallback_e:
                    logger.error(f"Express format fallback failed after encoding error: {str(fallback_e)}")
                    return None
            return None
        except pd.errors.EmptyDataError as e:
            logger.error(f"CSV file is empty: {file_path}. Error: {e}")
            return None
        except pd.errors.ParserError as e:
            logger.warning(f"CSV parsing error: {str(e)}")
            if fallback_to_express_format:
                try:
                    logger.info(f"Attempting to load as Express format due to parser error")
                    df = FileManager.load_express_format_csv(file_path)
                    return df
                except Exception as fallback_e:
                    logger.error(f"Express format fallback failed after parser error: {str(fallback_e)}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Failed to load standard CSV: {str(e)}")
            if fallback_to_express_format:
                try:
                    logger.info(f"Attempting to load as Express format")
                    df = FileManager.load_express_format_csv(file_path)
                    return df
                except Exception as fallback_e:
                    logger.error(f"Express format fallback also failed: {str(fallback_e)}")
                    return None
            return None
            
    @staticmethod
    def load_express_format_csv(file_path: str, encoding: str = "cp874") -> pd.DataFrame:
        """
        Load and process Express program formatted CSV report
        
        Args:
            file_path: Path to the Express format CSV file
            encoding: File encoding (default: cp874 for Thai language support)
            
        Returns:
            DataFrame containing the processed report data
        """
        try:
            if not FileManager.ensure_file_exists(file_path):
                error_msg = f"Express format CSV file not found: {file_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
                
            logger.info(f"Loading Express format CSV from {file_path}")
            
            # Read raw file content
            raw_lines = FileManager.load_raw_csv(file_path, encoding)
            
            # Filter lines that start with a number sequence (may have spaces before)
            filtered_lines = [line for line in raw_lines if match(r'^\s*"\s+\d+",', line)]
            display_items = 20
            logger.debug(f"Filtered {len(filtered_lines)} valid data lines")
            
            if not filtered_lines:
                error_msg = f"No valid data lines found in Express format file"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            filtered_sample = '\n'.join(filtered_lines[:display_items])
            logger.debug(f"Filtered lines: \n{filtered_sample}\n ...{display_items}/{len(filtered_lines)}...")
            
            # Convert to DataFrame
            csv_buffer = StringIO("".join(filtered_lines))
            csv_sample = csv_buffer.getvalue()[:500]
            logger.debug(f"CSV data sample: \n{csv_sample}...remaining{len(csv_buffer.getvalue())-500} characters...")
            
            express_df = pd.read_csv(csv_buffer, header=None, dtype=str)
            logger.debug(f"Express format data loaded: {express_df.shape[0]} rows, {express_df.shape[1]} columns")
            
            return express_df
        except FileNotFoundError as e:
            logger.error(f"Express format CSV file not found: {file_path}. Error: {e}")
            raise
        except UnicodeDecodeError as e:
            logger.error(f"Unicode decode error with Express format. Try a different encoding. Error: {e}")
            raise
        except pd.errors.EmptyDataError as e:
            logger.error(f"Express format CSV file is empty: {file_path}. Error: {e}")
            raise
        except pd.errors.ParserError as e:
            logger.error(f"Express format CSV parsing error: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Value error with Express format CSV: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to load Express format CSV: {str(e)}")
            raise

    @staticmethod
    def load_raw_csv(file_path:str, encoding:str = "utf-8") -> List[str]:
        """
        Load raw CSV file and return lines
        
        Args:
            file_path: Path to CSV file
            encoding: File encoding
            
        Returns:
            List of strings, each representing a line in the CSV
        """
        try:
            # Read raw file content
            with open(file_path, encoding=encoding) as f:
                raw_lines = f.readlines()
            
            display_items = 15
            logger.debug(f"Loaded {len(raw_lines)} lines from csv file")
            raw_sample = '\n'.join(raw_lines[:display_items])
            logger.debug(f"RAW lines sample: \n{raw_sample}\n...display {display_items}/{len(raw_lines)}...")
            return raw_lines
        except FileNotFoundError as e:
            logger.error(f"Raw CSV file not found: {file_path}. Error: {e}")
            raise
        except PermissionError as e:
            logger.error(f"Permission denied when reading raw CSV: {file_path}. Error: {e}")
            raise
        except UnicodeDecodeError as e:
            logger.error(f"Unicode decode error when reading raw CSV: {file_path}. Try a different encoding. Error: {e}")
            raise
        except IOError as e:
            logger.error(f"IO error when reading raw CSV: {file_path}. Error: {e}")
            raise
        except Exception as e:
            logger.error(f"csv loading error: {e}")
            raise
    
    @staticmethod
    def load_excel_to_dataframe(file_path: str, sheet_name: str) -> pd.DataFrame:
        """
        Load Excel sheet into DataFrame
        
        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to load
            
        Returns:
            DataFrame containing sheet data
        """
        try:
            # df = pd.read_excel(
            #     file_path,
            #     sheet_name=sheet_name,
            #     engine="openpyxl",
            #     dtype=str  # convert all columns to string
            # )
            # Custom converter for tax ID column to preserve leading zeros and formatting
            converters = {
                'เลขประจำตัวผู้เสียภาษี': lambda x: str(x).replace(' ', '')  # Remove spaces
                if pd.notna(x) else x
            }
            
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                engine="openpyxl",
                dtype=str,  # Convert all columns to string
                converters=converters  # Apply custom converter to tax ID
            )
            df.info()
            logger.debug(f"loaded excel: \n{df.head(5)}")
            return df
        except FileNotFoundError as e:
            logger.error(f"Excel file not found: {file_path}. Error: {e}")
            raise
        except PermissionError as e:
            logger.error(f"Permission denied when reading Excel file: {file_path}. Error: {e}")
            raise
        except ValueError as e:
            logger.error(f"Value error when reading Excel file: {file_path}. Sheet '{sheet_name}' might not exist. Error: {e}")
            raise
        except KeyError as e:
            logger.error(f"Key error when reading Excel file: {file_path}. Sheet '{sheet_name}' might not exist. Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load Excel file: {file_path}, sheet: {sheet_name}. Error: {e}")
            raise
    
    @staticmethod
    def list_excel_sheets(file_path: str) -> List[str]:
        """
        List sheet names in Excel file

        Args:
            file_path: Path to Excel file
            
        Returns:
            List of sheet names
        """
        try:
            # Load the Excel file
            excel_file = pd.ExcelFile(file_path)

            # Get the list of sheet names
            sheet_names = excel_file.sheet_names
            sheets_indent = '.\n\t\t- '.join(sheet_names)
            logger.debug(f"excel file: {file_path}\n\tSheets: {sheets_indent}")
            return sheet_names
        except FileNotFoundError as e:
            logger.error(f"Excel file not found: {file_path}. Error: {e}")
            raise
        except PermissionError as e:
            logger.error(f"Permission denied when reading Excel file: {file_path}. Error: {e}")
            raise
        except pd.errors.EmptyDataError as e:
            logger.error(f"Excel file is empty: {file_path}. Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to list sheets in Excel file: {file_path}. Error: {e}")
            raise
    
    @staticmethod
    def save_ocr_results(pages_text: List[str], file_path: str, encoding: str = 'utf-8') -> None:
        """
        Save OCR results to text file with page markers
        
        Args:
            pages_text: List of text for each page
            file_path: Path to save file
            encoding: File encoding
        """
        try:
            FileManager.ensure_directory_exists(file_path)
            with open(file_path, 'w', encoding=encoding) as f:
                for page_num, text in enumerate(pages_text, 1):
                    f.write(f"\n{'='*50}\nPage {page_num}\n{'='*50}\n\n")
                    f.write(f"{text[:500]}...")
                    f.write(f"\n...(remaining {len(text[500:])} characters)...\n")
            logger.info(f"Saved OCR results to {file_path}")
        except PermissionError as e:
            logger.error(f"Permission denied when saving OCR results to {file_path}. Error: {e}")
            raise
        except UnicodeEncodeError as e:
            logger.error(f"Encoding error when saving OCR results to {file_path}. Try a different encoding. Error: {e}")
            raise
        except IOError as e:
            logger.error(f"IO error when saving OCR results to {file_path}. Error: {e}")
            raise
        except TypeError as e:
            logger.error(f"Type error when saving OCR results. Ensure pages_text is a list of strings. Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to save OCR results to {file_path}. Error: {e}")
            raise