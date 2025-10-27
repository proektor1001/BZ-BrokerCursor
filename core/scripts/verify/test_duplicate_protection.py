#!/usr/bin/env python3
"""
Smoke test for duplicate protection functionality
Tests all 3 scenarios: unique import, exact duplicate, semantic duplicate
"""

import sys
import os
import argparse
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config
from core.database.operations import BrokerReportOperations
from core.scripts.import.import_reports import EnhancedReportImporter
from core.utils.file_manager import FileManager
from rich.console import Console
from rich.table import Table

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

class DuplicateProtectionTester:
    """Tests duplicate protection functionality"""
    
    def __init__(self):
        self.config = Config()
        self.db_ops = BrokerReportOperations()
        self.file_manager = FileManager()
        self.test_stats = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'errors': []
        }
        self.test_files = []
        self.test_dir = None
    
    def setup_test_environment(self) -> bool:
        """Setup temporary test environment"""
        try:
            # Create temporary test directory
            self.test_dir = Path(tempfile.mkdtemp(prefix="duplicate_test_"))
            logger.info(f"Created test directory: {self.test_dir}")
            
            # Create test files
            self.create_test_files()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
            return False
    
    def create_test_files(self):
        """Create test HTML files for testing"""
        try:
            # Test file 1: Unique report
            test_file_1 = self.test_dir / "test_unique_report.html"
            with open(test_file_1, 'w', encoding='utf-8') as f:
                f.write("""
                <html>
                <body>
                    <h1>Test Report 1</h1>
                    <p>Account: 4000T49</p>
                    <p>Period: 2023-07</p>
                    <p>Broker: tinkoff</p>
                    <p>This is a unique test report</p>
                </body>
                </html>
                """)
            
            # Test file 2: Exact duplicate of test_file_1
            test_file_2 = self.test_dir / "test_exact_duplicate.html"
            with open(test_file_2, 'w', encoding='utf-8') as f:
                f.write("""
                <html>
                <body>
                    <h1>Test Report 1</h1>
                    <p>Account: 4000T49</p>
                    <p>Period: 2023-07</p>
                    <p>Broker: tinkoff</p>
                    <p>This is a unique test report</p>
                </body>
                </html>
                """)
            
            # Test file 3: Semantic duplicate (different HTML, same broker/account/period)
            test_file_3 = self.test_dir / "test_semantic_duplicate.html"
            with open(test_file_3, 'w', encoding='utf-8') as f:
                f.write("""
                <html>
                <body>
                    <h1>Test Report 1 - Different HTML</h1>
                    <p>Account: 4000T49</p>
                    <p>Period: 2023-07</p>
                    <p>Broker: tinkoff</p>
                    <p>This is a different HTML but same semantic data</p>
                    <div>Additional content to make it different</div>
                </body>
                </html>
                """)
            
            self.test_files = [test_file_1, test_file_2, test_file_3]
            logger.info(f"Created {len(self.test_files)} test files")
            
        except Exception as e:
            logger.error(f"Failed to create test files: {e}")
            raise
    
    def cleanup_test_environment(self):
        """Cleanup test environment"""
        try:
            if self.test_dir and self.test_dir.exists():
                shutil.rmtree(self.test_dir)
                logger.info(f"Cleaned up test directory: {self.test_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup test environment: {e}")
    
    def test_unique_import(self) -> bool:
        """Test 1: Import unique report should succeed"""
        try:
            console.print("\n[bold blue]Test 1: Unique Import[/bold blue]")
            
            # Copy first test file to inbox
            inbox_file = self.config.INBOX_PATH / "test_unique_report.html"
            shutil.copy2(self.test_files[0], inbox_file)
            
            # Run import
            importer = EnhancedReportImporter()
            success = importer.import_reports(source="inbox", broker=None, dry_run=False)
            
            if not success:
                console.print("[red]❌ Import failed[/red]")
                return False
            
            # Check if file was moved to imported/
            imported_file = self.config.ARCHIVE_IMPORTED_PATH / "test_unique_report.html"
            if not imported_file.exists():
                console.print("[red]❌ File not moved to imported/[/red]")
                return False
            
            # Check if record was inserted
            reports = self.db_ops.list_reports(broker="tinkoff", period="2023-07")
            if not reports:
                console.print("[red]❌ No record found in database[/red]")
                return False
            
            console.print("[green]✅ Unique import test passed[/green]")
            return True
            
        except Exception as e:
            logger.error(f"Unique import test failed: {e}")
            console.print(f"[red]❌ Test failed: {e}[/red]")
            return False
    
    def test_exact_duplicate(self) -> bool:
        """Test 2: Re-import same file should be detected as exact duplicate"""
        try:
            console.print("\n[bold blue]Test 2: Exact Duplicate Detection[/bold blue]")
            
            # Copy second test file (exact duplicate) to inbox
            inbox_file = self.config.INBOX_PATH / "test_exact_duplicate.html"
            shutil.copy2(self.test_files[1], inbox_file)
            
            # Run import
            importer = EnhancedReportImporter()
            success = importer.import_reports(source="inbox", broker=None, dry_run=False)
            
            if not success:
                console.print("[red]❌ Import failed[/red]")
                return False
            
            # Check if file was moved to exact_duplicates/
            exact_duplicate_file = self.config.ARCHIVE_EXACT_DUPLICATES_PATH / "test_exact_duplicate.html"
            if not exact_duplicate_file.exists():
                console.print("[red]❌ File not moved to exact_duplicates/[/red]")
                return False
            
            # Check that no new record was inserted (should still be 1 from test 1)
            reports = self.db_ops.list_reports(broker="tinkoff", period="2023-07")
            if len(reports) != 1:
                console.print(f"[red]❌ Expected 1 record, found {len(reports)}[/red]")
                return False
            
            console.print("[green]✅ Exact duplicate test passed[/green]")
            return True
            
        except Exception as e:
            logger.error(f"Exact duplicate test failed: {e}")
            console.print(f"[red]❌ Test failed: {e}[/red]")
            return False
    
    def test_semantic_duplicate(self) -> bool:
        """Test 3: Import different HTML with same semantic data should be detected as semantic duplicate"""
        try:
            console.print("\n[bold blue]Test 3: Semantic Duplicate Detection[/bold blue]")
            
            # Copy third test file (semantic duplicate) to inbox
            inbox_file = self.config.INBOX_PATH / "test_semantic_duplicate.html"
            shutil.copy2(self.test_files[2], inbox_file)
            
            # Run import
            importer = EnhancedReportImporter()
            success = importer.import_reports(source="inbox", broker=None, dry_run=False)
            
            if not success:
                console.print("[red]❌ Import failed[/red]")
                return False
            
            # Check if file was moved to logical_duplicates/
            logical_duplicate_file = self.config.ARCHIVE_LOGICAL_DUPLICATES_PATH / "test_semantic_duplicate.html"
            if not logical_duplicate_file.exists():
                console.print("[red]❌ File not moved to logical_duplicates/[/red]")
                return False
            
            # Check that no new record was inserted (should still be 1 from test 1)
            reports = self.db_ops.list_reports(broker="tinkoff", period="2023-07")
            if len(reports) != 1:
                console.print(f"[red]❌ Expected 1 record, found {len(reports)}[/red]")
                return False
            
            console.print("[green]✅ Semantic duplicate test passed[/green]")
            return True
            
        except Exception as e:
            logger.error(f"Semantic duplicate test failed: {e}")
            console.print(f"[red]❌ Test failed: {e}[/red]")
            return False
    
    def verify_logging(self) -> bool:
        """Verify that all events were logged correctly"""
        try:
            console.print("\n[bold blue]Verifying Logging[/bold blue]")
            
            # Check import_duplicates.log
            log_file = self.config.PROJECT_ROOT / 'diagnostics' / 'import_duplicates.log'
            if not log_file.exists():
                console.print("[red]❌ import_duplicates.log not found[/red]")
                return False
            
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # Check for expected log entries
            expected_entries = [
                "imported successfully",
                "exact duplicate (hash match)",
                "logical duplicate (same broker/account/period)"
            ]
            
            for entry in expected_entries:
                if entry not in log_content:
                    console.print(f"[red]❌ Missing log entry: {entry}[/red]")
                    return False
            
            console.print("[green]✅ Logging verification passed[/green]")
            return True
            
        except Exception as e:
            logger.error(f"Logging verification failed: {e}")
            console.print(f"[red]❌ Logging verification failed: {e}[/red]")
            return False
    
    def cleanup_test_data(self):
        """Cleanup test data from database and filesystem"""
        try:
            # Remove test records from database
            reports = self.db_ops.list_reports(broker="tinkoff", period="2023-07")
            for report in reports:
                if "test_" in report['file_name']:
                    self.db_ops.delete_report(report['id'])
                    logger.info(f"Deleted test record: {report['id']}")
            
            # Remove test files from archive directories
            for archive_dir in [self.config.ARCHIVE_IMPORTED_PATH, 
                               self.config.ARCHIVE_EXACT_DUPLICATES_PATH, 
                               self.config.ARCHIVE_LOGICAL_DUPLICATES_PATH]:
                for test_file in archive_dir.glob("test_*.html"):
                    test_file.unlink()
                    logger.info(f"Removed test file: {test_file}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup test data: {e}")
    
    def run_all_tests(self) -> bool:
        """Run all duplicate protection tests"""
        try:
            console.print("[bold blue]Duplicate Protection Smoke Test[/bold blue]\n")
            
            # Setup test environment
            if not self.setup_test_environment():
                console.print("[red]❌ Failed to setup test environment[/red]")
                return False
            
            try:
                # Ensure archive directories exist
                self.config.ensure_archive_directories()
                
                # Test 1: Unique import
                self.test_stats['tests_run'] += 1
                if self.test_unique_import():
                    self.test_stats['tests_passed'] += 1
                else:
                    self.test_stats['tests_failed'] += 1
                
                # Test 2: Exact duplicate
                self.test_stats['tests_run'] += 1
                if self.test_exact_duplicate():
                    self.test_stats['tests_passed'] += 1
                else:
                    self.test_stats['tests_failed'] += 1
                
                # Test 3: Semantic duplicate
                self.test_stats['tests_run'] += 1
                if self.test_semantic_duplicate():
                    self.test_stats['tests_passed'] += 1
                else:
                    self.test_stats['tests_failed'] += 1
                
                # Verify logging
                self.test_stats['tests_run'] += 1
                if self.verify_logging():
                    self.test_stats['tests_passed'] += 1
                else:
                    self.test_stats['tests_failed'] += 1
                
                # Generate test report
                self.generate_test_report()
                
                # Display results
                self.display_results()
                
                return self.test_stats['tests_failed'] == 0
                
            finally:
                # Cleanup
                self.cleanup_test_data()
                self.cleanup_test_environment()
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            self.test_stats['errors'].append(f"Test execution failed: {e}")
            return False
    
    def display_results(self):
        """Display test results"""
        table = Table(title="Duplicate Protection Test Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")
        
        table.add_row("Tests Run", str(self.test_stats['tests_run']))
        table.add_row("Tests Passed", str(self.test_stats['tests_passed']))
        table.add_row("Tests Failed", str(self.test_stats['tests_failed']))
        
        console.print(table)
        
        if self.test_stats['tests_failed'] == 0:
            console.print("[green]✅ All tests passed![/green]")
        else:
            console.print("[red]❌ Some tests failed![/red]")
    
    def generate_test_report(self):
        """Generate test report"""
        try:
            diagnostics_dir = self.config.PROJECT_ROOT / 'diagnostics'
            diagnostics_dir.mkdir(parents=True, exist_ok=True)
            
            report_path = diagnostics_dir / 'duplicate_protection_test.md'
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('# Duplicate Protection Test Report\n\n')
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write('## Test Results\n\n')
                f.write(f"- **Tests Run**: {self.test_stats['tests_run']}\n")
                f.write(f"- **Tests Passed**: {self.test_stats['tests_passed']}\n")
                f.write(f"- **Tests Failed**: {self.test_stats['tests_failed']}\n\n")
                
                f.write('## Test Scenarios\n\n')
                f.write('1. **Unique Import**: Import new report → moved to `imported/`\n')
                f.write('2. **Exact Duplicate**: Re-import same file → moved to `exact_duplicates/`\n')
                f.write('3. **Semantic Duplicate**: Import different HTML with same data → moved to `logical_duplicates/`\n')
                f.write('4. **Logging Verification**: All events logged to `import_duplicates.log`\n\n')
                
                if self.test_stats['errors']:
                    f.write('## Errors\n\n')
                    for error in self.test_stats['errors']:
                        f.write(f'- {error}\n')
                    f.write('\n')
                
                f.write('## Status\n\n')
                if self.test_stats['tests_failed'] == 0:
                    f.write('✅ **ALL TESTS PASSED**\n\n')
                    f.write('Duplicate protection is working correctly.\n')
                else:
                    f.write('❌ **SOME TESTS FAILED**\n\n')
                    f.write('Review the test results and fix any issues.\n')
            
            logger.info(f"Test report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate test report: {e}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Test duplicate protection functionality")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    # Ensure directories exist
    config = Config()
    try:
        config.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        config.ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
        config.PARSED_PATH.mkdir(parents=True, exist_ok=True)
        config.ensure_archive_directories()
    except Exception:
        pass
    
    # Run tests
    tester = DuplicateProtectionTester()
    success = tester.run_all_tests()
    
    if success:
        console.print("[green]✅ All duplicate protection tests passed![/green]")
    else:
        console.print("[red]❌ Some duplicate protection tests failed![/red]")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
