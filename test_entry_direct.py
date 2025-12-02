"""Test entry lookup directly"""
from BaseXClient import BaseXClient

# Connect to BaseX
session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')

# Open the database
session.execute("OPEN dictionary")

entry_id = "acid test_dc82bb0e-f5cb-4390-8912-0b53a0e54800"

# Try direct query without variable binding
query = f"""
declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";

exists(//lift:entry[@id='{entry_id}'])
"""

print(f"Testing with entry ID: {entry_id}")
print("\n=== Test 1: Direct exists check (no variable binding) ===")
q = session.query(query)
result = q.execute()
print(f"Entry exists: {result}")
print(f"Result == 'true': {result == 'true'}")
q.close()

# Try to get the entry ID
query2 = f"""
declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";

//lift:entry[@id='{entry_id}']/@id/string()
"""

print("\n=== Test 2: Get entry ID ===")
q2 = session.query(query2)
entry_found = q2.execute()
print(f"Entry ID found: '{entry_found}'")
q2.close()

# List all entry IDs that contain "acid"
query3 = """
declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";

for $entry in //lift:entry[contains(@id, 'acid')]
return $entry/@id/string()
"""

print("\n=== Test 3: All entries containing 'acid' ===")
q3 = session.query(query3)
for entry_id_found in q3.iter():
    print(f"Found: '{entry_id_found}'")
q3.close()

session.close()
