#!/usr/bin/env python3
"""
Verification script to compare database values with HTML source
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations
from core.parsers.sber_html_parser import SberHtmlParser
from core.config import Config
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def compare_values(db_value, html_value, field_name: str) -> Tuple[bool, str]:
    """Compare two values and return match status and notes"""
    if db_value is None and html_value is None:
        return True, "Both null"
    
    if db_value is None or html_value is None:
        return False, f"One is null: DB={db_value}, HTML={html_value}"
    
    # Handle different data types
    if isinstance(db_value, (int, float)) and isinstance(html_value, (int, float)):
        # Numeric comparison with small tolerance
        tolerance = 0.01
        if abs(db_value - html_value) <= tolerance:
            return True, "Match"
        else:
            return False, f"Difference: {abs(db_value - html_value):.2f}"
    
    # String comparison
    if str(db_value).strip() == str(html_value).strip():
        return True, "Match"
    else:
        return False, f"Different: '{db_value}' vs '{html_value}'"


def format_value(value: Any, field_name: str) -> str:
    """Format value for display"""
    if value is None:
        return "N/A"
    
    if field_name == "balance_ending" and isinstance(value, (int, float)):
        return f"{value:,.2f} ₽"
    elif field_name == "financial_result" and isinstance(value, (int, float)):
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:,.2f} ₽"
    elif field_name == "trade_count" and isinstance(value, (int, float)):
        return str(int(value))
    elif field_name == "instruments" and isinstance(value, list):
        return f"{len(value)} instruments"
    else:
        return str(value)


def verify_report(report_id: int, ops: BrokerReportOperations) -> Dict[str, Any]:
    """Verify a single report by comparing DB data with fresh HTML parse"""
    try:
        # Get report from database
        report = ops.get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        html_content = report.get('html_content')
        if not html_content:
            raise ValueError(f"Report {report_id} has no HTML content")
        
        parsed_data = report.get('parsed_data')
        if not parsed_data:
            raise ValueError(f"Report {report_id} not parsed yet")
        
        # Re-parse HTML to get "expected" values
        parser = SberHtmlParser()
        fresh_parsed = parser.parse(html_content)
        
        # Compare key fields
        comparisons = []
        
        fields_to_compare = [
            ("balance_ending", "Balance Ending"),
            ("account_open_date", "Account Open Date"),
            ("trade_count", "Trade Count"),
            ("instruments", "Instruments Count"),
            ("financial_result", "Financial Result")
        ]
        
        for field_key, field_display in fields_to_compare:
            db_value = parsed_data.get(field_key)
            html_value = fresh_parsed.get(field_key)
            
            # Special handling for trade_count and instruments
            if field_key == "trade_count":
                db_value = parsed_data.get("trades", {}).get("count", 0)
                html_value = fresh_parsed.get("trades", {}).get("count", 0)
            elif field_key == "instruments":
                db_value = len(parsed_data.get("instruments", []))
                html_value = len(fresh_parsed.get("instruments", []))
            
            match, notes = compare_values(db_value, html_value, field_key)
            
            comparisons.append({
                "field": field_display,
                "db_value": format_value(db_value, field_key),
                "html_value": format_value(html_value, field_key),
                "match": match,
                "notes": notes
            })
        
        return {
            "report": report,
            "comparisons": comparisons,
            "all_match": all(comp["match"] for comp in comparisons),
            "fresh_parsed": fresh_parsed
        }
        
    except Exception as e:
        logger.error(f"Failed to verify report {report_id}: {e}")
        raise


def generate_markdown_report(verification_result: Dict[str, Any], output_path: Path):
    """Generate markdown verification report"""
    report = verification_result["report"]
    comparisons = verification_result["comparisons"]
    all_match = verification_result["all_match"]
    fresh_parsed = verification_result["fresh_parsed"]
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    content = f"""# Database Data Verification Report

**Report:** {report.get('file_name', 'Unknown')}
**Account:** {report.get('account', 'N/A')}
**Period:** {report.get('period', 'N/A')}
**Generated:** {timestamp}

## Verification Results

