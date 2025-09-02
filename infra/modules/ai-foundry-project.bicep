// Creates an Azure AI resource with proxied endpoints for the Azure AI services provider

@description('Azure region of the deployment')
param location string

@description('AI Foundry name')
param aiFoundryName string

@description('AI Project name')
param aiProjectName string

@description('AI Project display name')
param aiProjectFriendlyName string = aiProjectName

@description('AI Project description')
param aiProjectDescription string

param applicationInsightsName string
param bingSearchServiceName string

param customKey object = {
  name: 'xxxx'
  target: 'https://api.xxxx.com/'
  authKey: ''
}

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: aiFoundryName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02-preview' existing = {
  name: applicationInsightsName
}

resource bingSearchService 'Microsoft.Bing/accounts@2025-05-01-preview' existing = {
  name: bingSearchServiceName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiFoundry
  name: aiProjectName
  location: location
  properties: {
    description: aiProjectFriendlyName
    displayName: aiProjectDescription
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// Creates the Azure Foundry connection to your Azure App Insights resource
resource connectionAppInsight 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  name: 'appinsights-connection'
  parent: project
  properties: {
    category: 'AppInsights'
    target: applicationInsights.id
    authType: 'ApiKey'
    //isSharedToAll: true
    credentials: {
      key: applicationInsights.properties.connectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: applicationInsights.id
    }
  }
}

// Creates the Azure Foundry connection to Bing grounding
resource connectionBingGrounding 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
  name: '${aiFoundry.name}-bing-grounding-connection'
  parent: aiFoundry
  properties: {
    category: 'GroundingWithCustomSearch'
    target: 'https://api.bing.microsoft.com/'
    authType: 'ApiKey'
    //isSharedToAll: false
    credentials: {
      key: listKeys(bingSearchService.id, '2020-06-10').key1 // Use the primary key from the Bing Search Service
    }
    metadata: {
      ApiType: 'Azure'
      type: 'bing_custom_search'
      ResourceId: bingSearchService.id
    }
  }
}

resource connectionCustom 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
  name: '${customKey.name}-customkey-connection'
  parent: aiFoundry
  properties: {
    category: 'CustomKeys'
    target: customKey.target
    authType: 'CustomKeys'
    //isSharedToAll: true
    credentials: {
      keys: {
        'x-api-key': customKey.authKey
      }
    }
    metadata: {}
  }
}

// Creates the Azure Foundry ApiKey connection 
//Not used
/* resource connectionApiKey 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
  name: 'setlistfm-api-key-connection'
  parent: aiFoundry
  properties: {
    category: 'ApiKey'
    target: 'https://api.setlist.fm/rest/'
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: setlistfmApiKey
    }
    metadata: {}
  }
}
 */

output projectName string = project.name
output projectId string = project.id
output projectIdentityPrincipalId string = project.identity.principalId
output projectEndpoint string = project.properties.endpoints['AI Foundry API']
