# Azure App Configuration Integration

This document describes the changes made to support dynamic agent switching using Azure App Configuration and Feature Management.

## Key Changes

### 1. Dependencies Added
- `azure-appconfiguration-provider`: For loading configuration from Azure App Configuration
- `featuremanagement`: For feature flag and variant management

### 2. Environment Variables
- **Required**: `AZURE_APPCONFIGURATION_ENDPOINT` - The endpoint to your Azure App Configuration instance
- **Optional**: `ASSISTANT_ID` - Fallback agent ID if feature flags are not available

### 3. Azure App Configuration Setup

The application expects the following configuration in Azure App Configuration:

#### Configuration Keys
- `ai_endpoint`: The Azure AI Foundry endpoint

#### Feature Flags
- `Agent`: A variant feature flag with:
  - Configuration value containing the `agent_id`
  - Targeting rules for user assignment

### 4. Code Changes

#### app.py
- Added Azure App Configuration provider initialization
- Added Feature Management with targeting support
- Implemented user UUID assignment via `@app.before_request`
- Added dynamic service selection based on feature flags
- Service caching to avoid recreating OpenAI services

#### azure_open_ai_service.py
- No changes needed - already accepts ai_endpoint and assistant_id as parameters

## Usage

### Setup Azure App Configuration

1. Create an Azure App Configuration instance
2. Add the `ai_endpoint` configuration key with your Azure AI Foundry endpoint
3. Create a feature flag named `Agent` with variant support:
   - Set targeting rules to assign users to different agents
   - Configure the variant with the `agent_id` value

### Environment Variables

Set the required environment variable:
```bash
export AZURE_APPCONFIGURATION_ENDPOINT="https://your-appconfig.azconfig.io"
```

### Authentication

The application uses `DefaultAzureCredential` for authentication. Ensure you have:
- Azure CLI login (`az login`), or
- Managed Identity (in Azure), or
- Environment variables for service principal

### Permissions

The identity used needs:
- **App Configuration Data Reader** role on the App Configuration instance
- **Contributor** role on the Azure AI Foundry project

## Features

### Dynamic Agent Assignment
- Users are automatically assigned a unique UUID on their first request
- The Feature Management system uses this UUID for targeting
- Different users can be assigned to different agents based on targeting rules
- Configuration refreshes automatically when feature flag settings change

### Service Caching
- OpenAI services are cached based on agent_id to avoid recreation
- New services are only created when a new agent_id is encountered

### Fallback Support
- If feature flags are not available, the system falls back to the `ASSISTANT_ID` environment variable
- The application will fail to start if neither configuration source is available

## Monitoring

The application logs:
- User ID assignment
- Service creation for new agents
- Configuration refresh events
- Errors in configuration loading

Use Azure Application Insights to monitor:
- Feature flag usage
- Agent assignment distribution
- Performance metrics per agent