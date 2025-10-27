#!/usr/bin/env python3
"""
Unit tests for BaseHtmlParser class
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.parsers.base_parser import BaseHtmlParser

class TestBaseHtmlParser(unittest.TestCase):
    """Test cases for BaseHtmlParser abstract class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a concrete implementation for testing
        class TestParser(BaseHtmlParser):
            def parse(self, html_content: str):
                return {"test": "data"}
            
            def get_parser_version(self):
                return "1.0"
        
        self.parser = TestParser()
    
    def test_initialization(self):
        """Test parser initialization"""
        self.assertIsNone(self.parser.soup)
        self.assertEqual(self.parser.parsed_fields, {})
        self.assertEqual(self.parser.field_log, [])
    
    def test_load_html_success(self):
        """Test successful HTML loading"""
        html_content = "<html><body>Test</body></html>"
        result = self.parser.load_html(html_content)
        
        self.assertTrue(result)
        self.assertIsNotNone(self.parser.soup)
        self.assertEqual(self.parser.soup.get_text().strip(), "Test")
    
    def test_load_html_failure(self):
        """Test HTML loading failure"""
        # Test with None (should fail)
        result = self.parser.load_html(None)
        self.assertFalse(result)
    
    def test_log_field(self):
        """Test field logging functionality"""
        self.parser.log_field("test_field", "test_value", "test_source")
        
        self.assertEqual(len(self.parser.field_log), 1)
        self.assertEqual(self.parser.parsed_fields["test_field"], "test_value")
        
        log_entry = self.parser.field_log[0]
        self.assertEqual(log_entry["field"], "test_field")
        self.assertEqual(log_entry["value"], "test_value")
        self.assertEqual(log_entry["source"], "test_source")
        self.assertFalse(log_entry["is_null"])
    
    def test_log_field_null(self):
        """Test logging null field"""
        self.parser.log_field("null_field", None, "test_source")
        
        log_entry = self.parser.field_log[0]
        self.assertTrue(log_entry["is_null"])
    
    def test_get_parsed_fields(self):
        """Test getting parsed fields"""
        self.parser.log_field("field1", "value1", "source1")
        self.parser.log_field("field2", "value2", "source2")
        
        fields = self.parser.get_parsed_fields()
        self.assertEqual(fields["field1"], "value1")
        self.assertEqual(fields["field2"], "value2")
        self.assertEqual(len(fields), 2)
    
    def test_get_field_log(self):
        """Test getting field log"""
        self.parser.log_field("field1", "value1", "source1")
        log = self.parser.get_field_log()
        
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["field"], "field1")
    
    def test_clear_logs(self):
        """Test clearing logs"""
        self.parser.log_field("field1", "value1", "source1")
        self.parser.clear_logs()
        
        self.assertEqual(len(self.parser.field_log), 0)
        self.assertEqual(len(self.parser.parsed_fields), 0)
    
    def test_validate_output_success(self):
        """Test successful output validation"""
        parsed_data = {
            "parser_version": "1.0",
            "balance_ending": 1000.0,
            "account_open_date": "2023-01-01",
            "trade_count": 5,
            "instruments": [],
            "financial_result": 100.0
        }
        
        result = self.parser.validate_output(parsed_data)
        self.assertTrue(result)
    
    def test_validate_output_missing_fields(self):
        """Test validation with missing fields"""
        parsed_data = {
            "parser_version": "1.0"
        }
        
        result = self.parser.validate_output(parsed_data)
        self.assertTrue(result)  # Should not fail, just warn
    
    def test_validate_output_invalid_type(self):
        """Test validation with invalid data type"""
        result = self.parser.validate_output("invalid")
        self.assertFalse(result)
    
    def test_get_required_fields(self):
        """Test getting required fields"""
        fields = self.parser.get_required_fields()
        self.assertIsInstance(fields, list)
        self.assertIn("parser_version", fields)
        self.assertIn("balance_ending", fields)
    
    def test_set_supported_broker(self):
        """Test setting supported broker"""
        self.parser.set_supported_broker("test_broker")
        self.assertEqual(self.parser.get_supported_broker(), "test_broker")
    
    def test_get_supported_broker_default(self):
        """Test default supported broker"""
        self.assertEqual(self.parser.get_supported_broker(), "unknown")
    
    def test_str_representation(self):
        """Test string representation"""
        self.parser.set_supported_broker("test_broker")
        str_repr = str(self.parser)
        self.assertIn("TestParser", str_repr)
        self.assertIn("test_broker", str_repr)
    
    def test_repr_representation(self):
        """Test detailed string representation"""
        self.parser.set_supported_broker("test_broker")
        repr_str = repr(self.parser)
        self.assertIn("TestParser", repr_str)
        self.assertIn("test_broker", repr_str)
        self.assertIn("fields=0", repr_str)

if __name__ == '__main__':
    unittest.main()
