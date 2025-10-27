"""
File management utilities for broker reports
Handles file detection, metadata extraction, and safe file operations
"""

import os
import re
import hashlib
import shutil
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class FileManager:
    """File management utilities for broker reports"""
    
    def __init__(self):
        self.supported_extensions = {'.html', '.txt', '.pdf', '.md'}
        self.broker_patterns = {
            'sber': [
                r'сбербанк',
                r'сбер',
                r'sber',
                r'отчет брокера',
                r'брокерский отчет'
            ],
            'tinkoff': [
                r'тинькофф',
                r'tinkoff',
                r'т-банк',
                r'т банк'
            ],
            'vtb': [
                r'втб',
                r'vtb',
                r'втб капитал'
            ],
            'gazprombank': [
                r'газпромбанк',
                r'gazprombank',
                r'газпром'
            ],
            'alpha': [
                r'альфа',
                r'alpha',
                r'альфа-банк'
            ]
        }
    
    def detect_broker(self, content: str, file_name: str = "") -> Optional[str]:
        """Detect broker from content and filename"""
        text_to_analyze = f"{file_name} {content}".lower()
        
        broker_scores = {}
        for broker, patterns in self.broker_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_to_analyze, re.IGNORECASE))
                score += matches
            if score > 0:
                broker_scores[broker] = score
        
        if broker_scores:
            best_broker = max(broker_scores, key=broker_scores.get)
            logger.info(f"Detected broker: {best_broker} (score: {broker_scores[best_broker]})")
            return best_broker
        
        return None
    
    def extract_metadata_from_filename(self, file_name: str) -> Dict[str, Any]:
        """Extract metadata from filename patterns"""
        metadata = {}
        
        # Common patterns for broker reports
        patterns = {
            'account': r'([A-Z0-9]{6,10})',  # Account numbers like 4000T49, S000T49
            'period': r'(\d{4}-\d{2})',      # Period like 2023-07
            'date': r'(\d{2}\.\d{2}\.\d{4})', # Date like 29.12.2023
            'year': r'(\d{4})',              # Year
            'month': r'(\d{1,2})'            # Month
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, file_name)
            if match:
                metadata[key] = match.group(1)
        
        # Extract period from various formats
        if 'period' not in metadata and 'year' in metadata and 'month' in metadata:
            year = metadata['year']
            month = metadata['month'].zfill(2)
            metadata['period'] = f"{year}-{month}"
        
        return metadata
    
    def extract_metadata_from_content(self, content: str) -> Dict[str, Any]:
        """Extract metadata from HTML/content"""
        metadata = {}
        
        # Extract account number patterns
        account_patterns = [
            r'счет[а-я\s]*:?\s*([A-Z0-9]{6,10})',
            r'account[:\s]*([A-Z0-9]{6,10})',
            r'№\s*([A-Z0-9]{6,10})',
            r'([A-Z0-9]{6,10})'
        ]
        
        for pattern in account_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['account'] = match.group(1)
                break
        
        # Extract period patterns
        period_patterns = [
            r'период[а-я\s]*:?\s*(\d{4}-\d{2})',
            r'period[:\s]*(\d{4}-\d{2})',
            r'(\d{4}-\d{2})'
        ]
        
        for pattern in period_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['period'] = match.group(1)
                break
        
        # Extract client name
        client_patterns = [
            r'клиент[а-я\s]*:?\s*([А-Я][а-я]+\s+[А-Я]\.\s*[А-Я]\.)',
            r'client[:\s]*([А-Я][а-я]+\s+[А-Я]\.\s*[А-Я]\.)',
            r'([А-Я][а-я]+\s+[А-Я]\.\s*[А-Я]\.)'
        ]
        
        for pattern in client_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['client_name'] = match.group(1)
                break
        
        # Extract report date
        date_patterns = [
            r'дата[а-я\s]*:?\s*(\d{2}\.\d{2}\.\d{4})',
            r'date[:\s]*(\d{2}\.\d{2}\.\d{4})',
            r'(\d{2}\.\d{2}\.\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    metadata['report_date'] = datetime.strptime(date_str, '%d.%m.%Y').date()
                except ValueError:
                    pass
                break
        
        return metadata
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get comprehensive file information"""
        try:
            stat = file_path.stat()
            
            # Get file type using mimetypes
            try:
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if mime_type:
                    file_type = mime_type
                elif file_path.suffix.lower() == '.html':
                    file_type = 'text/html'
                elif file_path.suffix.lower() == '.txt':
                    file_type = 'text/plain'
                elif file_path.suffix.lower() == '.pdf':
                    file_type = 'application/pdf'
                elif file_path.suffix.lower() == '.md':
                    file_type = 'text/plain'
                else:
                    file_type = "unknown"
            except:
                file_type = "unknown"
            
            # Calculate file hash
            file_hash = self.calculate_file_hash(file_path)
            
            return {
                'file_name': file_path.name,
                'file_path': str(file_path),
                'file_size': stat.st_size,
                'file_hash': file_hash,
                'file_type': file_type,
                'created_at': datetime.fromtimestamp(stat.st_ctime),
                'modified_at': datetime.fromtimestamp(stat.st_mtime),
                'extension': file_path.suffix.lower()
            }
        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return {}
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    def read_file_content(self, file_path: Path, max_size_mb: int = 50) -> Optional[str]:
        """Read file content with size limit"""
        try:
            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > max_size_mb:
                logger.warning(f"File too large: {file_path} ({file_size_mb:.1f}MB)")
                return None
            
            # Read content based on file type
            if file_path.suffix.lower() in {'.html', '.txt', '.md'}:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_path.suffix.lower() == '.pdf':
                # For PDF files, return placeholder for now
                return f"[PDF_CONTENT_PLACEHOLDER: {file_path.name}]"
            else:
                logger.warning(f"Unsupported file type: {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None
    
    def is_supported_file(self, file_path: Path) -> bool:
        """Check if file is supported for processing"""
        return (file_path.suffix.lower() in self.supported_extensions and 
                file_path.is_file() and 
                file_path.stat().st_size > 0)
    
    def safe_move_file(self, source: Path, destination: Path) -> bool:
        """Safely move file with conflict resolution"""
        try:
            # Create destination directory if it doesn't exist
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle filename conflicts
            if destination.exists():
                counter = 1
                base_name = destination.stem
                extension = destination.suffix
                while destination.exists():
                    new_name = f"{base_name}_{counter}{extension}"
                    destination = destination.parent / new_name
                    counter += 1
            
            # Move file
            shutil.move(str(source), str(destination))
            logger.info(f"Moved file: {source} -> {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file {source} to {destination}: {e}")
            return False
    
    def scan_directory(self, directory: Path) -> List[Dict[str, Any]]:
        """Scan directory for supported files"""
        files_info = []
        
        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return files_info
        
        for file_path in directory.iterdir():
            if self.is_supported_file(file_path):
                file_info = self.get_file_info(file_path)
                if file_info:
                    files_info.append(file_info)
        
        logger.info(f"Found {len(files_info)} supported files in {directory}")
        return files_info
    
    def validate_file_integrity(self, file_path: Path) -> bool:
        """Validate file integrity and accessibility"""
        try:
            # Check if file exists and is readable
            if not file_path.exists() or not file_path.is_file():
                return False
            
            # Check if file is readable
            with open(file_path, 'rb') as f:
                f.read(1)  # Try to read first byte
            
            return True
            
        except Exception as e:
            logger.error(f"File integrity check failed for {file_path}: {e}")
            return False
    
    def log_import_event(self, filename: str, event_type: str, reason: str, 
                        file_hash: str = "", broker: str = None, account: str = None, 
                        period: str = None, filename_period: str = None, 
                        parsed_period: str = None):
        """
        Log import events to diagnostics/import_duplicates.log
        
        Args:
            filename: Name of the file being processed
            event_type: 'imported', 'exact_duplicate', 'semantic_duplicate', 'no_parser_found', 
                       'parse_failed', 'period_mismatch', 'error'
            reason: Human-readable explanation
            file_hash: SHA-256 hash of the file (optional)
            broker: Broker name (optional)
            account: Account number (optional)
            period: Period in YYYY-MM format (optional)
            filename_period: Period extracted from filename (for period_mismatch)
            parsed_period: Period extracted from parsed data (for period_mismatch)
        """
        try:
            from core.config import Config
            from datetime import datetime
            
            # Create diagnostics directory if it doesn't exist
            diagnostics_dir = Config.PROJECT_ROOT / 'diagnostics'
            diagnostics_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = diagnostics_dir / 'import_duplicates.log'
            
            # Format timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Build log entry
            log_parts = [f"[{timestamp}] {filename} — {reason}"]
            
            # Add metadata
            if file_hash:
                log_parts.append(f"hash={file_hash[:16]}...")
            if broker:
                log_parts.append(f"broker={broker}")
            if account:
                log_parts.append(f"account={account}")
            if period:
                log_parts.append(f"period={period}")
            
            # Special handling for period_mismatch
            if event_type == 'period_mismatch' and filename_period and parsed_period:
                log_parts.append(f"filename_period={filename_period}")
                log_parts.append(f"parsed_period={parsed_period}")
            
            log_entry = " | ".join(log_parts) + "\n"
            
            # Write to log file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.info(f"Logged import event: {event_type} for {filename}")
            
        except Exception as e:
            logger.error(f"Failed to log import event: {e}")