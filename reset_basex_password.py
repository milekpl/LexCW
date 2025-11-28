#!/usr/bin/env python3
"""
Generate BaseX password hash for 'admin' user
Based on BaseX password hashing algorithm
"""

import hashlib

# BaseX uses MD5 for digest algorithm with format: md5(md5(password):username)
password = "admin"
username = "admin"

# Generate digest hash
md5_password = hashlib.md5(password.encode()).hexdigest()
combined = f"{md5_password}:{username}"
final_hash = hashlib.md5(combined.encode()).hexdigest()

print(f"Password hash for 'admin': {final_hash}")

# Create users.xml content
users_xml = f"""<users>
  <user name="admin" permission="admin">
    <password algorithm="digest">
      <hash>{final_hash}</hash>
    </password>
  </user>
</users>"""

# Write to BaseX users file
import os
basex_home = os.path.expanduser("~/basex")
users_file = os.path.join(basex_home, "data", "users.xml")

with open(users_file, 'w') as f:
    f.write(users_xml)

print(f"✓ Updated {users_file}")
print("✓ BaseX admin password set to 'admin'")
