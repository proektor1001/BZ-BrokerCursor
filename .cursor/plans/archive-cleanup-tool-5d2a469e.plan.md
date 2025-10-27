<!-- 5d2a469e-31da-43ed-b02f-46d0dda5f70d 5daadb84-55a7-4e3e-ac8e-05cf828d8794 -->
# Archive Cleanup Tool

## Overview

Create a simplified cleanup script that scans `modules/broker-reports/archive/` for unsorted HTML files and categorizes them into appropriate subdirectories without reimporting to the database.

## Implementation Steps

### 1. Create cleanup script: `core/scripts/import/cleanup_unsorted_archive.py`

The script will implement a simplified 4-step categorization flow:

**Step 1: Find unsorted files**

- Scan `modules/broker-reports/archive/` for `.html`/`.HTML` files in root
- Exclude files already in subdirectories (`imported/`, `exact_duplicates/`, `logical_duplicates/`, `unrecognized/`)

**Step 2: Calculate hash and extract metadata**

- Calculate SHA-256 hash for each file
- Extract broker, account, period from filename using `FileManager.extract_metadata_from_filename()`
- Detect broker using `detect_broker_tiered()` from `import_reports.py`

**Step 3: Check database for duplicates**

- **Exact duplicate check**: Query `BrokerReportOperations.get_report_by_hash(file_hash)`
  - If found → category = `exact_duplicates`
- **Semantic duplicate check** (if not exact duplicate):
  - Attempt parsing using broker-specific parser
  - If parsing succeeds, extract `period_start[:7]` and `account_number`
  - Query `get_report_by_triple(broker, account, period)`
  - If found → category = `logical_duplicates`
- **Unrecognized check**:
  - If broker detection failed or parsing failed → category = `unrecognized`
- **Default**:
  - If no duplicates found and parsing succeeded → category = `imported`

**Step 4: Move files to subdirectories**

- Use `FileManager.safe_move_file()` to move to target directory
- Log each action to `diagnostics/import_duplicates.log` using `FileManager.log_import_event()`
- Format: `[timestamp] filename — reason | hash=... | broker=... | account=... | period=...`

**Step 5: Generate summary report**

- Create `diagnostics/archive_cleanup_report.md` with:
  - Total files processed
  - Breakdown by category (exact_duplicates, logical_duplicates, imported, unrecognized)
  - List of any errors encountered
  - Confirmation that archive root is clean

### 2. Key implementation details

**Reuse existing components:**

- `FileManager` for file operations and logging
- `BrokerReportOperations` for database queries
- Parser registry from `core/parsers/__init__.py`
- Broker detection from `import_reports.py`

**Differences from import flow:**

- No database insertion (read-only DB access)
- No 4-stage hybrid validation
- Files categorized as `imported` are NOT reimported (they go to imported/ folder only)
- Simplified error handling (just categorize as unrecognized)

**CLI interface:**

```bash
poetry run python core/scripts/import/cleanup_unsorted_archive.py [--dry-run]
```

### 3. Acceptance criteria verification

After execution:

- All HTML files moved from `archive/` root to subdirectories
- Each file logged in `import_duplicates.log`
- Report generated at `diagnostics/archive_cleanup_report.md`
- Archive root contains only subdirectories, no loose HTML files

## Files to create/modify

- **NEW**: `core/scripts/import/cleanup_unsorted_archive.py` (main script)
- **UPDATE**: `diagnostics/import_duplicates.log` (append new entries)
- **NEW**: `diagnostics/archive_cleanup_report.md` (summary report)

## Key dependencies

- `core/utils/file_manager.py` - file operations, logging
- `core/database/operations.py` - duplicate detection queries
- `core/parsers/__init__.py` - parser registry
- `core/config.py` - path configuration

### To-dos

- [ ] Create core/scripts/import/cleanup_unsorted_archive.py with simplified categorization logic
- [ ] Test script with --dry-run flag to verify categorization logic
- [ ] Run cleanup script on actual archive directory
- [ ] Verify archive root is empty and all files categorized correctly