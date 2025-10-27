#!/usr/bin/env python3
"""
Reparse Sber reports to fix securities_portfolio extraction
Updates parsed_data with corrected portfolio information
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime
from typing import List, Dict, Any
import json
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations
from core.parsers.sber_html_parser import SberHtmlParser
from core.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def safe_float_conversion(value_str):
    """Safely convert string to float, handling Russian number format"""
    if not value_str:
        return None
    try:
        # Remove spaces and replace comma with dot
        clean_value = str(value_str).replace(' ', '').replace(',', '.')
        return float(clean_value)
    except (ValueError, TypeError):
        return None


def main():
    parser = argparse.ArgumentParser(description="Reparse Sber reports to fix securities_portfolio")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    parser.add_argument("--limit", type=int, help="Limit number of reports to process (for testing)")
    args = parser.parse_args()

    # Initialize database operations
    ops = BrokerReportOperations()
    parser_instance = SberHtmlParser()
    
    # Get all Sber reports with parser_version 2.0
    query = """
        SELECT id, broker, account, period, file_name, html_content, parsed_data
        FROM broker_reports
        WHERE broker = 'sber' AND parsed_data->>'parser_version' = '2.0'
        ORDER BY id
    """
    
    if args.limit:
        query += f" LIMIT {args.limit}"
    
    reports = ops.execute_raw_query(query)
    total_reports = len(reports)
    
    logger.info(f"Found {total_reports} Sber reports to reparse")
    
    # Statistics tracking
    stats = {
        'total_reports': total_reports,
        'processed': 0,
        'successful': 0,
        'failed': 0,
        'before_empty': 0,
        'after_empty': 0,
        'total_securities_before': 0,
        'total_securities_after': 0,
        'errors': []
    }
    
    # Sample data for JSON export
    sample_reports = []
    error_log = []
    
    for i, report in enumerate(reports, 1):
        report_id = report['id']
        file_name = report['file_name']
        html_content = report['html_content']
        current_parsed_data = report['parsed_data'] or {}
        
        logger.info(f"Processing report {i}/{total_reports}: ID={report_id}, File={file_name}")
        
        # Count securities before
        current_portfolio = current_parsed_data.get('securities_portfolio', [])
        securities_before = len(current_portfolio)
        stats['total_securities_before'] += securities_before
        if securities_before == 0:
            stats['before_empty'] += 1
        
        try:
            # Parse the HTML content
            new_parsed_data = parser_instance.parse(html_content)
            
            # Count securities after
            new_portfolio = new_parsed_data.get('securities_portfolio', [])
            securities_after = len(new_portfolio)
            stats['total_securities_after'] += securities_after
            if securities_after == 0:
                stats['after_empty'] += 1
            
            # Update the parsed_data with new portfolio
            updated_parsed_data = current_parsed_data.copy()
            updated_parsed_data['securities_portfolio'] = new_portfolio
            updated_parsed_data['parser_version'] = '2.0'  # Ensure version is set
            
            # Store sample data (first 20 reports)
            if len(sample_reports) < 20:
                sample_reports.append({
                    'report_id': report_id,
                    'broker': report['broker'],
                    'account': report['account'],
                    'period': report['period'],
                    'file_name': file_name,
                    'portfolio_length_before': securities_before,
                    'portfolio_length_after': securities_after,
                    'securities_portfolio': new_portfolio[:5] if new_portfolio else []  # First 5 securities
                })
            
            # Update database if not dry run
            if not args.dry_run:
                success = ops.update_report_parsed_data(report_id, updated_parsed_data)
                if success:
                    stats['successful'] += 1
                    logger.info(f"✓ Updated report {report_id}: {securities_before} → {securities_after} securities")
                else:
                    stats['failed'] += 1
                    error_msg = f"Failed to update database for report {report_id}"
                    logger.error(error_msg)
                    error_log.append({
                        'report_id': report_id,
                        'file_name': file_name,
                        'error': error_msg,
                        'securities_before': securities_before,
                        'securities_after': securities_after
                    })
            else:
                stats['successful'] += 1
                logger.info(f"[DRY RUN] Would update report {report_id}: {securities_before} → {securities_after} securities")
            
            stats['processed'] += 1
            
        except Exception as e:
            stats['failed'] += 1
            error_msg = f"Parsing error for report {report_id}: {str(e)}"
            logger.error(error_msg)
            error_log.append({
                'report_id': report_id,
                'file_name': file_name,
                'error': error_msg,
                'securities_before': securities_before,
                'securities_after': 0
            })
    
    # Calculate success rate
    success_rate = (stats['successful'] / stats['processed'] * 100) if stats['processed'] > 0 else 0
    portfolio_success_rate = ((stats['total_reports'] - stats['after_empty']) / stats['total_reports'] * 100) if stats['total_reports'] > 0 else 0
    
    # Generate summary report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    summary_content = f"""# Securities Portfolio Fix Summary

