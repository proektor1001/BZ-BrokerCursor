#!/usr/bin/env python3
"""
Semantic duplicate verification script
Validates parsed_data consistency and detects semantic duplicates
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations
from core.config import Config
from rich.console import Console
from rich.table import Table

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

class SemanticDuplicateVerifier:
    """Verifies semantic duplicates in parsed_data"""
    
    def __init__(self):
        self.config = Config()
        self.db_ops = BrokerReportOperations()
        self.verification_stats = {
            'total_reports': 0,
            'parsed_reports': 0,
            'semantic_conflicts': 0,
            'period_mismatches': 0,
            'field_conflicts': 0,
            'errors': []
        }
    
    def get_parsed_reports(self) -> List[Dict[str, Any]]:
        """Get all reports with parsed_data"""
        try:
            query = """
                SELECT id, broker, account, period, parsed_data, file_name, created_at
                FROM broker_reports 
                WHERE parsed_data IS NOT NULL
                ORDER BY created_at DESC
            """
            result = self.db_ops.execute_raw_query(query)
            logger.info(f"Found {len(result)} reports with parsed_data")
            return result
        except Exception as e:
            logger.error(f"Failed to get parsed reports: {e}")
            return []
    
    def extract_semantic_fields(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract semantic fields from parsed_data"""
        try:
            if not parsed_data:
                return {}
            
            return {
                'broker': parsed_data.get('broker'),
                'account_number': parsed_data.get('account_number'),
                'period_start': parsed_data.get('period_start'),
                'period_end': parsed_data.get('period_end')
            }
        except Exception as e:
            logger.error(f"Failed to extract semantic fields: {e}")
            return {}
    
    def normalize_period(self, period_start: str, period_end: str) -> str:
        """Normalize period to YYYY-MM format"""
        try:
            if not period_start:
                return None
            
            # Extract YYYY-MM from period_start
            if isinstance(period_start, str) and len(period_start) >= 7:
                return period_start[:7]
            
            return None
        except Exception as e:
            logger.error(f"Failed to normalize period: {e}")
            return None
    
    def check_period_consistency(self, report: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if top-level period matches parsed_data period"""
        try:
            top_level_period = report.get('period')
            parsed_data = report.get('parsed_data', {})
            
            if not parsed_data:
                return True, "No parsed_data"
            
            parsed_period_start = parsed_data.get('period_start')
            parsed_period_end = parsed_data.get('period_end')
            
            if not parsed_period_start:
                return True, "No period_start in parsed_data"
            
            # Normalize parsed period
            normalized_parsed_period = self.normalize_period(parsed_period_start, parsed_period_end)
            
            if not normalized_parsed_period:
                return True, "Could not normalize parsed period"
            
            # Check if periods match
            if top_level_period == normalized_parsed_period:
                return True, "Periods match"
            else:
                return False, f"Period mismatch: top-level='{top_level_period}' vs parsed='{normalized_parsed_period}'"
                
        except Exception as e:
            logger.error(f"Failed to check period consistency: {e}")
            return False, f"Error: {e}"
    
    def find_semantic_duplicates(self, reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find semantic duplicates in parsed_data"""
        try:
            semantic_groups = {}
            duplicates = []
            
            for report in reports:
                parsed_data = report.get('parsed_data', {})
                if not parsed_data:
                    continue
                
                semantic_fields = self.extract_semantic_fields(parsed_data)
                
                # Create semantic key
                semantic_key = (
                    semantic_fields.get('broker'),
                    semantic_fields.get('account_number'),
                    semantic_fields.get('period_start'),
                    semantic_fields.get('period_end')
                )
                
                # Skip if any field is missing
                if None in semantic_key:
                    continue
                
                # Group by semantic key
                if semantic_key not in semantic_groups:
                    semantic_groups[semantic_key] = []
                
                semantic_groups[semantic_key].append(report)
            
            # Find groups with multiple reports
            for semantic_key, group_reports in semantic_groups.items():
                if len(group_reports) > 1:
                    duplicates.append({
                        'semantic_key': semantic_key,
                        'reports': group_reports,
                        'count': len(group_reports)
                    })
            
            logger.info(f"Found {len(duplicates)} semantic duplicate groups")
            return duplicates
            
        except Exception as e:
            logger.error(f"Failed to find semantic duplicates: {e}")
            return []
    
    def verify_semantic_consistency(self) -> bool:
        """Main verification function"""
        try:
            console.print("[bold blue]Semantic Duplicate Verification[/bold blue]\n")
            
            # Get all parsed reports
            reports = self.get_parsed_reports()
            if not reports:
                console.print("[yellow]No parsed reports found[/yellow]")
                return True
            
            self.verification_stats['total_reports'] = len(reports)
            self.verification_stats['parsed_reports'] = len([r for r in reports if r.get('parsed_data')])
            
            # Check period consistency
            period_issues = []
            for report in reports:
                is_consistent, message = self.check_period_consistency(report)
                if not is_consistent:
                    period_issues.append({
                        'report_id': report['id'],
                        'file_name': report['file_name'],
                        'issue': message
                    })
            
            self.verification_stats['period_mismatches'] = len(period_issues)
            
            # Find semantic duplicates
            semantic_duplicates = self.find_semantic_duplicates(reports)
            self.verification_stats['semantic_conflicts'] = len(semantic_duplicates)
            
            # Generate report
            self.generate_verification_report(period_issues, semantic_duplicates)
            
            # Display summary
            self.display_summary()
            
            return len(period_issues) == 0 and len(semantic_duplicates) == 0
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            self.verification_stats['errors'].append(f"Verification failed: {e}")
            return False
    
    def display_summary(self):
        """Display verification summary"""
        table = Table(title="Semantic Verification Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")
        
        table.add_row("Total Reports", str(self.verification_stats['total_reports']))
        table.add_row("Parsed Reports", str(self.verification_stats['parsed_reports']))
        table.add_row("Period Mismatches", str(self.verification_stats['period_mismatches']))
        table.add_row("Semantic Conflicts", str(self.verification_stats['semantic_conflicts']))
        
        console.print(table)
    
    def generate_verification_report(self, period_issues: List[Dict], semantic_duplicates: List[Dict]):
        """Generate detailed verification report"""
        try:
            diagnostics_dir = self.config.PROJECT_ROOT / 'diagnostics'
            diagnostics_dir.mkdir(parents=True, exist_ok=True)
            
            report_path = diagnostics_dir / 'semantic_duplicate_conflicts.md'
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('# Semantic Duplicate Conflicts Report\n\n')
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write('## Summary\n\n')
                f.write(f"- **Total Reports**: {self.verification_stats['total_reports']}\n")
                f.write(f"- **Parsed Reports**: {self.verification_stats['parsed_reports']}\n")
                f.write(f"- **Period Mismatches**: {self.verification_stats['period_mismatches']}\n")
                f.write(f"- **Semantic Conflicts**: {self.verification_stats['semantic_conflicts']}\n\n")
                
                # Period issues
                if period_issues:
                    f.write('## Period Consistency Issues\n\n')
                    for issue in period_issues:
                        f.write(f"- **Report ID {issue['report_id']}** ({issue['file_name']}): {issue['issue']}\n")
                    f.write('\n')
                
                # Semantic duplicates
                if semantic_duplicates:
                    f.write('## Semantic Duplicate Groups\n\n')
                    for i, duplicate in enumerate(semantic_duplicates, 1):
                        f.write(f'### Group {i}\n\n')
                        f.write(f'**Semantic Key**: {duplicate["semantic_key"]}\n')
                        f.write(f'**Count**: {duplicate["count"]} reports\n\n')
                        f.write('**Reports**:\n')
                        for report in duplicate['reports']:
                            f.write(f'- ID {report["id"]}: {report["file_name"]} (created: {report["created_at"]})\n')
                        f.write('\n')
                
                # Errors
                if self.verification_stats['errors']:
                    f.write('## Errors\n\n')
                    for error in self.verification_stats['errors']:
                        f.write(f'- {error}\n')
                    f.write('\n')
                
                f.write('## Recommendations\n\n')
                if period_issues:
                    f.write('- Review period extraction logic in parsers\n')
                if semantic_duplicates:
                    f.write('- Consider consolidating semantic duplicate reports\n')
                    f.write('- Review import logic for duplicate detection\n')
                if not period_issues and not semantic_duplicates:
                    f.write('- ✅ No semantic conflicts detected\n')
            
            logger.info(f"Verification report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate verification report: {e}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Verify semantic duplicates in parsed_data")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    # Ensure directories exist
    config = Config()
    try:
        config.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        config.ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
        config.PARSED_PATH.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    
    # Run verification
    verifier = SemanticDuplicateVerifier()
    success = verifier.verify_semantic_consistency()
    
    if success:
        console.print("[green]✅ Semantic verification completed successfully![/green]")
    else:
        console.print("[red]❌ Semantic verification found issues![/red]")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
