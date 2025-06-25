"""
BaseX Python Client

This is the official BaseX Python client adapted from the BaseX repository.
Source: https://github.com/BaseXdb/basex/tree/master/basex-api/src/main/python
"""

import socket
import hashlib
import io


class Session:
    """BaseX client session."""
    
    def __init__(self, host, port, username, password):
        """Initialize session with server credentials."""
        self.__host = host
        self.__port = port
        self.__username = username
        self.__password = password
        self.__socket = None
        self.__bos = None
        self.__bis = None
        
        # Connect to server
        self.__connect()
    
    def __connect(self):
        """Connect to BaseX server."""
        try:
            # Create socket connection
            self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__socket.connect((self.__host, self.__port))
            
            # Create input/output streams
            self.__bos = self.__socket.makefile('wb')
            self.__bis = self.__socket.makefile('rb')
            
            # Receive timestamp
            ts = self.__receive()
            
            # Hash password with timestamp
            m = hashlib.md5()
            m.update(hashlib.md5(self.__password.encode()).hexdigest().encode())
            m.update(ts.encode())
            pw = m.hexdigest()
            
            # Send username and hashed password
            self.__send(self.__username)
            self.__send(pw)
            
            # Check authentication result
            if self.__bis.read(1) != b'\x00':
                raise Exception("Authentication failed")
                
        except Exception as e:
            self.close()
            raise Exception(f"Connection failed: {e}")
    
    def execute(self, command):
        """Execute a command and return result."""
        try:
            # Send command
            self.__send(command)
            
            # Receive result
            result = self.__receive()
            info = self.__receive()
            
            # Check for errors
            if self.__bis.read(1) != b'\x00':
                raise Exception(info if info else "Command execution failed")
            
            return result
            
        except Exception as e:
            raise Exception(f"Command execution failed: {e}")
    
    def query(self, query):
        """Execute XQuery and return result."""
        return self.execute(f"xquery {query}")
    
    def close(self):
        """Close the session."""
        try:
            if self.__bos:
                self.__send("exit")
                self.__bos.close()
            if self.__bis:
                self.__bis.close()
            if self.__socket:
                self.__socket.close()
        except:
            pass
    
    def __send(self, value):
        """Send a string to server."""
        self.__bos.write(value.encode() + b'\x00')
        self.__bos.flush()
    
    def __receive(self):
        """Receive a string from server."""
        buffer = io.BytesIO()
        while True:
            b = self.__bis.read(1)
            if not b:
                raise Exception("Connection lost")
            if b == b'\x00':
                break
            buffer.write(b)
        return buffer.getvalue().decode()


# For backward compatibility
BaseXClient = Session