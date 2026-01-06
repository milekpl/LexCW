#!/usr/bin/env python3
"""
BaseX Setup Script for LCW (Little Chinese Dictionary)

This script creates a fresh BaseX installation with proper credentials.
It handles:
1. Creating the directory structure
2. Setting up the configuration
3. Creating the admin user with a known password
4. Starting the server
"""

import os
import sys
import subprocess
import shutil
import hashlib
import secrets

# Configuration
BASEX_DIR = os.path.expanduser("~/basex123")
BASEX_JAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "basex", "BaseX.jar")
ADMIN_PASSWORD = "admin"

def calculate_digest_hash(password):
    """Calculate the digest hash for BaseX password."""
    # BaseX uses MD5 digest: username:realm:password
    # The realm is usually "BaseX"
    realm = "BaseX"
    digest_input = f"admin:{realm}:{password}"
    return hashlib.md5(digest_input.encode()).hexdigest()

def create_users_xml(password):
    """Create a users.xml file with the admin user."""
    digest_hash = calculate_digest_hash(password)
    salt = secrets.token_hex(8)
    sha256_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    users_xml = f"""<users>
  <user name="admin" permission="admin">
    <password algorithm="digest">
      <hash>{digest_hash}</hash>
    </password>
    <password algorithm="salted-sha256">
      <salt>{salt}</salt>
      <hash>{sha256_hash}</hash>
    </password>
  </user>
</users>"""
    return users_xml

def create_basex_config():
    """Create the .basex configuration file."""
    config = """# BaseX Configuration for LCW
# General Options
DEBUG = false
DBPATH = {dbpath}
LOGPATH = .logs
REPOPATH = {repopath}
LANG = English
FAIRLOCK = false
CACHETIMEOUT = 3600
WRITESTORE = true
CACHEMAX = 65536

# Client/Server Architecture
HOST = localhost
PORT = 1984
SERVERPORT = 1984
USER = admin
PASSWORD = {password}
SERVERHOST =
PROXYHOST =
PROXYPORT = 0
NONPROXYHOSTS =
IGNORECERT = false
TIMEOUT = 30
KEEPALIVE = 600
PARALLEL = 8
LOG = data
LOGEXCLUDE =
LOGCUT =
LOGMSGMAXLEN = 5000
LOGTRACE = true
LOGMASKIP = false

# HTTP Services
WEBPATH = {webpath}
GZIP = false
RESTPATH =
RESTXQPATH =
PARSERESTXQ = 3
RESTXQERRORS = true
HTTPLOCAL = false
STOPPORT = 8081
AUTHMETHOD = Basic

# Local Options
""".format(
        dbpath=os.path.join(BASEX_DIR, "data"),
        repopath=os.path.join(BASEX_DIR, "repo"),
        webpath=os.path.join(BASEX_DIR, "webapp"),
        password=ADMIN_PASSWORD
    )
    return config

def stop_basex():
    """Stop any running BaseX server."""
    try:
        result = subprocess.run(
            ["lsof", "-i", ":1984"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if line and not line.startswith("COMMAND"):
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1])
                            print(f"Stopping BaseX (PID: {pid})...")
                            os.kill(pid, 9)
                        except (ValueError, ProcessLookupError):
                            pass
    except FileNotFoundError:
        # lsof not available, try other methods
        try:
            subprocess.run(["pkill", "-9", "-f", "BaseXServer"], capture_output=True)
        except:
            pass
    finally:
        # Wait for port to be freed
        import time
        time.sleep(2)

def create_directory_structure():
    """Create the BaseX directory structure."""
    dirs = ["bin", "data", "repo", "webapp", ".logs"]
    for d in dirs:
        path = os.path.join(BASEX_DIR, d)
        os.makedirs(path, exist_ok=True)
        print(f"Created: {path}")

