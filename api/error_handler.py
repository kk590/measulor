"""Tool 7: Error Handler
Centralized error handling and logging for the video measurement pipeline
"""

import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for better organization"""
    VIDEO_UPLOAD = "video_upload"
    FRAME_EXTRACTION = "frame_extraction"
    POSE_DETECTION = "pose_detection"
    QUALITY_VALIDATION = "quality_validation"
    MEASUREMENT_CALCULATION = "measurement_calculation"
    RESULTS_AGGREGATION = "results_aggregation"
    GENERAL = "general"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('measulor')

class ErrorHandler:
    """Centralized error handling"""
    
    def __init__(self):
        self.error_log = []
    
    def handle_error(self,
                    error: Exception,
                    category: ErrorCategory,
                    severity: ErrorSeverity = ErrorSeverity.ERROR,
                    context: Optional[Dict] = None) -> Dict:
        """
        Handle and log an error
        
        Args:
            error: The exception that occurred
            category: Error category
            severity: Error severity level
            context: Additional context information
        
        Returns:
            Formatted error response
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'category': category.value,
            'severity': severity.value,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {},
            'traceback': traceback.format_exc() if severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL] else None
        }
        
        # Log error
        self._log_error(error_info)
        
        # Store in memory (for analysis)
        self.error_log.append(error_info)
        
        # Return formatted response
        return self._format_error_response(error_info)
    
    def _log_error(self, error_info: Dict):
        """
        Log error with appropriate level
        
        Args:
            error_info: Error information dictionary
        """
        severity = error_info['severity']
        message = f"[{error_info['category']}] {error_info['error_type']}: {error_info['error_message']}"
        
        if severity == ErrorSeverity.INFO.value:
            logger.info(message)
        elif severity == ErrorSeverity.WARNING.value:
            logger.warning(message)
        elif severity == ErrorSeverity.ERROR.value:
            logger.error(message)
        elif severity == ErrorSeverity.CRITICAL.value:
            logger.critical(message)
    
    def _format_error_response(self, error_info: Dict) -> Dict:
        """
        Format error for API response
        
        Args:
            error_info: Error information dictionary
        
        Returns:
            Formatted error response
        """
        # Don't expose full traceback in production
        response = {
            'success': False,
            'error': {
                'message': error_info['error_message'],
                'category': error_info['category'],
                'type': error_info['error_type'],
                'timestamp': error_info['timestamp']
            }
        }
        
        # Add user-friendly message based on category
        response['error']['user_message'] = self._get_user_message(
            error_info['category'],
            error_info['error_type']
        )
        
        return response
    
    def _get_user_message(self, category: str, error_type: str) -> str:
        """
        Get user-friendly error message
        
        Args:
            category: Error category
            error_type: Error type
        
        Returns:
            User-friendly message
        """
        messages = {
            ErrorCategory.VIDEO_UPLOAD.value: {
                'default': 'Failed to upload video. Please ensure the file is a valid video format.',
                'ValueError': 'Invalid video file. Please upload a valid video.',
                'IOError': 'Error reading video file. Please try again.'
            },
            ErrorCategory.FRAME_EXTRACTION.value: {
                'default': 'Failed to extract frames from video. The video may be corrupted.',
                'RuntimeError': 'Video processing error. Please try a different video.'
            },
            ErrorCategory.POSE_DETECTION.value: {
                'default': 'Failed to detect pose in video frames.',
                'ImportError': 'Pose detection system not available. Please contact support.'
            },
            ErrorCategory.QUALITY_VALIDATION.value: {
                'default': 'Video quality is insufficient for accurate measurements.',
                'ValueError': 'Unable to validate pose quality. Please record a clearer video.'
            },
            ErrorCategory.MEASUREMENT_CALCULATION.value: {
                'default': 'Failed to calculate body measurements.',
                'KeyError': 'Missing required landmarks. Ensure full body is visible in video.'
            },
            ErrorCategory.RESULTS_AGGREGATION.value: {
                'default': 'Failed to aggregate results.'
            },
            ErrorCategory.GENERAL.value: {
                'default': 'An unexpected error occurred. Please try again.'
            }
        }
        
        category_messages = messages.get(category, messages[ErrorCategory.GENERAL.value])
        return category_messages.get(error_type, category_messages['default'])
    
    def get_error_summary(self) -> Dict:
        """
        Get summary of all errors
        
        Returns:
            Error summary statistics
        """
        if not self.error_log:
            return {'total_errors': 0}
        
        summary = {
            'total_errors': len(self.error_log),
            'by_category': {},
            'by_severity': {},
            'recent_errors': self.error_log[-5:]  # Last 5 errors
        }
        
        for error in self.error_log:
            # Count by category
            category = error['category']
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            # Count by severity
            severity = error['severity']
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
        
        return summary
    
    def clear_errors(self):
        """Clear error log"""
        self.error_log = []

# Global error handler instance
_error_handler = ErrorHandler()

def handle_pipeline_error(error: Exception,
                         category: ErrorCategory,
                         severity: ErrorSeverity = ErrorSeverity.ERROR,
                         context: Optional[Dict] = None) -> Dict:
    """
    Convenience function to handle errors
    
    Args:
        error: The exception
        category: Error category
        severity: Error severity
        context: Additional context
    
    Returns:
        Error response
    """
    return _error_handler.handle_error(error, category, severity, context)

def get_error_summary() -> Dict:
    """
    Get error summary
    
    Returns:
        Error summary
    """
    return _error_handler.get_error_summary()

def clear_error_log():
    """Clear error log"""
    _error_handler.clear_errors()

def safe_execute(func, category: ErrorCategory, *args, **kwargs):
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        category: Error category
        *args: Function arguments
        **kwargs: Function keyword arguments
    
    Returns:
        (success, result_or_error)
    """
    try:
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        error_response = handle_pipeline_error(
            e,
            category,
            ErrorSeverity.ERROR,
            {
                'function': func.__name__,
                'args': str(args)[:100],  # Limit length
                'kwargs': str(kwargs)[:100]
            }
        )
        return False, error_response
