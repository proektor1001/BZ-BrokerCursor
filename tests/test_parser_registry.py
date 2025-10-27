#!/usr/bin/env python3
"""
Unit tests for parser registry and factory functions
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.parsers import (
    get_parser, 
    list_supported_brokers, 
    is_broker_supported, 
    register_parser, 
    get_parser_info,
    PARSER_REGISTRY
)
from core.parsers.base_parser import BaseHtmlParser

class TestParserRegistry(unittest.TestCase):
    """Test cases for parser registry and factory functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock parser class for testing
        class MockParser(BaseHtmlParser):
            def parse(self, html_content: str):
                return {"test": "data"}
            
            def get_parser_version(self):
                return "1.0"
        
        self.mock_parser_class = MockParser
    
    def test_list_supported_brokers(self):
        """Test listing supported brokers"""
        brokers = list_supported_brokers()
        self.assertIsInstance(brokers, list)
        self.assertIn('sber', brokers)
    
    def test_is_broker_supported(self):
        """Test checking if broker is supported"""
        self.assertTrue(is_broker_supported('sber'))
        self.assertFalse(is_broker_supported('nonexistent'))
        self.assertFalse(is_broker_supported(''))
    
    def test_get_parser_success(self):
        """Test getting parser for supported broker"""
        parser = get_parser('sber')
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, BaseHtmlParser)
    
    def test_get_parser_unsupported(self):
        """Test getting parser for unsupported broker"""
        with self.assertRaises(ValueError) as context:
            get_parser('nonexistent')
        
        self.assertIn("No parser registered for broker: nonexistent", str(context.exception))
    
    def test_get_parser_empty_broker(self):
        """Test getting parser for empty broker name"""
        with self.assertRaises(ValueError) as context:
            get_parser('')
        
        self.assertIn("No parser registered for broker:", str(context.exception))
    
    def test_register_parser(self):
        """Test registering a new parser"""
        # Register a new parser
        register_parser('test_broker', self.mock_parser_class)
        
        # Check if it's now supported
        self.assertTrue(is_broker_supported('test_broker'))
        
        # Get the parser
        parser = get_parser('test_broker')
        self.assertIsInstance(parser, self.mock_parser_class)
        
        # Clean up
        if 'test_broker' in PARSER_REGISTRY:
            del PARSER_REGISTRY['test_broker']
    
    def test_get_parser_info_success(self):
        """Test getting parser info for supported broker"""
        info = get_parser_info('sber')
        
        self.assertIsInstance(info, dict)
        self.assertEqual(info['broker'], 'sber')
        self.assertIn('class_name', info)
        self.assertIn('version', info)
        self.assertIn('supported_broker', info)
        self.assertNotIn('error', info)
    
    def test_get_parser_info_unsupported(self):
        """Test getting parser info for unsupported broker"""
        info = get_parser_info('nonexistent')
        
        self.assertIsInstance(info, dict)
        self.assertIn('error', info)
        self.assertIn("No parser registered for broker: nonexistent", info['error'])
    
    def test_parser_registry_structure(self):
        """Test parser registry structure"""
        self.assertIsInstance(PARSER_REGISTRY, dict)
        self.assertIn('sber', PARSER_REGISTRY)
        
        # Check that all values are parser classes
        for broker, parser_class in PARSER_REGISTRY.items():
            self.assertTrue(issubclass(parser_class, BaseHtmlParser))
    
    def test_parser_instantiation(self):
        """Test that parsers can be instantiated correctly"""
        for broker in list_supported_brokers():
            parser = get_parser(broker)
            self.assertIsInstance(parser, BaseHtmlParser)
            self.assertEqual(parser.get_supported_broker(), broker)
    
    def test_parser_version_consistency(self):
        """Test that parser versions are consistent"""
        for broker in list_supported_brokers():
            parser = get_parser(broker)
            version = parser.get_parser_version()
            self.assertIsInstance(version, str)
            self.assertGreater(len(version), 0)
    
    def test_registry_immutability(self):
        """Test that registry operations don't break existing parsers"""
        original_brokers = set(list_supported_brokers())
        
        # Try to register a parser (should not affect existing ones)
        register_parser('temp_broker', self.mock_parser_class)
        
        # Check that original brokers are still there
        current_brokers = set(list_supported_brokers())
        self.assertTrue(original_brokers.issubset(current_brokers))
        
        # Clean up
        if 'temp_broker' in PARSER_REGISTRY:
            del PARSER_REGISTRY['temp_broker']
    
    def test_multiple_parser_instances(self):
        """Test that multiple parser instances can be created"""
        parser1 = get_parser('sber')
        parser2 = get_parser('sber')
        
        # Should be different instances
        self.assertIsNot(parser1, parser2)
        
        # But should be same class
        self.assertEqual(parser1.__class__, parser2.__class__)
    
    def test_parser_info_completeness(self):
        """Test that parser info contains all required fields"""
        for broker in list_supported_brokers():
            info = get_parser_info(broker)
            
            required_fields = ['broker', 'class_name', 'version', 'supported_broker']
            for field in required_fields:
                self.assertIn(field, info, f"Missing field '{field}' for broker '{broker}'")

if __name__ == '__main__':
    unittest.main()
