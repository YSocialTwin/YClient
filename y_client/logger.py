"""
Logging System Module

This module provides utilities for logging execution time of agent public methods.
Each log entry is written as a JSON object to a log file.
"""

import json
import time
import functools
import os
from datetime import datetime
from pathlib import Path


class AgentLogger:
    """
    A logger class for tracking agent method execution times.
    
    Writes log entries in JSON format to a log file, where each line represents
    a single method execution with timing information.
    
    Attributes:
        log_file (str): Path to the log file where entries are written
    """
    
    def __init__(self, log_file="agent_execution.log"):
        """
        Initialize the AgentLogger.
        
        Args:
            log_file (str): Path to the log file. Defaults to "agent_execution.log"
                           in the current working directory.
        
        Raises:
            OSError: If the log directory cannot be created due to permission issues
        """
        self.log_file = log_file
        # Ensure log directory exists
        log_path = Path(log_file)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            import sys
            print(f"Warning: Cannot create log directory {log_path.parent}: {e}", file=sys.stderr)
            print(f"Logging will be attempted but may fail.", file=sys.stderr)
    
    def log_execution(self, agent_name, method_name, execution_time, args_info=None, success=True, error=None):
        """
        Write a log entry to the log file in JSON format.
        
        Args:
            agent_name (str): Name of the agent executing the method
            method_name (str): Name of the method being executed
            execution_time (float): Time taken to execute the method in seconds
            args_info (dict, optional): Information about method arguments. Defaults to None.
            success (bool, optional): Whether the method executed successfully. Defaults to True.
            error (str, optional): Error message if method failed. Defaults to None.
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_name": agent_name,
            "method_name": method_name,
            "execution_time_seconds": round(execution_time, 4),
            "success": success
        }
        
        if args_info:
            log_entry["args"] = args_info
        
        if error:
            log_entry["error"] = str(error)
        
        # Write as single-line JSON with error handling
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except IOError as e:
            # If logging fails, print to stderr but don't crash the application
            import sys
            print(f"Warning: Failed to write to log file {self.log_file}: {e}", file=sys.stderr)


# Global logger instance
_default_logger = None


def get_logger(log_file=None):
    """
    Get the global logger instance or create one if it doesn't exist.
    
    Args:
        log_file (str, optional): Path to the log file. If None and no logger exists,
                                  defaults to "agent_execution.log". If a logger already
                                  exists, the existing logger is returned regardless of
                                  this parameter.
    
    Returns:
        AgentLogger: The global logger instance
    """
    global _default_logger
    if _default_logger is None:
        if log_file is None:
            log_file = "agent_execution.log"
        _default_logger = AgentLogger(log_file)
    return _default_logger


def set_logger(log_file):
    """
    Set or reset the global logger instance with a specific log file.
    
    This function allows reconfiguring the logger to use a different log file.
    Use this at client initialization to specify a custom log location.
    
    Args:
        log_file (str): Path to the log file
    
    Returns:
        AgentLogger: The newly configured logger instance
    """
    global _default_logger
    _default_logger = AgentLogger(log_file)
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
        
        # Prepare args info (only log tid and post_id if present for brevity)
        args_info = {}
        
        # Extract common arguments from kwargs
        if 'tid' in kwargs:
            args_info['tid'] = kwargs['tid']
        if 'post_id' in kwargs:
            args_info['post_id'] = kwargs['post_id']
        
        # Also check positional args for common patterns
        # Many methods have tid as first positional arg
        if args and isinstance(args[0], int) and 'tid' not in args_info:
            args_info['tid'] = args[0]
        # Some methods have post_id as first or second positional arg
        if len(args) > 1 and isinstance(args[1], int) and 'post_id' not in args_info:
            args_info['post_id'] = args[1]
        
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
