#!/usr/bin/env python3
"""Simple test script to verify Azure App Configuration integration."""

import os
import sys
import logging

# Add the backend directory to path
sys.path.insert(0, os.path.abspath('.'))

from configuration_service import ConfigurationService
from azure_open_ai_service import AzureOpenAIService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_configuration_service():
    """Test the configuration service."""
    print("=== Testing Configuration Service ===")
    
    config_service = ConfigurationService()
    print(f"Azure App Configuration enabled: {config_service.is_configured}")
    
    ai_config = config_service.get_ai_model_configuration()
    print(f"AI Configuration: {ai_config}")
    
    return config_service, ai_config

def test_openai_service(ai_config):
    """Test the OpenAI service."""
    print("\n=== Testing OpenAI Service ===")
    
    openai_service = AzureOpenAIService()
    print(f"Initial state - configured: {openai_service.is_configured}")
    print(f"Initial state - model: '{openai_service.model}'")
    print(f"Initial state - variant: '{openai_service.variant}'")
    
    # Update configuration
    result = openai_service.update_configuration(ai_config)
    print(f"Configuration update result: {result}")
    print(f"After update - configured: {openai_service.is_configured}")
    print(f"After update - model: '{openai_service.model}'")
    print(f"After update - variant: '{openai_service.variant}'")
    
    return openai_service

def main():
    """Main test function."""
    print("Testing Azure App Configuration Integration")
    print(f"Environment Variables:")
    print(f"  AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT', 'NOT SET')}")
    print(f"  AZURE_OPENAI_MODEL: {os.getenv('AZURE_OPENAI_MODEL', 'NOT SET')}")
    print(f"  AZURE_APP_CONFIGURATION_CONNECTION_STRING: {bool(os.getenv('AZURE_APP_CONFIGURATION_CONNECTION_STRING'))}")
    print()
    
    try:
        config_service, ai_config = test_configuration_service()
        openai_service = test_openai_service(ai_config)
        
        print(f"\n=== Summary ===")
        print(f"Configuration Service enabled: {config_service.is_configured}")
        print(f"OpenAI Service configured: {openai_service.is_configured}")
        print(f"Current model: {openai_service.model}")
        print(f"Current variant: {openai_service.variant}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()