def copy_basex_files():
    """Copy BaseX jar and scripts to the installation directory."""
    # Copy BaseX.jar
    if os.path.exists(BASEX_JAR):
        dest_jar = os.path.join(BASEX_DIR, "BaseX.jar")
        shutil.copy2(BASEX_JAR, dest_jar)
        print(f"Copied BaseX.jar to {dest_jar}")
    else:
        print(f"Warning: BaseX.jar not found at {BASEX_JAR}")
        return False

    # Copy bin scripts
    bin_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "basex", "bin")
    bin_dest = os.path.join(BASEX_DIR, "bin")
    if os.path.exists(bin_src):
        for item in os.listdir(bin_src):
            src = os.path.join(bin_src, item)
            dest = os.path.join(bin_dest, item)
            if os.path.isfile(src):
                shutil.copy2(src, dest)
                os.chmod(dest, 0o755)
                print(f"Copied {item} to {bin_dest}")

    return True

def setup_users():
    """Create the users.xml file with admin user."""
    users_file = os.path.join(BASEX_DIR, "data", "users.xml")
    users_xml = create_users_xml(ADMIN_PASSWORD)
    with open(users_file, "w") as f:
        f.write(users_xml)
    print(f"Created users.xml with admin user (password: {ADMIN_PASSWORD})")

def setup_config():
    """Create the .basex configuration file."""
    config_file = os.path.join(BASEX_DIR, ".basex")
    config = create_basex_config()
    with open(config_file, "w") as f:
        f.write(config)
    print(f"Created .basex configuration")

def start_basex():
    """Start the BaseX server."""
    start_script = os.path.join(BASEX_DIR, "bin", "start")
    if os.path.exists(start_script):
        result = subprocess.run([start_script], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    else:
        print(f"Error: Start script not found at {start_script}")
        return False

def test_connection():
    """Test the BaseX connection."""
    try:
        from BaseXClient.BaseXClient import Session
        s = Session('localhost', 1984, 'admin', ADMIN_PASSWORD)
        result = s.execute("xquery 1")
        s.close()
        print(f"Connection successful! Test query result: {result.strip()}")
        return True
    except ImportError:
        print("Warning: BaseXClient Python module not available")
        print("Testing with command line client...")
        # Fall back to command line test
        basexclient = os.path.join(BASEX_DIR, "bin", "basexclient")
        try:
            result = subprocess.run(
                [basexclient, "-c", "xquery 1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "1" in result.stdout:
                print("Connection successful!")
                return True
            else:
                print(f"Connection failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("Connection timed out")
            return False
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

def main():
    print("=" * 60)
    print("LCW BaseX Setup Script")
    print("=" * 60)
    print(f"Installation directory: {BASEX_DIR}")
    print(f"Admin password: {ADMIN_PASSWORD}")
    print("=" * 60)

    # Step 1: Stop any running BaseX
    print("\n[1/6] Stopping any running BaseX servers...")
    stop_basex()

    # Step 2: Create directory structure
    print("\n[2/6] Creating directory structure...")
    create_directory_structure()

    # Step 3: Copy BaseX files
    print("\n[3/6] Copying BaseX files...")
    if not copy_basex_files():
        print("Error: Failed to copy BaseX files")
        sys.exit(1)

    # Step 4: Setup configuration
    print("\n[4/6] Setting up configuration...")
    setup_config()
    setup_users()

    # Step 5: Start BaseX
    print("\n[5/6] Starting BaseX server...")
    if not start_basex():
        print("Error: Failed to start BaseX")
        sys.exit(1)

    # Step 6: Test connection
    print("\n[6/6] Testing connection...")
    if test_connection():
        print("\n" + "=" * 60)
        print("SUCCESS: BaseX is set up and running!")
        print("=" * 60)
        print(f"\nTo connect to BaseX:")
        print(f"  Host: localhost")
        print(f"  Port: 1984")
        print(f"  Username: admin")
        print(f"  Password: {ADMIN_PASSWORD}")
        print(f"\nTo start/stop BaseX:")
        print(f"  {BASEX_DIR}/bin/start")
        print(f"  {BASEX_DIR}/bin/stop")
        return 0
    else:
        print("\n" + "=" * 60)
        print("WARNING: BaseX started but connection test failed")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
