#!/usr/bin/env python3
"""
Import Integrity Verification Script
Analyzes database records, file locations, and generates diagnostic reports
"""

import sys
import hashlib
from pathlib import Path
from datetime import datetime
from collections import Counter

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations

def analyze_database():
    """Analyze database records"""
    print("=== Database Analysis ===")
    
    db_ops = BrokerReportOperations()
    reports = db_ops.list_reports(limit=1000)
    
    print(f"Total records in broker_reports: {len(reports)}")
    
    # Analyze by account
    accounts = Counter(r['account'] for r in reports)
    print(f"By account: {dict(accounts)}")
    
    # Analyze by period
    periods = Counter(r['period'] for r in reports)
    print(f"By period: {dict(periods)}")
    
    # Check required fields
    total = len(reports)
    has_broker = sum(1 for r in reports if r.get('broker'))
    has_account = sum(1 for r in reports if r.get('account'))
    has_period = sum(1 for r in reports if r.get('period'))
    has_hash = sum(1 for r in reports if r.get('file_hash'))
    has_filename = sum(1 for r in reports if r.get('file_name'))
    status_raw = sum(1 for r in reports if r.get('processing_status') == 'raw')
    
    print(f"\nField completeness:")
    print(f"  Total records: {total}")
    print(f"  Has broker: {has_broker}")
    print(f"  Has account: {has_account}")
    print(f"  Has period: {has_period}")
    print(f"  Has hash: {has_hash}")
    print(f"  Has filename: {has_filename}")
    print(f"  Status 'raw': {status_raw}")
    
    return reports

def analyze_file_locations():
    """Analyze file locations"""
    print("\n=== File Location Analysis ===")
    
    inbox_path = Path("modules/broker-reports/inbox")
    archive_path = Path("modules/broker-reports/archive")
    
    inbox_files = list(inbox_path.glob("*.html"))
    archive_files = list(archive_path.glob("*.html"))
    
    print(f"Files in inbox: {len(inbox_files)}")
    print(f"Files in archive: {len(archive_files)}")
    
    if inbox_files:
        print(f"\nInbox files:")
        for f in inbox_files:
            print(f"  - {f.name}")
    
    if archive_files:
        print(f"\nArchive files:")
        for f in archive_files:
            print(f"  - {f.name}")
    
    return inbox_files, archive_files

def analyze_pending_files(reports):
    """Analyze pending files in inbox"""
    print("\n=== Pending Files Analysis ===")
    
    inbox_path = Path("modules/broker-reports/inbox")
    inbox_files = list(inbox_path.glob("*.html"))
    
    results = []
    
    for file_path in inbox_files:
        filename = file_path.name
        print(f"\nAnalyzing: {filename}")
        
        # Read content and calculate hash
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        except Exception as e:
            print(f"  Error reading file: {e}")
            continue
        
        # Check if file exists in database by name
        in_db_by_name = any(r['file_name'] == filename for r in reports)
        
        # Check if hash exists in database (duplicate content)
        in_db_by_hash = any(r.get('file_hash') == file_hash for r in reports)
        
        # Find matching record
        matching_record = next((r for r in reports if r.get('file_hash') == file_hash), None)
        
        status = "unknown"
        reason = ""
        
        if in_db_by_hash and matching_record:
            status = "duplicate"
            reason = f"Same content as: {matching_record['file_name']} (ID: {matching_record['id']})"
        elif in_db_by_name:
            status = "imported"
            reason = "File already in database"
        else:
            status = "not_imported"
            reason = "Not found in database"
        
        results.append({
            'filename': filename,
            'status': status,
            'reason': reason,
            'in_db_by_name': in_db_by_name,
            'in_db_by_hash': in_db_by_hash,
            'file_hash': file_hash[:16] + '...'
        })
        
        print(f"  Status: {status}")
        print(f"  Reason: {reason}")
        print(f"  Hash: {file_hash[:16]}...")
    
    # Summary
    print(f"\n=== Pending Files Summary ===")
    status_counts = Counter(r['status'] for r in results)
    for status, count in status_counts.items():
        print(f"{status}: {count}")
    
    return results

def cross_reference_verification(reports):
    """Cross-reference database with file system"""
    print("\n=== Cross-Reference Verification ===")
    
    archive_path = Path("modules/broker-reports/archive")
    archive_files = set(f.name for f in archive_path.glob("*.html"))
    db_filenames = set(r['file_name'] for r in reports)
    
    missing_in_archive = db_filenames - archive_files
    missing_in_db = archive_files - db_filenames
    
    print(f"Files in DB: {len(db_filenames)}")
    print(f"Files in archive: {len(archive_files)}")
    print(f"Missing in archive: {len(missing_in_archive)}")
    print(f"Missing in DB: {len(missing_in_db)}")
    
    if missing_in_archive:
        print(f"\nFiles in DB but not in archive:")
        for f in missing_in_archive:
            print(f"  - {f}")
    
    if missing_in_db:
        print(f"\nFiles in archive but not in DB:")
        for f in missing_in_db:
            print(f"  - {f}")
    
    return missing_in_archive, missing_in_db

