#!/usr/bin/env python3
"""
Centralized Logging System for Endemic Grant Agent
Provides structured logging across all modules with rotation and formatting
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional
import sys

class GrantAgentLogger:
    """Centralized logger for Endemic Grant Agent"""
    
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GrantAgentLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is not None:
            return
            
        # Create logs directory
        log_dir = "/Users/home/grant_reports"
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure logger
        self._logger = logging.getLogger("endemic_grant_agent")
        self._logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if self._logger.handlers:
            return
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '%(levelname)-8s | %(message)s'
        )
        
        # File handler with rotation (10MB max, keep 5 files)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "system.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)
        
        # Log initial startup
        self._logger.info("=== Endemic Grant Agent Logger Initialized ===")
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Get logger instance with optional module name"""
        if name:
            return logging.getLogger(f"endemic_grant_agent.{name}")
        return self._logger
    
    def info(self, message: str, module: Optional[str] = None):
        """Log info level message"""
        logger = self.get_logger(module)
        logger.info(message)
    
    def warning(self, message: str, module: Optional[str] = None):
        """Log warning level message"""
        logger = self.get_logger(module)
        logger.warning(message)
    
    def error(self, message: str, module: Optional[str] = None, exc_info: bool = False):
        """Log error level message"""
        logger = self.get_logger(module)
        logger.error(message, exc_info=exc_info)
    
    def debug(self, message: str, module: Optional[str] = None):
        """Log debug level message"""
        logger = self.get_logger(module)
        logger.debug(message)


# Global logger instance
logger = GrantAgentLogger()

def get_logger(module_name: str = None) -> logging.Logger:
    """Convenience function to get logger for a module"""
    return logger.get_logger(module_name)

def log_function_start(func_name: str, module: str = None, **kwargs):
    """Log function start with parameters"""
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else "no parameters"
    logger.info(f"Starting {func_name}({params})", module)

def log_function_end(func_name: str, module: str = None, result: str = "completed"):
    """Log function completion"""
    logger.info(f"Finished {func_name}: {result}", module)

def log_processing_step(step: str, module: str = None, details: str = ""):
    """Log processing step with optional details"""
    message = f"Processing step: {step}"
    if details:
        message += f" | {details}"
    logger.info(message, module)

def log_error_with_context(error: Exception, context: str, module: str = None):
    """Log error with contextual information"""
    logger.error(f"Error in {context}: {str(error)}", module, exc_info=True)

def log_grant_processing(grant_name: str, organization: str, action: str, module: str = None):
    """Log grant-specific processing events"""
    logger.info(f"Grant Processing | {organization} - {grant_name} | {action}", module)

def log_validation_result(item_type: str, item_name: str, passed: bool, issues: str = "", module: str = None):
    """Log validation results"""
    status = "PASSED" if passed else "FAILED"
    message = f"Validation {status} | {item_type}: {item_name}"
    if issues and not passed:
        message += f" | Issues: {issues}"
    
    if passed:
        logger.info(message, module)
    else:
        logger.warning(message, module)

def log_performance_metric(operation: str, duration: float, module: str = None, **details):
    """Log performance metrics"""
    detail_str = ", ".join(f"{k}={v}" for k, v in details.items()) if details else ""
    message = f"Performance | {operation}: {duration:.2f}s"
    if detail_str:
        message += f" | {detail_str}"
    logger.info(message, module)


if __name__ == "__main__":
    # Test the logging system
    test_logger = get_logger("test_module")
    
    log_function_start("test_logging", "test_module", param1="value1", param2=123)
    logger.info("This is a test info message", "test_module")
    logger.warning("This is a test warning message", "test_module")
    logger.error("This is a test error message", "test_module")
    
    log_grant_processing("Test Grant", "Test Foundation", "validation", "test_module")
    log_validation_result("grant", "Test Grant", True, module="test_module")
    log_validation_result("question", "Test Question", False, "Invalid format", "test_module")
    log_performance_metric("grant_search", 2.5, "test_module", grants_found=10, sources_checked=5)
    
    log_function_end("test_logging", "test_module", "successfully")