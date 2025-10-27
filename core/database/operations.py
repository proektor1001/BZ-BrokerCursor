"""
Database operations for broker reports
CRUD operations and business logic for PostgreSQL + JSONB storage
"""

import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging
from core.database.connection import db_connection

logger = logging.getLogger(__name__)

class BrokerReportOperations:
    """Operations for managing broker reports in database"""
    
    def __init__(self):
        self.db = db_connection
    
    def insert_report(self, 
                     broker: str,
                     period: str,
                     file_name: str,
                     file_path: str = None,
                     html_content: str = None,
                     raw_content: str = None,
                     account: str = None,
                     client_name: str = None,
                     report_date: datetime = None,
                     metadata: Dict = None,
                     file_hash: str = None,
                     file_size: int = None) -> Optional[int]:
        """Insert new broker report and return report ID"""
        try:
            # Calculate file hash if not provided (fallback for legacy calls)
            content = html_content or raw_content or ""
            if not file_hash:
                file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Prepare metadata
            metadata = metadata or {}
            if file_path:
                metadata['file_path'] = file_path
            if content:
                metadata['content_length'] = len(content)
            if file_size is not None:
                metadata['file_size'] = file_size
            
            query = """
                INSERT INTO broker_reports 
                (broker, account, period, report_date, client_name, file_name, file_path, 
                 file_hash, html_content, raw_content, metadata, processing_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'raw')
                RETURNING id
            """
            
            # Serialize metadata safely
            try:
                serialized_metadata = json.dumps(metadata, default=str)
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize metadata, using empty dict: {e}")
                serialized_metadata = json.dumps({})
            
            params = (
                broker, account, period, report_date, client_name, file_name, file_path,
                file_hash, html_content, raw_content, serialized_metadata
            )
            
            with self.db.get_cursor() as cursor:
                cursor.execute(query, params)
                self.db.connection.commit()
                report_id = cursor.fetchone()['id']
                logger.info(f"Inserted report {report_id}: {broker}/{period}/{file_name}")
                return report_id
                
        except Exception as e:
            logger.error(f"Failed to insert report: {e}")
            return None
    
    def get_report(self, report_id: int) -> Optional[Dict]:
        """Get report by ID"""
        try:
            query = "SELECT * FROM broker_reports WHERE id = %s"
            result = self.db.execute_query(query, (report_id,))
            return dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"Failed to get report {report_id}: {e}")
            return None
    
    def get_report_by_hash(self, file_hash: str) -> Optional[Dict]:
        """Get report by file hash"""
        try:
            query = "SELECT * FROM broker_reports WHERE file_hash = %s"
            result = self.db.execute_query(query, (file_hash,))
            return dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"Failed to get report by hash: {e}")
            return None

    def get_report_by_triple(self, broker: str, account: Optional[str], period: str) -> Optional[Dict]:
        """Get report by unique triple broker+account+period"""
        try:
            query = """
                SELECT * FROM broker_reports
                WHERE broker = %s AND account IS NOT DISTINCT FROM %s AND period = %s
            """
            result = self.db.execute_query(query, (broker, account, period))
            return dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"Failed to get report by triple: {e}")
            return None
    
    def list_reports(self, 
                     broker: str = None,
                     period: str = None,
                     status: str = None,
                     account: str = None,
                     search_account: str = None,
                     limit: int = 100,
                     offset: int = 0) -> List[Dict]:
        """List reports with optional filtering"""
        try:
            conditions = []
            params = []
            
            if broker:
                conditions.append("broker = %s")
                params.append(broker)
            
            if period:
                conditions.append("period = %s")
                params.append(period)
            
            if status:
                conditions.append("processing_status = %s")
                params.append(status)
            
            if account:
                conditions.append("account = %s")
                params.append(account)
            
            if search_account:
                conditions.append("account ILIKE %s")
                params.append(f"%{search_account}%")
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            params.extend([limit, offset])
            
            query = f"""
                SELECT id, broker, account, period, report_date, client_name, 
                       file_name, processing_status, created_at, updated_at
                FROM broker_reports 
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            
            result = self.db.execute_query(query, params)
            return [dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"Failed to list reports: {e}")
            return []
    
    def update_report_status(self, report_id: int, status: str, 
                           parsed_data: Dict = None, error_log: str = None, 
                           parser_version: str = None) -> bool:
        """Update report processing status"""
        try:
            query = """
                UPDATE broker_reports 
                SET processing_status = %s, updated_at = NOW()
            """
            params = [status]
            
            if parsed_data:
                query += ", parsed_data = %s"
                params.append(json.dumps(parsed_data))
            
            if error_log:
                query += ", error_log = %s"
                params.append(error_log)
            
            if parser_version:
                query += ", parser_version = %s"
                params.append(parser_version)
            
            if status == 'parsed':
                query += ", processed_at = NOW()"
            
            query += " WHERE id = %s"
            params.append(report_id)
            
            affected = self.db.execute_update(query, tuple(params))
            logger.info(f"Updated report {report_id} status to {status}")
            return affected > 0
            
        except Exception as e:
            logger.error(f"Failed to update report {report_id}: {e}")
            return False
    
    def delete_report(self, report_id: int) -> bool:
        """Delete report by ID"""
        try:
            query = "DELETE FROM broker_reports WHERE id = %s"
            affected = self.db.execute_update(query, (report_id,))
            logger.info(f"Deleted report {report_id}")
            return affected > 0
        except Exception as e:
            logger.error(f"Failed to delete report {report_id}: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            # Total reports
            total_query = "SELECT COUNT(*) as total FROM broker_reports"
            total_result = self.db.execute_query(total_query)
            total_reports = total_result[0]['total'] if total_result else 0
            
            # Reports by broker
            broker_query = """
                SELECT broker, COUNT(*) as count 
                FROM broker_reports 
                GROUP BY broker 
                ORDER BY count DESC
            """
            broker_result = self.db.execute_query(broker_query)
            by_broker = {row['broker']: row['count'] for row in broker_result}
            
            # Reports by status
            status_query = """
                SELECT processing_status, COUNT(*) as count 
                FROM broker_reports 
                GROUP BY processing_status
            """
            status_result = self.db.execute_query(status_query)
            by_status = {row['processing_status']: row['count'] for row in status_result}
            
            # Recent imports
            recent_query = """
                SELECT COUNT(*) as count 
                FROM broker_reports 
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """
            recent_result = self.db.execute_query(recent_query)
            recent_imports = recent_result[0]['count'] if recent_result else 0
            
            return {
                "total_reports": total_reports,
                "by_broker": by_broker,
                "by_status": by_status,
                "recent_imports_24h": recent_imports
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def log_import_operation(self, operation_type: str, broker: str = None,
                           files_processed: int = 0, files_success: int = 0,
                           files_failed: int = 0, error_summary: str = None) -> int:
        """Log import operation"""
        try:
            query = """
                INSERT INTO import_log 
                (operation_type, broker, files_processed, files_success, files_failed, error_summary, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """
            
            with self.db.get_cursor() as cursor:
                cursor.execute(query, (operation_type, broker, files_processed, files_success, files_failed, error_summary))
                self.db.connection.commit()
                log_id = cursor.fetchone()['id']
                logger.info(f"Logged import operation {log_id}: {operation_type}")
                return log_id
                
        except Exception as e:
            logger.error(f"Failed to log import operation: {e}")
            return 0

    def log_import_file(self, status: str, broker: str = None, account: str = None,
                        period: str = None, file_name: str = None, file_hash: str = None,
                        error_summary: str = None) -> int:
        """Log per-file import status into import_log"""
        try:
            query = """
                INSERT INTO import_log
                (operation_type, broker, account, period, file_name, file_hash, status,
                 files_processed, files_success, files_failed, error_summary, completed_at)
                VALUES ('import', %s, %s, %s, %s, %s, %s,
                        1, CASE WHEN %s = 'success' THEN 1 ELSE 0 END,
                        CASE WHEN %s IN ('failure','duplicate_detected','collision_mismatch') THEN 1 ELSE 0 END,
                        %s, NOW())
                RETURNING id
            """
            params = (broker, account, period, file_name, file_hash, status, status, status, error_summary)
            with self.db.get_cursor() as cursor:
                cursor.execute(query, params)
                self.db.connection.commit()
                log_id = cursor.fetchone()['id']
                return log_id
        except Exception as e:
            logger.error(f"Failed to log import file: {e}")
            return 0
    
    def count_reports(self) -> int:
        """Count total reports in database"""
        try:
            query = "SELECT COUNT(*) as count FROM broker_reports"
            result = self.db.execute_query(query)
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"Failed to count reports: {e}")
            return 0
    
    def count_reports_with_hash(self) -> int:
        """Count reports that have file_hash"""
        try:
            query = "SELECT COUNT(*) as count FROM broker_reports WHERE file_hash IS NOT NULL"
            result = self.db.execute_query(query)
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"Failed to count reports with hash: {e}")
            return 0
    
    def count_reports_by_status(self, status: str) -> int:
        """Count reports by processing status"""
        try:
            query = "SELECT COUNT(*) as count FROM broker_reports WHERE processing_status = %s"
            result = self.db.execute_query(query, (status,))
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"Failed to count reports by status: {e}")
            return 0
    
    def count_reports_with_parsed_data(self) -> int:
        """Count reports that have parsed_data"""
        try:
            query = "SELECT COUNT(*) as count FROM broker_reports WHERE parsed_data IS NOT NULL"
            result = self.db.execute_query(query)
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"Failed to count reports with parsed data: {e}")
            return 0
    
    def count_import_log_entries(self) -> int:
        """Count import log entries"""
        try:
            query = "SELECT COUNT(*) as count FROM import_log"
            result = self.db.execute_query(query)
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"Failed to count import log entries: {e}")
            return 0
    
    def get_report_by_filename(self, filename: str) -> Optional[Dict]:
        """Get report by filename"""
        try:
            query = "SELECT * FROM broker_reports WHERE file_name = %s"
            result = self.db.execute_query(query, (filename,))
            return dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"Failed to get report by filename: {e}")
            return None
    
    def execute_raw_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute raw SQL query"""
        try:
            result = self.db.execute_query(query, params)
            return [dict(row) for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to execute raw query: {e}")
            return []
    
    def delete_report(self, report_id: int) -> bool:
        """Delete report by ID"""
        try:
            query = "DELETE FROM broker_reports WHERE id = %s"
            with self.db.get_cursor() as cursor:
                cursor.execute(query, (report_id,))
                self.db.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete report: {e}")
            return False
    
    def update_report_parsed_data(self, report_id: int, parsed_data: Dict, status: str = 'parsed') -> bool:
        """Update report's parsed data and status"""
        try:
            query = """
                UPDATE broker_reports 
                SET parsed_data = %s, processing_status = %s, updated_at = NOW(), processed_at = NOW()
                WHERE id = %s
            """
            # Serialize parsed_data safely
            try:
                serialized_parsed_data = json.dumps(parsed_data, default=str)
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize parsed_data, using empty dict: {e}")
                serialized_parsed_data = json.dumps({})
            
            with self.db.get_cursor() as cursor:
                cursor.execute(query, (serialized_parsed_data, status, report_id))
                self.db.connection.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update report parsed data: {e}")
            return False