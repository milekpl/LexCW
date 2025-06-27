"""
Custom exceptions for the application.
"""


class ValidationError(Exception):
    """Exception raised for validation errors."""
    
    def __init__(self, message="Validation error", errors=None):
        """
        Initialize a validation error.
        
        Args:
            message: Error message.
            errors: List of specific errors.
        """
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)
    
    def __str__(self):
        """
        Get a string representation of the error.
        
        Returns:
            String representation of the error.
        """
        if self.errors:
            return f"{self.message}: {', '.join(self.errors)}"
        return self.message


class DatabaseError(Exception):
    """Exception raised for database errors."""
    
    def __init__(self, message="Database error", cause=None):
        """
        Initialize a database error.
        
        Args:
            message: Error message.
            cause: Original exception that caused this error.
        """
        self.message = message
        self.cause = cause
        super().__init__(self.message)
    
    def __str__(self):
        """
        Get a string representation of the error.
        
        Returns:
            String representation of the error.
        """
        if hasattr(self, 'cause') and self.cause:
            return f"{self.message} (Caused by: {str(self.cause)})"
        return self.message


class NotFoundError(Exception):
    """Exception raised when a resource is not found."""
    
    def __init__(self, message="Resource not found", resource_type=None, resource_id=None):
        """
        Initialize a not found error.
        
        Args:
            message: Error message.
            resource_type: Type of resource that was not found.
            resource_id: ID of resource that was not found.
        """
        self.message = message
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(self.message)
    
    def __str__(self):
        """
        Get a string representation of the error.
        
        Returns:
            String representation of the error.
        """
        if hasattr(self, 'resource_type') and hasattr(self, 'resource_id') and self.resource_type and self.resource_id:
            return f"{self.resource_type} with ID {self.resource_id} not found"
        return self.message


class ExportError(Exception):
    """Exception raised when an export operation fails."""
    
    def __init__(self, message="Export failed", cause=None):
        """
        Initialize an export error.
        
        Args:
            message: Error message.
            cause: Original exception that caused this error.
        """
        self.message = message
        self.cause = cause
        super().__init__(self.message)
    
    def __str__(self):
        """
        Get a string representation of the error.
        
        Returns:
            String representation of the error.
        """
        if hasattr(self, 'cause') and self.cause:
            return f"{self.message} (Caused by: {str(self.cause)})"
        return self.message


class DatabaseConnectionError(Exception):
    """Exception raised for database connection errors."""
    
    def __init__(self, message: str = "Database connection error", cause: Exception | None = None):
        """
        Initialize a database connection error.
        
        Args:
            message: Error message.
            cause: Original exception that caused this error.
        """
        self.message = message
        self.cause = cause
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Get a string representation of the error."""
        if self.cause:
            return f"{self.message}: {self.cause}"
        return self.message
