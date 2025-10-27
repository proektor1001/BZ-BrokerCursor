#!/usr/bin/env python3
"""
Verification script for BrokerCursor setup
Tests database connection, imports sample data, and generates diagnostics
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.connection import db_connection
from core.database.operations import BrokerReportOperations
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

class SetupVerifier:
    """Verification and diagnostics for BrokerCursor setup"""
    
    def __init__(self):
        self.config = Config()
        self.db_ops = BrokerReportOperations()
        self.verification_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'overall_status': 'unknown'
        }
    
    def test_database_connection(self) -> bool:
        """Test database connection"""
        console.print("\n[bold blue]Testing Database Connection[/bold blue]")
        
        try:
            test_result = db_connection.test_connection()
            
            if test_result["status"] == "success":
                console.print(f"[green]✓[/green] Connected to: {test_result['database']}@{test_result['host']}:{test_result['port']}")
                console.print(f"[green]✓[/green] PostgreSQL version: {test_result['version']}")
                
                # Check tables
                existing_tables = test_result.get('existing_tables', [])
                required_tables = ['broker_reports', 'import_log']
                
                for table in required_tables:
                    if table in existing_tables:
                        console.print(f"[green]✓[/green] Table exists: {table}")
                    else:
                        console.print(f"[red]✗[/red] Missing table: {table}")
                        return False
                
                self.verification_results['tests']['database_connection'] = {
                    'status': 'passed',
                    'details': test_result
                }
                return True
            else:
                console.print(f"[red]✗[/red] Connection failed: {test_result.get('error', 'Unknown error')}")
                self.verification_results['tests']['database_connection'] = {
                    'status': 'failed',
                    'error': test_result.get('error', 'Unknown error')
                }
                return False
                
        except Exception as e:
            console.print(f"[red]✗[/red] Database connection test failed: {e}")
            self.verification_results['tests']['database_connection'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def test_database_operations(self) -> bool:
        """Test database operations"""
        console.print("\n[bold blue]Testing Database Operations[/bold blue]")
        
        try:
            # Test insert operation
            test_report = {
                'broker': 'test',
                'period': '2025-01',
                'file_name': 'test_report.html',
                'html_content': '<html><body>Test report</body></html>',
                'metadata': {'test': True}
            }
            
            report_id = self.db_ops.insert_report(**test_report)
            if report_id:
                console.print(f"[green]✓[/green] Test report inserted with ID: {report_id}")
                
                # Test get operation
                retrieved_report = self.db_ops.get_report(report_id)
                if retrieved_report:
                    console.print(f"[green]✓[/green] Test report retrieved successfully")
                else:
                    console.print(f"[red]✗[/red] Failed to retrieve test report")
                    return False
                
                # Test update operation
                if self.db_ops.update_report_status(report_id, 'parsed', {'test_data': 'updated'}):
                    console.print(f"[green]✓[/green] Test report status updated")
                else:
                    console.print(f"[red]✗[/red] Failed to update test report status")
                    return False
                
                # Clean up test data
                if self.db_ops.delete_report(report_id):
                    console.print(f"[green]✓[/green] Test report cleaned up")
                else:
                    console.print(f"[yellow]⚠[/yellow] Failed to clean up test report")
                
                self.verification_results['tests']['database_operations'] = {
                    'status': 'passed',
                    'test_report_id': report_id
                }
                return True
            else:
                console.print(f"[red]✗[/red] Failed to insert test report")
                self.verification_results['tests']['database_operations'] = {
                    'status': 'failed',
                    'error': 'Failed to insert test report'
                }
                return False
                
        except Exception as e:
            console.print(f"[red]✗[/red] Database operations test failed: {e}")
            self.verification_results['tests']['database_operations'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def test_file_system(self) -> bool:
        """Test file system setup"""
        console.print("\n[bold blue]Testing File System Setup[/bold blue]")
        
        try:
            # Check directories
            directories = [
                self.config.INBOX_PATH,
                self.config.ARCHIVE_PATH,
                self.config.PARSED_PATH
            ]
            
            for directory in directories:
                if directory.exists():
                    console.print(f"[green]✓[/green] Directory exists: {directory}")
                else:
                    console.print(f"[yellow]⚠[/yellow] Directory missing (will be created): {directory}")
                    directory.mkdir(parents=True, exist_ok=True)
                    console.print(f"[green]✓[/green] Directory created: {directory}")
            
            # Test file operations
            test_file = self.config.INBOX_PATH / "test_file.txt"
            test_file.write_text("Test content")
            
            if test_file.exists():
                console.print(f"[green]✓[/green] File creation test passed")
                test_file.unlink()  # Clean up
                console.print(f"[green]✓[/green] File deletion test passed")
            else:
                console.print(f"[red]✗[/red] File creation test failed")
                return False
            
            self.verification_results['tests']['file_system'] = {
                'status': 'passed',
                'directories_checked': [str(d) for d in directories]
            }
            return True
            
        except Exception as e:
            console.print(f"[red]✗[/red] File system test failed: {e}")
            self.verification_results['tests']['file_system'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def test_configuration(self) -> bool:
        """Test configuration"""
        console.print("\n[bold blue]Testing Configuration[/bold blue]")
        
        try:
            issues = self.config.validate_config()
            
            if not issues:
                console.print(f"[green]✓[/green] Configuration is valid")
                console.print(f"[green]✓[/green] Database: {self.config.DB_NAME}@{self.config.DB_HOST}:{self.config.DB_PORT}")
                console.print(f"[green]✓[/green] Environment: {self.config.APP_ENV}")
                
                self.verification_results['tests']['configuration'] = {
                    'status': 'passed',
                    'database': f"{self.config.DB_NAME}@{self.config.DB_HOST}:{self.config.DB_PORT}",
                    'environment': self.config.APP_ENV
                }
                return True
            else:
                console.print(f"[red]✗[/red] Configuration issues found:")
                for issue in issues:
                    console.print(f"  - {issue}")
                
                self.verification_results['tests']['configuration'] = {
                    'status': 'failed',
                    'issues': issues
                }
                return False
                
        except Exception as e:
            console.print(f"[red]✗[/red] Configuration test failed: {e}")
            self.verification_results['tests']['configuration'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def show_database_statistics(self):
        """Show current database statistics"""
        console.print("\n[bold blue]Database Statistics[/bold blue]")
        
        try:
            stats = self.db_ops.get_statistics()
            
            table = Table(title="Current Database State")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")
            
            table.add_row("Total Reports", str(stats.get('total_reports', 0)))
            table.add_row("Recent Imports (24h)", str(stats.get('recent_imports_24h', 0)))
            
            # By broker
            by_broker = stats.get('by_broker', {})
            if by_broker:
                table.add_row("", "")
                table.add_row("By Broker", "")
                for broker, count in by_broker.items():
                    table.add_row(f"  {broker}", str(count))
            
            # By status
            by_status = stats.get('by_status', {})
            if by_status:
                table.add_row("", "")
                table.add_row("By Status", "")
                for status, count in by_status.items():
                    table.add_row(f"  {status}", str(count))
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to get database statistics: {e}")
    
    def generate_diagnostics_report(self):
        """Generate comprehensive diagnostics report"""
        console.print("\n[bold blue]Generating Diagnostics Report[/bold blue]")
        
        try:
            # Determine overall status
            all_tests = self.verification_results['tests']
            passed_tests = sum(1 for test in all_tests.values() if test['status'] == 'passed')
            total_tests = len(all_tests)
            
            if passed_tests == total_tests:
                self.verification_results['overall_status'] = 'passed'
            elif passed_tests > 0:
                self.verification_results['overall_status'] = 'partial'
            else:
                self.verification_results['overall_status'] = 'failed'
            
            # Save report
            report_path = project_root / "diagnostics" / "import_verification.md"
            report_path.parent.mkdir(exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"# BrokerCursor Setup Verification Report\n\n")
                f.write(f"**Generated:** {self.verification_results['timestamp']}\n")
                f.write(f"**Overall Status:** {self.verification_results['overall_status'].upper()}\n\n")
                
                f.write(f"## Test Results\n\n")
                for test_name, test_result in all_tests.items():
                    status_emoji = "✓" if test_result['status'] == 'passed' else "✗"
                    f.write(f"- {status_emoji} **{test_name}**: {test_result['status']}\n")
                    
                    if 'error' in test_result:
                        f.write(f"  - Error: {test_result['error']}\n")
                
                f.write(f"\n## Configuration\n\n")
                f.write(f"- Database: {self.config.DB_NAME}@{self.config.DB_HOST}:{self.config.DB_PORT}\n")
                f.write(f"- Environment: {self.config.APP_ENV}\n")
                f.write(f"- Inbox Path: {self.config.INBOX_PATH}\n")
                f.write(f"- Archive Path: {self.config.ARCHIVE_PATH}\n")
                
                f.write(f"\n## Next Steps\n\n")
                if self.verification_results['overall_status'] == 'passed':
                    f.write(f"✅ Setup is complete! You can now:\n")
                    f.write(f"- Place broker reports in `{self.config.INBOX_PATH}`\n")
                    f.write(f"- Run `python core/scripts/import_reports.py` to import reports\n")
                    f.write(f"- Use `python core/scripts/import_reports.py --stats` to view statistics\n")
                else:
                    f.write(f"❌ Setup issues found. Please resolve the failed tests above.\n")
            
            console.print(f"[green]✓[/green] Diagnostics report saved: {report_path}")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to generate diagnostics report: {e}")
    
    def run_all_tests(self):
        """Run all verification tests"""
        console.print("[bold green]BrokerCursor Setup Verification[/bold green]")
        console.print("=" * 50)
        
        tests = [
            ("Configuration", self.test_configuration),
            ("File System", self.test_file_system),
            ("Database Connection", self.test_database_connection),
            ("Database Operations", self.test_database_operations)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    console.print(f"[red]Test failed: {test_name}[/red]")
            except Exception as e:
                console.print(f"[red]Test error: {test_name} - {e}[/red]")
        
        # Show results
        console.print(f"\n[bold]Verification Results: {passed}/{total} tests passed[/bold]")
        
        if passed == total:
            console.print("[green]🎉 All tests passed! Setup is complete.[/green]")
        elif passed > 0:
            console.print("[yellow]⚠️  Some tests failed. Check the issues above.[/yellow]")
        else:
            console.print("[red]❌ All tests failed. Setup needs attention.[/red]")
        
        # Show database statistics
        self.show_database_statistics()
        
        # Generate diagnostics report
        self.generate_diagnostics_report()
        
        return passed == total

def main():
    """Main verification function"""
    verifier = SetupVerifier()
    success = verifier.run_all_tests()
    
    if success:
        console.print("\n[bold green]✅ BrokerCursor is ready to use![/bold green]")
    else:
        console.print("\n[bold red]❌ Setup verification failed. Please fix the issues above.[/bold red]")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
