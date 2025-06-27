"""
Mock database connector for development mode when BaseX is not available.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime


class MockDatabaseConnector:
    """
    Mock database connector that stores data in memory for development purposes.
    """
    
    def __init__(self, host: str = 'localhost', port: int = 1984, 
                 username: str = 'admin', password: str = 'admin',
                 database: str = 'dictionary'):
        """Initialize the mock connector."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.logger = logging.getLogger(__name__)
        
        # In-memory storage
        self._entries: Dict[str, str] = {}  # entry_id -> xml_string
        self._ranges: Dict[str, Any] = {}   # range_type -> range_data
        self._connected = True
        
        self.logger.info("Mock database connector initialized")
        
        # Initialize with sample data
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with some sample entries for development."""
        sample_entries = [
            {
                'id': 'sample_1',
                'xml': '<entry id="sample_1"><lexical-unit><form lang="en"><text>hello</text></form></lexical-unit><sense><definition><form lang="en"><text>A greeting</text></form></definition><gloss lang="pl">cześć</gloss></sense></entry>'
            },
            {
                'id': 'sample_2', 
                'xml': '<entry id="sample_2"><lexical-unit><form lang="en"><text>world</text></form></lexical-unit><sense><definition><form lang="en"><text>The earth</text></form></definition><gloss lang="pl">świat</gloss></sense></entry>'
            }
        ]
        
        for entry_data in sample_entries:
            self._entries[entry_data['id']] = entry_data['xml']
    
    def connect(self) -> bool:
        """Mock connection - always succeeds."""
        self._connected = True
        self.logger.info("Mock database connection established")
        return True
    
    def disconnect(self):
        """Mock disconnection."""
        self._connected = False
        self.logger.info("Mock database connection closed")
    
    def is_connected(self) -> bool:
        """Check if mock connection is active."""
        return self._connected
    
    def execute_query(self, query: str) -> str:
        """
        Execute a query against the mock database.
        
        Args:
            query: XQuery query string
            
        Returns:
            Query result as string
        """
        # Simple query parsing for common operations
        self.logger.debug("Executing query: %s", query)
        
        # Handle common query patterns
        if "collection(" in query and "entry[@id=" in query:
            # Extract entry ID from query
            import re
            match = re.search(r'entry\[@id="([^"]+)"\]', query)
            if match:
                entry_id = match.group(1)
                return self._entries.get(entry_id, "")
        
        # Handle count queries
        if query.startswith("xquery count("):
            return str(len(self._entries))
        
        # Handle list queries
        if "for $entry in collection(" in query and "return $entry" in query:
            # Return all entries for list operations
            return "".join(self._entries.values())
        
        # Handle database operations
        if query == "LIST":
            return self.database if self.database else ""
        
        return ""
    
    def execute_lift_query(self, query: str, has_namespace: bool = False) -> str:
        """
        Execute a LIFT-specific query with namespace handling.
        
        Args:
            query: XQuery query string (without namespace prologue)
            has_namespace: Whether the database contains namespaced LIFT elements
            
        Returns:
            Query result as string
        """
        # For mock connector, add xquery prefix if missing
        if not query.strip().startswith('xquery'):
            query = f"xquery {query}"
        
        # Execute the query as-is for mock
        return self.execute_query(query)
    
    def execute_update(self, query: str) -> bool:
        """Execute a mock update query."""
        self.logger.debug("Mock update: %s", query)
        
        try:
            # Ensure update commands start with 'xquery' if they are XQuery expressions
            if any(keyword in query for keyword in ['insert', 'delete', 'replace', 'for']) and not query.strip().startswith('xquery'):
                query = f"xquery {query}"
            
            # Handle insertions
            if 'insert node' in query.lower():
                # Extract entry XML from query (simplified)
                import re
                match = re.search(r'<entry[^>]*id="([^"]+)"[^>]*>.*?</entry>', query, re.DOTALL)
                if match:
                    entry_xml = match.group(0)
                    entry_id = match.group(1)
                    self._entries[entry_id] = entry_xml
                    self.logger.info("Mock inserted entry: %s", entry_id)
                return True
            
            # Default: assume success
            return True
            
        except Exception as e:
            self.logger.error(f"Mock update error: {e}")
            return False
    
    def execute_update_lift(self, command: str, has_namespace: bool = False) -> None:
        """
        Execute a LIFT-specific update command with namespace handling.
        For mock testing, just calls execute_update.
        """
        self.execute_update(command)

    def create_database(self, name: str) -> bool:
        """Mock database creation - always succeeds."""
        self.logger.info(f"Mock database '{name}' created")
        return True
    
    def list_databases(self) -> List[str]:
        """Mock database listing."""
        return [self.database]
    
    def drop_database(self, name: str) -> bool:
        """Mock database dropping - always succeeds."""
        self.logger.info(f"Mock database '{name}' dropped")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get mock database statistics."""
        return {
            'total_entries': len(self._entries),
            'database_size': sum(len(xml) for xml in self._entries.values()),
            'last_modified': datetime.now().isoformat(),
            'connection_status': 'mock_connected' if self._connected else 'disconnected'
        }
