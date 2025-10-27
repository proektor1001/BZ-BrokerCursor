#!/usr/bin/env python3
"""
Script to fix invalid period values in broker_reports table
Identifies and corrects records with period outside 2000-01 to 2025-12 range
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations
from core.config import Config


def validate_date_format(date_str: str) -> bool:
    """Validate YYYY-MM-DD format"""
    if not date_str:
        return False
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, date_str))


def extract_period_from_date(date_str: str) -> Optional[str]:
    """Extract YYYY-MM from YYYY-MM-DD date string"""
    if not validate_date_format(date_str):
        return None
    return date_str[:7]  # YYYY-MM


def is_valid_period(period: str) -> bool:
    """Check if period is within valid range 2000-01 to 2025-12"""
    if not period:
        return False
    return '2000-01' <= period <= '2025-12'


def log_change(log_file: Path, report_id: int, old_period: str, new_period: str, 
               reason: str, filename: str):
    """Log a change to the diagnostics file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] ID={report_id} | OLD='{old_period}' | NEW='{new_period}' | REASON='{reason}' | FILE='{filename}'\n"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def find_invalid_records(ops: BrokerReportOperations) -> List[Dict]:
    """Find records with invalid period values"""
    query = """
        SELECT id, broker, account, period, file_name, 
               parsed_data ->> 'period_start' AS period_start,
               parsed_data ->> 'period_end' AS period_end,
               parser_version
        FROM broker_reports 
        WHERE (period < '2000-01' OR period > '2025-12')
        AND parser_version IS NOT NULL
        AND parsed_data IS NOT NULL
        AND parsed_data ->> 'period_start' IS NOT NULL
        ORDER BY id
    """
    
    return ops.execute_raw_query(query)


def check_duplicate_period(ops: BrokerReportOperations, broker: str, account: str, period: str, exclude_id: int) -> bool:
    """Check if a broker/account/period combination already exists (excluding given ID)"""
    query = """
        SELECT COUNT(*) as count
        FROM broker_reports 
        WHERE broker = %s AND account = %s AND period = %s AND id != %s
    """
    result = ops.execute_raw_query(query, (broker, account, period, exclude_id))
    return result[0]['count'] > 0 if result else False


def fix_record_period(ops: BrokerReportOperations, record: Dict, log_file: Path) -> bool:
    """Fix period for a single record"""
    report_id = record['id']
    old_period = record['period']
    period_start = record['period_start']
    filename = record['file_name']
    broker = record['broker']
    account = record['account']
    
    # Extract corrected period from period_start
    new_period = extract_period_from_date(period_start)
    
    if not new_period:
        log_change(log_file, report_id, old_period, "FAILED", 
                  "Invalid period_start format", filename)
        return False
    
    if not is_valid_period(new_period):
        log_change(log_file, report_id, old_period, "FAILED", 
                  f"Extracted period {new_period} outside valid range", filename)
        return False
    
    if new_period == old_period:
        log_change(log_file, report_id, old_period, "SKIPPED", 
                  "Period already correct", filename)
        return True
    
    # Check for duplicate period combination
    if check_duplicate_period(ops, broker, account, new_period, report_id):
        # Set period to a unique invalid value to avoid duplicate constraint violation
        # Use a format that's clearly invalid: 9999-MM (where MM is the original month)
        unique_invalid_period = f"9999-{new_period.split('-')[1]}"
        
        try:
            update_query = """
                UPDATE broker_reports 
                SET period = %s, updated_at = NOW() 
                WHERE id = %s
            """
            
            with ops.db.get_cursor() as cursor:
                cursor.execute(update_query, (unique_invalid_period, report_id))
                ops.db.connection.commit()
                
                if cursor.rowcount > 0:
                    log_change(log_file, report_id, old_period, unique_invalid_period, 
                              f"Period {new_period} already exists for {broker}/{account}, set to {unique_invalid_period}", filename)
                    return True
                else:
                    log_change(log_file, report_id, old_period, "FAILED", 
                              "No rows updated when setting to unique invalid period", filename)
                    return False
                    
        except Exception as e:
            log_change(log_file, report_id, old_period, "ERROR", 
                      f"Database error when setting to unique invalid period: {str(e)}", filename)
            return False
    
    # Update the record
    try:
        update_query = """
            UPDATE broker_reports 
            SET period = %s, updated_at = NOW() 
            WHERE id = %s
        """
        
        with ops.db.get_cursor() as cursor:
            cursor.execute(update_query, (new_period, report_id))
            ops.db.connection.commit()
            
            if cursor.rowcount > 0:
                log_change(log_file, report_id, old_period, new_period, 
                          "Period corrected from period_start", filename)
                return True
            else:
                log_change(log_file, report_id, old_period, "FAILED", 
                          "No rows updated", filename)
                return False
                
    except Exception as e:
        log_change(log_file, report_id, old_period, "ERROR", 
                  f"Database error: {str(e)}", filename)
        return False


