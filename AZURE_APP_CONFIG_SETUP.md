# Azure App Configuration Setup Guide

This guide explains how to configure Azure App Configuration with feature variants for dynamic AI model selection.

## Prerequisites

- Azure subscription
- Azure App Configuration resource
- Azure OpenAI resource(s)
- Appropriate permissions to manage configuration and feature flags

## Azure App Configuration Setup

### 1. Create Azure App Configuration Resource

```bash
# Create resource group (if needed)
az group create --name myResourceGroup --location eastus

# Create Azure App Configuration
az appconfig create --name myAppConfig --resource-group myResourceGroup --location eastus --sku standard
```

### 2. Get Connection String

```bash
# Get connection string
az appconfig credential list --name myAppConfig --resource-group myResourceGroup --query "[?name=='Primary'].connectionString" --output tsv
```

### 3. Configure Base Settings (Optional)

You can set base configuration values that will be used as fallbacks:

```bash
# Set base Azure OpenAI configuration
az appconfig kv set --name myAppConfig --key "AzureOpenAI:Endpoint" --value "https://your-openai.openai.azure.com/"
az appconfig kv set --name myAppConfig --key "AzureOpenAI:Model" --value "gpt-35-turbo"
```

### 4. Create Feature Flag with Variants

#### Option A: Using Azure Portal

1. Navigate to your Azure App Configuration resource in the Azure Portal
2. Go to **Feature manager** → **Feature flags**
3. Click **+ Create** to create a new feature flag
4. Configure the feature flag:
   - **Feature flag name**: `AIModelSelection`
   - **Enable feature flag**: ✅ Checked
   - **Use feature filter**: ✅ Checked if you want conditional logic

5. Add variants by clicking **+ Add variant**:
   
   **Variant 1 - GPT-3.5 Turbo:**
   - **Name**: `gpt35turbo`
   - **Configuration value**:
     ```json
     {
       "endpoint": "https://your-openai.openai.azure.com/",
       "model": "gpt-35-turbo"
     }
     ```

   **Variant 2 - GPT-4:**
   - **Name**: `gpt4`
   - **Configuration value**:
     ```json
     {
       "endpoint": "https://your-openai.openai.azure.com/",
       "model": "gpt-4"
     }
     ```

#### Option B: Using Azure CLI

```bash
# Create the feature flag
az appconfig feature set --name myAppConfig --feature AIModelSelection --yes

# Add variants (requires Azure CLI extension for App Configuration)
# Note: Variant management via CLI might require REST API calls or ARM templates
```

#### Option C: Using REST API

```bash
# Set feature flag with variants
curl -X PUT "https://myAppConfig.azconfig.io/kv/.appconfig.featureflag%2FAIModelSelection" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "value": "{
      \"id\": \"AIModelSelection\",
      \"enabled\": true,
      \"variants\": [
        {
          \"name\": \"gpt35turbo\",
          \"configuration_value\": {
            \"endpoint\": \"https://your-openai.openai.azure.com/\",
            \"model\": \"gpt-35-turbo\"
          }
        },
        {
          \"name\": \"gpt4\",
          \"configuration_value\": {
            \"endpoint\": \"https://your-openai.openai.azure.com/\",
            \"model\": \"gpt-4\"
          }
        }
      ]
    }"
  }'
```

### 5. Configure Allocation (Optional)

You can configure allocation percentages for A/B testing:

1. In the Azure Portal, edit your `AIModelSelection` feature flag
2. Go to the **Allocation** tab
3. Set percentages for each variant:
   - `gpt35turbo`: 70%
   - `gpt4`: 30%

## Application Configuration

### Environment Variables

Set the following environment variable in your application:

```bash
export AZURE_APP_CONFIGURATION_CONNECTION_STRING="Endpoint=https://myAppConfig.azconfig.io;Id=xxx;Secret=xxx"
```

### Authentication

The application uses `DefaultAzureCredential` which supports:

1. **Environment variables** (for service principal)
2. **Managed Identity** (when deployed to Azure)
3. **Azure CLI** credentials (for local development)
4. **Visual Studio** credentials

For local development with Azure CLI:
```bash
az login
```

### Required Permissions

Grant the following permissions to your identity:

- **Azure App Configuration**: `App Configuration Data Reader`
- **Azure Key Vault**: `Key Vault Secrets User` (if using Key Vault references)

## Configuration Refresh

The application automatically refreshes configuration every 30 seconds. You can also trigger manual refresh:

```bash
curl -X POST http://localhost:5000/api/config/refresh
```

## Testing the Setup

### Check Configuration Status

```bash
curl http://localhost:5000/api/chat/model
```

Expected response with Azure App Configuration:
```json
{
  "app_config_enabled": true,
  "configured": true,
  "model": "gpt-35-turbo",
  "variant": "gpt35turbo"
}
```

### Test Variant Switching

1. Change the variant allocation in Azure Portal
2. Wait up to 30 seconds for automatic refresh, or call the manual refresh endpoint
3. Check the model endpoint again to see the updated configuration

## Troubleshooting

### Common Issues

1. **Connection String Not Found**
   - Ensure `AZURE_APP_CONFIGURATION_CONNECTION_STRING` is set
   - Verify the connection string format

2. **Authentication Failed**
   - Check Azure credentials with `az account show`
   - Verify permissions on the App Configuration resource

3. **Feature Flag Not Found**
   - Ensure the feature flag `AIModelSelection` exists
   - Check that variants are properly configured

4. **Variant Configuration Invalid**
   - Verify JSON format in variant configuration
   - Ensure required fields `endpoint` and `model` are present

### Debug Logging

Enable debug logging by setting:
```bash
export FLASK_ENV=development
```

Check logs for configuration loading and refresh activities.

## Architecture

```
Azure App Configuration
├── Feature Flag: AIModelSelection
│   ├── Variant: gpt35turbo
│   │   └── Configuration: {"endpoint": "...", "model": "gpt-35-turbo"}
│   └── Variant: gpt4
│       └── Configuration: {"endpoint": "...", "model": "gpt-4"}
└── Optional Base Settings
    ├── AzureOpenAI:Endpoint
    └── AzureOpenAI:Model

Application
├── ConfigurationService
│   ├── Loads from Azure App Configuration
│   ├── Falls back to environment variables
│   └── Refreshes every 30 seconds
└── AzureOpenAIService
    ├── Updates dynamically when configuration changes
    └── Maintains client instances per endpoint
```