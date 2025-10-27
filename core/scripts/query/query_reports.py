#!/usr/bin/env python3
"""
CLI tool to query broker reports with flexible filters
"""

import sys
from pathlib import Path
import argparse
from typing import Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations
from core.config import Config
from rich.console import Console
from rich.table import Table
import json


def parse_filters(filter_args):
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


def show_field(field_name: str, parsed_data: dict, console: Console):
    """Display specific field from parsed_data"""
    if field_name == "balance_ending":
        balance = parsed_data.get("balance_ending", 0)
        console.print(f"[green]Balance Ending: {balance:,.2f} RUB[/green]")
    
    elif field_name == "account_open_date":
        date = parsed_data.get("account_open_date", "N/A")
        console.print(f"[green]Account Open Date: {date}[/green]")
    
    elif field_name == "trade_count":
        trades = parsed_data.get("trades", {})
        count = trades.get("count", 0)
        console.print(f"[green]Trade Count: {count}[/green]")
        if count > 0:
            details = trades.get("details", [])
            if details:
                table = Table(title="Trade Details")
                table.add_column("Instrument", style="cyan")
                table.add_column("ISIN", style="magenta")
                table.add_column("Quantity Change", style="green")
                for trade in details:
                    table.add_row(
                        trade.get("instrument", ""),
                        trade.get("isin", ""),
                        trade.get("quantity_change", "")
                    )
                console.print(table)
    
    elif field_name == "instruments":
        instruments = parsed_data.get("instruments", [])
        console.print(f"[green]Instruments Count: {len(instruments)}[/green]")
        if instruments:
            table = Table(title="Instruments")
            table.add_column("Name", style="cyan")
            table.add_column("ISIN", style="magenta")
            table.add_column("Quantity", style="green")
            for instrument in instruments:
                table.add_row(
                    instrument.get("name", ""),
                    instrument.get("isin", ""),
                    str(instrument.get("quantity", 0))
                )
            console.print(table)
    
    elif field_name == "result":
        result = parsed_data.get("financial_result", 0)
        color = "green" if result >= 0 else "red"
        sign = "+" if result >= 0 else ""
        console.print(f"[{color}]Financial Result: {sign}{result:,.2f} RUB[/{color}]")
    
    else:
        console.print(f"[red]Unknown field: {field_name}[/red]")
        console.print("Available fields: balance_ending, account_open_date, trade_count, instruments, result")


def main():
    parser = argparse.ArgumentParser(description="Query broker reports")
    parser.add_argument("--filter", action="append", help="key=value; broker, period, status, account", dest="filters")
    parser.add_argument("--search", action="append", help="key=value; supports account", dest="search")
    parser.add_argument("--show", help="Show specific field from parsed_data: balance_ending, account_open_date, trade_count, instruments, result")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    # Ensure directories exist before any DB operations
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
    rows = ops.list_reports(
        broker=filters.get("broker"),
        period=filters.get("period"),
        status=filters.get("status"),
        account=filters.get("account"),
        search_account=search_map.get("account"),
        limit=args.limit,
        offset=args.offset,
    )

    console = Console()
    
    # Handle --show parameter for specific field extraction
    if args.show:
        if not rows:
            console.print("[yellow]No reports found[/yellow]")
            return 0
        
        # Get full report data with parsed_data
        report_ids = [r['id'] for r in rows]
        if len(report_ids) == 1:
            # Single report - get full data
            full_report = ops.get_report(report_ids[0])
            if not full_report:
                console.print("[red]Report not found[/red]")
                return 1
            
            parsed_data = full_report.get('parsed_data')
            if not parsed_data:
                console.print("[yellow]Report not parsed yet. Run parse_reports.py first.[/yellow]")
                return 1
            
            # Display specific field
            show_field(args.show, parsed_data, console)
        else:
            console.print(f"[yellow]Found {len(rows)} reports. Please filter to single report for --show[/yellow]")
            return 1
    else:
        # Default table display
        table = Table(title="Broker Reports")
        for col in ["id", "broker", "account", "period", "file_name", "processing_status", "created_at"]:
            table.add_column(col)
        for r in rows:
            table.add_row(
                str(r.get("id")),
                str(r.get("broker")),
                str(r.get("account")),
                str(r.get("period")),
                str(r.get("file_name")),
                str(r.get("processing_status")),
                str(r.get("created_at")),
            )
        console.print(table)


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok is None else (0 if ok else 1))


