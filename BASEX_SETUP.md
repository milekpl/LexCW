# BaseX Setup Reference

## Quick Commands

```bash
# Start/Stop BaseX
./start-basex.sh start
./start-basex.sh stop
./start-basex.sh restart
./start-basex.sh status

# Reset password (if forgotten)
./start-basex.sh reset-pass newpassword
```

## Manual Recovery (if script fails)

```bash
# 1. Kill running BaseX
killall java

# 2. Remove stale users.xml (BaseX will recreate with empty password)
mv ~/basex/data/users.xml ~/basex/data/users.xml.backup

# 3. Start BaseX
~/basex/bin/basexserver -p1984 &

# 4. Connect with empty password and set new password
~/basex/bin/basexclient -c "ALTER PASSWORD admin admin"
```

## Configuration

| Setting | Value |
|---------|-------|
| Data directory | `~/basex/data` |
| Server port | `1984` |
| HTTP port | `8081` |
| Admin user | `admin` |
| Default password | `admin` |

## Important Files

- `~/.basex` - BaseX client configuration
- `~/basex/data/users.xml` - User/password database
- `~/basex/.pid` - Server PID file
- `~/basex/log/server.log` - Server logs

## Common Issues

**"Access denied: admin"**
- Password hash is stale. Follow manual recovery steps above.

**"Port 1984 already in use"**
- Stale PID file: `rm ~/basex/.pid`
- Or another process: `lsof -i :1984`

**BaseX won't start**
- Check logs: `cat ~/basex/log/server.log`
- Ensure no zombie java processes: `killall java`
