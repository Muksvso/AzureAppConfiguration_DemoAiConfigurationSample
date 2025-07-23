# AI Configuration Demo Application

This repository contains a demo application that showcases integration with Azure OpenAI services using Azure App Configuration for dynamic AI model configuration.

![Chat Interface Screenshot](Images/ChatScreenshot.png)

![Configuration Screenshot](Images/ConfigurationScreenshot.png)

## Project Structure

- **Backend**: .NET API that integrates with Azure OpenAI
- **Frontend**: TypeScript/Vite application that provides a chat interface

## Prerequisites

- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- [Node.js](https://nodejs.org/) (v16+)
- [npm](https://www.npmjs.com/)
- Azure account with the following services:
  - Azure App Configuration
  - Azure OpenAI
  - Azure Key Vault

## Setup Instructions

### 1. Frontend Setup

1. Navigate to the Frontend directory:
   ```
   cd Frontend
   ```

1. Install dependencies:
   ```
   npm install
   ```

1. Build the project:
   ```
   npm run build
   ```

1. Start the development server:
   ```
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`

### 2. Backend Configuration

1. Configure Azure App Configuration with the following settings:

## TODO

### 3. Authentication Setup

The application uses `DefaultAzureCredential` for authentication, which requires either:

1. Authentication via Visual Studio / Visual Studio Code
2. Authentication via Azure CLI
3. Managed identity (for deployment scenarios)

Ensure you are logged in with an identity that has the following permissions:
- **Azure App Configuration**: App Configuration Data Reader role
- **Azure Key Vault**: Key Vault Secret User role for the key vault containing the OpenAI API key

#### Authentication Steps:

1. **Visual Studio Code**:
   - Install the Azure Account extension
   - Sign in using the Azure: Sign In command

2. **Azure CLI**:
   ```
   az login
   ```

### 4. Running the Application

1. Start the backend API:
   ```
   cd Backend
   pip install -r requirements.txt
   flask run
   ```
   The API will be available at `https://localhost:5000`

2. Ensure the frontend is running (from step 1.4)

3. Navigate to `http://localhost:5173` in your browser to use the application

## Troubleshooting

- **Authentication issues**: Ensure you're logged in with an account that has appropriate permissions
- **Key Vault access**: Verify that the identity used by DefaultAzureCredential has proper access to the Key Vault
- **CORS errors**: Ensure the backend is running and the frontend URL is properly configured in the CORS policy
- **Model errors**: Verify that your Azure OpenAI deployment name is correct and the model is available