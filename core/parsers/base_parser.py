"""
Base HTML parser class for broker reports
Provides common functionality for all broker-specific parsers
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class BaseHtmlParser(ABC):
    """
    Abstract base class for HTML broker report parsers
    
    Provides common functionality:
    - HTML loading and parsing with BeautifulSoup
    - Field validation and logging
    - Error handling patterns
    - Output validation
    """
    
    def __init__(self):
        self.soup = None
        self.parsed_fields = {}
        self.field_log = []
    
    def load_html(self, html_content: str) -> bool:
        """
        Load and parse HTML content using BeautifulSoup
        
        Args:
            html_content: Raw HTML content as string
            
        Returns:
            bool: True if HTML loaded successfully, False otherwise
        """
        try:
            self.soup = BeautifulSoup(html_content, 'html.parser')
            if not self.soup:
                logger.error("Failed to parse HTML content")
                return False
            
            logger.debug(f"HTML loaded successfully, found {len(self.soup.find_all())} elements")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load HTML: {e}")
            return False
    
    def log_field(self, field_name: str, value: Any, source: str = "parser") -> None:
        """
        Log field extraction for debugging and validation
        
        Args:
            field_name: Name of the extracted field
            value: Extracted value
            source: Source of the field (parser, computed, etc.)
        """
        log_entry = {
            'field': field_name,
            'value': value,
            'type': type(value).__name__,
            'source': source,
            'is_null': value is None
        }
        
        self.field_log.append(log_entry)
        self.parsed_fields[field_name] = value
        
        if value is not None:
            logger.debug(f"Extracted {field_name}: {value} ({type(value).__name__})")
        else:
            logger.debug(f"Field {field_name} is null")
    
    def validate_output(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Validate parsed data structure and content
        
        Args:
            parsed_data: Dictionary of parsed data
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            # Check if parsed_data is a dictionary
            if not isinstance(parsed_data, dict):
                logger.error("Parsed data is not a dictionary")
                return False
            
            # Check for required fields (to be overridden by subclasses)
            required_fields = self.get_required_fields()
            missing_fields = []
            
            for field in required_fields:
                if field not in parsed_data:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                # Don't fail validation for missing fields, just warn
            
            # Check for parser version
            if 'parser_version' not in parsed_data:
                logger.warning("No parser_version in parsed data")
            
            # Log validation summary
            total_fields = len(parsed_data)
            non_null_fields = sum(1 for v in parsed_data.values() if v is not None)
            null_fields = total_fields - non_null_fields
            
            logger.info(f"Validation complete: {total_fields} fields, {non_null_fields} non-null, {null_fields} null")
            
            return True
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    def get_required_fields(self) -> List[str]:
        """
        Get list of required fields for this parser
        To be overridden by subclasses
        
        Returns:
            List[str]: List of required field names
        """
        return [
            'parser_version',
            'balance_ending',
            'account_open_date',
            'trade_count',
            'instruments',
            'financial_result'
        ]
    
    def get_field_log(self) -> List[Dict[str, Any]]:
        """
        Get field extraction log
        
        Returns:
            List[Dict]: List of field extraction entries
        """
        return self.field_log.copy()
    
    def get_parsed_fields(self) -> Dict[str, Any]:
        """
        Get dictionary of parsed fields
        
        Returns:
            Dict[str, Any]: Dictionary of field_name -> value
        """
        return self.parsed_fields.copy()
    
    def clear_logs(self) -> None:
        """Clear field logs and parsed fields"""
        self.field_log.clear()
        self.parsed_fields.clear()
    
    @abstractmethod
    def parse(self, html_content: str) -> Dict[str, Any]:
        """
        Parse HTML content and extract structured data
        
        Args:
            html_content: Raw HTML content as string
            
        Returns:
            Dict[str, Any]: Structured parsed data
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        pass
    
    @abstractmethod
    def get_parser_version(self) -> str:
        """
        Get parser version string
        
        Returns:
            str: Parser version (e.g., "2.0", "3.0")
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        pass
    
    def get_supported_broker(self) -> str:
        """
        Get the broker this parser supports
        
        Returns:
            str: Broker name (e.g., "sber", "tinkoff")
        """
        return getattr(self, '_supported_broker', 'unknown')
    
    def set_supported_broker(self, broker: str) -> None:
        """
        Set the broker this parser supports
        
        Args:
            broker: Broker name
        """
        self._supported_broker = broker
    
    def __str__(self) -> str:
        """String representation of parser"""
        return f"{self.__class__.__name__}(broker={self.get_supported_broker()}, version={self.get_parser_version()})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return f"{self.__class__.__name__}(broker={self.get_supported_broker()}, version={self.get_parser_version()}, fields={len(self.parsed_fields)})"
