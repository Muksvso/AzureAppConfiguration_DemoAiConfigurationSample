# AI Configuration Demo Application

This repository contains a demo application that showcases integration with Azure OpenAI services using Azure App Configuration for dynamic AI model configuration with feature variants.

![Chat Interface Screenshot](Images/ChatScreenshot.png)

![Configuration Screenshot](Images/ConfigurationScreenshot.png)

## Features

- **Dynamic Model Selection**: Use Azure App Configuration feature variants to switch between AI models without application restart
- **Automatic Configuration Refresh**: Real-time configuration updates every 30 seconds
- **Fallback Support**: Graceful fallback to environment variables when Azure App Configuration is unavailable
- **A/B Testing Ready**: Support for percentage-based allocation across model variants
- **RESTful Configuration API**: Endpoints to check configuration status and trigger manual refresh

## Project Structure

- **Backend**: Python Flask API that integrates with Azure OpenAI and Azure App Configuration
- **Frontend**: TypeScript/Vite application that provides a chat interface

## Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/) (v16+)
- [npm](https://www.npmjs.com/)
- Azure account with the following services:
  - Azure App Configuration
  - Azure OpenAI
  - Azure Key Vault (optional, for secure key storage)

## Quick Start

### 1. Backend Setup

1. Navigate to the Backend directory:
   ```bash
   cd Backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Option A: Using Azure App Configuration (Recommended)**
   
   Set up Azure App Configuration with feature variants:
   ```bash
   export AZURE_APP_CONFIGURATION_CONNECTION_STRING="Endpoint=https://your-config.azconfig.io;Id=xxx;Secret=xxx"
   ```
   
   See [Azure App Configuration Setup Guide](AZURE_APP_CONFIG_SETUP.md) for detailed instructions.

4. **Option B: Using Environment Variables (Fallback)**
   
   Set environment variables:
   ```bash
   export AZURE_OPENAI_ENDPOINT="https://your-openai.openai.azure.com/"
   export AZURE_OPENAI_MODEL="gpt-35-turbo"
   ```

5. Start the backend:
   ```bash
   python app.py
   ```
   The API will be available at `http://localhost:5000`

### 2. Frontend Setup

1. Navigate to the Frontend directory:
   ```bash
   cd Frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Build the project:
   ```bash
   npm run build
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`

## Configuration Management

### API Endpoints

- **GET `/api/chat/model`**: Get current model configuration and status
- **POST `/api/config/refresh`**: Manually trigger configuration refresh
- **POST `/api/chat`**: Send chat messages to the AI model

### Example API Response

```json
{
  "app_config_enabled": true,
  "configured": true,
  "model": "gpt-4",
  "variant": "gpt4"
}
```

### Dynamic Model Switching

When using Azure App Configuration with feature variants:

1. Update variant allocation in Azure Portal
2. Configuration automatically refreshes within 30 seconds
3. New chat requests use the updated model configuration
4. No application restart required

## Authentication

The application uses `DefaultAzureCredential` for authentication, which supports:

1. **Azure CLI** (for local development): `az login`
2. **Environment variables** (for CI/CD)
3. **Managed Identity** (for Azure deployments)
4. **Visual Studio/VS Code** authentication

Required permissions:
- **Azure App Configuration**: App Configuration Data Reader role
- **Azure Key Vault**: Key Vault Secret User role (if using Key Vault references)

## Troubleshooting

### Configuration Issues

- **Azure App Configuration not working**: Check connection string and verify the feature flag `AIModelSelection` exists with proper variants
- **Authentication errors**: Ensure you're logged in with `az login` or have proper managed identity configuration
- **Model not switching**: Check variant allocation and wait up to 30 seconds for automatic refresh, or call the manual refresh endpoint

### Development Mode

For development without Azure App Configuration, simply set environment variables:
```bash
export AZURE_OPENAI_ENDPOINT="https://your-openai.openai.azure.com/"
export AZURE_OPENAI_MODEL="gpt-35-turbo"
```

### Debug Information

Check configuration status:
```bash
curl http://localhost:5000/api/chat/model
```

View application logs for detailed information about configuration loading and refresh activities.

## Advanced Configuration

For detailed setup instructions including feature variant configuration, see the [Azure App Configuration Setup Guide](AZURE_APP_CONFIG_SETUP.md).