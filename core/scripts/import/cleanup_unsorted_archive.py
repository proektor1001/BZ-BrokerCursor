#!/usr/bin/env python3
"""
Archive cleanup tool for organizing unsorted HTML files
Scans modules/broker-reports/archive/ for loose HTML files and categorizes them
into appropriate subdirectories without reimporting to database.
"""

import sys
import os
import argparse
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.operations import BrokerReportOperations
from core.utils.file_manager import FileManager
from core.config import Config
from core.parsers import get_parser, is_broker_supported
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

def load_broker_patterns() -> Dict[str, Any]:
    """Load broker detection patterns from JSON file"""
    try:
        patterns_path = project_root / 'core' / 'brokers_patterns.json'
        with open(patterns_path, 'r', encoding='utf-8') as f:
            patterns = json.load(f)
        logger.info(f"Loaded broker patterns for {len(patterns)} brokers")
        return patterns
    except Exception as e:
        logger.error(f"Failed to load broker patterns: {e}")
        return {}

def detect_broker_tiered(file_path: Path, content: str, patterns: Dict[str, Any]) -> str:
    """
    Tiered broker detection using filename and HTML patterns
    
    Args:
        file_path: Path to the file
        content: File content (HTML/text)
        patterns: Broker patterns dictionary
        
    Returns:
        str: Detected broker name or 'unknown'
    """
    filename_lower = file_path.name.lower()
    content_lower = content.lower()
    
    # Tier 1: Filename patterns (highest priority)
    for broker, config in patterns.items():
        if broker == 'unknown':
            continue
            
        filename_patterns = config.get('filename_patterns', [])
        for pattern in filename_patterns:
            if pattern.lower() in filename_lower:
                logger.info(f"Detected broker '{broker}' from filename pattern: {pattern}")
                return broker
    
    # Tier 2: HTML content patterns
    for broker, config in patterns.items():
        if broker == 'unknown':
            continue
            
        html_patterns = config.get('html_patterns', [])
        for pattern in html_patterns:
            if pattern.lower() in content_lower:
                logger.info(f"Detected broker '{broker}' from HTML pattern: {pattern}")
                return broker
    
    # Tier 3: Fallback to unknown
    logger.warning(f"Could not detect broker for file: {file_path.name}")
    return 'unknown'

def extract_period_from_filename(filename):
    """Enhanced period extraction from filename"""
    import re
    
    # Look for YYYY-MM pattern
    period_match = re.search(r'(\d{4})-(\d{2})', filename)
    if period_match:
        return f"{period_match.group(1)}-{period_match.group(2)}"
    
    # Look for year in filename
    year_match = re.search(r'(\d{4})', filename)
    if year_match:
        year = year_match.group(1)
        # Try to guess month from context
        if "03" in filename or "март" in filename.lower():
            return f"{year}-03"
        elif "04" in filename or "апрель" in filename.lower():
            return f"{year}-04"
        elif "05" in filename or "май" in filename.lower():
            return f"{year}-05"
        elif "06" in filename or "июнь" in filename.lower():
            return f"{year}-06"
        elif "07" in filename or "июль" in filename.lower():
            return f"{year}-07"
        elif "08" in filename or "август" in filename.lower():
            return f"{year}-08"
        elif "10" in filename or "октябрь" in filename.lower():
            return f"{year}-10"
        elif "11" in filename or "ноябрь" in filename.lower():
            return f"{year}-11"
        elif "12" in filename or "декабрь" in filename.lower():
            return f"{year}-12"
    
    return "unknown"

def extract_account_from_filename(filename):
    """Extract account from filename"""
    if "4000T49" in filename:
        return "4000T49"
    elif "S000T49" in filename:
        return "S000T49"
    return None

