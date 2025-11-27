"""
Logging System Module

This module provides utilities for logging execution time of agent public methods.
Each log entry is written as a JSON object to a log file with rotating file support.
"""

import json
import time
import functools
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from pathlib import Path


# Default rotation settings
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5


class AgentLogger:
    """
    A logger class for tracking agent method execution times.
    
    Writes log entries in JSON format to a log file, where each line represents
    a single method execution with timing information. Supports rotating log files
    to prevent unbounded log growth.
    
    Attributes:
        log_file (str): Path to the log file where entries are written
        max_bytes (int): Maximum size of a log file in bytes before rotation
        backup_count (int): Number of backup files to keep
    """
    
    def __init__(self, log_file="agent_execution.log", max_bytes=None, backup_count=None):
        """
        Initialize the AgentLogger with rotating file support.
        
        Args:
            log_file (str): Path to the log file. Defaults to "agent_execution.log"
                           in the current working directory.
            max_bytes (int, optional): Maximum size of a log file in bytes before rotation.
                                      Defaults to 10 MB (10 * 1024 * 1024 bytes).
            backup_count (int, optional): Number of backup files to keep.
                                         Defaults to 5 (files: .log, .log.1, .log.2, .log.3, .log.4, .log.5).
        
        Raises:
            OSError: If the log directory cannot be created due to permission issues
        """
        self.log_file = log_file
        self.max_bytes = max_bytes if max_bytes is not None else DEFAULT_MAX_BYTES
        self.backup_count = backup_count if backup_count is not None else DEFAULT_BACKUP_COUNT
        
        # Ensure log directory exists
        log_path = Path(log_file)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            import sys
            print(f"Warning: Cannot create log directory {log_path.parent}: {e}", file=sys.stderr)
            print(f"Logging will be attempted but may fail.", file=sys.stderr)
        
        # Set up rotating file handler
        self._handler = None
        self._setup_handler()
    
    def _setup_handler(self):
        """Set up the rotating file handler."""
        try:
            self._handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            # Use a simple formatter that outputs only the message (JSON entry)
            formatter = logging.Formatter('%(message)s')
            self._handler.setFormatter(formatter)
        except (IOError, OSError) as e:
            import sys
            print(f"Warning: Failed to create rotating file handler for {self.log_file}: {e}", file=sys.stderr)
            self._handler = None
    
    def log_execution(self, agent_name, method_name, execution_time, args_info=None, success=True, error=None):
        """
        Write a log entry to the log file in JSON format.
        
        Args:
            agent_name (str): Name of the agent executing the method
            method_name (str): Name of the method being executed
            execution_time (float): Time taken to execute the method in seconds
            args_info (dict, optional): Information about method arguments including tid, day, hour. Defaults to None.
            success (bool, optional): Whether the method executed successfully. Defaults to True.
            error (str, optional): Error message if method failed. Defaults to None.
        """
        log_entry = {
            "time": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            "agent_name": agent_name,
            "method_name": method_name,
            "execution_time_seconds": round(execution_time, 4),
            "success": success
        }
        
        if args_info:
            # Include tid, day, and hour from args_info
            if 'tid' in args_info:
                log_entry["tid"] = args_info['tid']
            if 'day' in args_info:
                log_entry["day"] = args_info['day']
            if 'hour' in args_info:
                log_entry["hour"] = args_info['hour']
        
        if error:
            log_entry["error"] = str(error)
        
        # Write as single-line JSON with error handling using rotating file handler
        try:
            if self._handler is not None:
                # Create a log record and emit it through the rotating handler
                record = logging.LogRecord(
                    name='agent_logger',
                    level=logging.INFO,
                    pathname='',
                    lineno=0,
                    msg=json.dumps(log_entry),
                    args=(),
                    exc_info=None
                )
                self._handler.emit(record)
            else:
                # Fallback to direct file write if handler setup failed
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
        except IOError as e:
            # If logging fails, print to stderr but don't crash the application
            import sys
            print(f"Warning: Failed to write to log file {self.log_file}: {e}", file=sys.stderr)
    
    def close(self):
        """Close the rotating file handler."""
        if self._handler is not None:
            self._handler.close()
            self._handler = None


# Global logger instance
_default_logger = None


def get_logger(log_file=None, max_bytes=None, backup_count=None):
    """
    Get the global logger instance or create one if it doesn't exist.
    
    Args:
        log_file (str, optional): Path to the log file. If None and no logger exists,
                                  defaults to "agent_execution.log". If a logger already
                                  exists, the existing logger is returned regardless of
                                  this parameter.
        max_bytes (int, optional): Maximum size of a log file in bytes before rotation.
                                  Defaults to 10 MB. Only used when creating a new logger.
        backup_count (int, optional): Number of backup files to keep.
                                     Defaults to 5. Only used when creating a new logger.
    
    Returns:
        AgentLogger: The global logger instance
    """
    global _default_logger
    if _default_logger is None:
        if log_file is None:
            log_file = "agent_execution.log"
        _default_logger = AgentLogger(log_file, max_bytes=max_bytes, backup_count=backup_count)
    return _default_logger


def set_logger(log_file, max_bytes=None, backup_count=None):
    """
    Set or reset the global logger instance with a specific log file.
    
    This function allows reconfiguring the logger to use a different log file
    with optional rotation settings. Use this at client initialization to 
    specify a custom log location and rotation parameters.
    
    Args:
        log_file (str): Path to the log file
        max_bytes (int, optional): Maximum size of a log file in bytes before rotation.
                                  Defaults to 10 MB (10 * 1024 * 1024 bytes).
        backup_count (int, optional): Number of backup files to keep.
                                     Defaults to 5 (files: .log, .log.1, .log.2, .log.3, .log.4, .log.5).
    
    Returns:
        AgentLogger: The newly configured logger instance
    """
    global _default_logger
    # Close existing logger if present
    if _default_logger is not None:
        _default_logger.close()
    _default_logger = AgentLogger(log_file, max_bytes=max_bytes, backup_count=backup_count)
    return _default_logger


def log_execution_time(func):
    """
    Decorator to log execution time of agent public methods.
    
    This decorator measures the execution time of a method and logs it
    to the agent execution log file in JSON format. It captures method name,
    execution time, and success/failure status.
    
    Args:
        func: The function to be decorated
    
    Returns:
        The wrapped function with logging capabilities
    
    Example:
        @log_execution_time
        def post(self, tid):
            # method implementation
            pass
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Get logger
        logger = get_logger()
        
        # Get agent name
        agent_name = getattr(self, 'name', 'UnknownAgent')
        method_name = func.__name__
        
        # Prepare args info (extract tid and calculate day/hour)
        args_info = {}
        tid = None
        
        # Extract tid from kwargs or positional args
        if 'tid' in kwargs:
            tid = kwargs['tid']
        elif args and isinstance(args[0], int):
            # Many methods have tid as first positional arg
            tid = args[0]
        
        # If we have tid, calculate day and hour (assuming 24 slots per day)
        if tid is not None:
            args_info['tid'] = tid
            args_info['day'] = tid // 24
            args_info['hour'] = tid % 24
        
        # Measure execution time
        start_time = time.time()
        success = True
        error = None
        
        try:
            result = func(self, *args, **kwargs)
            return result
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Log the execution
            logger.log_execution(
                agent_name=agent_name,
                method_name=method_name,
                execution_time=execution_time,
                args_info=args_info if args_info else None,
                success=success,
                error=error
            )
    
    return wrapper
