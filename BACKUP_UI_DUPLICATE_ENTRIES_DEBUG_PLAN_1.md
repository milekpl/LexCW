# Backup UI Duplicate Entries Debug Plan

## Issue Description
When a backup is created, it appears twice in the backup history list:
- Once as "full" type with description
- Once as "manual" type without description
- Same file/timestamp but different metadata

## Todo Items

### 1. Investigate API Layer
- [ ] Check `/api/backup/history` endpoint
- [ ] Verify how backup entries are retrieved from storage
- [ ] Check if duplicate entries are returned at the API level
- [ ] Examine query logic in backup API service

### 2. Review Backend Data Storage
- [ ] Verify how backup entries are stored in the database/filesystem
- [ ] Check if duplicate records are being created during backup process
- [ ] Examine `BaseXBackupManager.backup_database()` method
- [ ] Look for multiple calls or race conditions during backup creation

### 3. Inspect UI JavaScript Logic
- [ ] Review `backup-manager.js` JavaScript file
- [ ] Check how backup history is loaded and rendered in the DataTable
- [ ] Examine `renderBackupHistory()` and `createBackupRowData()` methods
- [ ] Look for duplicate insertion or rendering logic

### 4. Debug Backup Type Assignment
- [ ] Trace how backup type ("full", "manual") is assigned
- [ ] Check if there are two different backup creation paths being triggered
- [ ] Verify backup type metadata storage and retrieval
- [ ] Look for logic that might classify the same backup as different types

### 5. Check Description Assignment
- [ ] Verify how backup descriptions are stored and retrieved
- [ ] Check if the same backup has inconsistent metadata
- [ ] Examine where description data comes from in the backup record

### 6. Test Scenarios
- [ ] Create a backup and observe both entries in detail
- [ ] Compare the backup file content to ensure it's the same file
- [ ] Check timestamps and file sizes of both entries
- [ ] Test different backup types (manual vs scheduled) to reproduce

### 7. Implement Fix Strategy
- [ ] Identify root cause (duplicate creation vs duplicate display)
- [ ] If duplicate creation: fix the backup creation logic
- [ ] If duplicate display: fix the UI rendering/filtering logic
- [ ] Add unique constraint or deduplication logic as needed

### 8. Verification
- [ ] Create backup multiple times and verify no duplicates appear
- [ ] Check backup history shows entries with consistent metadata
- [ ] Verify backup functionality still works correctly
- [ ] Test edge cases (backup with/without descriptions, different backup types)