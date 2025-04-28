# src\utils\data_cleaner.py
import pandas as pd
import numpy as np
import math
import re
import json
from typing import Tuple, List
from utils import get_logger

logger = get_logger()

class DataFrameCleaner:
    """Handles DataFrame cleaning with single responsibility methods"""
    
    @staticmethod
    def fill_missing_values(df: pd.DataFrame, columns: List[str], default_values: List[str]) -> pd.DataFrame:
        """Fill missing values in specified columns with specific values"""
        try:
            if df is None or df.empty:
                raise ValueError("DataFrame is empty.")
            if len(columns) != len(default_values):
                raise ValueError("Columns and default values must have the same length.")
            
            # Check if columns exist in DataFrame
            missing_cols = [col for col in columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Columns {missing_cols} not found in DataFrame")
            
            filled_df = df.copy()

            for col, default_value in zip(columns, default_values):
                filled_df[col] = filled_df[col].fillna(default_value)
                logger.debug(f"Filled column '{col}' with default value '{default_value}'")

            return filled_df
        except Exception as e:
            logger.error(f"Error filling missing values: {e}")
            raise
    
    @staticmethod
    def find_na_rows(df: pd.DataFrame, columns: List[str]) -> None:
        """Find rows with NA values in specified columns"""
        try:
            for column in columns:
                if column not in df.columns:
                    raise ValueError(f"Column {column} not found in DataFrame")
                any_na_rows = df[[column]].isna().any(axis=1)
                logger.debug(f"any_na_rows: \n{any_na_rows}")
                rows = df.index[any_na_rows].tolist()
                if any_na_rows.any():
                    logger.debug(f"Found rows containing NA values: \n{rows}")
                    # Display the actual data of rows containing NA values
                    na_rows_data = df[any_na_rows]
                    logger.debug(f"NA rows data:\n{na_rows_data}")
                    logger.warning(f"Column '{column}' contains NaN values")
                else:
                    logger.debug(f"No NA values found in column {column}")
        except Exception as e:
            logger.error(f"Error finding NA rows: {e}")
            raise

    @staticmethod
    def remove_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows where all values are null/empty"""
        try:
            before_count = len(df)
            # Store indices before dropping
            before_indices = set(df.index)
            any_na_rows = df.isna().any(axis=1)
            rows = df.index[any_na_rows].tolist()
            if any_na_rows.any():
                logger.debug(f"Found rows containing NA values: \n{rows}")
                # Display the actual data of rows containing NA values
                na_rows_data = df[any_na_rows]
                logger.debug(f"NA rows data:\n{na_rows_data}")
                df = df.dropna(how='any')
                # Find dropped indices
                dropped_indices = before_indices - set(df.index)
                removed_count = before_count - len(df)
                logger.debug(f"Removed {removed_count} empty rows at indices: {sorted(list(dropped_indices))}")
            else:
                logger.debug("No any empty rows found")
            return df
        except Exception as e:
            logger.error(f"Error removing empty rows: {e}")
            raise

    @staticmethod
    def remove_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Remove columns where all values are null/empty"""
        before_cols = df.columns.tolist()
        logger.debug("Removing column containing only empty values['X', 'x', '']")
        logger.debug(f"Before removing empty columns: {before_cols}")
        df = df.replace(['X', 'x', ''], np.nan)
        df = df.dropna(axis=1, how='all')
        removed_cols = set(before_cols) - set(df.columns.tolist())
        if removed_cols:
            logger.debug(f"Removed empty columns: {sorted(removed_cols)}")
        return df

    @staticmethod
    def is_valid_content(text: str) -> bool:
        """Check if string contains Thai, English, or numbers"""
        if pd.isna(text):
            return False
        # Thai unicode range: \u0E00-\u0E7F
        # English letters and numbers
        pattern = r'[\u0E00-\u0E7F\w\d]+'
        return bool(re.search(pattern, str(text)))

    @staticmethod
    def remove_invalid_content_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Remove columns with no valid Thai/English/numeric content"""
        try:
            invalid_cols = []
            for col in df.columns:
                # Check if column has any valid content
                if not df[col].apply(DataFrameCleaner.is_valid_content).any():
                    invalid_cols.append(col)
            
            if invalid_cols:
                logger.debug(f"Removing columns with no valid content: {invalid_cols}")
                df = df.drop(columns=invalid_cols)
            return df
        except Exception as e:
            logger.error(f"Error removing invalid content columns: {e}")
            raise

    @staticmethod
    def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Convert columns to numeric if valid:
        - Only 0 or 1 NaN allowed
        - No leading zeros in values
        - More than 80% numeric-like values
        """
        for col in df.columns:
            try:
                logger.debug(f"Processing column '{col}' for numeric conversion")
                # Skip non-object dtype
                if pd.api.types.is_numeric_dtype(df[col]):
                    logger.debug(f"Skipped column '{col}' due to already numeric dtype")
                    continue
                elif not pd.api.types.is_object_dtype(df[col]):
                    logger.debug(f"Skipped column '{col}' due to non-object dtype")
                    continue
    
                # Count real NaN and empty values (before string conversion)
                nan_count = df[col].isna().sum() + (df[col] == '').sum()
                
                # Skip if too many NaNs
                if nan_count > 1:
                    logger.debug(f"Column '{col}' has {nan_count} NaNs/nulls")
                    logger.debug(f"Skipped column '{col}' due to NaN count > 1")
                    continue

                # Convert to string for analysis
                string_values = df[col].astype(str).str.strip()

                # Check for company tax ID pattern (13 digits)
                company_tax_id_pattern = r'^\d{13}$'
                has_tax_id = string_values.str.match(company_tax_id_pattern).any()
                if has_tax_id:
                    logger.debug(f"Skipped column '{col}' due to company tax ID pattern")
                    continue
    
                # Check if more than 80% are numeric
                numeric_mask = pd.to_numeric(string_values, errors='coerce').notna()
                if numeric_mask.mean() > 0.8:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    logger.debug(f"Converted column '{col}' to numeric")
                    continue

                # Check for document ID patterns (including partial matches)
                id_pattern = r'^(?:\d{1,4}[-/]?\d{1,4}|[A-Z]{2,}\d+|\d{6,})'
                has_id_format = string_values.str.match(id_pattern).any()

                if has_id_format:
                    logger.debug(f"Skipped column '{col}' due to document ID pattern")
                    continue
    
                logger.debug(f"Skipped column '{col}' due to non-numeric values")
    
            except Exception as e:
                logger.debug(f"Could not convert column '{col}': {e}")
                raise
                
        return df

    @staticmethod
    def standardize_whitespace(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize whitespace in string columns"""
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip() # Converts values to strings (handles non-string data safely) and Removes leading/trailing whitespace
            #NOTE - Use with CAUTION! the following line may impact the performance on a large dataset, consider using apply instead
            df[col] = df[col].replace(r'\s+', ' ', regex=True) # Replaces internal space in the string with single space
            logger.debug(f"Standardized whitespace in column '{col}'")
        return df
    
    @staticmethod
    def _convert_thai_date(date_str: str) -> str:
        """
        Convert Thai Buddhist calendar date to a standardized format

        :param date_str: Input date string
        :return: Converted date string
        """
        try:
            # Handle Excel datetime objects (date with "-")
            if isinstance(date_str, str) and "-" in date_str:
                try:
                    # Parse Excel datetime format
                    date_obj = pd.to_datetime(date_str)
                    dd = date_obj.day
                    mm = date_obj.month
                    # Convert year from Buddhist calendar (CE + 43), if the year is 6x
                    yy = (date_obj.year - 1900) - 43  # Adjust for 2-digit year
                    return f"{dd:02d}/{mm:02d}/{yy:02d}"
                except ValueError:
                    logger.warning(f"Failed to parse Excel datetime format for {date_str}")
                    return date_str
            
            # Handle string dates with "/" (General type)
            elif isinstance(date_str, str) and "/" in date_str:
                dd, mm, yy = date_str.split("/")
                # Ensure yy is 2 digits and convert from BE to CE
                yy = int(yy) - 43 if len(yy) == 2 else int(yy[-2:]) - 43
                return f"{int(dd):02d}/{int(mm):02d}/{yy:02d}"
                
            return date_str
        except Exception as e:
            logger.warning(f"Date conversion failed for {date_str}: {str(e)}")
            return date_str
    
    @staticmethod
    def _find_date_column(df: pd.DataFrame) -> List[str]:
        """
        find a column that look like date column from a datafram by Regex
        """
        try:
            possible_date_formats = [
                # Year first formats (YYYY-MM-DD or YY-MM-DD)
                r'^\d{2,4}[\/\-\.]{1}\d{1,2}[\/\-\.]{1}\d{1,2}',
                # Day first formats (DD-MM-YYYY or DD-MM-YY)
                r'^\d{1,2}[\/\-\.]{1}\d{1,2}[\/\-\.]{1}\d{2,4}',
                # Add support for month names (Jan-15-2024)
                r'^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\/\-\s\.]{1}\d{1,2}[\/\-\s\.]{1}\d{2,4}$'
            ]
            date_columns = []
            for col in df.columns:
                if df[col].dtype == 'datetime64[ns]':
                    date_columns.append(col)
                elif df[col].dtype == 'object':  # Only check object type columns
                    if df[col].dropna().astype(str).str.match('|'.join(possible_date_formats)).any():
                        date_columns.append(col)
                        logger.debug(f"found date column: {col}")
            return date_columns

        except Exception as e:
            logger.error(f"Error finding date columns: {e}")
            raise

    @staticmethod
    def _find_time_column(df: pd.DataFrame) -> List[str]:
        """Find columns containing time format data"""
        try:
            # Time format patterns
            time_patterns = [
                r'^\d{1,2}:\d{2}(?::\d{2})?$',  # HH:MM or HH:MM:SS
                r'^(?:2[0-3]|[01]?[0-9]):[0-5][0-9](?::[0-5][0-9])?$'  # Strict time validation
            ]
            
            time_columns = []
            for col in df.columns:
                if df[col].dtype == 'object':  # Only check string columns
                    # Check if any non-null value matches time pattern
                    if df[col].dropna().astype(str).str.match('|'.join(time_patterns)).any():
                        time_columns.append(col)
                        logger.debug(f"found time column: {col}")
            
            return time_columns
    
        except Exception as e:
            logger.error(f"Error finding time columns: {e}")
            raise

    @staticmethod
    def merge_transaction_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge transaction-related columns and add transaction type indicator
        """
        try:
            logger.info("Merging transaction and datetime columns")
            df = df.copy()
            
            # 1. Find date and time columns
            date_columns = DataFrameCleaner._find_date_column(df)
            time_columns = DataFrameCleaner._find_time_column(df)
            
            if not date_columns:
                raise ValueError("No date column found")
            
            # Use first found date column
            date_col = date_columns[0]
            
            # 2. Merge date and time if time column exists
            if time_columns:
                time_col = time_columns[0]
                df['datetime'] = pd.to_datetime(
                    df[date_col].astype(str) + ' ' + 
                    df[time_col].fillna('00:00:00').astype(str)
                )
            else:
                df['datetime'] = pd.to_datetime(df[date_col])
                logger.debug("No time column found, using date only")
            
            # 3. Identify deposit/withdrawal columns by name
            deposit_col = next((col for col in df.columns if 'ฝาก' in col), None)
            withdraw_col = next((col for col in df.columns if 'ถอน' in col), None)
            
            if not (deposit_col and withdraw_col):
                raise ValueError("Could not find deposit/withdrawal columns")
            
            # 4. Create amount column and isDeposit indicator
            df[deposit_col] = pd.to_numeric(df[deposit_col], errors='coerce').fillna(0).astype(float)
            df[withdraw_col] = pd.to_numeric(df[withdraw_col], errors='coerce').fillna(0).astype(float)
            
            # Set amount based on which column has a value
            df['amount'] = 0.0
            df['isDeposit'] = "False"
            
            # Handle deposits
            deposit_mask = df[deposit_col] > 0
            df.loc[deposit_mask, 'amount'] = df.loc[deposit_mask, deposit_col]
            df.loc[deposit_mask, 'isDeposit'] = "True"
            
            # Handle withdrawals
            withdraw_mask = df[withdraw_col] > 0
            df.loc[withdraw_mask, 'amount'] = df.loc[withdraw_mask, withdraw_col]
            df.loc[withdraw_mask, 'isDeposit'] = "False"
            
            # Round amounts to 2 decimal places
            df['amount'] = df['amount'].round(2)
            
            # 6. Rename remaining columns
            column_mapping = {
                'คงเหลือ': 'balance',
                'หน้าที่': 'page'
            }
            df = df.rename(columns=column_mapping)
            
            # 7. Select and reorder columns
            final_columns = ['datetime', 'amount', 'isDeposit', 'balance', 'page']
            df = df[final_columns]
            
            logger.debug(f"Merged transaction columns. Result:\n{df.head()}")
            return df
            
        except Exception as e:
            logger.error(f"Error merging transaction columns: {e}")
            raise

    @staticmethod
    def clean_purchase_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
        """
        Clean DataFrame using a sequential pipeline of cleaning operations
        
        Args:
            df: Input DataFrame to clean
            
        Returns:
            Tuple of (cleaned DataFrame, cleaning stats dictionary)
        """
        stats = {
            'original_shape': df.shape,
            'removed_rows': 0,
            'removed_columns': 0
        }
        
        try:
            logger.info("Starting DataFrame cleaning process")
            # Make a copy to avoid modifying original
            df = df.copy()
            
            # Remove empty columns
            original_cols = len(df.columns)
            df = DataFrameCleaner.remove_empty_columns(df)
            
            # Remove invalid content columns
            df = DataFrameCleaner.remove_invalid_content_columns(df)
            stats['removed_columns'] = original_cols - len(df.columns)

            # Convert numeric columns
            df = DataFrameCleaner.convert_numeric_columns(df)
            
            # Remove empty rows
            original_rows = len(df)
            df = DataFrameCleaner.remove_empty_rows(df)
            stats['removed_rows'] = original_rows - len(df)
            
            # Standardize whitespace
            df = DataFrameCleaner.standardize_whitespace(df)

            # standardize date format
            date_columns = DataFrameCleaner._find_date_column(df)
            logger.debug(f"Found date columns: {date_columns}")
            if not date_columns:
                logger.warning("No date columns found for conversion")
                raise ValueError("No date columns found for conversion")

            for col in date_columns:
                df[col] = df[col].astype(str).apply(DataFrameCleaner._convert_thai_date)
                df[col] = pd.to_datetime(df[col])
                logger.info(f"Converted column '{col}' to datetime")

            
            stats['final_shape'] = df.shape
            logger.info(f"Cleaning complete. Stats: \n{json.dumps(stats, indent=4)}")
            
            return df, stats
            
        except Exception as e:
            logger.error(f"Error cleaning DataFrame: {e}")
            raise
    
    @staticmethod
    def clean_sale_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
        """
        Clean DataFrame using a sequential pipeline of cleaning operations
        
        Args:
            df: Input DataFrame to clean
            
        Returns:
            Tuple of (cleaned DataFrame, cleaning stats dictionary)
        """
        stats = {
            'original_shape': df.shape,
            'removed_rows': 0,
            'removed_columns': 0
        }
        
        try:
            logger.info("Starting DataFrame cleaning process")
            # Make a copy to avoid modifying original
            df = df.copy()
            
            # Remove empty columns
            original_cols = len(df.columns)
            df = DataFrameCleaner.remove_empty_columns(df)
            
            # Remove invalid content columns
            df = DataFrameCleaner.remove_invalid_content_columns(df)
            stats['removed_columns'] = original_cols - len(df.columns)

            # Convert numeric columns
            df = DataFrameCleaner.convert_numeric_columns(df)
            df = DataFrameCleaner.fill_missing_values(df, [5], ['0000000000000'])

            # Remove empty rows
            original_rows = len(df)
            df = DataFrameCleaner.remove_empty_rows(df)
            stats['removed_rows'] = original_rows - len(df)
            
            # Standardize whitespace
            df = DataFrameCleaner.standardize_whitespace(df)

            # standardize date format
            date_columns = DataFrameCleaner._find_date_column(df)
            logger.debug(f"Found date columns: {date_columns}")
            if not date_columns:
                logger.warning("No date columns found for conversion")
                raise ValueError("No date columns found for conversion")

            for col in date_columns:
                df[col] = df[col].astype(str).apply(DataFrameCleaner._convert_thai_date)
                df[col] = pd.to_datetime(df[col])
                logger.info(f"Converted column '{col}' to datetime")

            
            stats['final_shape'] = df.shape
            logger.info(f"Cleaning complete. Stats: \n{json.dumps(stats, indent=4)}")
            
            return df, stats
            
        except Exception as e:
            logger.error(f"Error cleaning DataFrame: {e}")
            raise
    
    @staticmethod
    def clean_withholding_tax_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
        """
        Clean DataFrame using a sequential pipeline of cleaning operations
        
        Args:
            df: Input DataFrame to clean
            
        Returns:
            Tuple of (cleaned DataFrame, cleaning stats dictionary)
        """
        stats = {
            'original_shape': df.shape,
            'removed_rows': 0,
            'removed_columns': 0
        }
        
        try:
            logger.info("Starting DataFrame cleaning process")
            # Make a copy to avoid modifying original
            df = df.copy()
            
            # Remove empty columns
            original_cols = len(df.columns)
            df = DataFrameCleaner.remove_empty_columns(df)
            df = df.iloc[:, :5]  # Keep only first 5 columns
            logger.info("keep only first 5 columns")
            
            # Remove invalid content columns
            df = DataFrameCleaner.remove_invalid_content_columns(df)
            
            stats['removed_columns'] = original_cols - len(df.columns)

            # Remove empty rows
            DataFrameCleaner.find_na_rows(df, [r'ชื่อและที่อยู่ผู้หักภาษี'])
            original_rows = len(df)
            df = DataFrameCleaner.remove_empty_rows(df)
            stats['removed_rows'] = original_rows - len(df)
            # pad leading zero to 'เลขประจำตัวผู้เสียภาษี' column that have less than 13 digits
            df['เลขประจำตัวผู้เสียภาษี'] = df['เลขประจำตัวผู้เสียภาษี'].astype(str)
            df['เลขประจำตัวผู้เสียภาษี'] = df['เลขประจำตัวผู้เสียภาษี'].apply(lambda x: x.zfill(13) if len(x) < 13 else x)
            logger.debug(f"df after removing empty rows/columns and padd leading zero: \n{df.head(5)}")

            # Convert numeric columns
            df = DataFrameCleaner.convert_numeric_columns(df)
            
            # Standardize whitespace
            df = DataFrameCleaner.standardize_whitespace(df)

            # standardize date format
            date_columns = DataFrameCleaner._find_date_column(df)
            logger.debug(f"Found date columns: {date_columns}")
            if not date_columns:
                logger.warning("No date columns found for conversion")
                raise ValueError("No date columns found for conversion")

            for col in date_columns:
                df[col] = df[col].astype(str).apply(DataFrameCleaner._convert_thai_date)
                df[col] = pd.to_datetime(df[col])
                logger.info(f"Converted column '{col}' to datetime")    

            if df.empty:
                logger.debug(f"invalid input data")
                raise ValueError(f"invalid input data")
            
            stats['final_shape'] = df.shape
            logger.info(f"Cleaning complete. Stats: \n{json.dumps(stats, indent=4)}")
            
            return df, stats
            
        except Exception as e:
            logger.error(f"Error cleaning DataFrame: {e}")
            raise
    
    @staticmethod
    def clean_statement_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
        """
        Clean DataFrame using a sequential pipeline of cleaning operations
        
        Args:
            df: Input DataFrame to clean
            
        Returns:
            Tuple of (cleaned DataFrame, cleaning stats dictionary)
        """
        stats = {
            'original_shape': df.shape,
            'removed_rows': 0,
            'removed_columns': 0
        }
        
        try:
            logger.info("Starting DataFrame cleaning process")
            # Make a copy to avoid modifying original
            df = df.copy()
            
            # Remove empty columns
            original_cols = len(df.columns)
            df = df.iloc[:, :6]
            df = DataFrameCleaner.remove_empty_columns(df)
            
            # Remove invalid content columns
            df = DataFrameCleaner.remove_invalid_content_columns(df)

            df = DataFrameCleaner.merge_transaction_columns(df)
            stats['removed_columns'] = original_cols - len(df.columns)

            # Convert numeric columns
            df = DataFrameCleaner.convert_numeric_columns(df)

            # Remove empty rows
            original_rows = len(df)
            df = DataFrameCleaner.remove_empty_rows(df)
            stats['removed_rows'] = original_rows - len(df)
            
            # Standardize whitespace
            df = DataFrameCleaner.standardize_whitespace(df)  
            
            stats['final_shape'] = df.shape
            logger.info(f"Cleaning complete. Stats: \n{json.dumps(stats, indent=4)}")
            
            return df, stats
            
        except Exception as e:
            logger.error(f"Error cleaning DataFrame: {e}")
            raise