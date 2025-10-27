#!/usr/bin/env python3
"""
Unified hash backfill utility for broker reports
Consolidates functionality from update_hashes.py and backfill_hashes.py
Supports both updating existing records and backfilling missing hashes
"""

import sys
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations

def find_file_in_paths(filename: str, search_paths: List[Path]) -> Tuple[bool, Path]:
    """Find file in multiple search paths"""
    for base_path in search_paths:
        potential_path = base_path / filename
        if potential_path.exists():
            return True, potential_path
    return False, None

def update_hashes_for_records(reports: List[Dict[str, Any]], search_paths: List[Path], 
                             update_existing: bool = True, backfill_missing: bool = True) -> Tuple[int, int]:
    """Update file_hash values for existing records"""
    print("=== Updating File Hashes ===")
    
    db_ops = BrokerReportOperations()
    updated = 0
    not_found = 0
    
    for report in reports:
        print(f"\nProcessing ID {report['id']}: {report['file_name']}")
        
        # Try to find the file
        file_found, file_path = find_file_in_paths(report['file_name'], search_paths)
        
        if file_found:
            try:
                # Calculate hash
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                
                print(f"  Found at: {file_path}")
                print(f"  Hash: {file_hash[:16]}...")
                
                # Check if we should update this record
                should_update = False
                if update_existing and report.get('file_hash'):
                    # Update existing hash
                    should_update = True
                    print(f"  Updating existing hash")
                elif backfill_missing and not report.get('file_hash'):
                    # Backfill missing hash
                    should_update = True
                    print(f"  Backfilling missing hash")
                
                if should_update:
                    # Update database record using raw SQL
                    update_query = """
                        UPDATE broker_reports 
                        SET file_hash = %s, updated_at = NOW()
                        WHERE id = %s
                    """
                    
                    with db_ops.db.get_cursor() as cursor:
                        cursor.execute(update_query, (file_hash, report['id']))
                        db_ops.db.connection.commit()
                    
                    print(f"  Updated database record {report['id']}")
                    updated += 1
                else:
                    print(f"  Skipped (no update needed)")
                
            except Exception as e:
                print(f"  Error processing file: {e}")
                not_found += 1
        else:
            print(f"  File not found in any archive location")
            not_found += 1
    
    return updated, not_found

def main():
    """Main function with enhanced CLI options"""
    parser = argparse.ArgumentParser(description="Unified hash backfill utility for broker reports")
    parser.add_argument("--update-existing", action="store_true", 
                       help="Update existing file_hash values")
    parser.add_argument("--backfill-missing", action="store_true", 
                       help="Backfill missing file_hash values")
    parser.add_argument("--all", action="store_true", 
                       help="Update all records (equivalent to --update-existing --backfill-missing)")
    parser.add_argument("--limit", type=int, default=1000, 
                       help="Maximum number of records to process")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be processed without making changes")
    
    args = parser.parse_args()
    
    # Determine operation mode
    if args.all:
        update_existing = True
        backfill_missing = True
    else:
        update_existing = args.update_existing
        backfill_missing = args.backfill_missing
    
    if not update_existing and not backfill_missing:
        print("Error: Must specify --update-existing, --backfill-missing, or --all")
        return 1
    
    print(f"Mode: update_existing={update_existing}, backfill_missing={backfill_missing}")
    
    # Initialize database operations
    db_ops = BrokerReportOperations()
    reports = db_ops.list_reports(limit=args.limit)
    
    print(f"Found {len(reports)} records to process")
    
    if args.dry_run:
        print("\n=== DRY RUN - No changes will be made ===")
        for report in reports[:5]:  # Show first 5
            print(f"ID {report['id']}: {report['file_name']} (hash: {report.get('file_hash', 'None')[:16] if report.get('file_hash') else 'None'}...)")
        if len(reports) > 5:
            print(f"... and {len(reports) - 5} more records")
        return 0
    
    # Define search paths for archived files
    search_paths = [
        Path("L:/modules/broker-reports/archive"),
        Path("modules/broker-reports/archive"),
        Path("L:/BZ-BrokerCursor/modules/broker-reports/archive"),
        Path("modules/broker-reports/archive").resolve(),
    ]
    
    print(f"Search paths: {[str(p) for p in search_paths]}")
    
    # Process records
    updated, not_found = update_hashes_for_records(
        reports, search_paths, update_existing, backfill_missing
    )
    
    # Print summary
    print(f"\n=== Update Summary ===")
    print(f"Records updated: {updated}")
    print(f"Records not found: {not_found}")
    
    return 0 if not_found == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
