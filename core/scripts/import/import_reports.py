#!/usr/bin/env python3
"""
Enhanced CLI tool for importing broker reports into PostgreSQL database
Consolidates functionality from import_reports.py, simple_import.py, and fixed_import.py
Scans inbox directory, processes files, and archives them with enhanced error handling
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

def detect_broker_from_filename(filename):
    """Legacy broker detection from filename (kept for backward compatibility)"""
    filename_lower = filename.lower()
    
    # Tinkoff patterns
    if "4000t49" in filename_lower or "s000t49" in filename_lower:
        return "tinkoff"
    
    # Sber patterns
    if "sber" in filename_lower or "сбер" in filename_lower:
        return "sber"
    
    # VTB patterns
    if "vtb" in filename_lower or "втб" in filename_lower:
        return "vtb"
    
    return "unknown"

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

class EnhancedReportImporter:
    """Enhanced class for importing broker reports with consolidated functionality"""
    
    def __init__(self):
        self.config = Config()
        self.db_ops = BrokerReportOperations()
        self.file_manager = FileManager()
        self.broker_patterns = load_broker_patterns()
        self.stats = {
            'files_processed': 0,
            'files_success': 0,
            'files_failed': 0,
            'files_skipped': 0,
            'unknown_broker': 0,
            'errors': []
        }
    
    def is_exact_duplicate(self, file_hash: str) -> Tuple[bool, Optional[Dict]]:
        """Check if file hash already exists in DB"""
        existing = self.db_ops.get_report_by_hash(file_hash)
        return (existing is not None, existing)

    def is_semantic_duplicate(self, broker: str, account: str, period: str, parsed_data: Optional[Dict] = None) -> Tuple[bool, Optional[Dict]]:
        """
        Check semantic duplicate using:
        1. Filename-based period (fast check)
        2. Parsed period_start[:7] (accurate check if parsed_data available)
        """
        # If parsed_data available, use period_start[:7]
        if parsed_data and 'period_start' in parsed_data:
            parsed_period = parsed_data['period_start'][:7]  # YYYY-MM format
            # Use parsed account_number if available, otherwise fall back to filename account
            parsed_account = parsed_data.get('account_number', account)
            existing = self.db_ops.get_report_by_triple(broker, parsed_account, parsed_period)
            return (existing is not None, existing)
        
        # Otherwise use filename-based period
        existing = self.db_ops.get_report_by_triple(broker, account, period)
        return (existing is not None, existing)

    def _parse_file_content(self, broker: str, content: str, filename: str) -> Tuple[Optional[Dict], str]:
        """
        Parse file content using broker-specific parser with comprehensive error handling
        
        Args:
            broker: Broker name (e.g., 'sber', 'tinkoff')
            content: HTML file content
            filename: Filename for logging purposes
        
        Returns:
            Tuple[parsed_data or None, status_message]
            - (parsed_data_dict, 'success') if parsing succeeded
            - (None, 'no_parser_found') if broker has no registered parser
            - (None, 'parse_failed: <error>') if parsing threw exception
        """
        # 1. Check if broker has parser in registry
        if not is_broker_supported(broker):
            logger.warning(f"No parser found for broker: {broker}")
            return (None, 'no_parser_found')
        
        # 2. Get parser instance
        try:
            parser = get_parser(broker)
        except Exception as e:
            logger.error(f"Failed to instantiate parser for {broker}: {e}")
            return (None, f'parser_instantiation_failed: {e}')
        
        # 3. Invoke parser.parse(content)
        try:
            parsed_data = parser.parse(content)
            
            # Validate parsed_data structure
            if not parsed_data or not isinstance(parsed_data, dict):
                logger.error(f"Parser returned invalid data for {filename}")
                return (None, 'invalid_parser_output')
            
            # Check for required fields
            required_fields = ['account_number', 'period_start']
            missing = [f for f in required_fields if f not in parsed_data]
            if missing:
                logger.warning(f"Parser missing fields {missing} for {filename}")
                # Still return parsed_data but log warning
            
            logger.info(f"Successfully parsed {filename} using {broker} parser")
            return (parsed_data, 'success')
            
        except Exception as e:
            logger.error(f"Parser failed for {filename}: {e}")
            return (None, f'parse_failed: {str(e)}')

    def _serialize_parsed_data(self, parsed_data: Dict) -> Dict:
        """
        Convert date objects and other non-JSON-serializable objects to strings
        
        Args:
            parsed_data: Dictionary containing parsed data with potential date objects
            
        Returns:
            Dict: Serialized data safe for JSON storage
        """
        from datetime import date, datetime
        
        serialized = {}
        for key, value in parsed_data.items():
            if isinstance(value, (date, datetime)):
                # Convert date/datetime to ISO format string
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                # Recursively serialize nested dictionaries
                serialized[key] = self._serialize_parsed_data(value)
            elif isinstance(value, list):
                # Serialize list items
                serialized[key] = [
                    item.isoformat() if isinstance(item, (date, datetime)) else item
                    for item in value
                ]
            else:
                # Keep other types as-is
                serialized[key] = value
        
        return serialized

    def move_to_duplicate_archive(self, file_path: Path, duplicate_type: str, reason: str) -> bool:
        """Move duplicate file to appropriate archive subdirectory"""
        try:
            # Ensure archive directories exist
            self.config.ensure_archive_directories()
            
            # Determine target directory
            if duplicate_type == 'exact_duplicates':
                target_dir = self.config.ARCHIVE_EXACT_DUPLICATES_PATH
            elif duplicate_type == 'logical_duplicates':
                target_dir = self.config.ARCHIVE_LOGICAL_DUPLICATES_PATH
            else:
                logger.error(f"Unknown duplicate type: {duplicate_type}")
                return False
            
            # Move file
            target_path = target_dir / file_path.name
            file_path.rename(target_path)
            
            # Log the event
            self.file_manager.log_import_event(
                filename=file_path.name,
                event_type=duplicate_type.replace('_', '_'),
                reason=reason,
                file_hash="",  # Will be filled by caller
                broker="",     # Will be filled by caller
                account="",    # Will be filled by caller
                period=""      # Will be filled by caller
            )
            
            logger.info(f"Moved {file_path.name} to {target_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move duplicate file {file_path}: {e}")
            return False

    def scan_inbox(self, inbox_path: Path) -> List[Dict[str, Any]]:
        """Scan inbox directory for supported files"""
        logger.info(f"Scanning inbox directory: {inbox_path}")
        
        if not inbox_path.exists():
            logger.error(f"Inbox directory does not exist: {inbox_path}")
            return []
        
        files_info = self.file_manager.scan_directory(inbox_path)
        logger.info(f"Found {len(files_info)} supported files")
        
        return files_info
    
    def process_file_enhanced(self, file_info: Dict[str, Any], archive_path: Path) -> bool:
        """Enhanced file processing with 4-stage hybrid flow"""
        file_path = Path(file_info['file_path'])
        
        try:
            print(f"\nProcessing: {file_path.name}")
            
            # STAGE 1: Hash-based duplicate detection
            # 1. Read file content
            content = self.file_manager.read_file_content(file_path)
            if not content:
                logger.warning(f"Could not read content from {file_path}")
                self.stats['files_failed'] += 1
                return False
            
            # 2. Calculate SHA-256 hash
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            print(f"  Hash: {file_hash[:16]}...")
            
            # 3. Check exact duplicate in DB by hash
            is_exact, existing_exact = self.is_exact_duplicate(file_hash)
            if is_exact:
                # Move to exact_duplicates/, log, return
                self.move_to_duplicate_archive(
                    file_path, 
                    'exact_duplicates', 
                    'exact duplicate (hash match)'
                )
                
                # Log to database
                self.db_ops.log_import_file(
                    status='duplicate_detected',
                    broker='unknown',  # Will be updated after broker detection
                    account=None,
                    period=None,
                    file_name=file_info['file_name'],
                    file_hash=file_hash,
                    error_summary='Exact duplicate detected'
                )
                
                # Log to import_duplicates.log
                self.file_manager.log_import_event(
                    filename=file_info['file_name'],
                    event_type='exact_duplicate',
                    reason='exact duplicate (hash match)',
                    file_hash=file_hash
                )
                
                logger.info(f"Skipped {file_path} - exact duplicate")
                self.stats['files_skipped'] += 1
                return True
            
            # STAGE 2: Filename-based pre-filtering
            # 4. Extract broker/account/period from filename
            broker = detect_broker_tiered(file_path, content, self.broker_patterns)
            if broker == "unknown":
                logger.warning(f"Could not detect broker for {file_path}")
                self.stats['unknown_broker'] += 1
                # Continue processing with 'unknown' broker instead of failing
            
            period = extract_period_from_filename(file_path.name)
            account = extract_account_from_filename(file_path.name)
            
            print(f"  Broker: {broker}, Account: {account}, Period: {period}")
            
            # 5. Quick semantic check using filename metadata (flag potential duplicates)
            is_semantic_filename, existing_semantic_filename = self.is_semantic_duplicate(broker, account, period)
            
            # STAGE 3: Full parsing and validation
            # 6. Invoke broker-specific parser
            parsed_data, parse_status = self._parse_file_content(broker, content, file_info['file_name'])
            
            if parse_status == 'no_parser_found':
                # Move to archive/unrecognized/, log, return
                self.config.ensure_archive_directories()
                unrecognized_path = self.config.ARCHIVE_UNRECOGNIZED_PATH / file_info['file_name']
                try:
                    file_path.rename(unrecognized_path)
                    print(f"  Archived to unrecognized/: {unrecognized_path}")
                except Exception as e:
                    print(f"  Archive failed: {e}")
                    self.stats['files_failed'] += 1
                    return False
                
                # Log to database
                self.db_ops.log_import_file(
                    status='skipped',
                    broker=broker,
                    account=account,
                    period=period,
                    file_name=file_info['file_name'],
                    file_hash=file_hash,
                    error_summary='No parser found for broker'
                )
                
                # Log to import_duplicates.log
                self.file_manager.log_import_event(
                    filename=file_info['file_name'],
                    event_type='no_parser_found',
                    reason='no parser found for broker',
                    file_hash=file_hash,
                    broker=broker
                )
                
                logger.info(f"Skipped {file_path} - no parser found")
                self.stats['files_skipped'] += 1
                return True
            
            elif parse_status.startswith('parse_failed'):
                # Parser failed - fall back to filename metadata
                logger.warning(f"Parser failed for {file_info['file_name']}, using filename metadata")
                parsed_data = None
                # Continue with filename-based metadata
            
            # 7. Check for period mismatch between filename and parsed data
            if parsed_data and 'period_start' in parsed_data:
                parsed_period = parsed_data['period_start'][:7]
                if period != parsed_period:
                    logger.warning(f"Period mismatch: filename={period}, parsed={parsed_period}")
                    # Log period mismatch
                    self.file_manager.log_import_event(
                        filename=file_info['file_name'],
                        event_type='period_mismatch',
                        reason='period mismatch between filename and parsed data',
                        file_hash=file_hash,
                        broker=broker,
                        account=account,
                        filename_period=period,
                        parsed_period=parsed_period
                    )
                    # Trust parsed data for semantic check
                    period = parsed_period
                    account = parsed_data.get('account_number', account)
            
            # 8. Re-check semantic duplicate using parsed metadata
            is_semantic_parsed, existing_semantic_parsed = self.is_semantic_duplicate(broker, account, period, parsed_data)
            if is_semantic_parsed:
                # Move to logical_duplicates/, log, return
                self.move_to_duplicate_archive(
                    file_path, 
                    'logical_duplicates', 
                    'semantic duplicate (same broker/account/period)'
                )
                
                # Log to database
                self.db_ops.log_import_file(
                    status='collision_mismatch',
                    broker=broker,
                    account=account,
                    period=period,
                    file_name=file_info['file_name'],
                    file_hash=file_hash,
                    error_summary='semantic duplicate: account + period already imported'
                )
                
                # Log to import_duplicates.log
                self.file_manager.log_import_event(
                    filename=file_info['file_name'],
                    event_type='semantic_duplicate',
                    reason='semantic duplicate (same broker/account/period)',
                    file_hash=file_hash,
                    broker=broker,
                    account=account,
                    period=period
                )
                
                logger.info(f"Skipped {file_path} - semantic duplicate")
                self.stats['files_skipped'] += 1
                return True
            
            # STAGE 4: Insert to DB
            # 9. Extract additional metadata
            filename_metadata = self.file_manager.extract_metadata_from_filename(file_info['file_name'])
            content_metadata = self.file_manager.extract_metadata_from_content(content)
            
            # Merge metadata
            metadata = {**filename_metadata, **content_metadata}
            
            # Prepare data for database
            report_data = {
                'broker': broker,
                'period': period,
                'file_name': file_info['file_name'],
                'file_path': str(file_path),
                'account': account,
                'client_name': metadata.get('client_name'),
                'report_date': metadata.get('report_date'),
                'metadata': {
                    'file_size': file_info['file_size'],
                    'file_type': file_info['file_type'],
                    'extracted_metadata': metadata,
                    'import_method': 'hybrid_import'
                }
            }
            
            # Add content based on file type
            if file_path.suffix.lower() == '.html':
                report_data['html_content'] = content
            else:
                report_data['raw_content'] = content
            
            # Insert into database with parsed_data if available
            if parsed_data:
                # Convert date objects to strings for JSON serialization
                serialized_parsed_data = self._serialize_parsed_data(parsed_data)
                
                # Insert with parsed_data and set processing_status = 'parsed'
                report_id = self.db_ops.insert_report(
                    **report_data,
                    file_hash=file_hash,
                    file_size=file_info.get('file_size')
                )
                
                if report_id:
                    # Update with parsed_data and set status to 'parsed'
                    self.db_ops.update_report_parsed_data(report_id, serialized_parsed_data, 'parsed')
            else:
                # Insert without parsed_data (processing_status = 'raw')
                report_id = self.db_ops.insert_report(
                    **report_data,
                    file_hash=file_hash,
                    file_size=file_info.get('file_size')
                )
            
            if not report_id:
                logger.error(f"Failed to insert report into database: {file_path}")
                self.stats['files_failed'] += 1
                self.db_ops.log_import_file(
                    status='failure',
                    broker=broker,
                    account=account,
                    period=period,
                    file_name=file_info['file_name'],
                    file_hash=file_hash,
                    error_summary='Insert failed'
                )
                return False
            else:
                print(f"  Success: Report ID {report_id}")
                self.stats['files_success'] += 1
                
                # Log success to database
                self.db_ops.log_import_file(
                    status='success',
                    broker=broker,
                    account=account,
                    period=period,
                    file_name=file_info['file_name'],
                    file_hash=file_hash,
                    error_summary=None
                )
                
                # Log success to import_duplicates.log
                self.file_manager.log_import_event(
                    filename=file_info['file_name'],
                    event_type='imported',
                    reason='imported successfully',
                    file_hash=file_hash,
                    broker=broker,
                    account=account,
                    period=period
                )
                
                # 10. Move file to imported/ archive
                self.config.ensure_archive_directories()
                imported_path = self.config.ARCHIVE_IMPORTED_PATH / file_info['file_name']
                try:
                    file_path.rename(imported_path)
                    print(f"  Archived to imported/: {imported_path}")
                    return True
                except Exception as e:
                    print(f"  Archive failed: {e}")
                    self.stats['files_failed'] += 1
                    return False
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            self.stats['files_failed'] += 1
            self.stats['errors'].append(f"{file_path}: {str(e)}")
            return False
    
    def import_reports(self, source: str = "inbox", broker: str = None, dry_run: bool = False) -> bool:
        """Enhanced import function with better error handling"""
        logger.info(f"Starting enhanced import from {source} (broker: {broker or 'all'})")
        
        # Determine source path
        if source == "inbox":
            source_path = self.config.INBOX_PATH
        else:
            source_path = Path(source)
        
        if not source_path.exists():
            logger.error(f"Source path does not exist: {source_path}")
            return False
        
        # Create archive directory
        archive_path = self.config.ARCHIVE_PATH
        archive_path.mkdir(parents=True, exist_ok=True)
        print(f"Archive directory: {archive_path.absolute()}")
        
        # Scan for files
        files_info = self.scan_inbox(source_path)
        if not files_info:
            logger.info("No files found to process")
            return True
        
        # Filter by broker if specified
        if broker:
            filtered_files = []
            for file_info in files_info:
                content = self.file_manager.read_file_content(Path(file_info['file_path']))
                if content and detect_broker_from_filename(file_info['file_name']) == broker:
                    filtered_files.append(file_info)
            files_info = filtered_files
            logger.info(f"Filtered to {len(files_info)} files for broker: {broker}")
        
        if dry_run:
            logger.info("DRY RUN - No files will be processed")
            for file_info in files_info:
                content = self.file_manager.read_file_content(Path(file_info['file_path']))
                detected_broker = detect_broker_from_filename(file_info['file_name'])
                logger.info(f"Would process: {file_info['file_name']} (broker: {detected_broker})")
            return True
        
        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing files...", total=len(files_info))
            
            for file_info in files_info:
                progress.update(task, description=f"Processing {file_info['file_name']}")
                
                success = self.process_file_enhanced(file_info, archive_path)
                self.stats['files_processed'] += 1
                
                progress.advance(task)
        
        # Log import operation (aggregate)
        self.db_ops.log_import_operation(
            operation_type="import",
            broker=broker,
            files_processed=self.stats['files_processed'],
            files_success=self.stats['files_success'],
            files_failed=self.stats['files_failed'],
            error_summary="; ".join(self.stats['errors']) if self.stats['errors'] else None
        )
        
        # Generate diagnostics summary
        try:
            diagnostics_dir = self.config.PROJECT_ROOT / 'diagnostics'
            diagnostics_dir.mkdir(parents=True, exist_ok=True)
            summary_path = diagnostics_dir / 'enhanced_import_summary.md'
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write('# Enhanced Import Summary\n\n')
                f.write(f"Total processed: {self.stats['files_processed']}\n")
                f.write(f"Inserted: {self.stats['files_success']}\n")
                f.write(f"Skipped (duplicates/collisions): {self.stats['files_skipped']}\n")
                f.write(f"Failed: {self.stats['files_failed']}\n")
                if self.stats['errors']:
                    f.write('\n## Errors (first 10)\n')
                    for e in self.stats['errors'][:10]:
                        f.write(f"- {e}\n")
        except Exception as e:
            logger.error(f"Failed to write diagnostics summary: {e}")

        return True
    
    def show_statistics(self):
        """Show import statistics"""
        stats = self.db_ops.get_statistics()
        
        table = Table(title="Database Statistics")
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
        
        # Show current import stats
        if self.stats['files_processed'] > 0:
            console.print(f"\nCurrent Import Session:")
            console.print(f"  Files processed: {self.stats['files_processed']}")
            console.print(f"  Success: {self.stats['files_success']}")
            console.print(f"  Failed: {self.stats['files_failed']}")
            console.print(f"  Unknown broker: {self.stats['unknown_broker']}")
            
            if self.stats['errors']:
                console.print(f"\nErrors:")
                for error in self.stats['errors'][:5]:  # Show first 5 errors
                    console.print(f"  - {error}")

def main():
    """Enhanced main CLI function"""
    parser = argparse.ArgumentParser(description="Enhanced import broker reports into PostgreSQL database")
    parser.add_argument("--source", default="inbox", help="Source directory (default: inbox)")
    parser.add_argument("--broker", help="Filter by specific broker")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without importing")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    
    args = parser.parse_args()
    
    # Show database statistics
    if args.stats:
        importer = EnhancedReportImporter()
        importer.show_statistics()
        return
    
    # Prepare configuration and ensure directories exist before validation
    config = Config()
    try:
        config.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        config.ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
        config.PARSED_PATH.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    
    # Validate configuration
    issues = config.validate_config()
    
    if issues:
        console.print("[red]Configuration issues found:[/red]")
        for issue in issues:
            console.print(f"  - {issue}")
        return False
    
    # Run enhanced import
    importer = EnhancedReportImporter()
    success = importer.import_reports(
        source=args.source,
        broker=args.broker,
        dry_run=args.dry_run
    )
    
    if success:
        importer.show_statistics()
        console.print("[green]Enhanced import completed successfully![/green]")
    else:
        console.print("[red]Enhanced import failed![/red]")
        return False
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
