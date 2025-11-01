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
        """
        self.log_file = log_file
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
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
        
        # Write as single-line JSON
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')


# Global logger instance
_default_logger = None


def get_logger(log_file="agent_execution.log"):
    """
    Get the global logger instance or create one if it doesn't exist.
    
    Args:
        log_file (str): Path to the log file. Defaults to "agent_execution.log"
    
    Returns:
        AgentLogger: The global logger instance
    """
    global _default_logger
    if _default_logger is None:
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
        
        # Prepare args info (only log tid if present for brevity)
        args_info = {}
        if args:
            # First positional arg for many methods is 'tid'
            if len(args) > 0 and isinstance(args[0], int):
                args_info['tid'] = args[0]
        if 'tid' in kwargs:
            args_info['tid'] = kwargs['tid']
        if 'post_id' in kwargs:
            args_info['post_id'] = kwargs['post_id']
        elif len(args) > 1 and isinstance(args[1], int):
            # Some methods have post_id as second arg
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
