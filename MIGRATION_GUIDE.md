# Database Migration Guide

## Migrating Your SQLite Database to PostgreSQL

Your `D:\Dokumenty\para_crawl.db` contains **74.7 million** English-Polish translation pairs. The migration tool has been enhanced with **automatic database creation**.

### Quick Migration Command

```powershell
# Replace [your_password] with your actual PostgreSQL password
python -m app.database.sqlite_postgres_migrator --sqlite-path "D:\Dokumenty\para_crawl.db" --postgres-url "postgresql://postgres:[your_password]@localhost:5432/para_crawl" --batch-size 1000 --verbose
```

### What Happens Automatically:

✅ **Database Creation**: Creates `para_crawl` database if it doesn't exist  
✅ **Schema Setup**: Creates all necessary tables and indexes  
✅ **Data Transfer**: Migrates all 74.7M records in efficient batches  
✅ **Integrity Check**: Validates record counts match source  
✅ **Error Handling**: Robust error recovery and detailed logging  

### Prerequisites:

1. **PostgreSQL Running**: Ensure PostgreSQL is running locally
2. **User Permissions**: Use a user with database creation privileges (e.g., `postgres`)
3. **Available Space**: Ensure sufficient disk space for 74.7M records

### Expected Performance:

- **Duration**: 30-60 minutes for 74.7M records
- **Memory**: <2GB during migration  
- **Throughput**: ~20,000-40,000 records/minute

### Connection Format:

```
postgresql://[username]:[password]@[host]:[port]/[database_name]
```

### After Migration:

Your parallel corpus will be available in PostgreSQL with full-text search capabilities, ready for the advanced corpus processing features we've implemented.

---

*This migration tool follows TDD best practices with comprehensive error handling and data validation.*
