targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

param LAWname string
param location string
param LAWsku string
param AIname string
param AItype string
param AIrequestSource string
param AACname string
param AACsku string
param AACsoftDeleteRetentionInDays int
param AACenablePurgeProtection bool
param AACdisableLocalAuth bool
param ai_endpoint string

// Tags that should be applied to all resources.
// 
// Note that 'azd-service-name' tags should be applied separately to service host resources.
// Example usage:
//   tags: union(tags, { 'azd-service-name': <service name in azure.yaml> })
var tags = {
  'azd-env-name': environmentName
}

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

module monitoring './monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    logAnalyticsName: '${LAWname}${resourceToken}'
    applicationInsightsName: '${AIname}${resourceToken}'
    AIrequestSource: AIrequestSource
    AItype: AItype    
    LAWsku: LAWsku
    tags: tags
  }
  scope: rg
}

module appConfiguration './appConfiguration.bicep' = {
  name: 'appConfiguration'
  params: {
    AACdisableLocalAuth: AACdisableLocalAuth
    AACenablePurgeProtection: AACenablePurgeProtection
    AACsoftDeleteRetentionInDays: AACsoftDeleteRetentionInDays
    AACsku: AACsku
    location: location
    name: '${AACname}${resourceToken}'
    applicationInsightsId: monitoring.outputs.applicationInsightsId
    ai_endpoint: ai_endpoint
  }
  scope: rg
}

output AZURE_APPCONFIGURATION_NAME string = appConfiguration.outputs.appConfigurationName
output AzureAppConfigurationConnectionString string = appConfiguration.outputs.appConfigurationConnectionString
output ApplicationInsightsConnectionString string = monitoring.outputs.applicationInsightsConnectionString
