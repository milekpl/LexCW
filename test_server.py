import sys
import os
import webbrowser
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from threading import Thread
import time

def start_server():
    """Start the Flask server in a separate thread"""
    app = create_app()
    # Use a random port to avoid conflicts
    app.run(debug=False, port=5678)

if __name__ == "__main__":
    # Start the server in a background thread
    server_thread = Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for the server to start
    time.sleep(2)
    
    # Open the browser to the entry edit page
    entry_id = "Protestantism_b97495fb-d52f-4755-94bf-a7a762339605"
    url = f"http://127.0.0.1:5678/entries/{entry_id}/edit"
    
    print(f"Opening browser to {url}")
    webbrowser.open(url)
    
    # Keep the script running until Ctrl+C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server stopped by user")
