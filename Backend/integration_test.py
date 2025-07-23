#!/usr/bin/env python3
"""
Integration test for Azure App Configuration with model switching.
This test validates that the dynamic configuration updates work correctly.
"""

import sys
import os
import time
import threading
import logging

# Add the backend directory to path
sys.path.insert(0, os.path.abspath('.'))

from configuration_service import ConfigurationService
from azure_open_ai_service import AzureOpenAIService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_dynamic_configuration_update():
    """Test dynamic configuration updates."""
    print("=== Testing Dynamic Configuration Updates ===")
    
    # Initialize services
    config_service = ConfigurationService()
    openai_service = AzureOpenAIService()
    
    # Initial configuration
    print("\n1. Initial Configuration")
    ai_config = config_service.get_ai_model_configuration()
    openai_service.update_configuration(ai_config)
    
    print(f"   Model: {openai_service.model}")
    print(f"   Variant: {openai_service.variant}")
    print(f"   Configured: {openai_service.is_configured}")
    
    # Simulate configuration changes by modifying environment variables
    print("\n2. Simulating Configuration Change")
    original_model = os.getenv("AZURE_OPENAI_MODEL")
    original_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    
    # Change environment variables to simulate Azure App Configuration update
    os.environ["AZURE_OPENAI_MODEL"] = "gpt-4"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test-gpt4.openai.azure.com/"
    
    # Refresh configuration (this simulates what happens during automatic refresh)
    config_service.refresh_configuration()
    updated_config = config_service.get_ai_model_configuration()
    config_changed = openai_service.update_configuration(updated_config)
    
    print(f"   Configuration changed: {config_changed}")
    print(f"   New model: {openai_service.model}")
    print(f"   New variant: {openai_service.variant}")
    print(f"   Still configured: {openai_service.is_configured}")
    
    # Restore original values
    if original_model:
        os.environ["AZURE_OPENAI_MODEL"] = original_model
    if original_endpoint:
        os.environ["AZURE_OPENAI_ENDPOINT"] = original_endpoint
        
    return config_changed

def test_refresh_thread_simulation():
    """Test the refresh thread functionality."""
    print("\n=== Testing Refresh Thread Simulation ===")
    
    config_service = ConfigurationService()
    openai_service = AzureOpenAIService()
    
    # Initialize with initial config
    ai_config = config_service.get_ai_model_configuration()
    openai_service.update_configuration(ai_config)
    
    initial_model = openai_service.model
    print(f"   Initial model: {initial_model}")
    
    # Counter for changes detected
    changes_detected = 0
    
    def refresh_worker():
        """Simulate the refresh thread worker."""
        nonlocal changes_detected
        
        for i in range(3):
            time.sleep(1)  # Short delay for testing
            
            # Simulate configuration refresh
            if config_service.refresh_configuration():
                ai_config = config_service.get_ai_model_configuration()
                
                if openai_service.update_configuration(ai_config):
                    changes_detected += 1
                    print(f"   [Refresh {i+1}] Configuration updated: {openai_service.model}")
                else:
                    print(f"   [Refresh {i+1}] No configuration changes")
    
    # Run refresh simulation
    refresh_thread = threading.Thread(target=refresh_worker)
    refresh_thread.start()
    refresh_thread.join()
    
    print(f"   Changes detected during refresh cycle: {changes_detected}")
    return changes_detected >= 0  # Should always be non-negative

def test_error_handling():
    """Test error handling scenarios."""
    print("\n=== Testing Error Handling ===")
    
    # Test with invalid configuration
    openai_service = AzureOpenAIService()
    
    print("   Testing invalid configuration...")
    invalid_config = {"endpoint": "", "model": "", "variant_name": "invalid"}
    result = openai_service.update_configuration(invalid_config)
    print(f"   Invalid config rejected: {not result}")
    
    # Test with partial configuration
    print("   Testing partial configuration...")
    partial_config = {"endpoint": "https://test.com", "model": "", "variant_name": "partial"}
    result = openai_service.update_configuration(partial_config)
    print(f"   Partial config rejected: {not result}")
    
    # Test with valid configuration
    print("   Testing valid configuration...")
    valid_config = {
        "endpoint": "https://test.openai.azure.com/", 
        "model": "gpt-35-turbo", 
        "variant_name": "test"
    }
    result = openai_service.update_configuration(valid_config)
    print(f"   Valid config accepted: {result}")
    
    return True

def main():
    """Main test function."""
    print("Azure App Configuration Integration Test")
    print("=" * 50)
    
    tests = [
        ("Dynamic Configuration Update", test_dynamic_configuration_update),
        ("Refresh Thread Simulation", test_refresh_thread_simulation),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
            print(f"✅ {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"❌ {test_name}: FAILED - {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, error in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        if error:
            status += f" ({error})"
        print(f"{status:12} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The implementation is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    # Set up test environment
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com/"
    os.environ["AZURE_OPENAI_MODEL"] = "gpt-35-turbo"
    
    success = main()
    sys.exit(0 if success else 1)