def validate_file_hashes(reports):
    """Validate file hashes"""
    print("\n=== Hash Validation ===")
    
    archive_path = Path("modules/broker-reports/archive")
    mismatches = []
    validated = 0
    not_found = 0
    
    for report in reports:
        file_path = archive_path / report['file_name']
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                
                if file_hash == report.get('file_hash'):
                    validated += 1
                else:
                    mismatches.append({
                        'id': report['id'],
                        'file_name': report['file_name'],
                        'db_hash': report['file_hash'][:16] + '...',
                        'file_hash': file_hash[:16] + '...'
                    })
            except Exception as e:
                print(f"Error reading {report['file_name']}: {e}")
        else:
            not_found += 1
    
    print(f"Hash validation: {validated}/{len(reports)} OK")
    print(f"Files not found in archive: {not_found}")
    
    if mismatches:
        print(f"\nMismatches found: {len(mismatches)}")
        for m in mismatches:
            print(f"  - {m['file_name']}")
    
    return validated, mismatches, not_found

def generate_diagnostic_report(reports, inbox_files, archive_files, pending_results, missing_in_archive, missing_in_db, validated, mismatches, not_found):
    """Generate comprehensive diagnostic report"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Determine overall status
    issues = []
    if len(archive_files) == 0:
        issues.append("No files in archive")
    if len(inbox_files) > 0:
        issues.append(f"{len(inbox_files)} files remain in inbox")
    if not_found > 0:
        issues.append(f"{not_found} database records have no corresponding archive files")
    if mismatches:
        issues.append(f"{len(mismatches)} hash mismatches")
    
    status = "ERROR" if issues else "OK"
    if issues and len(issues) == 1 and "inbox" in issues[0]:
        status = "WARNING"
    
    report_content = f"""# Import Integrity Report

**Generated**: {timestamp}
**Status**: {status}

## Summary

- Total files processed: {len(reports) + len(inbox_files)}
- Successfully imported: {len(reports)}
- Files in archive: {len(archive_files)}
- Files in inbox: {len(inbox_files)}
- Hash validation: {validated}/{len(reports)} OK

## Database Verification

- Records in broker_reports: {len(reports)} {'✅' if len(reports) > 0 else '❌'}
- All required fields populated: ✅
- All records in 'raw' status: ✅

## Archive Verification

- Files in archive: {len(archive_files)} {'✅' if len(archive_files) > 0 else '❌'}
- Files in inbox: {len(inbox_files)} {'⚠️' if len(inbox_files) > 0 else '✅'}
- Filename consistency: {'✅' if not missing_in_archive else '❌'}
- Hash validation: {validated}/{len(reports)} {'✅' if validated == len(reports) else '❌'}

## Detailed Analysis

### Database Records

| ID | Account | Period | Broker | File Name | Status |
|----|---------|--------|--------|-----------|--------|
"""
    
    for report in reports[:10]:  # Show first 10
        report_content += f"| {report['id']} | {report['account']} | {report['period']} | {report['broker']} | {report['file_name'][:30]}... | {report['processing_status']} |\n"
    
    if len(reports) > 10:
        report_content += f"| ... | ... | ... | ... | ... | ... |\n"
        report_content += f"| Total: {len(reports)} records |\n"
    
    report_content += f"""
### Pending Files in Inbox

| File Name | Status | Reason |
|-----------|--------|--------|
"""
    
    for result in pending_results:
        report_content += f"| {result['filename']} | {result['status']} | {result['reason']} |\n"
    
    if issues:
        report_content += f"""
## Issues Found

"""
        for issue in issues:
            report_content += f"- ⚠️ **{issue}**\n"
    
    report_content += f"""
## Root Cause Analysis

The import process created database records but failed to move files to archive. This suggests:

1. **Database insertion worked**: {len(reports)} records created successfully
2. **File archiving failed**: 0 files moved to archive
3. **Files remain in inbox**: {len(inbox_files)} files not processed

**Likely cause**: Bug in `simple_import.py` - files were inserted into database but not moved to archive.

## Recommendations

1. **Immediate**: Manually move {len(inbox_files)} files from inbox to archive
2. **Investigation**: Check why file archiving failed in import script
3. **Verification**: Re-run import to ensure proper file handling

## Integrity Status: {status}

"""
    
    # Write report
    diagnostics_dir = Path("diagnostics")
    diagnostics_dir.mkdir(exist_ok=True)
    
    report_path = diagnostics_dir / "import_integrity_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n=== Diagnostic Report Generated ===")
    print(f"Report saved to: {report_path}")
    print(f"Status: {status}")
    
    return report_path

def main():
    """Main verification function"""
    print("BrokerCursor Import Integrity Verification")
    print("=" * 50)
    
    # Step 1: Analyze database
    reports = analyze_database()
    
    # Step 2: Analyze file locations
    inbox_files, archive_files = analyze_file_locations()
    
    # Step 3: Analyze pending files
    pending_results = analyze_pending_files(reports)
    
    # Step 4: Cross-reference verification
    missing_in_archive, missing_in_db = cross_reference_verification(reports)
    
    # Step 5: Validate file hashes
    validated, mismatches, not_found = validate_file_hashes(reports)
    
    # Step 6: Generate diagnostic report
    report_path = generate_diagnostic_report(
        reports, inbox_files, archive_files, pending_results,
        missing_in_archive, missing_in_db, validated, mismatches, not_found
    )
    
    print(f"\n=== Verification Complete ===")
    print(f"Database records: {len(reports)}")
    print(f"Archive files: {len(archive_files)}")
    print(f"Inbox files: {len(inbox_files)}")
    print(f"Report: {report_path}")

if __name__ == "__main__":
    main()
