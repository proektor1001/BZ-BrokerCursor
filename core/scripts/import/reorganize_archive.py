#!/usr/bin/env python3
"""
Archive reorganization script
Moves existing files from archive/ to archive/imported/ and verifies database consistency
"""

import sys
import os
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

class ArchiveReorganizer:
    """Reorganizes existing archive files"""
    
    def __init__(self):
        self.config = Config()
        self.db_ops = BrokerReportOperations()
        self.file_manager = FileManager()
        self.reorganization_stats = {
            'files_found': 0,
            'files_moved': 0,
            'files_verified': 0,
            'files_not_in_db': 0,
            'errors': []
        }
    
    def scan_existing_archive(self) -> List[Path]:
        """Scan existing archive directory for files"""
        try:
            archive_path = self.config.ARCHIVE_PATH
            if not archive_path.exists():
                logger.warning(f"Archive directory does not exist: {archive_path}")
                return []
            
            # Find all files in archive (excluding subdirectories)
            files = []
            for item in archive_path.iterdir():
                if item.is_file() and not item.name.startswith('.'):
                    files.append(item)
            
            logger.info(f"Found {len(files)} files in archive directory")
            self.reorganization_stats['files_found'] = len(files)
            return files
            
        except Exception as e:
            logger.error(f"Failed to scan archive directory: {e}")
            return []
    
    def verify_file_in_database(self, file_path: Path) -> bool:
        """Verify if file exists in database"""
        try:
            filename = file_path.name
            
            # Check by filename
            report = self.db_ops.get_report_by_filename(filename)
            if report:
                logger.info(f"File {filename} found in database (ID: {report['id']})")
                return True
            
            # Check by file hash
            file_info = self.file_manager.get_file_info(file_path)
            if file_info and file_info.get('file_hash'):
                report = self.db_ops.get_report_by_hash(file_info['file_hash'])
                if report:
                    logger.info(f"File {filename} found in database by hash (ID: {report['id']})")
                    return True
            
            logger.warning(f"File {filename} not found in database")
            return False
            
        except Exception as e:
            logger.error(f"Failed to verify file {file_path}: {e}")
            return False
    
    def move_file_to_imported(self, file_path: Path) -> bool:
        """Move file to imported/ directory"""
        try:
            # Ensure imported directory exists
            self.config.ensure_archive_directories()
            
            # Move file
            target_path = self.config.ARCHIVE_IMPORTED_PATH / file_path.name
            shutil.move(str(file_path), str(target_path))
            
            logger.info(f"Moved {file_path.name} to imported/")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file {file_path}: {e}")
            self.reorganization_stats['errors'].append(f"Failed to move {file_path.name}: {e}")
            return False
    
    def log_reorganization_event(self, filename: str, action: str, in_database: bool):
        """Log reorganization event"""
        try:
            # Create diagnostics directory if it doesn't exist
            diagnostics_dir = self.config.PROJECT_ROOT / 'diagnostics'
            diagnostics_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = diagnostics_dir / 'archive_reorganization.log'
            
            # Format timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Build log entry
            log_entry = f"[{timestamp}] {filename} — {action} | in_database={in_database}\n"
            
            # Write to log file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.debug(f"Logged reorganization event: {action} for {filename}")
            
        except Exception as e:
            logger.error(f"Failed to log reorganization event: {e}")
    
    def reorganize_archive(self) -> bool:
        """Main reorganization function"""
        try:
            console.print("[bold blue]Archive Reorganization[/bold blue]\n")
            
            # Ensure archive directories exist
            self.config.ensure_archive_directories()
            
            # Scan existing files
            archive_files = self.scan_existing_archive()
            if not archive_files:
                console.print("[yellow]No files found in archive directory[/yellow]")
                return True
            
            console.print(f"Found {len(archive_files)} files to reorganize\n")
            
            # Process each file
            for file_path in archive_files:
                console.print(f"Processing: {file_path.name}")
                
                # Verify file in database
                in_database = self.verify_file_in_database(file_path)
                if in_database:
                    self.reorganization_stats['files_verified'] += 1
                else:
                    self.reorganization_stats['files_not_in_db'] += 1
                
                # Move file to imported/
                if self.move_file_to_imported(file_path):
                    self.reorganization_stats['files_moved'] += 1
                    
                    # Log the event
                    self.log_reorganization_event(
                        filename=file_path.name,
                        action='moved_to_imported',
                        in_database=in_database
                    )
                    
                    console.print(f"  ✅ Moved to imported/")
                else:
                    console.print(f"  ❌ Failed to move")
            
            # Generate reorganization report
            self.generate_reorganization_report()
            
            # Display summary
            self.display_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"Reorganization failed: {e}")
            self.reorganization_stats['errors'].append(f"Reorganization failed: {e}")
            return False
    
    def display_summary(self):
        """Display reorganization summary"""
        table = Table(title="Archive Reorganization Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")
        
        table.add_row("Files Found", str(self.reorganization_stats['files_found']))
        table.add_row("Files Moved", str(self.reorganization_stats['files_moved']))
        table.add_row("Files Verified in DB", str(self.reorganization_stats['files_verified']))
        table.add_row("Files Not in DB", str(self.reorganization_stats['files_not_in_db']))
        
        console.print(table)
        
        if self.reorganization_stats['files_moved'] == self.reorganization_stats['files_found']:
            console.print("[green]✅ All files reorganized successfully![/green]")
        else:
            console.print("[yellow]⚠️ Some files could not be moved[/yellow]")
    
    def generate_reorganization_report(self):
        """Generate reorganization report"""
        try:
            diagnostics_dir = self.config.PROJECT_ROOT / 'diagnostics'
            diagnostics_dir.mkdir(parents=True, exist_ok=True)
            
            report_path = diagnostics_dir / 'archive_reorganization_report.md'
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('# Archive Reorganization Report\n\n')
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write('## Summary\n\n')
                f.write(f"- **Files Found**: {self.reorganization_stats['files_found']}\n")
                f.write(f"- **Files Moved**: {self.reorganization_stats['files_moved']}\n")
                f.write(f"- **Files Verified in DB**: {self.reorganization_stats['files_verified']}\n")
                f.write(f"- **Files Not in DB**: {self.reorganization_stats['files_not_in_db']}\n\n")
                
                f.write('## Actions Taken\n\n')
                f.write('1. **Scanned** existing archive directory\n')
                f.write('2. **Verified** files against database records\n')
                f.write('3. **Moved** files to `archive/imported/` directory\n')
                f.write('4. **Logged** all reorganization events\n\n')
                
                if self.reorganization_stats['errors']:
                    f.write('## Errors\n\n')
                    for error in self.reorganization_stats['errors']:
                        f.write(f'- {error}\n')
                    f.write('\n')
                
                f.write('## New Archive Structure\n\n')
                f.write('```\n')
                f.write('modules/broker-reports/archive/\n')
                f.write('├── imported/           # Successfully imported reports\n')
                f.write('├── exact_duplicates/   # Byte-identical files (same hash)\n')
                f.write('└── logical_duplicates/ # Same semantic data, different HTML\n')
                f.write('```\n\n')
                
                f.write('## Status\n\n')
                if self.reorganization_stats['files_moved'] == self.reorganization_stats['files_found']:
                    f.write('✅ **REORGANIZATION COMPLETED SUCCESSFULLY**\n\n')
                    f.write('All existing files have been moved to the new archive structure.\n')
                else:
                    f.write('⚠️ **REORGANIZATION PARTIALLY COMPLETED**\n\n')
                    f.write('Some files could not be moved. Check the errors section above.\n')
            
            logger.info(f"Reorganization report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate reorganization report: {e}")

def main():
    """Main CLI function"""
    # Ensure directories exist
    config = Config()
    try:
        config.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        config.ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
        config.PARSED_PATH.mkdir(parents=True, exist_ok=True)
        config.ensure_archive_directories()
    except Exception:
        pass
    
    # Run reorganization
    reorganizer = ArchiveReorganizer()
    success = reorganizer.reorganize_archive()
    
    if success:
        console.print("[green]✅ Archive reorganization completed![/green]")
    else:
        console.print("[red]❌ Archive reorganization failed![/red]")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