| Field | DB Value | HTML Value | Match | Notes |
|-------|----------|------------|-------|-------|"""
    
    for comp in comparisons:
        match_symbol = "✅" if comp["match"] else "❌"
        content += f"\n| {comp['field']} | {comp['db_value']} | {comp['html_value']} | {match_symbol} | {comp['notes']} |"
    
    content += f"""

## Instruments List

| Name | ISIN | Quantity |
|------|------|----------|"""
    
    instruments = fresh_parsed.get("instruments", [])
    for instrument in instruments:
        content += f"\n| {instrument.get('name', '')} | {instrument.get('isin', '')} | {instrument.get('quantity', 0)} |"
    
    content += f"""

## Summary

- {'✅ All fields match' if all_match else '❌ Some fields do not match'}
- 🔍 Data integrity: {'VERIFIED' if all_match else 'NEEDS ATTENTION'}

## Technical Details

- **Report ID:** {report.get('id')}
- **Broker:** {report.get('broker')}
- **Processing Status:** {report.get('processing_status')}
- **Created:** {report.get('created_at')}
- **Updated:** {report.get('updated_at')}
"""
    
    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"Verification report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Verify report data from database")
    parser.add_argument("--report-id", type=int, help="Verify specific report by ID")
    parser.add_argument("--search", action="append", help="key=value; supports account", dest="search")
    parser.add_argument("--filter", action="append", help="key=value; broker, period, status, account", dest="filters")
    parser.add_argument("--output", help="Output file path (default: diagnostics/db_data_verification.md)")
    args = parser.parse_args()

    # Ensure directories exist
    config = Config()
    try:
        config.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        config.ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
        config.PARSED_PATH.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Parse filters
    def parse_filters(filter_args):
        filters = {}
        for item in filter_args or []:
            if '=' not in item:
                continue
            key, value = item.split('=', 1)
            key = key.strip().lower()
            value = value.strip()
            if key in {"broker", "period", "status", "account"}:
                filters[key] = value
        return filters

    filters = parse_filters(args.filters)
    search_map = parse_filters(args.search)

    ops = BrokerReportOperations()
    console = Console()

    # Find report to verify
    if args.report_id:
        report = ops.get_report(args.report_id)
        if not report:
            console.print(f"[red]Report {args.report_id} not found[/red]")
            return 1
        reports = [report]
    else:
        # Search for reports
        reports = ops.list_reports(
            broker=filters.get("broker"),
            period=filters.get("period"),
            status='parsed',  # Only verify parsed reports
            account=filters.get("account"),
            search_account=search_map.get("account"),
            limit=1,  # Only one report for verification
            offset=0
        )

    if not reports:
        console.print("[yellow]No parsed reports found to verify[/yellow]")
        return 0

    if len(reports) > 1:
        console.print("[yellow]Multiple reports found. Please specify --report-id for single report verification[/yellow]")
        return 1

    # Verify the report
    report = reports[0]
    console.print(f"[green]Verifying report {report['id']}: {report.get('file_name', 'Unknown')}[/green]")
    
    try:
        verification_result = verify_report(report['id'], ops)
        
        # Display results
        table = Table(title="Verification Results")
        table.add_column("Field", style="cyan")
        table.add_column("DB Value", style="green")
        table.add_column("HTML Value", style="blue")
        table.add_column("Match", style="magenta")
        table.add_column("Notes", style="white")
        
        for comp in verification_result["comparisons"]:
            match_symbol = "✅" if comp["match"] else "❌"
            table.add_row(
                comp["field"],
                comp["db_value"],
                comp["html_value"],
                match_symbol,
                comp["notes"]
            )
        
        console.print(table)
        
        # Show summary
        all_match = verification_result["all_match"]
        if all_match:
            console.print(Panel("[green]✅ All fields match - Data integrity VERIFIED[/green]", title="Summary"))
        else:
            console.print(Panel("[red]❌ Some fields do not match - Data integrity NEEDS ATTENTION[/red]", title="Summary"))
        
        # Generate markdown report
        output_path = Path(args.output) if args.output else Path("diagnostics/db_data_verification.md")
        generate_markdown_report(verification_result, output_path)
        console.print(f"[green]Verification report saved to {output_path}[/green]")
        
        return 0 if all_match else 1
        
    except Exception as e:
        console.print(f"[red]Verification failed: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
