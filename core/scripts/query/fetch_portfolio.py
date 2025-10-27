#!/usr/bin/env python3
"""
CLI tool to fetch current portfolio from database
Extracts securities holdings from the most recent parsed reports per broker/account
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime
from typing import List, Dict, Any
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations
from core.config import Config


def format_null_value(value: Any) -> str:
    """Format NULL values for markdown table"""
    if value is None or value == "":
        return "N/A"
    return str(value)


def format_currency(value: Any) -> str:
    """Format currency values"""
    if value is None or value == "" or value == "0":
        return "0.00"
    try:
        # Remove spaces and convert to float, then format
        clean_value = str(value).replace(' ', '').replace(',', '.')
        return f"{float(clean_value):.2f}"
    except (ValueError, TypeError):
        return "0.00"


def generate_portfolio_table(portfolio_data: List[Dict]) -> str:
    """Generate markdown table from portfolio data"""
    if not portfolio_data:
        return "No portfolio data found in database."
    
    # Table header
    markdown = "| Broker | Account | Period End | Security Name | ISIN | Quantity | Price | Value |\n"
    markdown += "|--------|---------|------------|--------------|------|----------|-------|-------|\n"
    
    # Table rows
    for item in portfolio_data:
        row = "|".join([
            format_null_value(item.get('broker')),
            format_null_value(item.get('account')),
            format_null_value(item.get('period_end')),
            format_null_value(item.get('name')),
            format_null_value(item.get('isin')),
            format_null_value(item.get('quantity_end')),
            format_currency(item.get('price_end')),
            format_currency(item.get('value_end'))
        ])
        markdown += f"|{row}|\n"
    
    return markdown


def generate_summary_stats(portfolio_data: List[Dict]) -> str:
    """Generate summary statistics"""
    if not portfolio_data:
        return "No data available for summary."
    
    # Count unique brokers and accounts
    brokers = set(item.get('broker') for item in portfolio_data)
    accounts = set(f"{item.get('broker')}/{item.get('account')}" for item in portfolio_data)
    
    # Calculate total portfolio value
    total_value = 0.0
    securities_count = 0
    
    for item in portfolio_data:
        securities_count += 1
        try:
            value_str = str(item.get('value_end', '0')).replace(' ', '').replace(',', '.')
            total_value += float(value_str) if value_str else 0.0
        except (ValueError, TypeError):
            pass
    
    return f"""
## Summary Statistics

- **Total Securities**: {securities_count}
- **Unique Brokers**: {len(brokers)} ({', '.join(sorted(brokers))})
- **Unique Accounts**: {len(accounts)}
- **Total Portfolio Value**: {total_value:.2f} RUB
"""


def save_sql_query() -> str:
    """Generate and save the SQL query used for portfolio extraction"""
    sql_query = """-- Portfolio Query: Extract Current Securities Holdings
-- Generated: {timestamp}
-- Purpose: Get latest portfolio data per broker/account from parsed reports

WITH latest_reports AS (
  SELECT DISTINCT ON (broker, COALESCE(account, '∅'))
    id, broker, account, 
    parsed_data->>'period_end' AS period_end,
    parsed_data->'securities_portfolio' AS portfolio
  FROM broker_reports
  WHERE processing_status = 'parsed'
    AND parsed_data->>'parser_version' = '2.0'
    AND parsed_data->'securities_portfolio' IS NOT NULL
  ORDER BY broker, COALESCE(account, '∅'), 
           TO_DATE(parsed_data->>'period_end', 'YYYY-MM-DD') DESC
)
SELECT 
  broker, 
  account, 
  period_end,
  security->>'name' AS name,
  security->>'isin' AS isin,
  security->>'quantity_end' AS quantity_end,
  security->>'price_end' AS price_end,
  security->>'value_end' AS value_end
FROM latest_reports,
     jsonb_array_elements(portfolio) AS security
WHERE security->>'name' IS NOT NULL 
  AND security->>'name' != ''
ORDER BY broker, account, name;
""".format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    return sql_query


def main():
    parser = argparse.ArgumentParser(description="Fetch current portfolio from database")
    parser.add_argument("--output", "-o", help="Output report file path", 
                       default="diagnostics/current_portfolio_report.md")
    parser.add_argument("--sql-output", "-s", help="SQL query output file path",
                       default="diagnostics/sql_portfolio_query.sql")
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
    
    # Execute the portfolio query
    query = """
        WITH latest_reports AS (
          SELECT DISTINCT ON (broker, COALESCE(account, '∅'))
            id, broker, account, 
            parsed_data->>'period_end' AS period_end,
            parsed_data->'securities_portfolio' AS portfolio
          FROM broker_reports
          WHERE processing_status = 'parsed'
            AND parsed_data->>'parser_version' = '2.0'
            AND parsed_data->'securities_portfolio' IS NOT NULL
          ORDER BY broker, COALESCE(account, '∅'), 
                   TO_DATE(parsed_data->>'period_end', 'YYYY-MM-DD') DESC
        )
        SELECT 
          broker, 
          account, 
          period_end,
          security->>'name' AS name,
          security->>'isin' AS isin,
          security->>'quantity_end' AS quantity_end,
          security->>'price_end' AS price_end,
          security->>'value_end' AS value_end
        FROM latest_reports,
             jsonb_array_elements(portfolio) AS security
        WHERE security->>'name' IS NOT NULL 
          AND security->>'name' != ''
        ORDER BY broker, account, name
    """
    
    try:
        portfolio_data = ops.execute_raw_query(query)
        
        # Generate markdown content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_securities = len(portfolio_data)
        
        content = f"""# Current Portfolio Report

Generated: {timestamp}
Source: Database query on `broker_reports.parsed_data` (JSONB)
Total Securities: {total_securities}

## Portfolio Holdings

{generate_portfolio_table(portfolio_data)}

{generate_summary_stats(portfolio_data)}

## Data Source Verification

- **Query Type**: Direct SQL query to `broker_reports` table
- **Data Field**: `parsed_data` (JSONB) containing `securities_portfolio` array
- **Parser Version**: 2.0 (filtered)
- **Processing Status**: parsed (filtered)
- **Date Sorting**: `TO_DATE(parsed_data->>'period_end', 'YYYY-MM-DD') DESC`
- **Latest Report Selection**: Per broker+account combination

## Notes

- Data extracted exclusively from database `parsed_data` field
- Only includes securities with non-empty names
- Currency values formatted as decimal numbers
- NULL values displayed as "N/A"
- Reports ordered by broker, account, then security name
"""
        
        # Write portfolio report
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Write SQL query
        sql_query = save_sql_query()
        sql_output_path = Path(args.sql_output)
        sql_output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(sql_output_path, 'w', encoding='utf-8') as f:
            f.write(sql_query)
        
        print(f"Portfolio report generated: {output_path}")
        print(f"SQL query saved: {sql_output_path}")
        print(f"Total securities: {total_securities}")
        return 0
        
    except Exception as e:
        print(f"Error fetching portfolio: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
