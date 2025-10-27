#!/usr/bin/env python3
"""
Database migration script for multi-broker support
Updates existing records to set broker='sber' and validates data integrity
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Also add current directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.database.operations import BrokerReportOperations
from core.database.connection import db_connection
from rich.console import Console

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console()

class DatabaseMigrator:
    """Handles database migration for multi-broker support"""
    
    def __init__(self):
        self.ops = BrokerReportOperations()
        self.db = db_connection
        self.migration_stats = {
            'total_records': 0,
            'updated_records': 0,
            'already_sber': 0,
            'null_broker': 0,
            'empty_broker': 0,
            'errors': []
        }
    
    def check_current_state(self) -> Dict[str, Any]:
        """Check current database state before migration"""
        try:
            # Count total records
            total_records = self.ops.count_reports()
            self.migration_stats['total_records'] = total_records
            
            # Check broker distribution
            broker_query = """
                SELECT broker, COUNT(*) as count 
                FROM broker_reports 
                GROUP BY broker 
                ORDER BY count DESC
            """
            broker_distribution = self.db.execute_query(broker_query)
            
            # Check for NULL or empty broker values
            null_broker_query = """
                SELECT COUNT(*) as count 
                FROM broker_reports 
                WHERE broker IS NULL OR broker = ''
            """
            null_broker_result = self.db.execute_query(null_broker_query)
            null_broker_count = null_broker_result[0]['count'] if null_broker_result else 0
            
            console.print(f"[blue]Current database state:[/blue]")
            console.print(f"  Total records: {total_records}")
            console.print(f"  Records with NULL/empty broker: {null_broker_count}")
            
            if broker_distribution:
                console.print(f"  Current broker distribution:")
                for row in broker_distribution:
                    console.print(f"    {row['broker'] or 'NULL'}: {row['count']}")
            
            return {
                'total_records': total_records,
                'null_broker_count': null_broker_count,
                'broker_distribution': [dict(row) for row in broker_distribution]
            }
            
        except Exception as e:
            logger.error(f"Failed to check current state: {e}")
            self.migration_stats['errors'].append(f"State check failed: {e}")
            return {}
    
    def migrate_broker_field(self) -> bool:
        """Update broker field for all records"""
        try:
            console.print(f"\n[yellow]Starting broker field migration...[/yellow]")
            
            # Update NULL broker values to 'sber'
            null_update_query = """
                UPDATE broker_reports 
                SET broker = 'sber' 
                WHERE broker IS NULL
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(null_update_query)
                null_updated = cursor.rowcount
                self.migration_stats['null_broker'] = null_updated
                console.print(f"  Updated NULL broker records: {null_updated}")
            
            # Update empty broker values to 'sber'
            empty_update_query = """
                UPDATE broker_reports 
                SET broker = 'sber' 
                WHERE broker = ''
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(empty_update_query)
                empty_updated = cursor.rowcount
                self.migration_stats['empty_broker'] = empty_updated
                console.print(f"  Updated empty broker records: {empty_updated}")
            
            # Commit changes
            self.db.connection.commit()
            
            total_updated = null_updated + empty_updated
            self.migration_stats['updated_records'] = total_updated
            
            console.print(f"[green]Migration completed: {total_updated} records updated[/green]")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.migration_stats['errors'].append(f"Migration failed: {e}")
            self.db.connection.rollback()
            return False
    
    def add_semantic_duplicate_index(self) -> bool:
        """Add semantic duplicate index for parsed_data fields"""
        try:
            console.print(f"\n[yellow]Adding semantic duplicate index...[/yellow]")
            
            # Check if index already exists
            check_index_query = """
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'broker_reports' 
                AND indexname = 'ux_semantic_duplicate'
            """
            existing_index = self.db.execute_query(check_index_query)
            
            if existing_index:
                console.print(f"  Semantic duplicate index already exists")
                return True
            
            # Create the semantic duplicate index
            create_index_query = """
                CREATE UNIQUE INDEX ux_semantic_duplicate 
                ON broker_reports ((parsed_data->>'broker'), (parsed_data->>'account_number'), (parsed_data->>'period_start'), (parsed_data->>'period_end')) 
                WHERE parsed_data IS NOT NULL
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(create_index_query)
                console.print(f"  Created semantic duplicate index")
            
            # Commit changes
            self.db.connection.commit()
            console.print(f"[green]✅ Semantic duplicate index created successfully[/green]")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create semantic duplicate index: {e}")
            self.migration_stats['errors'].append(f"Index creation failed: {e}")
            self.db.connection.rollback()
            return False

    def validate_migration(self) -> bool:
        """Validate that migration was successful"""
        try:
            console.print(f"\n[blue]Validating migration...[/blue]")
            
            # Check for any remaining NULL or empty broker values
            validation_query = """
                SELECT COUNT(*) as count 
                FROM broker_reports 
                WHERE broker IS NULL OR broker = ''
            """
            validation_result = self.db.execute_query(validation_query)
            remaining_issues = validation_result[0]['count'] if validation_result else 0
            
            if remaining_issues == 0:
                console.print(f"[green]✅ All records have valid broker field[/green]")
                return True
            else:
                console.print(f"[red]❌ {remaining_issues} records still have NULL/empty broker[/red]")
                return False
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            self.migration_stats['errors'].append(f"Validation failed: {e}")
            return False
    
    def get_final_statistics(self) -> Dict[str, Any]:
        """Get final statistics after migration"""
        try:
            # Get updated broker distribution
            broker_query = """
                SELECT broker, COUNT(*) as count 
                FROM broker_reports 
                GROUP BY broker 
                ORDER BY count DESC
            """
            broker_distribution = self.db.execute_query(broker_query)
            
            # Get total count
            total_records = self.ops.count_reports()
            
            return {
                'total_records': total_records,
                'broker_distribution': [dict(row) for row in broker_distribution],
                'migration_stats': self.migration_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get final statistics: {e}")
            return {}
    
    def generate_migration_report(self) -> str:
        """Generate migration report"""
        try:
            stats = self.get_final_statistics()
            
            report_content = f"""# Multi-Broker Migration Report

## Migration Summary

- **Total Records**: {stats.get('total_records', 0)}
- **Records Updated**: {self.migration_stats['updated_records']}
- **NULL broker fixed**: {self.migration_stats['null_broker']}
- **Empty broker fixed**: {self.migration_stats['empty_broker']}

## Final Broker Distribution

"""
            
            broker_dist = stats.get('broker_distribution', [])
            for row in broker_dist:
                report_content += f"- **{row['broker']}**: {row['count']} records\n"
            
            if self.migration_stats['errors']:
                report_content += f"\n## Errors\n\n"
                for error in self.migration_stats['errors']:
                    report_content += f"- {error}\n"
            
            report_content += f"""
## Migration Status

{'✅ SUCCESS' if not self.migration_stats['errors'] else '❌ FAILED'}

All existing records now have the broker field populated.
The system is ready for multi-broker support.
"""
            
            return report_content
            
        except Exception as e:
            logger.error(f"Failed to generate migration report: {e}")
            return f"# Migration Report\n\nError generating report: {e}"
    
    def run_migration(self) -> bool:
        """Run complete migration process"""
        try:
            console.print(f"[bold blue]Multi-Broker Database Migration[/bold blue]\n")
            
            # 1. Check current state
            current_state = self.check_current_state()
            if not current_state:
                console.print(f"[red]Failed to check current state[/red]")
                return False
            
            # 2. Run migration
            if not self.migrate_broker_field():
                console.print(f"[red]Migration failed[/red]")
                return False
            
            # 3. Add semantic duplicate index
            if not self.add_semantic_duplicate_index():
                console.print(f"[red]Index creation failed[/red]")
                return False
            
            # 4. Validate migration
            if not self.validate_migration():
                console.print(f"[red]Migration validation failed[/red]")
                return False
            
            # 4. Generate report
            report_content = self.generate_migration_report()
            report_path = project_root / 'diagnostics' / 'multi_broker_migration_report.md'
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            console.print(f"[green]Migration report saved to: {report_path}[/green]")
            console.print(f"[bold green]✅ Migration completed successfully![/bold green]")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            console.print(f"[red]Migration failed: {e}[/red]")
            return False

def main():
    """Main migration entry point"""
    migrator = DatabaseMigrator()
    success = migrator.run_migration()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()