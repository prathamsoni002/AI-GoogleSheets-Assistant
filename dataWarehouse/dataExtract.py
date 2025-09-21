import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

# Enhanced dependency checking
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logging.warning("openpyxl not available - Excel file support will be limited")

try:
    import xlrd
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False
    logging.warning("xlrd not available - Legacy Excel file support will be limited")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataExtractor:
    """
    Data extraction utilities for MITRA AI project
    Handles extraction from various file formats including error files
    """
    
    def __init__(self):
        self.excluded_message_numbers = [347, 161]  # Message numbers to avoid
        
    def extract_error_file_data(self, file_path: str) -> Dict[str, any]:
        """
        Extract and process error data from validation error file
        
        Args:
            file_path (str): Path to the error file (Excel/CSV)
            
        Returns:
            Dict containing processed error data and metadata
        """
        try:
            # Check file extension and dependencies
            file_ext = file_path.lower()
            
            if file_ext.endswith('.xlsx') or file_ext.endswith('.xlsm'):
                if not OPENPYXL_AVAILABLE:
                    raise ImportError(
                        "openpyxl is required to read .xlsx files. "
                        "Install it using: pip install openpyxl"
                    )
                df = pd.read_excel(file_path, engine='openpyxl')
                
            elif file_ext.endswith('.xls'):
                if not XLRD_AVAILABLE:
                    raise ImportError(
                        "xlrd is required to read .xls files. "
                        "Install it using: pip install xlrd"
                    )
                df = pd.read_excel(file_path, engine='xlrd')
                
            elif file_ext.endswith('.csv'):
                df = pd.read_csv(file_path)
                
            else:
                raise ValueError(
                    f"Unsupported file format: {file_ext}. "
                    "Supported formats: .xlsx, .xlsm, .xls, .csv"
                )
                
            logger.info(f"Successfully loaded error file: {file_path}")
            logger.info(f"Total rows in file: {len(df)}")
            
            # Process the error data
            processed_data = self._process_error_data(df)
            
            return {
                "status": "success",
                "total_errors": len(df),
                "filtered_errors": len(processed_data["error_summary"]),
                "excluded_count": processed_data["excluded_count"],
                "error_summary": processed_data["error_summary"],
                "error_details": processed_data["error_details"],
                "metadata": processed_data["metadata"]
            }
            
        except ImportError as e:
            logger.error(f"Dependency error for file {file_path}: {str(e)}")
            return {
                "status": "error",
                "message": f"Missing dependency: {str(e)}",
                "error_type": "dependency_error",
                "error_summary": [],
                "error_details": [],
                "metadata": {}
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "error_type": "processing_error",
                "error_summary": [],
                "error_details": [],
                "metadata": {}
            }
    
    def _process_error_data(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Process the error DataFrame and extract relevant information
        
        Args:
            df (pd.DataFrame): Raw error data
            
        Returns:
            Dict containing processed error information
        """
        # Standardize column names (handle case variations)
        df.columns = df.columns.str.strip().str.title()
        column_mapping = {
            'Type': 'Type',
            'Message Title': 'Message_Title', 
            'Message Class': 'Message_Class',
            'Message Number': 'Message_Number',
            'Message Count': 'Message_Count',
            'Date And Time (Utc)': 'DateTime_UTC'
        }
        
        # Rename columns to standardized format
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        
        # Filter for 'Error' type only
        error_df = df[df['Type'].str.upper() == 'ERROR'].copy()
        logger.info(f"Filtered to {len(error_df)} error records")
        
        # Remove excluded message numbers
        initial_count = len(error_df)
        error_df = error_df[~error_df['Message_Number'].isin(self.excluded_message_numbers)]
        excluded_count = initial_count - len(error_df)
        
        logger.info(f"Excluded {excluded_count} records with message numbers {self.excluded_message_numbers}")
        
        # Group by Message_Number and take one representative error per group
        error_summary = self._create_error_summary(error_df)
        
        # Get detailed breakdown
        error_details = self._get_error_details(error_df)
        
        # Create metadata
        metadata = self._create_metadata(error_df)
        
        return {
            "error_summary": error_summary,
            "error_details": error_details,
            "excluded_count": excluded_count,
            "metadata": metadata
        }
    
    def _create_error_summary(self, error_df: pd.DataFrame) -> List[Dict]:
        """
        Create a summary of unique errors (one per message number)
        
        Args:
            error_df (pd.DataFrame): Filtered error DataFrame
            
        Returns:
            List of dictionaries containing error summaries
        """
        # Group by Message_Number and get representative record + count
        summary_list = []
        
        for message_num, group in error_df.groupby('Message_Number'):
            # Get the first occurrence as representative
            representative = group.iloc[0]
            total_count = group['Message_Count'].sum() if 'Message_Count' in group.columns else len(group)
            
            summary_list.append({
                "message_number": int(message_num),
                "message_title": representative.get('Message_Title', 'N/A'),
                "message_class": representative.get('Message_Class', 'N/A'),
                "total_occurrences": int(total_count),
                "first_occurrence": representative.get('DateTime_UTC', 'N/A'),
                "sample_record": {
                    "type": representative.get('Type', 'N/A'),
                    "title": representative.get('Message_Title', 'N/A'),
                    "class": representative.get('Message_Class', 'N/A'),
                    "datetime": representative.get('DateTime_UTC', 'N/A')
                }
            })
        
        # Sort by total occurrences (descending) to prioritize most frequent errors
        summary_list.sort(key=lambda x: x['total_occurrences'], reverse=True)
        
        logger.info(f"Created summary for {len(summary_list)} unique error types")
        return summary_list
    
    def _get_error_details(self, error_df: pd.DataFrame) -> List[Dict]:
        """
        Get detailed breakdown of all error occurrences
        
        Args:
            error_df (pd.DataFrame): Filtered error DataFrame
            
        Returns:
            List of all error records with details
        """
        details_list = []
        
        for _, row in error_df.iterrows():
            details_list.append({
                "message_number": row.get('Message_Number', 'N/A'),
                "type": row.get('Type', 'N/A'),
                "title": row.get('Message_Title', 'N/A'),
                "class": row.get('Message_Class', 'N/A'),
                "count": row.get('Message_Count', 1),
                "datetime": row.get('DateTime_UTC', 'N/A')
            })
            
        return details_list
    
    def _create_metadata(self, error_df: pd.DataFrame) -> Dict:
        """
        Create metadata about the error dataset
        
        Args:
            error_df (pd.DataFrame): Filtered error DataFrame
            
        Returns:
            Dict containing metadata
        """
        if len(error_df) == 0:
            return {"message": "No valid errors found after filtering"}
        
        total_occurrences = error_df['Message_Count'].sum() if 'Message_Count' in error_df.columns else len(error_df)
        unique_error_types = error_df['Message_Number'].nunique()
        unique_classes = error_df['Message_Class'].nunique() if 'Message_Class' in error_df.columns else 0
        
        # Time range analysis
        datetime_col = 'DateTime_UTC'
        time_range = {}
        if datetime_col in error_df.columns:
            try:
                error_df[datetime_col] = pd.to_datetime(error_df[datetime_col], errors='coerce')
                time_range = {
                    "earliest_error": error_df[datetime_col].min().strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(error_df[datetime_col].min()) else 'N/A',
                    "latest_error": error_df[datetime_col].max().strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(error_df[datetime_col].max()) else 'N/A'
                }
            except:
                time_range = {"earliest_error": "N/A", "latest_error": "N/A"}
        
        metadata = {
            "total_error_occurrences": int(total_occurrences),
            "unique_error_types": int(unique_error_types),
            "unique_message_classes": int(unique_classes),
            "time_range": time_range,
            "most_frequent_error": self._get_most_frequent_error(error_df),
            "processing_timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return metadata
    
    def _get_most_frequent_error(self, error_df: pd.DataFrame) -> Dict:
        """Get the most frequently occurring error"""
        if len(error_df) == 0:
            return {"message": "No errors to analyze"}
        
        # Group by message number and sum counts
        if 'Message_Count' in error_df.columns:
            frequency_analysis = error_df.groupby('Message_Number').agg({
                'Message_Count': 'sum',
                'Message_Title': 'first',
                'Message_Class': 'first'
            }).reset_index()
            
            most_frequent = frequency_analysis.loc[frequency_analysis['Message_Count'].idxmax()]
            
            return {
                "message_number": int(most_frequent['Message_Number']),
                "title": most_frequent['Message_Title'],
                "class": most_frequent['Message_Class'],
                "total_count": int(most_frequent['Message_Count'])
            }
        else:
            # Fallback to record count
            most_frequent = error_df['Message_Number'].mode().iloc[0] if len(error_df['Message_Number'].mode()) > 0 else None
            if most_frequent:
                sample = error_df[error_df['Message_Number'] == most_frequent].iloc[0]
                return {
                    "message_number": int(most_frequent),
                    "title": sample.get('Message_Title', 'N/A'),
                    "class": sample.get('Message_Class', 'N/A'),
                    "total_count": len(error_df[error_df['Message_Number'] == most_frequent])
                }
        
        return {"message": "Unable to determine most frequent error"}

# Convenience function for external use
def extract_validation_errors(file_path: str) -> Dict[str, any]:
    """
    Convenience function to extract validation errors from file
    
    Args:
        file_path (str): Path to error file
        
    Returns:
        Dict containing processed error data
    """
    extractor = DataExtractor()
    return extractor.extract_error_file_data(file_path)
