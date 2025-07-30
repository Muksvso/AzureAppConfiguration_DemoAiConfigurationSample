param location string
param name string
param AACsku string
param AACsoftDeleteRetentionInDays int
param AACenablePurgeProtection bool
param AACdisableLocalAuth bool
param applicationInsightsId string
param ai_endpoint string
param userObjectId string

resource appConfigurationStore 'Microsoft.AppConfiguration/configurationStores@2023-09-01-preview' = {
  name: name
  location: location
  sku: {
    name: AACsku
  }
  properties: {
    softDeleteRetentionInDays: AACsoftDeleteRetentionInDays
    enablePurgeProtection: AACenablePurgeProtection
    disableLocalAuth: AACdisableLocalAuth
    telemetry: {
      resourceId: applicationInsightsId
    }
  }
}

resource SQLAlchemyDatabaseUri 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  name: 'SQLALCHEMY_DATABASE_URI'
  parent: appConfigurationStore
  properties: {
    value: 'sqlite:///db.sqlite'
  }
}

resource AzureOpenAIEndpoint 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  name: 'AZURE_OPENAI_ENDPOINT'
  parent: appConfigurationStore
  properties: {
    value: ai_endpoint
  }
}

resource VariantFeatureFlagGreeting 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  name: '.appconfig.featureflag~2FAgent'
  parent: appConfigurationStore
  properties: {
    contentType: 'application/vnd.microsoft.appconfig.ff+json;charset=utf-8'
    value: '''
    {
      "id": "Agent",
      "description": "",
      "enabled": true,
      "variants": [
        {
          "name": "OldAgent",
          "configuration_value": "asst_0n12xDQzPThXEdaYInkSF3fY"
        },
        {
          "name": "NewAgent",
          "configuration_value": "asst_4cqaxg1p2RbDR3XROhBpsBRX"
        }
      ],
      "allocation": {
        "percentile": [
          {
            "variant": "OldAgent",
            "from": 0,
            "to": 99
          },
          {
            "variant": "NewAgent",
            "from": 99,
            "to": 100
          }
        ],
        "default_when_enabled": "OldAgent",
        "default_when_disabled": "OldAgent"
      },
      "telemetry": {
        "enabled": true
      }
    }
    '''
  }
}

// After appConfiguration module
resource appConfigRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appConfigurationStore.name, userObjectId, '516239f1-63e1-4d78-a4de-a74fb236a071')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '516239f1-63e1-4d78-a4de-a74fb236a071')
    principalId: userObjectId
    principalType: 'User'
  }
}

var readonlyKey = filter(appConfigurationStore.listKeys().value, k => k.name == 'Primary Read Only')[0]

output appConfigurationConnectionString string = readonlyKey.connectionString
output appConfigurationName string = appConfigurationStore.name
