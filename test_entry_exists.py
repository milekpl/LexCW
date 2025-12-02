"""Test if entry exists in BaseX"""
from BaseXClient import BaseXClient

# Connect to BaseX
session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')

# Open the database
session.execute("OPEN dictionary")

entry_id = "acid test_dc82bb0e-f5cb-4390-8912-0b53a0e54800"

# Check if entry exists
query = f"""
declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
declare variable $entryId external;

exists(//lift:entry[@id=$entryId])
"""

q = session.query(query)
q.bind('entryId', entry_id)
result = q.execute()
q.close()

print(f"Entry exists query result: '{result}'")
print(f"Result == 'true': {result.strip().lower() == 'true'}")

# Also try to get the entry
query2 = f"""
declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
declare variable $entryId external;

//lift:entry[@id=$entryId]/@id/string()
"""

q2 = session.query(query2)
q2.bind('entryId', entry_id)
result2 = q2.execute()
q2.close()

print(f"\nEntry ID found: '{result2}'")

session.close()
