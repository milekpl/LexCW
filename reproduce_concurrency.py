
import threading
import time
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
import os

# Mock config
HOST = os.getenv('BASEX_HOST', 'localhost')
PORT = int(os.getenv('BASEX_PORT', 1984))
USER = os.getenv('BASEX_USERNAME', 'admin')
PASS = os.getenv('BASEX_PASSWORD', 'admin')
DB = "test_concurrency_db"

def run_queries(service, thread_id):
    try:
        print(f"Thread {thread_id} starting")
        # Run a simple query multiple times
        for i in range(5):
            service.db_connector.execute_query(f"1 + {i}")
            # Also try a search-like query
            service.db_connector.execute_query(f"for $i in 1 to 10 return $i")
        print(f"Thread {thread_id} finished")
    except Exception as e:
        print(f"Thread {thread_id} failed: {e}")

def main():
    connector = BaseXConnector(HOST, PORT, USER, PASS, None)
    try:
        connector.connect()
        # Create DB if not exists
        try:
            connector.create_database(DB)
        except:
            pass
        
        connector.database = DB
        connector.execute_command(f"OPEN {DB}")
            
        service = DictionaryService(connector)
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=run_queries, args=(service, i))
            threads.append(t)
            t.start()
            # run_queries(service, i)
            
        for t in threads:
            t.join()
            
    finally:
        try:
            connector.execute_command(f"DROP DB {DB}")
        except:
            pass
        connector.disconnect()

if __name__ == "__main__":
    main()
