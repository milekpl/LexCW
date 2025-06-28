#!/usr/bin/env python3
"""Test script to isolate the encoding issue."""

import sqlite3
import sys

def test_encoding():
    """Test reading from the SQLite database with different encodings."""
    sqlite_path = r"D:\Dokumenty\para_crawl.db"
    
    print("Testing SQLite encoding...")
    
    try:
        # Test 1: Default connection
        with sqlite3.connect(sqlite_path) as conn:
            conn.text_factory = str  # Use str factory
            cursor = conn.cursor()
            cursor.execute("SELECT c0en, c1pl, c2source FROM tmdata_content LIMIT 3")
            rows = cursor.fetchall()
            
            print("Sample data (first 3 rows):")
            for i, row in enumerate(rows):
                print(f"Row {i+1}:")
                print(f"  English: {repr(row[0][:100])}")
                print(f"  Polish: {repr(row[1][:100])}")
                print(f"  Source: {repr(row[2][:50])}")
                print()
                
    except Exception as e:
        print(f"Error reading SQLite: {e}")
        
    # Test 2: Try bytes factory
    try:
        with sqlite3.connect(sqlite_path) as conn:
            conn.text_factory = bytes  # Use bytes factory
            cursor = conn.cursor()
            cursor.execute("SELECT c0en, c1pl, c2source FROM tmdata_content LIMIT 1")
            row = cursor.fetchone()
            
            print("Raw bytes sample:")
            print(f"  English bytes: {row[0][:50]}")
            print(f"  Polish bytes: {row[1][:50]}")
            
            # Try decoding with different encodings
            encodings = ['utf-8', 'windows-1252', 'iso-8859-1', 'cp1250']
            for encoding in encodings:
                try:
                    decoded = row[1].decode(encoding)
                    print(f"  Polish decoded with {encoding}: {decoded[:100]}")
                    break
                except UnicodeDecodeError as e:
                    print(f"  Failed with {encoding}: {e}")
                    
    except Exception as e:
        print(f"Error with bytes factory: {e}")

if __name__ == "__main__":
    test_encoding()