class ArchiveCleanupTool:
    """Tool for cleaning up unsorted files in archive directory"""
    
    def __init__(self):
        self.config = Config()
        self.db_ops = BrokerReportOperations()
        self.file_manager = FileManager()
        self.broker_patterns = load_broker_patterns()
        self.stats = {
            'files_processed': 0,
            'exact_duplicates': 0,
            'logical_duplicates': 0,
            'imported': 0,
            'unrecognized': 0,
            'errors': []
        }
    
    def find_unsorted_files(self, archive_path: Path) -> List[Path]:
        """Find HTML files in archive root that need categorization"""
        unsorted_files = []
        
        if not archive_path.exists():
            logger.error(f"Archive directory does not exist: {archive_path}")
            return unsorted_files
        
        # Scan for HTML files in root directory only
        for file_path in archive_path.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() in {'.html', '.HTML'} and
                file_path.name not in ['index.json', 'README.md']):
                unsorted_files.append(file_path)
        
        logger.info(f"Found {len(unsorted_files)} unsorted HTML files in archive root")
        return unsorted_files
    
    def categorize_file(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """
        Categorize a single file into appropriate subdirectory
        
        Returns:
            Tuple[category, metadata]
            - category: 'exact_duplicates', 'logical_duplicates', 'imported', 'unrecognized'
            - metadata: dict with broker, account, period, hash, etc.
        """
        try:
            # Read file content
            content = self.file_manager.read_file_content(file_path)
            if not content:
                logger.warning(f"Could not read content from {file_path}")
                return 'unrecognized', {'error': 'Could not read file content'}
            
            # Calculate hash
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Extract metadata from filename
            filename_metadata = self.file_manager.extract_metadata_from_filename(file_path.name)
            broker = detect_broker_tiered(file_path, content, self.broker_patterns)
            period = extract_period_from_filename(file_path.name)
            account = extract_account_from_filename(file_path.name)
            
            metadata = {
                'file_hash': file_hash,
                'broker': broker,
                'account': account,
                'period': period,
                'filename_metadata': filename_metadata
            }
            
            # Step 1: Check for exact duplicate by hash
            existing_exact = self.db_ops.get_report_by_hash(file_hash)
            if existing_exact:
                logger.info(f"Exact duplicate found for {file_path.name}")
                return 'exact_duplicates', metadata
            
            # Step 2: Check for semantic duplicate
            if broker != 'unknown' and is_broker_supported(broker):
                try:
                    # Attempt parsing
                    parser = get_parser(broker)
                    parsed_data = parser.parse(content)
                    
                    if parsed_data and 'period_start' in parsed_data:
                        # Use parsed data for semantic check
                        parsed_period = parsed_data['period_start'][:7]  # YYYY-MM format
                        parsed_account = parsed_data.get('account_number', account)
                        
                        existing_semantic = self.db_ops.get_report_by_triple(
                            broker, parsed_account, parsed_period
                        )
                        
                        if existing_semantic:
                            logger.info(f"Semantic duplicate found for {file_path.name}")
                            metadata['parsed_period'] = parsed_period
                            metadata['parsed_account'] = parsed_account
                            return 'logical_duplicates', metadata
                        
                        # Update metadata with parsed values
                        metadata['period'] = parsed_period
                        metadata['account'] = parsed_account
                        metadata['parsed_data'] = parsed_data
                        
                        logger.info(f"File {file_path.name} successfully parsed, no duplicates found")
                        return 'imported', metadata
                    
                except Exception as e:
                    logger.warning(f"Parser failed for {file_path.name}: {e}")
                    metadata['parse_error'] = str(e)
            
            # Step 3: Check for unrecognized
            if broker == 'unknown':
                logger.warning(f"Unknown broker for {file_path.name}")
                return 'unrecognized', metadata
            
            # Default: treat as imported if no duplicates found
            logger.info(f"File {file_path.name} categorized as imported")
            return 'imported', metadata
            
        except Exception as e:
            logger.error(f"Error categorizing {file_path}: {e}")
            return 'unrecognized', {'error': str(e)}
    
    def move_file_to_category(self, file_path: Path, category: str, metadata: Dict[str, Any]) -> bool:
        """Move file to appropriate subdirectory"""
        try:
            # Determine target directory
            if category == 'exact_duplicates':
                target_dir = self.config.ARCHIVE_EXACT_DUPLICATES_PATH
            elif category == 'logical_duplicates':
                target_dir = self.config.ARCHIVE_LOGICAL_DUPLICATES_PATH
            elif category == 'imported':
                target_dir = self.config.ARCHIVE_IMPORTED_PATH
            elif category == 'unrecognized':
                target_dir = self.config.ARCHIVE_UNRECOGNIZED_PATH
            else:
                logger.error(f"Unknown category: {category}")
                return False
            
            # Ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Move file
            target_path = target_dir / file_path.name
            success = self.file_manager.safe_move_file(file_path, target_path)
            
            if success:
                # Log the event
                self.file_manager.log_import_event(
                    filename=file_path.name,
                    event_type=category.replace('_', '_'),
                    reason=f"archived to {category}",
                    file_hash=metadata.get('file_hash', ''),
                    broker=metadata.get('broker', ''),
                    account=metadata.get('account', ''),
                    period=metadata.get('period', '')
                )
                
                logger.info(f"Moved {file_path.name} to {target_dir}")
                return True
            else:
                logger.error(f"Failed to move {file_path.name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to move file {file_path}: {e}")
            return False
    
    def cleanup_archive(self, dry_run: bool = False) -> bool:
        """Main cleanup function"""
        logger.info("Starting archive cleanup")
        
        archive_path = self.config.ARCHIVE_PATH
        if not archive_path.exists():
            logger.error(f"Archive directory does not exist: {archive_path}")
            return False
        
        # Find unsorted files
        unsorted_files = self.find_unsorted_files(archive_path)
        if not unsorted_files:
            logger.info("No unsorted files found in archive")
            return True
        
        console.print(f"\n[cyan]Found {len(unsorted_files)} unsorted files[/cyan]")
        
        if dry_run:
            console.print("[yellow]DRY RUN - No files will be moved[/yellow]")
        
        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing files...", total=len(unsorted_files))
            
            for file_path in unsorted_files:
                progress.update(task, description=f"Processing {file_path.name}")
                
                # Categorize file
                category, metadata = self.categorize_file(file_path)
                
                # Update statistics
                self.stats['files_processed'] += 1
                self.stats[category] += 1
                
                if dry_run:
                    console.print(f"  {file_path.name} → {category}")
                else:
                    # Move file to appropriate directory
                    success = self.move_file_to_category(file_path, category, metadata)
                    if not success:
                        self.stats['errors'].append(f"Failed to move {file_path.name}")
                
                progress.advance(task)
        
        # Generate summary report
        self.generate_cleanup_report()
        
        # Show final statistics
        self.show_statistics()
        
        return True
    
    def generate_cleanup_report(self):
        """Generate cleanup summary report"""
        try:
            diagnostics_dir = self.config.PROJECT_ROOT / 'diagnostics'
            diagnostics_dir.mkdir(parents=True, exist_ok=True)
            
            report_path = diagnostics_dir / 'archive_cleanup_report.md'
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('# Archive Cleanup Report\n\n')
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write('## Summary\n\n')
                f.write(f"- **Total files processed:** {self.stats['files_processed']}\n")
                f.write(f"- **Exact duplicates:** {self.stats['exact_duplicates']}\n")
                f.write(f"- **Logical duplicates:** {self.stats['logical_duplicates']}\n")
                f.write(f"- **Imported:** {self.stats['imported']}\n")
                f.write(f"- **Unrecognized:** {self.stats['unrecognized']}\n\n")
                
                if self.stats['errors']:
                    f.write('## Errors\n\n')
                    for error in self.stats['errors']:
                        f.write(f"- {error}\n")
                    f.write('\n')
                
                # Check if archive root is clean
                archive_path = self.config.ARCHIVE_PATH
                remaining_files = self.find_unsorted_files(archive_path)
                
                if remaining_files:
                    f.write('## Warning: Archive root still contains files\n\n')
                    for file_path in remaining_files:
                        f.write(f"- {file_path.name}\n")
                else:
                    f.write('## Status: Archive root is clean ✅\n\n')
                    f.write('All HTML files have been successfully categorized and moved to appropriate subdirectories.\n')
            
            logger.info(f"Cleanup report generated: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate cleanup report: {e}")
    
    def show_statistics(self):
        """Show cleanup statistics"""
        table = Table(title="Archive Cleanup Statistics")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="magenta")
        
        table.add_row("Total Processed", str(self.stats['files_processed']))
        table.add_row("Exact Duplicates", str(self.stats['exact_duplicates']))
        table.add_row("Logical Duplicates", str(self.stats['logical_duplicates']))
        table.add_row("Imported", str(self.stats['imported']))
        table.add_row("Unrecognized", str(self.stats['unrecognized']))
        
        console.print(table)
        
        if self.stats['errors']:
            console.print(f"\n[red]Errors encountered:[/red]")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                console.print(f"  - {error}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Clean up unsorted files in archive directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without moving files")
    
    args = parser.parse_args()
    
    # Initialize cleanup tool
    cleanup_tool = ArchiveCleanupTool()
    
    # Run cleanup
    success = cleanup_tool.cleanup_archive(dry_run=args.dry_run)
    
    if success:
        console.print("[green]Archive cleanup completed successfully![/green]")
    else:
        console.print("[red]Archive cleanup failed![/red]")
        return False
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