Generated: {timestamp}
Mode: {'DRY RUN' if args.dry_run else 'LIVE UPDATE'}

## Processing Results

- **Total Reports**: {stats['total_reports']}
- **Processed**: {stats['processed']}
- **Successful**: {stats['successful']}
- **Failed**: {stats['failed']}
- **Success Rate**: {success_rate:.1f}%

## Portfolio Statistics

- **Reports with Empty Portfolio (Before)**: {stats['before_empty']}
- **Reports with Empty Portfolio (After)**: {stats['after_empty']}
- **Portfolio Success Rate**: {portfolio_success_rate:.1f}%
- **Total Securities (Before)**: {stats['total_securities_before']}
- **Total Securities (After)**: {stats['total_securities_after']}

## Sample Securities Extracted

"""
    
    if sample_reports:
        summary_content += "| Report ID | Broker | Account | Period | Portfolio Length | Sample Securities |\n"
        summary_content += "|-----------|--------|---------|--------|------------------|-------------------|\n"
        
        for sample in sample_reports[:10]:  # Show first 10
            sample_securities = ", ".join([f"{s['name']} ({s['isin']})" for s in sample['securities_portfolio'][:3]])
            summary_content += f"| {sample['report_id']} | {sample['broker']} | {sample['account']} | {sample['period']} | {sample['portfolio_length_after']} | {sample_securities} |\n"
    
    # Add error section if any
    if error_log:
        summary_content += f"\n## Errors Encountered\n\n"
        summary_content += f"Total Errors: {len(error_log)}\n\n"
        summary_content += "| Report ID | File Name | Error |\n"
        summary_content += "|-----------|-----------|-------|\n"
        for error in error_log[:10]:  # Show first 10 errors
            summary_content += f"| {error['report_id']} | {error['file_name']} | {error['error']} |\n"
    
    # Add success criteria check
    summary_content += f"\n## Success Criteria Check\n\n"
    summary_content += f"- ✅ Minimum 50% portfolio success rate: {portfolio_success_rate:.1f}% {'✓' if portfolio_success_rate >= 50 else '✗'}\n"
    summary_content += f"- ✅ Processing success rate: {success_rate:.1f}% {'✓' if success_rate >= 90 else '✗'}\n"
    summary_content += f"- ✅ Total securities extracted: {stats['total_securities_after']} {'✓' if stats['total_securities_after'] > 0 else '✗'}\n"
    
    if portfolio_success_rate < 50:
        summary_content += f"\n⚠️ **WARNING**: Portfolio success rate ({portfolio_success_rate:.1f}%) is below 50% threshold!\n"
    
    # Write summary report
    summary_path = Path("diagnostics/securities_portfolio_fix_summary.md")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    # Write sample data JSON
    sample_data = {
        'timestamp': timestamp,
        'mode': 'DRY RUN' if args.dry_run else 'LIVE UPDATE',
        'statistics': stats,
        'success_rate': success_rate,
        'portfolio_success_rate': portfolio_success_rate,
        'sample_reports': sample_reports
    }
    
    sample_path = Path("diagnostics/parsed_reports_after_fix.json")
    with open(sample_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    # Write error log JSON
    if error_log:
        error_path = Path("diagnostics/securities_portfolio_errors.json")
        with open(error_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'total_errors': len(error_log),
                'errors': error_log
            }, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n=== REPARSE SUMMARY ===")
    print(f"Reports processed: {stats['processed']}/{stats['total_reports']}")
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Portfolio success rate: {portfolio_success_rate:.1f}%")
    print(f"Total securities extracted: {stats['total_securities_after']}")
    print(f"Summary report: {summary_path}")
    print(f"Sample data: {sample_path}")
    if error_log:
        print(f"Error log: diagnostics/securities_portfolio_errors.json")
    
    # Return appropriate exit code
    if portfolio_success_rate < 50:
        print(f"\n⚠️ WARNING: Portfolio success rate below 50% threshold!")
        return 1
    elif success_rate < 90:
        print(f"\n⚠️ WARNING: Processing success rate below 90% threshold!")
        return 1
    else:
        print(f"\n✅ SUCCESS: All criteria met!")
        return 0


if __name__ == "__main__":
    sys.exit(main())