#!/usr/bin/env python3
"""
External directory sync script for broker reports
Syncs files from external directory to inbox for processing
"""

import sys
import os
import argparse
import hashlib
import shutil
from pathlib import Path
from typing import List, Dict, Any, Set
import logging
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config
from core.utils.file_manager import FileManager
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

class ExternalSyncManager:
    """Manages synchronization from external directory to inbox"""
    
    def __init__(self):
        self.config = Config()
        self.file_manager = FileManager()
        self.sync_stats = {
            'files_scanned': 0,
            'files_copied': 0,
            'files_skipped': 0,
            'files_failed': 0,
            'errors': []
        }
    
    def scan_external_directory(self, external_path: Path) -> List[Dict[str, Any]]:
        """Scan external directory for supported files"""
        logger.info(f"Scanning external directory: {external_path}")
        
        if not external_path.exists():
            logger.error(f"External directory does not exist: {external_path}")
            return []
        
        files_info = self.file_manager.scan_directory(external_path)
        logger.info(f"Found {len(files_info)} supported files in external directory")
        
        return files_info
    
    def get_inbox_hashes(self) -> Set[str]:
        """Get set of file hashes already in inbox"""
        try:
            inbox_files = self.file_manager.scan_directory(self.config.INBOX_PATH)
            return {file_info['file_hash'] for file_info in inbox_files if file_info.get('file_hash')}
        except Exception as e:
            logger.error(f"Failed to scan inbox directory: {e}")
            return set()
    
    def get_inbox_filenames(self) -> Set[str]:
        """Get set of filenames already in inbox"""
        try:
            inbox_files = self.file_manager.scan_directory(self.config.INBOX_PATH)
            return {file_info['file_name'] for file_info in inbox_files}
        except Exception as e:
            logger.error(f"Failed to scan inbox directory: {e}")
            return set()
    
    def copy_file_to_inbox(self, file_info: Dict[str, Any], external_path: Path, force: bool = False) -> bool:
        """Copy file from external directory to inbox"""
        try:
            source_path = Path(file_info['file_path'])
            target_path = self.config.INBOX_PATH / file_info['file_name']
            
            # Check if file already exists in inbox
            if target_path.exists() and not force:
                logger.info(f"File already exists in inbox: {file_info['file_name']}")
                self.sync_stats['files_skipped'] += 1
                return True
            
            # Copy file
            shutil.copy2(source_path, target_path)
            logger.info(f"Copied {file_info['file_name']} to inbox")
            
            # Log sync operation
            self.log_sync_event(
                filename=file_info['file_name'],
                action='copied',
                source_path=str(source_path),
                target_path=str(target_path),
                file_hash=file_info.get('file_hash', ''),
                file_size=file_info.get('file_size', 0)
            )
            
            self.sync_stats['files_copied'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy file {file_info['file_name']}: {e}")
            self.sync_stats['files_failed'] += 1
            self.sync_stats['errors'].append(f"{file_info['file_name']}: {str(e)}")
            return False
    
    def log_sync_event(self, filename: str, action: str, source_path: str, 
                      target_path: str, file_hash: str, file_size: int):
        """Log sync operation to diagnostics/external_sync.log"""
        try:
            # Create diagnostics directory if it doesn't exist
            diagnostics_dir = self.config.PROJECT_ROOT / 'diagnostics'
            diagnostics_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = diagnostics_dir / 'external_sync.log'
            
            # Format timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Build log entry
            log_entry = f"[{timestamp}] {filename} — {action} | source={source_path} | target={target_path} | hash={file_hash[:16]}... | size={file_size}\n"
            
            # Write to log file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.debug(f"Logged sync event: {action} for {filename}")
            
        except Exception as e:
            logger.error(f"Failed to log sync event: {e}")
    
    def sync_external_directory(self, external_path: str, force: bool = False, dry_run: bool = False) -> bool:
        """Sync files from external directory to inbox"""
        logger.info(f"Starting external sync from {external_path} (force: {force}, dry_run: {dry_run})")
        
        external_path = Path(external_path)
        if not external_path.exists():
            logger.error(f"External directory does not exist: {external_path}")
            return False
        
        # Ensure inbox directory exists
        self.config.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        
        # Scan external directory
        external_files = self.scan_external_directory(external_path)
        if not external_files:
            logger.info("No files found in external directory")
            return True
        
        # Get existing files in inbox
        inbox_hashes = self.get_inbox_hashes()
        inbox_filenames = self.get_inbox_filenames()
        
        logger.info(f"Found {len(inbox_hashes)} existing files in inbox")
        
        if dry_run:
            logger.info("DRY RUN - No files will be copied")
            for file_info in external_files:
                filename = file_info['file_name']
                file_hash = file_info.get('file_hash', '')
                
                if file_hash in inbox_hashes:
                    logger.info(f"Would skip {filename} (hash already exists)")
                elif filename in inbox_filenames:
                    logger.info(f"Would skip {filename} (filename already exists)")
                else:
                    logger.info(f"Would copy {filename}")
            return True
        
        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Syncing files...", total=len(external_files))
            
            for file_info in external_files:
                filename = file_info['file_name']
                file_hash = file_info.get('file_hash', '')
                
                progress.update(task, description=f"Processing {filename}")
                
                # Check if file already exists
                if file_hash in inbox_hashes:
                    logger.info(f"Skipping {filename} - hash already exists in inbox")
                    self.sync_stats['files_skipped'] += 1
                elif filename in inbox_filenames and not force:
                    logger.info(f"Skipping {filename} - filename already exists in inbox")
                    self.sync_stats['files_skipped'] += 1
                else:
                    # Copy file
                    success = self.copy_file_to_inbox(file_info, external_path, force)
                    if not success:
                        logger.error(f"Failed to copy {filename}")
                
                self.sync_stats['files_scanned'] += 1
                progress.advance(task)
        
        # Generate sync summary
        self.generate_sync_summary()
        
        logger.info(f"Sync completed: {self.sync_stats['files_copied']} copied, {self.sync_stats['files_skipped']} skipped, {self.sync_stats['files_failed']} failed")
        return True
    
    def generate_sync_summary(self):
        """Generate sync summary report"""
        try:
            diagnostics_dir = self.config.PROJECT_ROOT / 'diagnostics'
            diagnostics_dir.mkdir(parents=True, exist_ok=True)
            
            summary_path = diagnostics_dir / 'external_sync_summary.md'
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write('# External Sync Summary\n\n')
                f.write(f"Files scanned: {self.sync_stats['files_scanned']}\n")
                f.write(f"Files copied: {self.sync_stats['files_copied']}\n")
                f.write(f"Files skipped: {self.sync_stats['files_skipped']}\n")
                f.write(f"Files failed: {self.sync_stats['files_failed']}\n")
                
                if self.sync_stats['errors']:
                    f.write('\n## Errors\n')
                    for error in self.sync_stats['errors']:
                        f.write(f"- {error}\n")
            
            logger.info(f"Sync summary saved to: {summary_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate sync summary: {e}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Sync external broker reports to inbox")
    parser.add_argument("--source", required=True, help="External directory path to sync from")
    parser.add_argument("--force", action="store_true", help="Force copy even if files exist")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be copied without actually copying")
    
    args = parser.parse_args()
    
    # Validate external directory
    external_path = Path(args.source)
    if not external_path.exists():
        console.print(f"[red]External directory does not exist: {external_path}[/red]")
        return False
    
    # Ensure inbox directory exists
    config = Config()
    config.INBOX_PATH.mkdir(parents=True, exist_ok=True)
    
    # Run sync
    sync_manager = ExternalSyncManager()
    success = sync_manager.sync_external_directory(
        source=args.source,
        force=args.force,
        dry_run=args.dry_run
    )
    
    if success:
        console.print("[green]External sync completed successfully![/green]")
    else:
        console.print("[red]External sync failed![/red]")
        return False
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
