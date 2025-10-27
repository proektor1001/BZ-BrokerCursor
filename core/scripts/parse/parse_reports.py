#!/usr/bin/env python3
"""
CLI tool to parse raw broker reports and extract structured data
"""

import sys
from pathlib import Path
import argparse
from typing import Dict, Any, List

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations
from core.parsers import get_parser, is_broker_supported, list_supported_brokers
from core.config import Config
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_filters(filter_args):
    """Parse filter arguments"""
    filters: Dict[str, Any] = {}
    for item in filter_args or []:
        if '=' not in item:
            continue
        key, value = item.split('=', 1)
        key = key.strip().lower()
        value = value.strip()
        if key in {"broker", "period", "status", "account"}:
            filters[key] = value
    return filters


def get_parser_for_broker(broker: str):
    """Get appropriate parser for broker using registry"""
    try:
        return get_parser(broker)
    except ValueError as e:
        logger.error(f"Parser error for broker '{broker}': {e}")
        raise


def parse_single_report(report: Dict[str, Any], ops: BrokerReportOperations) -> bool:
    """Parse a single report and update database"""
    try:
        report_id = report['id']
        broker = report['broker']
        html_content = report.get('html_content')
        
        # Handle unknown broker gracefully
        if broker == 'unknown':
            logger.warning(f"Report {report_id} has unknown broker, skipping parsing")
            ops.update_report_status(report_id, 'error', error_log='Unknown broker - no parser available')
            return False
        
        # Check if broker is supported
        if not is_broker_supported(broker):
            logger.warning(f"Report {report_id} has unsupported broker '{broker}', skipping parsing")
            ops.update_report_status(report_id, 'error', error_log=f'Unsupported broker: {broker}')
            return False
        
        if not html_content:
            logger.warning(f"Report {report_id} has no HTML content")
            return False
        
        # Get appropriate parser
        parser = get_parser_for_broker(broker)
        
        # Parse the HTML content
        parsed_data = parser.parse(html_content)
        
        # Update the report in database
        success = ops.update_report_status(
            report_id=report_id,
            status='parsed',
            parsed_data=parsed_data
        )
        
        if success:
            logger.info(f"Successfully parsed report {report_id}")
            return True
        else:
            logger.error(f"Failed to update report {report_id}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to parse report {report.get('id', 'unknown')}: {e}")
        # Update status to error
        try:
            ops.update_report_status(
                report_id=report['id'],
                status='error',
                error_log=str(e)
            )
        except:
            pass
        return False


def main():
    parser = argparse.ArgumentParser(description="Parse raw broker reports")
    parser.add_argument("--filter", action="append", help="key=value; broker, period, status, account", dest="filters")
    parser.add_argument("--search", action="append", help="key=value; supports account", dest="search")
    parser.add_argument("--report-id", type=int, help="Parse specific report by ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be parsed without actually parsing")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of reports to process")
    args = parser.parse_args()

    # Ensure directories exist
    config = Config()
    try:
        config.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        config.ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
        config.PARSED_PATH.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    filters = parse_filters(args.filters)
    search_map = parse_filters(args.search)

    ops = BrokerReportOperations()
    console = Console()

    # Get reports to parse
    if args.report_id:
        # Parse specific report
        report = ops.get_report(args.report_id)
        if not report:
            console.print(f"[red]Report {args.report_id} not found[/red]")
            return 1
        reports = [report]
    else:
        # Get raw reports with filters
        reports = ops.list_reports(
            broker=filters.get("broker"),
            period=filters.get("period"),
            status='raw',  # Only parse raw reports
            account=filters.get("account"),
            search_account=search_map.get("account"),
            limit=args.limit,
            offset=0
        )

    if not reports:
        console.print("[yellow]No raw reports found to parse[/yellow]")
        return 0

    # Show what will be parsed
    if args.dry_run:
        table = Table(title="Reports to Parse (Dry Run)")
        table.add_column("ID", style="cyan")
        table.add_column("Broker", style="magenta")
        table.add_column("Account", style="green")
        table.add_column("Period", style="blue")
        table.add_column("File Name", style="white")
        
        for report in reports:
            table.add_row(
                str(report.get("id")),
                str(report.get("broker")),
                str(report.get("account", "N/A")),
                str(report.get("period")),
                str(report.get("file_name"))
            )
        
        console.print(table)
        console.print(f"[green]Found {len(reports)} reports to parse[/green]")
        return 0

    # Parse reports
    console.print(f"[green]Parsing {len(reports)} reports...[/green]")
    
    success_count = 0
    error_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing reports...", total=len(reports))
        
        for report in reports:
            progress.update(task, description=f"Parsing {report.get('file_name', 'unknown')}")
            
            if parse_single_report(report, ops):
                success_count += 1
            else:
                error_count += 1
            
            progress.advance(task)

    # Show results
    console.print(f"\n[green]Parsing completed![/green]")
    console.print(f"[green]Success: {success_count}[/green]")
    console.print(f"[red]Errors: {error_count}[/red]")
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
