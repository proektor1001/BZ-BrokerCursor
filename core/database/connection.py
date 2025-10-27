"""
Database connection management for BrokerCursor
Handles PostgreSQL connections with proper error handling and connection pooling
"""

import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Optional, Dict, Any
import logging
from core.config import Config

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """PostgreSQL database connection manager"""
    
    def __init__(self):
        self.connection = None
        self.config = Config()
    
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                host=self.config.DB_HOST,
                port=self.config.DB_PORT,
                database=self.config.DB_NAME,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            self.connection.autocommit = False
            logger.info(f"Connected to PostgreSQL: {self.config.DB_NAME}@{self.config.DB_HOST}")
            return True
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def is_connected(self) -> bool:
        """Check if connection is active"""
        if not self.connection:
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except psycopg2.Error:
            return False
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        if not self.connection:
            if not self.connect():
                raise ConnectionError("Failed to establish database connection")
        
        cursor = self.connection.cursor()
        try:
            yield cursor
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute SELECT query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            self.connection.commit()
            return cursor.rowcount
    
    def execute_many(self, query: str, params_list: list) -> int:
        """Execute query with multiple parameter sets"""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            self.connection.commit()
            return cursor.rowcount
    
    def test_connection(self) -> Dict[str, Any]:
        """Test database connection and return status info"""
        try:
            if not self.connect():
                return {"status": "failed", "error": "Connection failed"}
            
            # Test basic query
            result = self.execute_query("SELECT version()")
            version = result[0]['version'] if result else "Unknown"
            
            # Test table existence
            tables_result = self.execute_query("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('broker_reports', 'import_log')
            """)
            existing_tables = [row['table_name'] for row in tables_result]
            
            return {
                "status": "success",
                "version": version,
                "database": self.config.DB_NAME,
                "host": self.config.DB_HOST,
                "port": self.config.DB_PORT,
                "existing_tables": existing_tables
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
        finally:
            self.disconnect()

# Global connection instance
db_connection = DatabaseConnection()
