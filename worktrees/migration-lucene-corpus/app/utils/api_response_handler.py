"""
API Response Handler Utilities

This module provides decorators and utilities to handle common API response patterns,
reducing code duplication across API endpoints.
"""

from functools import wraps
from flask import jsonify, current_app
from typing import Callable, Any, Union, Tuple
from werkzeug.wrappers.response import Response


def api_response_handler(
    success_status: int = 200,
    error_status: int = 500,
    handle_not_found: bool = True,
    handle_validation: bool = True,
    custom_validation_func: Callable = None
):
    """
    Decorator to handle common API response patterns.

    Args:
        success_status: HTTP status code for successful responses (default 200)
        error_status: HTTP status code for server errors (default 500)
        handle_not_found: Whether to handle NotFoundError specifically
        handle_validation: Whether to handle ValidationError specifically
        custom_validation_func: Optional function to perform custom validation before the main function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Union[Response, Tuple[Response, int]]:
            try:
                # Run custom validation if provided
                if custom_validation_func:
                    validation_result = custom_validation_func(*args, **kwargs)
                    if validation_result is not None:
                        # If validation returns a response, return it directly
                        if isinstance(validation_result, (Response, tuple)):
                            return validation_result
                        # If validation returns a dict with error, return error response
                        elif isinstance(validation_result, dict) and 'error' in validation_result:
                            return jsonify({'success': False, 'error': validation_result['error']}), 400

                result = func(*args, **kwargs)

                # If the function already returns a response, return it directly
                if isinstance(result, tuple):
                    response, status_code = result
                    if isinstance(response, Response):
                        return result

                # If the function returns a response object directly
                if isinstance(result, Response):
                    return result

                # Otherwise, assume it's data to be returned as success response
                return jsonify({'success': True, 'data': result}), success_status

            except Exception as e:
                # Import error types only when needed to avoid circular imports
                error_type_name = type(e).__name__

                # Handle specific error types if requested
                if handle_not_found and error_type_name == 'NotFoundError':
                    return jsonify({'success': False, 'error': str(e)}), 404
                elif handle_validation and error_type_name == 'ValidationError':
                    return jsonify({'success': False, 'error': str(e)}), 400
                else:
                    # Log the error with context
                    endpoint_name = f"{func.__module__}.{func.__name__}"
                    current_app.logger.error(
                        f"Error in {endpoint_name}: {str(e)}",
                        exc_info=True
                    )
                    return jsonify({'success': False, 'error': str(e)}), error_status

        return wrapper
    return decorator


def validate_json_request(required_fields: list = None):
    """
    Helper function to validate JSON request data.

    Args:
        required_fields: List of required field names in the JSON request
    """
    def validation_func(*args, **kwargs):
        data = request.get_json()

        if not data:
            return {"error": "Request body is required"}

        if required_fields:
            for field in required_fields:
                if field not in data:
                    return {"error": f"Field '{field}' is required"}

        return None  # No validation errors

    return validation_func


def success_response(data: Any = None, status: int = 200) -> Tuple[Response, int]:
    """Create a standardized success response."""
    return jsonify({'success': True, 'data': data}), status


def error_response(error_msg: str, status: int = 500) -> Tuple[Response, int]:
    """Create a standardized error response."""
    return jsonify({'success': False, 'error': error_msg}), status


def get_service(service_class):
    """Utility function to get a service instance from the injector."""
    try:
        return current_app.injector.get(service_class)
    except AttributeError:
        # Handle case where injector is not available
        raise RuntimeError(f"Dependency injector not available when getting {service_class.__name__}")
    except Exception as e:
        current_app.logger.error(f"Error getting service {service_class.__name__}: {str(e)}")
        raise