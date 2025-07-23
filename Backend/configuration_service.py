"""
Configuration service for Azure App Configuration integration with feature management.
"""

import os
import logging
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential
from azure.appconfiguration.provider import (
    load,
    SettingSelector
)
from featuremanagement import FeatureManager

logger = logging.getLogger(__name__)


class ConfigurationService:
    """
    Service for managing Azure App Configuration and feature flags.
    """

    def __init__(self):
        self.credential = DefaultAzureCredential()
        self._config_provider: Optional[Any] = None
        self._feature_manager: Optional[FeatureManager] = None
        self._initialize_configuration()

    def _initialize_configuration(self):
        """Initialize Azure App Configuration provider and feature manager."""
        try:
            # Get the connection string from environment variable
            connection_string = os.getenv("AZURE_APP_CONFIGURATION_CONNECTION_STRING")
            
            if not connection_string:
                logger.warning("AZURE_APP_CONFIGURATION_CONNECTION_STRING not found, using fallback configuration")
                return

            # Create the configuration provider using the load function
            self._config_provider = load(
                connection_string=connection_string,
                selectors=[
                    SettingSelector(key_filter="*", label_filter=None),  # Default settings
                ],
                feature_flag_enabled=True,
                feature_flag_selectors=[
                    SettingSelector(key_filter="*")  # All feature flags
                ],
                refresh_on=[
                    "AppSettings:refreshTrigger"  # Refresh trigger setting
                ],
                refresh_interval_in_seconds=30  # Refresh every 30 seconds
            )

            # Initialize feature manager with the configuration
            self._feature_manager = FeatureManager(self._config_provider)
            
            logger.info("Azure App Configuration initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Azure App Configuration: {e}")
            self._config_provider = None
            self._feature_manager = None

    def get_setting(self, key: str, default_value: Any = None) -> Any:
        """
        Get a configuration setting value.
        
        Args:
            key: The configuration key
            default_value: Default value if key not found
            
        Returns:
            The configuration value or default
        """
        if self._config_provider:
            try:
                return self._config_provider.get(key, default_value)
            except Exception as e:
                logger.error(f"Error getting configuration key '{key}': {e}")
                
        # Fallback to environment variables
        env_key = key.replace(":", "_").upper()
        return os.getenv(env_key, default_value)

    def get_ai_model_configuration(self) -> Dict[str, str]:
        """
        Get AI model configuration using feature variants.
        
        Returns:
            Dictionary containing model configuration
        """
        try:
            if self._feature_manager:
                # Check if AI model feature flag is enabled and get variant
                try:
                    variant = self._feature_manager.get_variant("AIModelSelection")
                    
                    if variant and hasattr(variant, 'configuration') and variant.configuration:
                        logger.info(f"Using AI model variant: {variant.name}")
                        return {
                            "endpoint": variant.configuration.get("endpoint", ""),
                            "model": variant.configuration.get("model", ""),
                            "variant_name": variant.name
                        }
                except Exception as e:
                    logger.debug(f"No feature variant found for AIModelSelection: {e}")
                
            # Fallback to regular configuration or environment variables
            endpoint = self.get_setting("AzureOpenAI:Endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
            model = self.get_setting("AzureOpenAI:Model") or os.getenv("AZURE_OPENAI_MODEL")
            
            return {
                "endpoint": endpoint or "",
                "model": model or "",
                "variant_name": "default"
            }
            
        except Exception as e:
            logger.error(f"Error getting AI model configuration: {e}")
            # Ultimate fallback to environment variables
            return {
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
                "model": os.getenv("AZURE_OPENAI_MODEL", ""),
                "variant_name": "fallback"
            }

    def refresh_configuration(self) -> bool:
        """
        Refresh configuration from Azure App Configuration.
        
        Returns:
            True if refresh was successful, False otherwise
        """
        try:
            if self._config_provider and hasattr(self._config_provider, 'refresh'):
                self._config_provider.refresh()
                logger.info("Configuration refreshed successfully")
                return True
        except Exception as e:
            logger.error(f"Error refreshing configuration: {e}")
            
        return False

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            feature_name: Name of the feature flag
            
        Returns:
            True if feature is enabled, False otherwise
        """
        try:
            if self._feature_manager:
                return self._feature_manager.is_enabled(feature_name)
        except Exception as e:
            logger.error(f"Error checking feature flag '{feature_name}': {e}")
            
        return False

    @property
    def is_configured(self) -> bool:
        """Check if Azure App Configuration is properly configured."""
        return self._config_provider is not None