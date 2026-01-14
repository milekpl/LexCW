# PostgreSQL Setup for WSL Integration Tests

## Windows PostgreSQL Installation

1. **Install PostgreSQL on Windows** (if not already installed):
   - Download from: https://www.postgresql.org/download/windows/
   - Install with default settings
   - Remember the superuser password you set during installation
   - Default port: 5432

2. **Configure PostgreSQL to accept WSL connections**:

   Edit `pg_hba.conf` (typically at `C:\Program Files\PostgreSQL\<version>\data\pg_hba.conf`):
   
   Add these lines **before** the existing IPv4 local connections:
   ```
   # TYPE  DATABASE        USER            ADDRESS                 METHOD
   # WSL connections - add both common subnets
   host    all             all             172.16.0.0/12           scram-sha-256
   host    all             all             10.0.0.0/8              scram-sha-256
   ```
   
   This covers both common WSL subnet ranges (172.x.x.x and 10.x.x.x).
   
   **Note:** Use `ip route | grep default | awk '{print $3}'` in WSL to find your actual gateway IP.

3. **Edit `postgresql.conf`** (same directory as pg_hba.conf):
   
   Find and modify:
   ```
   listen_addresses = '*'
   ```
   
   Or more restrictively:
   ```
   listen_addresses = 'localhost, 10.*'
   ```

4. **Restart PostgreSQL service**:
   - Open Services (services.msc)
   - Find "postgresql-x64-XX" service
   - Right-click → Restart

5. **Configure Windows Firewall to allow PostgreSQL from WSL**:

   **Option A: Using PowerShell (Recommended - Quick & Easy)**
   
   Open PowerShell **as Administrator** and run:
   ```powershell
   New-NetFirewallRule -DisplayName "PostgreSQL for WSL" -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow -Profile Private
   ```
   
   **Option B: Using Windows Defender Firewall GUI**
   
   1. Press `Win + R`, type `wf.msc`, press Enter
   2. Click "Inbound Rules" in the left panel
   3. Click "New Rule..." in the right panel
   4. Select "Port" → Click Next
   5. Select "TCP" and enter "5432" in Specific local ports → Click Next
   6. Select "Allow the connection" → Click Next
   7. Check "Private" (uncheck Domain and Public for security) → Click Next
   8. Name it "PostgreSQL for WSL" → Click Finish
   
   **Verify the firewall rule:**
   ```powershell
   # In PowerShell
   Get-NetFirewallRule -DisplayName "PostgreSQL for WSL" | Format-List
   ```

## Database Setup

**Note:** This setup assumes you already have a PostgreSQL database on Windows. We'll configure WSL to connect to your existing `dictionary_analytics` database.

If you need to verify your database exists:

```powershell
# In Windows PowerShell
psql -U postgres -l
```

You should see your `dictionary_analytics` database listed.

## WSL Connection

### Find Windows Host IP from WSL

From your WSL terminal:
```bash
# Method 1: Get Windows host IP
cat /etc/resolv.conf | grep nameserver | awk '{print $2}'

# Method 2: Alternative
ip route | grep default | awk '{print $3}'
```

The IP will typically be something like `172.X.X.X` or `10.X.X.X` depending on your WSL version and configuration.

**Recommended:** Use the `ip route` method as it's more reliable:
```bash
ip route | grep default | awk '{print $3}'
```

### Test Connection from WSL

```bash
# Install PostgreSQL client in WSL if needed
sudo apt-get update
sudo apt-get install postgresql-client

# Test connection (replace with your Windows IP from ip route command)
# Use your actual database credentials from config.py
psql -h 172.17.96.1 -U dict_user -d dictionary_analytics
# Enter your actual database password when prompted

# If no password prompt appears, add -W to force password prompt:
psql -h 172.17.96.1 -U dict_user -d dictionary_analytics -W
```

### Environment Variables for Tests

Create or update `.env` file in your project root:

```bash
# PostgreSQL Configuration (use your production database)
POSTGRES_HOST=172.17.96.1  # Replace with your Windows IP from 'ip route' command
POSTGRES_PORT=5432
POSTGRES_USER=dict_user
POSTGRES_PASSWORD=your_actual_password  # Use your actual password
POSTGRES_DB=dictionary_analytics
```

Or export them in your shell:

```bash
# Auto-detect Windows host IP (use ip route, more reliable than resolv.conf)
export POSTGRES_HOST=$(ip route | grep default | awk '{print $3}')
export POSTGRES_PORT=5432
export POSTGRES_USER=dict_user
export POSTGRES_PASSWORD=your_actual_password  # Use your actual password
export POSTGRES_DB=dictionary_analytics
```

## Troubleshooting

### Connection Refused or Hangs Without Password Prompt
- Check Windows Firewall: Allow PostgreSQL (port 5432)
- Verify PostgreSQL is listening: `netstat -an | findstr 5432` (in PowerShell)
- Check pg_hba.conf has the WSL subnet (both 172.16.0.0/12 and 10.0.0.0/8)
- Restart PostgreSQL service after config changes
- **If connection hangs without password prompt:**
  - Connection may be blocked at firewall level
  - Check Windows Firewall allows inbound on port 5432 from private networks
  - Verify your WSL IP is in the allowed subnet in pg_hba.conf
  - Use `psql -h <IP> -U dict_user -d dictionary_analytics -W` to force password prompt
  - Check PostgreSQL logs in `C:\Program Files\PostgreSQL\<version>\data\log\`

### Authentication Failed
- Double-check password (use your actual production password)
- Ensure user exists: `psql -U postgres -c "\du"`
- Check pg_hba.conf has `scram-sha-256` for the connection
- If you changed from `md5` to `scram-sha-256`, you may need to reset the user password:
  ```sql
  ALTER USER dict_user WITH PASSWORD 'your_actual_password';
  ```

### Permission Denied
```sql
-- In psql as postgres user:
GRANT ALL PRIVILEGES ON DATABASE dictionary_analytics TO dict_user;
GRANT ALL ON SCHEMA public TO dict_user;
```

## Using the Fixture

In your tests:

```python
def test_something_with_postgres(postgres_test_connection):
    """Test using PostgreSQL connection."""
    cursor = postgres_test_connection.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL version: {version}")
```

Or with SQLAlchemy:

```python
def test_with_sqlalchemy(postgres_test_engine):
    """Test using SQLAlchemy engine."""
    from sqlalchemy import text
    
    with postgres_test_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
```
