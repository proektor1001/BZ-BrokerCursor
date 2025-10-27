#!/usr/bin/env python3
"""
CLI tool to fetch broker report summary and generate markdown table
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime
from typing import List, Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations
from core.config import Config


def format_null_value(value: Any) -> str:
    """Format NULL values for markdown table"""
    if value is None:
        return "N/A"
    return str(value)


def generate_markdown_table(reports: List[Dict]) -> str:
    """Generate markdown table from report data"""
    if not reports:
        return "No reports found in database."
    
    # Table header
    markdown = "| Report ID | Broker | Account | Period | Account Number | Period Start | Period End |\n"
    markdown += "|-----------|--------|---------|--------|----------------|--------------|------------|\n"
    
    # Table rows
    for report in reports:
        row = "|".join([
            format_null_value(report.get('report_id')),
            format_null_value(report.get('broker')),
            format_null_value(report.get('account')),
            format_null_value(report.get('period')),
            format_null_value(report.get('account_number')),
            format_null_value(report.get('period_start')),
            format_null_value(report.get('period_end'))
        ])
        markdown += f"|{row}|\n"
    
    return markdown


def main():
    parser = argparse.ArgumentParser(description="Fetch broker report summary")
    parser.add_argument("--output", "-o", help="Output file path", 
                       default="diagnostics/broker_reports_summary.md")
    args = parser.parse_args()

    # Ensure directories exist before any DB operations
    config = Config()
    try:
        config.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        config.ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
        config.PARSED_PATH.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Initialize database operations
    ops = BrokerReportOperations()
    
    # Execute the SQL query from task_87
    query = """
        SELECT
            id AS report_id,
            broker,
            account,
            period,
            parsed_data ->> 'account_number' AS account_number,
            parsed_data ->> 'period_start' AS period_start,
            parsed_data ->> 'period_end' AS period_end
        FROM broker_reports
        ORDER BY (parsed_data ->> 'period_start') DESC NULLS LAST
    """
    
    try:
        reports = ops.execute_raw_query(query)
        
        # Generate markdown content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_count = len(reports)
        
        content = f"""# Broker Reports Summary

Generated: {timestamp}
Total Reports: {total_count}

{generate_markdown_table(reports)}

## Notes

- Fields from `parsed_data` (Account Number, Period Start, Period End) may be NULL for unparsed reports
- Reports are ordered by period_start (from parsed_data) in descending order
- NULL values are displayed as "N/A"
"""
        
        # Write to output file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Summary generated: {output_path}")
        print(f"Total reports: {total_count}")
        return 0
        
    except Exception as e:
        print(f"Error fetching report summary: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
