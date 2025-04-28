# src\utils\log_setup.py
import os
import sys
import logging
import uuid
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

# Constants
DEFAULT_LOG_DIR = './data/logs'
DEFAULT_LOG_LEVEL = 'DEBUG'
DEFAULT_MODULE_NAME = 'main'

class TruncateFilter(logging.Filter):
    """
    Custom logging filter to truncate extremely long messages
    """
    def filter(self, record):
        if isinstance(record.msg, str) and len(record.msg) > 10000:
            record.msg = record.msg[:10000] + "... [truncated]"
        return True

class LoggerManager:
    """
    Singleton manager for handling application-wide logging configuration
    """
    _instance = None
    _logger = None
    _run_id = None
    _initialized = False
    
    @classmethod
    def initialize(cls, 
                  log_dir: str = DEFAULT_LOG_DIR,
                  log_level: str = DEFAULT_LOG_LEVEL,
                  module: str = DEFAULT_MODULE_NAME,
                  run_id: Optional[str] = None) -> None:
        """
        Initialize the logger manager with configuration parameters.
        Should be called once at application startup.
        
        Args:
            log_dir: Directory to store log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            module: Base module name for the logger
            run_id: Unique identifier for this run, will be generated if not provided
        """
        print(f"Initializing loggerManager with kwargs: {locals()}")
        if not cls._initialized:
            print("no intialized yet, initializing...")
            # Generate run ID if not provided
            cls._run_id = run_id if run_id else str(uuid.uuid4())[:8]
            
            # Configure the logger
            cls._logger = cls._setup_logging(log_dir, log_level, module, cls._run_id)
            cls._initialized = True
    
    @classmethod
    def get_logger(cls) -> logging.Logger:
        """
        Get the configured logger instance.
        
        Returns:
            The configured logger instance
        
        Raises:
            RuntimeError: If logger hasn't been initialized
        """
        if not cls._initialized:
            print("no intialized yet, initializing...")
            run_id = None
            # Generate run ID if not provided
            cls._run_id = run_id if run_id else str(uuid.uuid4())[:8]
        
            cls._logger = cls._setup_logging(DEFAULT_LOG_DIR, DEFAULT_LOG_LEVEL, DEFAULT_MODULE_NAME, cls._run_id)
        return cls._logger
    
    @classmethod
    def get_run_id(cls) -> str:
        """
        Get the current run ID.
        
        Returns:
            The run ID for the current execution
            
        Raises:
            RuntimeError: If logger hasn't been initialized
        """
        if not cls._initialized:
            raise RuntimeError("Logger not initialized. Call LoggerManager.initialize() first.")
        return cls._run_id
    
    @staticmethod
    def _setup_logging(
        log_dir: str,
        log_level: str, 
        module: str,
        run_id: str
    ) -> logging.Logger:
        """
        Configure advanced logging with process and run ID tracking
        
        Args:
            log_dir: Directory to store log files
            log_level: Logging level
            module: Base module name for the logger
            run_id: Unique identifier for this run
        
        Returns:
            Configured logger instance
        """
        print("setting up logging...")
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log filename with timestamp
        log_filename = os.path.join(
            log_dir, 
            f'invoice_matcher_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )

        # Formatter with run ID
        formatter = logging.Formatter(
            f'%(process)d-%(thread)d [%(asctime)s.%(msecs)03d] [run:{run_id}] [%(module)s/%(funcName)s:%(lineno)d] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Get or create logger
        logger = logging.getLogger(module)
        logger.setLevel(log_level)
        
        # Remove existing handlers if any
        if logger.hasHandlers():
            logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(log_filename, encoding='utf-8', mode='a')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Add custom filter
        logger.addFilter(TruncateFilter())
        
        # Redirect stdout/stderr to UTF-8
        try:
            if sys.stdout.encoding != 'utf-8':
                sys.stdout.reconfigure(encoding='utf-8')
            if sys.stderr.encoding != 'utf-8':
                sys.stderr.reconfigure(encoding='utf-8')
            logger.info(f"Stdout/stderr encoding set to UTF-8")
        except Exception as e:
            logger.warning(f"Could not reconfigure stdout/stderr encoding: {e}")
        
        return logger

# Simple API for external modules
def initialize_logging(**kwargs) -> None:
    """
    Initialize the application-wide logger with the provided configuration.
    
    Args:
        **kwargs: Configuration parameters to pass to LoggerManager.initialize()
    """
    print(f"Initializing logger with kwargs: {kwargs}")
    LoggerManager.initialize(**kwargs)

def get_logger() -> logging.Logger:
    """
    Get the configured application logger.
    
    Returns:
        The configured logger instance
    """
    return LoggerManager.get_logger()

def get_run_id() -> str:
    """
    Get the current run ID.
    
    Returns:
        The run ID for the current execution
    """
    return LoggerManager.get_run_id()