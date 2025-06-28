import sqlite3

conn = sqlite3.connect(r'd:\Dokumenty\para_crawl.db')
cursor = conn.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables in SQLite database:')
for table in tables:
    print(f'  - {table[0]}')

# Check the first table
if tables:
    table_name = tables[0][0]
    cursor = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    count = cursor.fetchone()[0]
    print(f'Records in {table_name}: {count:,}')
    
    # Show schema
    cursor = conn.execute(f'PRAGMA table_info("{table_name}")')
    columns = cursor.fetchall()
    print(f'Columns in {table_name}:')
    for col in columns:
        print(f'  - {col[1]} ({col[2]})')

conn.close()
