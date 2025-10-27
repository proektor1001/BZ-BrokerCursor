"""
Parser registry and factory for multi-broker support
Provides centralized access to broker-specific parsers
"""

from typing import Dict, Type, List
from .base_parser import BaseHtmlParser
from .sber_html_parser import SberHtmlParser

# Registry of available parsers by broker name
PARSER_REGISTRY: Dict[str, Type[BaseHtmlParser]] = {
    'sber': SberHtmlParser,
    # Future parsers can be added here:
    # 'tinkoff': TinkoffHtmlParser,
    # 'vtb': VtbHtmlParser,
    # 'gazprombank': GazprombankHtmlParser,
    # 'alpha': AlphaHtmlParser,
}

def get_parser(broker: str) -> BaseHtmlParser:
    """
    Get parser instance for specified broker
    
    Args:
        broker: Broker name (e.g., 'sber', 'tinkoff')
        
    Returns:
        BaseHtmlParser: Parser instance for the broker
        
    Raises:
        ValueError: If no parser is registered for the broker
    """
    parser_class = PARSER_REGISTRY.get(broker)
    if parser_class:
        return parser_class()
    else:
        raise ValueError(f"No parser registered for broker: {broker}")

def list_supported_brokers() -> List[str]:
    """
    Get list of supported broker names
    
    Returns:
        List[str]: List of broker names with registered parsers
    """
    return list(PARSER_REGISTRY.keys())

def is_broker_supported(broker: str) -> bool:
    """
    Check if broker has a registered parser
    
    Args:
        broker: Broker name to check
        
    Returns:
        bool: True if parser is available, False otherwise
    """
    return broker in PARSER_REGISTRY

def register_parser(broker: str, parser_class: Type[BaseHtmlParser]) -> None:
    """
    Register a new parser for a broker
    
    Args:
        broker: Broker name
        parser_class: Parser class that inherits from BaseHtmlParser
    """
    PARSER_REGISTRY[broker] = parser_class

def get_parser_info(broker: str) -> Dict[str, str]:
    """
    Get information about a parser
    
    Args:
        broker: Broker name
        
    Returns:
        Dict[str, str]: Parser information (class, version, etc.)
    """
    if not is_broker_supported(broker):
        return {'error': f'No parser registered for broker: {broker}'}
    
    try:
        parser = get_parser(broker)
        return {
            'broker': broker,
            'class_name': parser.__class__.__name__,
            'version': parser.get_parser_version(),
            'supported_broker': parser.get_supported_broker()
        }
    except Exception as e:
        return {'error': f'Failed to get parser info: {e}'}

__all__ = ['BaseHtmlParser', 'SberHtmlParser', 'get_parser', 'list_supported_brokers', 'is_broker_supported', 'register_parser', 'get_parser_info', 'PARSER_REGISTRY']
