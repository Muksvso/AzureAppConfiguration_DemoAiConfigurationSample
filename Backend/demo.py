#!/usr/bin/env python3
"""
Demo script showing Azure App Configuration integration for AI model selection.
This script demonstrates how configuration changes are reflected in real-time.
"""

import requests
import time
import json

API_BASE = "http://localhost:5000"

def get_model_info():
    """Get current model configuration."""
    try:
        response = requests.get(f"{API_BASE}/api/chat/model")
        return response.json()
    except Exception as e:
        print(f"Error getting model info: {e}")
        return None

def refresh_config():
    """Manually trigger configuration refresh."""
    try:
        response = requests.post(f"{API_BASE}/api/config/refresh")
        return response.json()
    except Exception as e:
        print(f"Error refreshing config: {e}")
        return None

def send_chat_message(message, history=None):
    """Send a chat message to the AI."""
    try:
        data = {
            "message": message,
            "history": history or []
        }
        response = requests.post(f"{API_BASE}/api/chat", json=data)
        return response.json()
    except Exception as e:
        print(f"Error sending chat message: {e}")
        return None

def main():
    """Main demo function."""
    print("🚀 Azure App Configuration Demo")
    print("=" * 50)
    
    # Check initial configuration
    print("\n📊 Current Configuration:")
    model_info = get_model_info()
    if model_info:
        print(f"  Model: {model_info.get('model', 'N/A')}")
        print(f"  Variant: {model_info.get('variant', 'N/A')}")
        print(f"  Configured: {model_info.get('configured', False)}")
        print(f"  App Config Enabled: {model_info.get('app_config_enabled', False)}")
    else:
        print("  ❌ Could not retrieve configuration")
        return
    
    if not model_info.get('configured'):
        print("\n⚠️  AI service is not configured properly.")
        print("   Please check your Azure OpenAI configuration.")
        return
    
    # Send a test message
    print("\n💬 Sending test message...")
    chat_response = send_chat_message("Hello! What AI model are you?")
    if chat_response and 'message' in chat_response:
        print(f"  Response: {chat_response['message'][:100]}...")
    else:
        print("  ❌ Could not get chat response")
    
    # Demonstrate configuration refresh
    if model_info.get('app_config_enabled'):
        print("\n🔄 Azure App Configuration is enabled!")
        print("   You can now change the feature variant allocation in Azure Portal.")
        print("   The application will automatically pick up changes within 30 seconds.")
        
        # Monitor for configuration changes
        print("\n👀 Monitoring for configuration changes (press Ctrl+C to stop)...")
        original_variant = model_info.get('variant')
        
        try:
            for i in range(10):  # Monitor for 5 minutes
                time.sleep(30)  # Wait 30 seconds
                
                current_info = get_model_info()
                if current_info:
                    current_variant = current_info.get('variant')
                    if current_variant != original_variant:
                        print(f"\n🎉 Configuration changed!")
                        print(f"   Old variant: {original_variant}")
                        print(f"   New variant: {current_variant}")
                        print(f"   New model: {current_info.get('model')}")
                        
                        # Send another test message with the new configuration
                        print("\n💬 Testing with new configuration...")
                        new_response = send_chat_message("Hello again! What model are you using now?")
                        if new_response and 'message' in new_response:
                            print(f"   Response: {new_response['message'][:100]}...")
                        break
                    else:
                        print(f"   [{i+1}/10] No change detected (variant: {current_variant})")
                else:
                    print(f"   [{i+1}/10] Could not check configuration")
                    
        except KeyboardInterrupt:
            print("\n\n⏹️  Monitoring stopped by user")
            
    else:
        print("\n💡 Azure App Configuration is not enabled.")
        print("   The application is using fallback configuration (environment variables).")
        print("   To test dynamic configuration:")
        print("   1. Set up Azure App Configuration with feature variants")
        print("   2. Set AZURE_APP_CONFIGURATION_CONNECTION_STRING environment variable")
        print("   3. Restart the application")
        
        # Demonstrate manual refresh (should fail gracefully)
        print("\n🔄 Testing manual configuration refresh...")
        refresh_result = refresh_config()
        if refresh_result:
            print(f"   Result: {refresh_result}")
    
    print("\n✅ Demo completed!")
    print("\n📚 For more information:")
    print("   - See AZURE_APP_CONFIG_SETUP.md for detailed setup instructions")
    print("   - Check the application logs for debugging information")
    print("   - Use the API endpoints to integrate with your own applications")

if __name__ == "__main__":
    main()