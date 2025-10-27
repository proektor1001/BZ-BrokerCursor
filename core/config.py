"""
Configuration management for BrokerCursor
Loads settings from environment variables with sensible defaults
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # Database settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'brokercursor')
    DB_USER = os.getenv('DB_USER', 'brokercursor_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # Application settings
    APP_ENV = os.getenv('APP_ENV', 'development')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # File paths (relative to project root)
    PROJECT_ROOT = Path(__file__).parent.parent
    INBOX_PATH = PROJECT_ROOT / os.getenv('INBOX_PATH', 'modules/broker-reports/inbox')
    ARCHIVE_PATH = PROJECT_ROOT / os.getenv('ARCHIVE_PATH', 'modules/broker-reports/archive')
    ARCHIVE_IMPORTED_PATH = ARCHIVE_PATH / 'imported'
    ARCHIVE_EXACT_DUPLICATES_PATH = ARCHIVE_PATH / 'exact_duplicates'
    ARCHIVE_LOGICAL_DUPLICATES_PATH = ARCHIVE_PATH / 'logical_duplicates'
    ARCHIVE_UNRECOGNIZED_PATH = ARCHIVE_PATH / 'unrecognized'
    PARSED_PATH = PROJECT_ROOT / os.getenv('PARSED_PATH', 'modules/broker-reports/parsed')
    
    # Processing settings
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '50'))
    SUPPORTED_EXTENSIONS = os.getenv('SUPPORTED_EXTENSIONS', '.html,.txt,.pdf,.md').split(',')
    
    @classmethod
    def get_db_connection_string(cls):
        """Get PostgreSQL connection string"""
        return f"host={cls.DB_HOST} port={cls.DB_PORT} dbname={cls.DB_NAME} user={cls.DB_USER} password={cls.DB_PASSWORD}"
    
    @classmethod
    def ensure_archive_directories(cls):
        """Ensure all archive subdirectories exist"""
        directories = [
            cls.ARCHIVE_PATH,
            cls.ARCHIVE_IMPORTED_PATH,
            cls.ARCHIVE_EXACT_DUPLICATES_PATH,
            cls.ARCHIVE_LOGICAL_DUPLICATES_PATH,
            cls.ARCHIVE_UNRECOGNIZED_PATH
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate_config(cls):
        """Validate configuration and return any issues"""
        issues = []
        
        if not cls.DB_PASSWORD:
            issues.append("DB_PASSWORD is required")
        
        if not cls.INBOX_PATH.exists():
            issues.append(f"INBOX_PATH does not exist: {cls.INBOX_PATH}")
        
        if not cls.ARCHIVE_PATH.exists():
            issues.append(f"ARCHIVE_PATH does not exist: {cls.ARCHIVE_PATH}")
        
        return issues
