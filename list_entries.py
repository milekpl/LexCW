"""List all entries in BaseX"""
from BaseXClient import BaseXClient

# Connect to BaseX
session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')

# Open the database
session.execute("OPEN dictionary")

# Count total entries
query_count = """
declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
count(//lift:entry)
"""

print("=== Total Entries ===")
q = session.query(query_count)
count = q.execute()
print(f"Total entries: {count}")
q.close()

# List first 10 entry IDs
query_list = """
declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";

for $entry in //lift:entry[position() <= 10]
return $entry/@id/string()
"""

print("\n=== First 10 Entry IDs ===")
q2 = session.query(query_list)
for idx, entry_id in enumerate(q2.iter(), 1):
    print(f"{idx}. '{entry_id}'")
q2.close()

# Search for entries with "test" in ID
query_test = """
declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";

for $entry in //lift:entry[contains(@id, 'test')]
return $entry/@id/string()
"""

print("\n=== Entries containing 'test' ===")
q3 = session.query(query_test)
for entry_id in q3.iter():
    print(f"'{entry_id}'")
q3.close()

session.close()