def verify_fixes(ops: BrokerReportOperations) -> Dict[str, int]:
    """Verify that all periods are now within valid range"""
    # Count remaining invalid periods (excluding special 9999- periods used for duplicates)
    invalid_query = """
        SELECT COUNT(*) as count
        FROM broker_reports 
        WHERE (period < '2000-01' OR period > '2025-12')
        AND period NOT LIKE '9999-%'
        AND parser_version IS NOT NULL
    """
    
    invalid_result = ops.execute_raw_query(invalid_query)
    remaining_invalid = invalid_result[0]['count'] if invalid_result else 0
    
    # Count total records with parser_version
    total_query = """
        SELECT COUNT(*) as count
        FROM broker_reports 
        WHERE parser_version IS NOT NULL
    """
    
    total_result = ops.execute_raw_query(total_query)
    total_parsed = total_result[0]['count'] if total_result else 0
    
    return {
        'remaining_invalid': remaining_invalid,
        'total_parsed': total_parsed,
        'fixed_count': total_parsed - remaining_invalid
    }


def main():
    parser = argparse.ArgumentParser(description="Fix invalid period values in broker_reports")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be changed without making changes")
    parser.add_argument("--log-file", default="diagnostics/fixed_invalid_periods.log",
                       help="Path to log file")
    args = parser.parse_args()

    # Ensure directories exist
    config = Config()
    try:
        config.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        config.ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
        config.PARSED_PATH.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Initialize database operations
    ops = BrokerReportOperations()
    
    # Setup log file
    log_file = Path(args.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    if not args.dry_run:
        # Clear existing log file
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"# Fixed Invalid Periods Log\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    print("Searching for records with invalid periods...")
    
    # Find invalid records
    invalid_records = find_invalid_records(ops)
    
    if not invalid_records:
        print("No records with invalid periods found.")
        return 0
    
    print(f"Found {len(invalid_records)} records with invalid periods:")
    
    fixed_count = 0
    failed_count = 0
    
    for record in invalid_records:
        report_id = record['id']
        old_period = record['period']
        period_start = record['period_start']
        filename = record['file_name']
        
        print(f"  ID {report_id}: {old_period} -> {extract_period_from_date(period_start)} ({filename})")
        
        if args.dry_run:
            continue
        
        # Fix the record
        if fix_record_period(ops, record, log_file):
            fixed_count += 1
        else:
            failed_count += 1
    
    if args.dry_run:
        print(f"\nDRY RUN: Would fix {len(invalid_records)} records")
        return 0
    
    # Verify fixes
    print(f"\nFixing completed:")
    print(f"  Fixed: {fixed_count}")
    print(f"  Failed: {failed_count}")
    
    # Final verification
    verification = verify_fixes(ops)
    print(f"\nVerification:")
    print(f"  Total parsed records: {verification['total_parsed']}")
    print(f"  Remaining invalid: {verification['remaining_invalid']}")
    print(f"  Successfully fixed: {verification['fixed_count']}")
    
    if verification['remaining_invalid'] > 0:
        print(f"\nWARNING: {verification['remaining_invalid']} records still have invalid periods")
        print("Check the log file for details on failed corrections")
        return 1
    
    print(f"\nAll periods are now within valid range (2000-01 to 2025-12)")
    print(f"Log file: {log_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
