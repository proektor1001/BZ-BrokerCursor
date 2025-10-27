<!-- 09791fa6-aa18-49d6-86a8-f89e95f9021f 1f7cd8c3-72e9-454a-9fb6-7ef8fa1103b9 -->
# Fix Import Failures and Restore Consistency

## Overview

Resolve critical import failures discovered during verification: fix file hashing, process 6 remaining files, archive all imported files, and ensure full synchronization between database and filesystem.

## Critical Issues Identified

1. **Missing file_hash values**: All 18 DB records have empty file_hash
2. **Files not archived**: 0 files in archive (should be 18)
3. **Incomplete processing**: 6 files remain in inbox unprocessed
4. **No archive path in import**: Files stay in L:\modules\broker-reports\archive instead of proper path

## Fix Strategy

### 1. Analyze simple_import.py Issues

**Root cause investigation**:

```python
# Check the archive path issue
archive_path = config.ARCHIVE_PATH / file_path.name
# This creates path: L:\modules\broker-reports\archive\filename
# But script archives to wrong location
```

**Issues found**:

- Archive path calculation incorrect
- Files moved but not found later
- Need to fix Path resolution

### 2. Update Database with Missing Hashes

Create script to backfill file_hash values for existing 18 records:

```python
# backfill_hashes.py
import hashlib
from pathlib import Path
from core.database.operations import BrokerReportOperations

db_ops = BrokerReportOperations()
reports = db_ops.list_reports(limit=1000)

# Search for files in both possible locations
search_paths = [
    Path("L:/modules/broker-reports/archive"),
    Path("modules/broker-reports/archive"),
    Path("L:/BZ-BrokerCursor/modules/broker-reports/archive")
]

for report in reports:
    # Try to find the file
    file_found = False
    file_path = None
    
    for base_path in search_paths:
        potential_path = base_path / report['file_name']
        if potential_path.exists():
            file_found = True
            file_path = potential_path
            break
    
    if file_found:
        # Calculate hash
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Update database
        # Need to add update_file_hash method to BrokerReportOperations
        print(f"Would update ID {report['id']} with hash {file_hash[:16]}...")
```

### 3. Fix simple_import.py Script

**Issues to fix**:

1. **Archive path resolution**:
```python
# OLD (incorrect):
archive_path = config.ARCHIVE_PATH / file_path.name

# NEW (correct):
archive_path = Path("modules/broker-reports/archive") / file_path.name
archive_path.parent.mkdir(parents=True, exist_ok=True)
```

2. **Ensure file_hash is set**:
```python
# Already present, but verify it's being passed:
report_id = db_ops.insert_report(
    ...
    file_hash=file_hash,  # Ensure this is calculated
    file_size=file_path.stat().st_size,
    ...
)
```

3. **Verify archive operation**:
```python
# After successful insert:
if report_id:
    try:
        file_path.rename(archive_path)
        print(f"  Archived: {archive_path}")
    except Exception as e:
        print(f"  Archive failed: {e}")
```


### 4. Process Remaining 6 Files

Re-run import for the 6 unprocessed files:

```bash
python simple_import.py
```

Expected behavior:

- Process 6 new files
- Calculate SHA-256 hashes
- Insert into database with proper file_hash
- Move to archive directory

### 5. Locate and Consolidate Archived Files

Find where the 18 files were actually moved:

```powershell
# Search for archived files
Get-ChildItem -Path L:\ -Filter "*.html" -Recurse | Where-Object { $_.FullName -like "*broker*" }
```

Move any misplaced files to correct archive location:

```powershell
# Move files to correct location
$correctArchive = "L:\BZ-BrokerCursor\modules\broker-reports\archive"
# Move misplaced files
```

### 6. Verify Final State

Run verification script again:

```bash
python verify_import.py
```

Expected results:

- 24 total files processed
- 18 unique records in database
- 6 duplicates logged in import_log
- 24 files in archive
- 0 files in inbox
- All file_hash values populated

### 7. Generate Recovery Report

Create `diagnostics/import_recovery_report.md`:

```markdown
# Import Recovery Report

**Generated**: [timestamp]
**Status**: RECOVERED / FAILED

## Recovery Actions Taken

1. ✅ Analyzed import failures
2. ✅ Fixed simple_import.py script
3. ✅ Backfilled missing file_hash values
4. ✅ Processed remaining 6 files
5. ✅ Consolidated archived files
6. ✅ Verified final state

## Final State

- Total files: 24
- Database records: 18 unique + 6 duplicates in log
- Files in archive: 24
- Files in inbox: 0
- All file_hash values: populated ✅

## Before vs After

| Metric | Before | After |
|--------|--------|-------|
| DB records | 18 | 18 |
| file_hash populated | 0 | 18 |
| Files archived | 0 | 24 |
| Files in inbox | 6 | 0 |

## Status: ✅ RECOVERED
```

## Implementation Steps

### Step 1: Create Fixed Import Script

Create `fixed_import.py` with corrections:

- Proper path resolution
- Correct archive location
- Better error handling
- File hash verification

### Step 2: Backfill Existing Records

Create and run `backfill_hashes.py` to update 18 existing records with file_hash values.

### Step 3: Process Remaining Files

Run fixed import script to process 6 remaining files from inbox.

### Step 4: Locate Misplaced Files

Find and move the 18 archived files to correct location.

### Step 5: Final Verification

Run `verify_import.py` to confirm all issues resolved.

### Step 6: Generate Recovery Report

Document the recovery process and final state.

## Success Criteria

- ✅ All 24 files processed
- ✅ 18 unique records in broker_reports
- ✅ All file_hash values populated (non-null)
- ✅ 24 files in modules/broker-reports/archive/
- ✅ 0 files in modules/broker-reports/inbox/
- ✅ 6 duplicate entries in import_log
- ✅ Recovery report generated
- ✅ System fully synchronized

## Risk Mitigation

- Backup database before updates
- Test file operations on single file first
- Verify each step before proceeding
- Keep diagnostic reports for audit trail

### To-dos

- [ ] Analyze simple_import.py to identify root causes of failures
- [ ] Find where the 18 files were actually moved during import
- [ ] Create fixed_import.py with proper path handling and error checking
- [ ] Create and run script to backfill file_hash values for 18 existing records
- [ ] Process the 6 remaining files in inbox with fixed script
- [ ] Move all files to correct archive location
- [ ] Run verification script to confirm all issues resolved
- [ ] Create import_recovery_report.md documenting the recovery