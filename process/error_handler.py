import streamlit as st
import pandas as pd
import traceback
import logging
import os
import sys
from datetime import datetime

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, f'app_errors_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('crm_dashboard')


class ErrorHandler:
    """
    Class to handle errors in the application
    """
    
    @staticmethod
    def log_error(error, context=None):
        """
        Log an error with optional context
        
        Args:
            error: The exception object
            context: Optional context information (e.g., function name, input data)
        """
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'context': context or {}
        }
        
        # Log to file
        logger.error(
            f"Error: {error_details['error_type']} - {error_details['error_message']}\n"
            f"Context: {error_details['context']}\n"
            f"Traceback: {error_details['traceback']}"
        )
        
        return error_details
    
    @staticmethod
    def handle_data_error(func):
        """
        Decorator to handle errors in data processing functions
        
        Args:
            func: The function to decorate
            
        Returns:
            Wrapped function with error handling
        """
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                }
                error_details = ErrorHandler.log_error(e, context)
                
                # Return empty DataFrame or appropriate default value
                if func.__name__.startswith('calculate'):
                    return {}
                elif func.__name__.startswith('join'):
                    return pd.DataFrame()
                else:
                    return None
        
        return wrapper
    
    @staticmethod
    def display_error(error_details, show_traceback=False):
        """
        Display error information in the Streamlit UI
        
        Args:
            error_details: Dictionary with error information
            show_traceback: Whether to show the full traceback
        """
        st.error(
            f"Error: {error_details['error_type']} - {error_details['error_message']}"
        )
        
        if show_traceback:
            with st.expander("Error Details"):
                st.code(error_details['traceback'])
    
    @staticmethod
    def handle_missing_data(df, required_columns):
        """
        Check if required columns exist in the dataframe
        
        Args:
            df: DataFrame to check
            required_columns: List of required column names
            
        Returns:
            Tuple of (is_valid, missing_columns)
        """
        if df is None or df.empty:
            return False, ["DataFrame is empty or None"]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        is_valid = len(missing_columns) == 0
        
        return is_valid, missing_columns
    
    @staticmethod
    def safe_convert_dates(df, date_columns):
        """
        Safely convert date columns to datetime
        
        Args:
            df: DataFrame to process
            date_columns: List of column names to convert
            
        Returns:
            Processed DataFrame
        """
        if df is None or df.empty:
            return df
        
        result_df = df.copy()
        
        for col in date_columns:
            if col in result_df.columns:
                try:
                    result_df[col] = pd.to_datetime(result_df[col], errors='coerce')
                except Exception as e:
                    context = {
                        'function': 'safe_convert_dates',
                        'column': col,
                        'dataframe_info': f"Shape: {result_df.shape}, Columns: {result_df.columns.tolist()}"
                    }
                    ErrorHandler.log_error(e, context)
        
        return result_df


def try_except_decorator(func):
    """
    Decorator to wrap functions with try-except and display errors in Streamlit
    
    Args:
        func: The function to decorate
        
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = {
                'function': func.__name__,
                'args': str(args),
                'kwargs': str(kwargs)
            }
            error_details = ErrorHandler.log_error(e, context)
            
            # Display error in Streamlit
            st.error(f"Error in {func.__name__}: {str(e)}")
            
            # Show detailed error in expander
            with st.expander("Error Details"):
                st.code(traceback.format_exc())
            
            # Return appropriate default value
            return None
    
    return wrapper