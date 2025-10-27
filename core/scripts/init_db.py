#!/usr/bin/env python3
"""
Database initialization script for BrokerCursor
Creates tables, indexes, and verifies database setup
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database.connection import db_connection
from core.config import Config
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_schema_file():
    """Read SQL schema from file"""
    schema_path = project_root / "core" / "database" / "schema.sql"
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Schema file not found: {schema_path}")
        return None
    except Exception as e:
        logger.error(f"Failed to read schema file: {e}")
        return None

def initialize_database():
    """Initialize database with schema"""
    logger.info("Starting database initialization...")
    
    # Test connection first
    logger.info("Testing database connection...")
    test_result = db_connection.test_connection()
    
    if test_result["status"] != "success":
        logger.error(f"Database connection failed: {test_result}")
        return False
    
    logger.info(f"Connected to: {test_result['database']}@{test_result['host']}:{test_result['port']}")
    logger.info(f"PostgreSQL version: {test_result['version']}")
    
    # Read and execute schema
    schema_sql = read_schema_file()
    if not schema_sql:
        return False
    
    try:
        # Connect to database
        if not db_connection.connect():
            logger.error("Failed to connect to database")
            return False
        
        # Execute schema
        logger.info("Executing database schema...")
        with db_connection.get_cursor() as cursor:
            cursor.execute(schema_sql)
            db_connection.connection.commit()
        
        logger.info("Database schema executed successfully")
        
        # Verify tables were created
        tables_result = db_connection.execute_query("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN ('broker_reports', 'import_log')
            ORDER BY table_name
        """)
        
        created_tables = [row['table_name'] for row in tables_result]
        logger.info(f"Created tables: {', '.join(created_tables)}")
        
        # Check indexes
        indexes_result = db_connection.execute_query("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename IN ('broker_reports', 'import_log')
            ORDER BY indexname
        """)
        
        created_indexes = [row['indexname'] for row in indexes_result]
        logger.info(f"Created indexes: {', '.join(created_indexes)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False
    finally:
        db_connection.disconnect()

def show_database_status():
    """Show current database status and statistics"""
    logger.info("Checking database status...")
    
    try:
        if not db_connection.connect():
            logger.error("Failed to connect to database")
            return
        
        # Get table counts
        tables_info = db_connection.execute_query("""
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_rows
            FROM pg_stat_user_tables 
            WHERE tablename IN ('broker_reports', 'import_log')
            ORDER BY tablename
        """)
        
        logger.info("Database Statistics:")
        for table in tables_info:
            logger.info(f"  {table['tablename']}: {table['live_rows']} rows")
        
        # Get recent activity
        recent_imports = db_connection.execute_query("""
            SELECT COUNT(*) as count 
            FROM broker_reports 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        
        if recent_imports:
            logger.info(f"  Recent imports (24h): {recent_imports[0]['count']}")
        
    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
    finally:
        db_connection.disconnect()

def main():
    """Main initialization function"""
    print("BrokerCursor Database Initialization")
    print("=" * 40)
    
    # Check configuration
    config = Config()
    issues = config.validate_config()
    
    if issues:
        logger.error("Configuration issues found:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    
    # Initialize database
    success = initialize_database()
    
    if success:
        logger.info("Database initialization completed successfully!")
        show_database_status()
    else:
        logger.error("Database initialization failed!")
        return False
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
