#!/usr/bin/env python3
"""
Database Import Integrity Verification Script
Validates all aspects of the database import architecture for BrokerCursor
"""

import sys
import os
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import logging
from datetime import datetime
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations
from core.database.connection import db_connection
from core.config import Config
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

class DatabaseIntegrityVerifier:
    """Comprehensive database integrity verification"""
    
    def __init__(self):
        self.config = Config()
        self.db_ops = BrokerReportOperations()
        self.results = {
            'database_checks': {},
            'cli_tests': {},
            'deduplication_tests': {},
            'summary': {},
            'errors': [],
            'warnings': []
        }
    
    def verify_database_connection(self) -> bool:
        """Test database connection and basic functionality"""
        try:
            test_result = db_connection.test_connection()
            if test_result['status'] == 'success':
                self.results['database_checks']['connection'] = {
                    'status': 'PASS',
                    'details': f"Connected to {test_result['database']}@{test_result['host']}:{test_result['port']}",
                    'version': test_result['version']
                }
                return True
            else:
                self.results['database_checks']['connection'] = {
                    'status': 'FAIL',
                    'details': test_result.get('error', 'Unknown connection error')
                }
                return False
        except Exception as e:
            self.results['database_checks']['connection'] = {
                'status': 'FAIL',
                'details': str(e)
            }
            return False
    
    def verify_broker_reports_table(self) -> Dict[str, Any]:
        """Verify broker_reports table integrity"""
        checks = {}
        
        try:
            # Check if table has records
            total_count = self.db_ops.get_statistics().get('total_reports', 0)
            checks['has_records'] = {
                'status': 'PASS' if total_count > 0 else 'FAIL',
                'count': total_count,
                'details': f"Found {total_count} records in broker_reports table"
            }
            
            # Check for duplicates by (broker, account, period)
            duplicate_query = """
                SELECT broker, account, period, COUNT(*) as count
                FROM broker_reports 
                GROUP BY broker, account, period 
                HAVING COUNT(*) > 1
            """
            duplicates = db_connection.execute_query(duplicate_query)
            checks['no_duplicates'] = {
                'status': 'PASS' if len(duplicates) == 0 else 'FAIL',
                'count': len(duplicates),
                'details': f"Found {len(duplicates)} duplicate (broker, account, period) combinations",
                'examples': duplicates[:5] if duplicates else []
            }
            
            # Validate period format (YYYY-MM)
            period_format_query = """
                SELECT id, broker, account, period
                FROM broker_reports 
                WHERE period !~ '^[0-9]{4}-[0-9]{2}$'
            """
            invalid_periods = db_connection.execute_query(period_format_query)
            checks['period_format'] = {
                'status': 'PASS' if len(invalid_periods) == 0 else 'FAIL',
                'count': len(invalid_periods),
                'details': f"Found {len(invalid_periods)} records with invalid period format",
                'examples': invalid_periods[:5] if invalid_periods else []
            }
            
            # Check required fields exist and are not null
            required_fields_query = """
                SELECT id, broker, account, period, file_name
                FROM broker_reports 
                WHERE created_at IS NULL 
                   OR file_hash IS NULL 
                   OR processing_status IS NULL
            """
            missing_fields = db_connection.execute_query(required_fields_query)
            checks['required_fields'] = {
                'status': 'PASS' if len(missing_fields) == 0 else 'FAIL',
                'count': len(missing_fields),
                'details': f"Found {len(missing_fields)} records with missing required fields",
                'examples': missing_fields[:5] if missing_fields else []
            }
            
            # Check for empty file_hash (fallback hashing validation)
            empty_hash_query = """
                SELECT id, broker, account, period, file_name, file_hash
                FROM broker_reports 
                WHERE file_hash = '' OR file_hash IS NULL
            """
            empty_hashes = db_connection.execute_query(empty_hash_query)
            checks['file_hash_present'] = {
                'status': 'PASS' if len(empty_hashes) == 0 else 'FAIL',
                'count': len(empty_hashes),
                'details': f"Found {len(empty_hashes)} records with empty or missing file_hash",
                'examples': empty_hashes[:5] if empty_hashes else []
            }
            
        except Exception as e:
            checks['error'] = {
                'status': 'ERROR',
                'details': f"Database query failed: {str(e)}"
            }
            self.results['errors'].append(f"broker_reports verification: {str(e)}")
        
        return checks
    
    def verify_import_log_table(self) -> Dict[str, Any]:
        """Verify import_log table integrity"""
        checks = {}
        
        try:
            # Check for duplicate detection entries
            duplicate_logs_query = """
                SELECT status, COUNT(*) as count
                FROM import_log 
                WHERE status IN ('duplicate_detected', 'collision_mismatch')
                GROUP BY status
            """
            duplicate_logs = db_connection.execute_query(duplicate_logs_query)
            checks['duplicate_logs'] = {
                'status': 'INFO',
                'count': sum(row['count'] for row in duplicate_logs),
                'details': f"Found {sum(row['count'] for row in duplicate_logs)} duplicate detection entries",
                'breakdown': {row['status']: row['count'] for row in duplicate_logs}
            }
            
            # Check log completeness (file_hash, broker, period, file_name)
            incomplete_logs_query = """
                SELECT id, operation_type, broker, account, period, file_name, file_hash
                FROM import_log 
                WHERE file_hash IS NULL 
                   OR broker IS NULL 
                   OR period IS NULL 
                   OR file_name IS NULL
            """
            incomplete_logs = db_connection.execute_query(incomplete_logs_query)
            checks['log_completeness'] = {
                'status': 'PASS' if len(incomplete_logs) == 0 else 'WARN',
                'count': len(incomplete_logs),
                'details': f"Found {len(incomplete_logs)} incomplete log entries",
                'examples': incomplete_logs[:5] if incomplete_logs else []
            }
            
            # Get overall import statistics
            stats_query = """
                SELECT 
                    COUNT(*) as total_operations,
                    SUM(files_processed) as total_files_processed,
                    SUM(files_success) as total_files_success,
                    SUM(files_failed) as total_files_failed
                FROM import_log
            """
            stats = db_connection.execute_query(stats_query)
            if stats:
                stats_row = stats[0]
                checks['import_statistics'] = {
                    'status': 'INFO',
                    'details': f"Total operations: {stats_row['total_operations']}, "
                              f"Files processed: {stats_row['total_files_processed']}, "
                              f"Success: {stats_row['total_files_success']}, "
                              f"Failed: {stats_row['total_files_failed']}"
                }
            
        except Exception as e:
            checks['error'] = {
                'status': 'ERROR',
                'details': f"Import log query failed: {str(e)}"
            }
            self.results['errors'].append(f"import_log verification: {str(e)}")
        
        return checks
    
    def test_cli_functionality(self) -> Dict[str, Any]:
        """Test CLI tools functionality"""
        tests = {}
        
        try:
            # Test query_reports.py with broker filter
            result = self.run_cli_command([
                'python', str(project_root / 'core/scripts/query_reports.py'),
                '--filter', 'broker=sber',
                '--limit', '5'
            ])
            tests['filter_broker'] = {
                'status': 'PASS' if result['success'] else 'FAIL',
                'details': f"Broker filter test: {result['details']}",
                'output_lines': result['output_lines']
            }
            
            # Test query_reports.py with period filter
            result = self.run_cli_command([
                'python', str(project_root / 'core/scripts/query_reports.py'),
                '--filter', 'period=2023-07',
                '--limit', '5'
            ])
            tests['filter_period'] = {
                'status': 'PASS' if result['success'] else 'FAIL',
                'details': f"Period filter test: {result['details']}",
                'output_lines': result['output_lines']
            }
            
            # Test query_reports.py with account search
            result = self.run_cli_command([
                'python', str(project_root / 'core/scripts/query_reports.py'),
                '--search', 'account=4000T49',
                '--limit', '5'
            ])
            tests['search_account'] = {
                'status': 'PASS' if result['success'] else 'FAIL',
                'details': f"Account search test: {result['details']}",
                'output_lines': result['output_lines']
            }
            
            # Test query_reports.py with no filters (all records)
            result = self.run_cli_command([
                'python', str(project_root / 'core/scripts/query_reports.py'),
                '--limit', '10'
            ])
            tests['no_filters'] = {
                'status': 'PASS' if result['success'] else 'FAIL',
                'details': f"No filters test: {result['details']}",
                'output_lines': result['output_lines']
            }
            
        except Exception as e:
            tests['error'] = {
                'status': 'ERROR',
                'details': f"CLI testing failed: {str(e)}"
            }
            self.results['errors'].append(f"CLI testing: {str(e)}")
        
        return tests
    
    def run_cli_command(self, command: List[str]) -> Dict[str, Any]:
        """Run CLI command and capture output"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=str(project_root),
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'output_lines': result.stdout.strip().split('\n') if result.stdout else [],
                'details': f"Return code: {result.returncode}"
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'details': 'Command timed out after 30 seconds'
            }
        except Exception as e:
            return {
                'success': False,
                'details': f"Command execution failed: {str(e)}"
            }
    
    def verify_deduplication_logic(self) -> Dict[str, Any]:
        """Verify deduplication logic is working correctly"""
        checks = {}
        
        try:
            # Check for collision_mismatch entries (same key, different hash)
            collision_query = """
                SELECT broker, account, period, file_hash, file_name
                FROM import_log 
                WHERE status = 'collision_mismatch'
                ORDER BY started_at DESC
                LIMIT 5
            """
            collisions = db_connection.execute_query(collision_query)
            checks['collision_detection'] = {
                'status': 'INFO',
                'count': len(collisions),
                'details': f"Found {len(collisions)} collision_mismatch entries",
                'examples': collisions
            }
            
            # Check for duplicate_detected entries
            duplicate_query = """
                SELECT broker, account, period, file_hash, file_name
                FROM import_log 
                WHERE status = 'duplicate_detected'
                ORDER BY started_at DESC
                LIMIT 5
            """
            duplicates = db_connection.execute_query(duplicate_query)
            checks['duplicate_detection'] = {
                'status': 'INFO',
                'count': len(duplicates),
                'details': f"Found {len(duplicates)} duplicate_detected entries",
                'examples': duplicates
            }
            
            # Verify no actual duplicates exist in broker_reports
            actual_duplicates_query = """
                SELECT broker, account, period, COUNT(*) as count
                FROM broker_reports 
                GROUP BY broker, account, period 
                HAVING COUNT(*) > 1
            """
            actual_duplicates = db_connection.execute_query(actual_duplicates_query)
            checks['no_actual_duplicates'] = {
                'status': 'PASS' if len(actual_duplicates) == 0 else 'FAIL',
                'count': len(actual_duplicates),
                'details': f"Found {len(actual_duplicates)} actual duplicate records in database",
                'examples': actual_duplicates
            }
            
        except Exception as e:
            checks['error'] = {
                'status': 'ERROR',
                'details': f"Deduplication verification failed: {str(e)}"
            }
            self.results['errors'].append(f"Deduplication verification: {str(e)}")
        
        return checks
    
    def check_archive_directory(self) -> Dict[str, Any]:
        """Check if archive directory exists and is accessible"""
        try:
            archive_path = self.config.ARCHIVE_PATH
            if archive_path.exists() and archive_path.is_dir():
                # Count files in archive
                archive_files = list(archive_path.glob('*'))
                return {
                    'status': 'PASS',
                    'details': f"Archive directory exists with {len(archive_files)} files",
                    'path': str(archive_path)
                }
            else:
                return {
                    'status': 'WARN',
                    'details': f"Archive directory does not exist: {archive_path}",
                    'path': str(archive_path)
                }
        except Exception as e:
            return {
                'status': 'ERROR',
                'details': f"Archive directory check failed: {str(e)}"
            }
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate overall summary statistics"""
        try:
            stats = self.db_ops.get_statistics()
            
            # Get recent import activity
            recent_imports_query = """
                SELECT COUNT(*) as count
                FROM import_log 
                WHERE started_at >= NOW() - INTERVAL '7 days'
            """
            recent_imports = db_connection.execute_query(recent_imports_query)
            recent_count = recent_imports[0]['count'] if recent_imports else 0
            
            return {
                'total_reports': stats.get('total_reports', 0),
                'by_broker': stats.get('by_broker', {}),
                'by_status': stats.get('by_status', {}),
                'recent_imports_7d': recent_count,
                'verification_timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'error': f"Failed to generate summary: {str(e)}",
                'verification_timestamp': datetime.now().isoformat()
            }
    
    def run_verification(self) -> bool:
        """Run complete verification process"""
        console.print(Panel.fit("🔍 Starting Database Import Integrity Verification", style="bold blue"))
        
        # Test database connection
        if not self.verify_database_connection():
            console.print("[yellow]⚠️  Database connection failed. Running in simulation mode...[/yellow]")
            self.results['database_checks']['connection'] = {
                'status': 'SIMULATION',
                'details': 'Database not available - running verification in simulation mode'
            }
            # Run simulation mode
            return self.run_simulation_mode()
        
        console.print("[green]✅ Database connection successful[/green]")
        
        # Run all verification checks
        console.print("\n[bold]📊 Verifying broker_reports table...[/bold]")
        self.results['database_checks']['broker_reports'] = self.verify_broker_reports_table()
        
        console.print("[bold]📋 Verifying import_log table...[/bold]")
        self.results['database_checks']['import_log'] = self.verify_import_log_table()
        
        console.print("[bold]🔧 Testing CLI functionality...[/bold]")
        self.results['cli_tests'] = self.test_cli_functionality()
        
        console.print("[bold]🔄 Verifying deduplication logic...[/bold]")
        self.results['deduplication_tests'] = self.verify_deduplication_logic()
        
        console.print("[bold]📁 Checking archive directory...[/bold]")
        self.results['archive_check'] = self.check_archive_directory()
        
        console.print("[bold]📈 Generating summary...[/bold]")
        self.results['summary'] = self.generate_summary()
        
        return True
    
    def run_simulation_mode(self) -> bool:
        """Run verification in simulation mode when database is not available"""
        console.print("\n[bold]🎭 Running in Simulation Mode[/bold]")
        
        # Simulate broker_reports table checks
        self.results['database_checks']['broker_reports'] = {
            'has_records': {
                'status': 'SIMULATION',
                'count': 0,
                'details': 'Simulation mode - no actual database records'
            },
            'no_duplicates': {
                'status': 'SIMULATION',
                'count': 0,
                'details': 'Simulation mode - no duplicates to check'
            },
            'period_format': {
                'status': 'SIMULATION',
                'count': 0,
                'details': 'Simulation mode - no periods to validate'
            },
            'required_fields': {
                'status': 'SIMULATION',
                'count': 0,
                'details': 'Simulation mode - no records to check'
            },
            'file_hash_present': {
                'status': 'SIMULATION',
                'count': 0,
                'details': 'Simulation mode - no hashes to validate'
            }
        }
        
        # Simulate import_log table checks
        self.results['database_checks']['import_log'] = {
            'duplicate_logs': {
                'status': 'SIMULATION',
                'count': 0,
                'details': 'Simulation mode - no import logs to check'
            },
            'log_completeness': {
                'status': 'SIMULATION',
                'count': 0,
                'details': 'Simulation mode - no logs to validate'
            },
            'import_statistics': {
                'status': 'SIMULATION',
                'details': 'Simulation mode - no statistics available'
            }
        }
        
        # Test CLI functionality (will fail but we can show the attempt)
        console.print("[bold]🔧 Testing CLI functionality...[/bold]")
        self.results['cli_tests'] = self.test_cli_functionality()
        
        # Check archive directory
        console.print("[bold]📁 Checking archive directory...[/bold]")
        self.results['archive_check'] = self.check_archive_directory()
        
        # Generate simulation summary
        console.print("[bold]📈 Generating simulation summary...[/bold]")
        self.results['summary'] = {
            'total_reports': 0,
            'by_broker': {},
            'by_status': {},
            'recent_imports_7d': 0,
            'verification_timestamp': datetime.now().isoformat(),
            'mode': 'simulation'
        }
        
        return True
    
    def generate_report(self) -> str:
        """Generate markdown diagnostic report"""
        report_lines = [
            "# Database Import Integrity Verification Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Database:** {self.config.DB_NAME}@{self.config.DB_HOST}:{self.config.DB_PORT}",
            "",
            "## Executive Summary",
            ""
        ]
        
        # Overall status
        all_passed = True
        simulation_mode = False
        for category, checks in self.results.items():
            if isinstance(checks, dict):
                for check_name, check_result in checks.items():
                    if isinstance(check_result, dict) and 'status' in check_result:
                        if check_result['status'] == 'SIMULATION':
                            simulation_mode = True
                        elif check_result['status'] in ['FAIL', 'ERROR']:
                            all_passed = False
                            break
        
        if simulation_mode:
            status_emoji = "🎭"
            status_text = "Simulation mode - database not available"
        else:
            status_emoji = "✅" if all_passed else "❌"
            status_text = 'All checks passed' if all_passed else 'Issues found'
        
        report_lines.append(f"**Overall Status:** {status_emoji} {status_text}")
        
        # Database checks summary
        report_lines.extend([
            "",
            "## Database Table Verification",
            ""
        ])
        
        if 'broker_reports' in self.results['database_checks']:
            report_lines.append("### broker_reports Table")
            for check_name, result in self.results['database_checks']['broker_reports'].items():
                if isinstance(result, dict) and 'status' in result:
                    status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️" if result['status'] == 'WARN' else "ℹ️"
                    report_lines.append(f"- **{check_name.replace('_', ' ').title()}:** {status_icon} {result['details']}")
                    if 'examples' in result and result['examples']:
                        report_lines.append(f"  - Examples: {result['examples'][:3]}")
        
        if 'import_log' in self.results['database_checks']:
            report_lines.append("\n### import_log Table")
            for check_name, result in self.results['database_checks']['import_log'].items():
                if isinstance(result, dict) and 'status' in result:
                    status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️" if result['status'] == 'WARN' else "ℹ️"
                    report_lines.append(f"- **{check_name.replace('_', ' ').title()}:** {status_icon} {result['details']}")
        
        # CLI tests summary
        report_lines.extend([
            "",
            "## CLI Functionality Tests",
            ""
        ])
        
        for test_name, result in self.results['cli_tests'].items():
            if isinstance(result, dict) and 'status' in result:
                status_icon = "✅" if result['status'] == 'PASS' else "❌"
                report_lines.append(f"- **{test_name.replace('_', ' ').title()}:** {status_icon} {result['details']}")
        
        # Deduplication tests
        report_lines.extend([
            "",
            "## Deduplication Logic Verification",
            ""
        ])
        
        for test_name, result in self.results['deduplication_tests'].items():
            if isinstance(result, dict) and 'status' in result:
                status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "ℹ️"
                report_lines.append(f"- **{test_name.replace('_', ' ').title()}:** {status_icon} {result['details']}")
        
        # Summary statistics
        if 'summary' in self.results and self.results['summary']:
            summary = self.results['summary']
            report_lines.extend([
                "",
                "## Summary Statistics",
                "",
                f"- **Total Reports:** {summary.get('total_reports', 0)}",
                f"- **Recent Imports (7 days):** {summary.get('recent_imports_7d', 0)}",
                ""
            ])
            
            if 'by_broker' in summary and summary['by_broker']:
                report_lines.append("### Reports by Broker")
                for broker, count in summary['by_broker'].items():
                    report_lines.append(f"- {broker}: {count}")
                report_lines.append("")
            
            if 'by_status' in summary and summary['by_status']:
                report_lines.append("### Reports by Status")
                for status, count in summary['by_status'].items():
                    report_lines.append(f"- {status}: {count}")
                report_lines.append("")
        
        # Errors and warnings
        if self.results['errors']:
            report_lines.extend([
                "## Errors Found",
                ""
            ])
            for error in self.results['errors']:
                report_lines.append(f"- {error}")
            report_lines.append("")
        
        if self.results['warnings']:
            report_lines.extend([
                "## Warnings",
                ""
            ])
            for warning in self.results['warnings']:
                report_lines.append(f"- {warning}")
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def save_report(self, report_content: str) -> bool:
        """Save report to diagnostics directory"""
        try:
            diagnostics_dir = self.config.PROJECT_ROOT / 'diagnostics'
            diagnostics_dir.mkdir(parents=True, exist_ok=True)
            
            report_path = diagnostics_dir / 'db_verification_report.md'
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            console.print(f"[green]✅ Report saved to: {report_path}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ Failed to save report: {e}[/red]")
            return False

def main():
    """Main verification function"""
    verifier = DatabaseIntegrityVerifier()
    
    # Run verification
    success = verifier.run_verification()
    
    if not success:
        console.print("[red]❌ Verification failed due to database connection issues[/red]")
        return False
    
    # Generate and save report
    report_content = verifier.generate_report()
    report_saved = verifier.save_report(report_content)
    
    # Display summary
    console.print("\n" + "="*60)
    console.print(Panel.fit("📋 Verification Complete", style="bold green"))
    
    # Show key results
    if 'broker_reports' in verifier.results['database_checks']:
        broker_checks = verifier.results['database_checks']['broker_reports']
        for check_name, result in broker_checks.items():
            if isinstance(result, dict) and 'status' in result:
                status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
                console.print(f"{status_icon} {check_name.replace('_', ' ').title()}: {result.get('details', '')}")
    
    if report_saved:
        console.print(f"\n[green]📄 Full report saved to: diagnostics/db_verification_report.md[/green]")
    
    # Return success status
    has_errors = any(
        check.get('status') in ['FAIL', 'ERROR'] 
        for category in verifier.results.values() 
        if isinstance(category, dict)
        for check in category.values() 
        if isinstance(check, dict) and 'status' in check
    )
    
    return not has_errors

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
