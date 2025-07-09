@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string = 'francecentral'

@description('Location for AI Foundry resources.')
param aiFoundryLocation string = 'swedencentral' //'westus' 'switzerlandnorth'

@description('Name of the resource group to deploy to.')
param rootname string = 'mysetlistagent'

@description('Spotify Client ID for MCP Spotify microservice.')
param spotifyClientId string

@description('Spotify Client Secret for MCP Spotify microservice.')
@secure()
param spotifyClientSecret string

@description('Indicates if the latest image for the Spotify MCP microservice exists in the ACR.')
param isLatestImageExist bool = true

var chainlitAuthSecret = 'u.tT0881gp@T9$mRHr4XWs/uk2R8mqI5dSo@R2AO_Rj63t5P$3T,x4aN,Shpo@~'

// tags that should be applied to all resources.
var tags = {
  // Tag all resources with the environment name.
  'azd-env-name': environmentName
}

#disable-next-line no-unused-vars
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

module applicationInsights 'modules/app-insights.bicep' = {
  name: 'application-insights'
  params: {
    location: location
    workspaceName: logAnalyticsWorkspace.outputs.name
    applicationInsightsName: '${rootname}-app-insights'
  }
}

module logAnalyticsWorkspace 'modules/log-analytics-workspace.bicep' = {
  name: 'log-analytics-workspace'
  params: {
    location: location
    logAnalyticsName: '${rootname}-log-analytics'
  }
}

module eventHub 'modules/event-hub.bicep' = {
  name: 'event-hub'
  params: {
    location: location
    eventHubNamespaceName: '${rootname}-ehn-${uniqueString(resourceGroup().id)}'
    eventHubName: '${rootname}-eh-${uniqueString(resourceGroup().id)}'
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: '${rootname}${uniqueString(resourceToken)}'
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    adminUserEnabled: false
  }
  tags: tags
}

@description('Creates an Azure Key Vault.')
resource kv 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: 'kv${uniqueString(rootname, resourceToken)}'
  location: location
  properties: {
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    sku: {
      name: 'standard'
      family: 'A'
    }
    //publicNetworkAccess: 'Enabled'
  }
}

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-10-02-preview' = {
  name: rootname
  location: location
  tags: tags
  properties: {
    appInsightsConfiguration: {
      connectionString: applicationInsights.outputs.connectionString
    }
    openTelemetryConfiguration: {
      tracesConfiguration: {
        destinations: ['appInsights']
      }
      logsConfiguration: {
        destinations: ['appInsights']
      }
    }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.outputs.customerId
        sharedKey: logAnalyticsWorkspace.outputs.primarySharedKey
      }
    }
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${containerApplicationIdentity.id}': {}
    }
  }
  dependsOn: [
    containerApplicationIdentityAcrPull // Assigns the ACR Pull role to the container application identity
    containerApplicationIdentityKeyVaultContributorRoleAssignment // Assigns the Key Vault Contributor role to the container application identity
  ]
}

resource containerApplicationIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2022-01-31-preview' = {
  name: '${rootname}-container-app-identity'
  location: location
}

resource containerApplicationIdentityAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, containerApplicationIdentity.id, 'ACR Pull Role RG')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: containerApplicationIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

module setlistfmMcpApp 'modules/mcp-container-app.bicep' = {
  name: 'setlistfm-mcp-app'
  params: {
    name: 'setlistfm-mcp-server'
    location: location
    managedEnvironmentId: containerAppsEnv.id
    acrLoginServer: acr.properties.loginServer
    identityId: containerApplicationIdentity.id
    isLatestImageExist: isLatestImageExist
    secrets: [
      {
        name: 'setlistfm-api-key'
        keyVaultUrl: secretSetlistFMApiKey.properties.secretUri
        identity: containerApplicationIdentity.id
      }
      {
        name: 'applicationinsights-connectionstring'
        keyVaultUrl: secretAppInsightCS.properties.secretUri
        identity: containerApplicationIdentity.id
      }
    ]
    envVars: [
      {
        name: 'SETLISTFM_API_KEY'
        secretRef: 'setlistfm-api-key'
      }
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        secretRef: 'applicationinsights-connectionstring'
      }
    ]
  }
}

module spotifyMcpApp 'modules/mcp-container-app.bicep' = {
  name: 'spotify-mcp-app'
  params: {
    name: 'spotify-mcp-server'
    location: location
    managedEnvironmentId: containerAppsEnv.id
    acrLoginServer: acr.properties.loginServer
    identityId: containerApplicationIdentity.id
    isLatestImageExist: isLatestImageExist
    secrets: [
      {
        name: 'applicationinsights-connectionstring'
        keyVaultUrl: secretAppInsightCS.properties.secretUri
        identity: containerApplicationIdentity.id
      }
    ]
    envVars: [
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        secretRef: 'applicationinsights-connectionstring'
      }
    ]
  }
}

module setlistAgentpApp 'modules/mcp-container-app.bicep' = {
  name: 'setlist-agent'
  params: {
    name: 'setlist-agent'
    location: location
    managedEnvironmentId: containerAppsEnv.id
    acrLoginServer: acr.properties.loginServer
    identityId: containerApplicationIdentity.id
    isLatestImageExist: isLatestImageExist
    secrets: [
      {
        name: 'spotify-client-id'
        keyVaultUrl: secretSpotifyClientId.properties.secretUri
        identity: containerApplicationIdentity.id
      }
      {
        name: 'spotify-client-secret'
        keyVaultUrl: secretSpotifyClientSecret.properties.secretUri
        identity: containerApplicationIdentity.id
      }

      {
        name: 'applicationinsights-connectionstring'
        keyVaultUrl: secretAppInsightCS.properties.secretUri
        identity: containerApplicationIdentity.id
      }
    ]
    envVars: [
      {
        name: 'AZURE_AI_INFERENCE_API_KEY'
        value: listKeys(aiFoundry.id, '2025-04-01-preview').key1
      }
      {
        name: 'AZURE_AI_INFERENCE_ENDPOINT'
        value: '${aiFoundry.properties.endpoints['Azure AI Model Inference API']}models'
      }
      {
        name: 'MODEL_DEPLOYMENT_NAME'
        value: modelDeploymentsParameters[0].name
      }
      {
        name: 'PROJECT_ENDPOINT'
        value: project.properties.endpoints['AI Foundry API']
      }

      {
        name: 'SPOTIFY_MCP_URL'
        value: 'http://${spotifyMcpApp.outputs.containerAppName}/sse'
      }
      {
        name: 'SETLISTFM_MCP_URL'
        value: 'http://${setlistfmMcpApp.outputs.containerAppName}/sse'
      }
      {
        name: 'OAUTH_SPOTIFY_CLIENT_ID'
        secretRef: 'spotify-client-id'
      }
      {
        name: 'OAUTH_SPOTIFY_CLIENT_SECRET'
        secretRef: 'spotify-client-secret'
      }

      {
        name: 'OAUTH_SPOTIFY_SCOPES'
        value: 'user-read-private user-read-email user-library-read user-top-read playlist-read-private playlist-modify-public playlist-modify-private user-follow-read user-follow-modify streaming'
      }
      {
        name: 'CHAINLIT_AUTH_SECRET'
        value: chainlitAuthSecret
      }
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        secretRef: 'applicationinsights-connectionstring'
      }
      {
        name: 'AZURE_CLIENT_ID'
        value: containerApplicationIdentity.properties.clientId
      }
      {
        name: 'AZURE_LOG_LEVEL' // To display the missing permissions in the logs
        value: 'DEBUG'
      }
    ]
  }
}

resource containerApplicationIdentityKeyVaultContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(kv.id, containerApplicationIdentity.id, 'Key Vault Contributor Role')
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets Officer
    )
    principalId: containerApplicationIdentity.properties.principalId
  }
}

@description('Creates an Azure Key Vault Secret APPLICATIONINSIGHTS-CONNECTION-STRING.')
resource secretAppInsightCS 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'APPLICATIONINSIGHTS-CONNECTIONSTRING'
  properties: {
    value: applicationInsights.outputs.connectionString
  }
}

@description('Creates an Azure Key Vault Secret APPINSIGHTS-INSTRUMENTATIONKEY.')
resource secretAppInsightInstKey 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'APPINSIGHTS-INSTRUMENTATIONKEY'
  properties: {
    value: applicationInsights.outputs.instrumentationKey
  }
}

@description('Creates an Azure Key Vault Secret SPOTIFY-CLIENT-ID KEY.')
resource secretSpotifyClientId 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'SPOTIFY-CLIENT-ID'
  properties: {
    value: spotifyClientId
  }
}

@description('Creates an Azure Key Vault Secret SPOTIFY_CLIENT_SECRET KEY.')
resource secretSpotifyClientSecret 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'SPOTIFY-CLIENT-SECRET'
  properties: {
    value: spotifyClientSecret
  }
}

@description('SetlistFM API Key for MCP SetlistFM microservice.')
@secure()
param setlistfmApiKey string

@description('Creates an Azure Key Vault Secret SetListFM API KEY.')
resource secretSetlistFMApiKey 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'SETLISTFM-API-KEY'
  properties: {
    value: setlistfmApiKey
  }
}

module userPortalAccess 'modules/user_portal_role.bicep' = {
  name: 'user-portal-access'
  params: {
    kvName: kv.name
    projectName: aiFoundry.name
    applicationInsightsName: applicationInsights.outputs.aiName
  }
}

/*
  An AI Foundry resources is a variant of a CognitiveServices/account resource type
  from https://github.com/azure-ai-foundry/foundry-samples/blob/main/samples/microsoft/infrastructure-setup/00-basic/main.bicep
*/
resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: '${rootname}-ai-foundry-${aiFoundryLocation}'
  location: aiFoundryLocation
  tags: {
    'azd-service-name': 'ai-foundry'
    'azd-env-name': environmentName
  }
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    // required to work in AI Foundry
    allowProjectManagement: true
    // Defines developer API endpoint subdomain
    customSubDomainName: '${rootname}-ai-foundry-${aiFoundryLocation}'
    publicNetworkAccess: 'Enabled'

    //disableLocalAuth: true
  }
}

resource aiFoundryRoleAssignmentOnContainerApplicationIdentity 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(aiFoundry.id, containerApplicationIdentity.id, 'AI Foundry Azure AI User role')
  scope: aiFoundry
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Azure AI User
    )
    //Principal ID of the current user
    principalId: containerApplicationIdentity.properties.principalId
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiFoundry
  name: '${rootname}-project-${aiFoundryLocation}'
  location: aiFoundryLocation
  properties: {
    description: 'a world of music'
    displayName: 'setlist-agent'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

//https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/rbac-azure-ai-foundry?pivots=fdp-project#azure-ai-account-owner
resource aiFoundryProjectRoleAssignmentOnContainerApplicationIdentity 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(project.id, containerApplicationIdentity.id, 'AI Foundry Project Azure AI User role')
  scope: project
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Azure AI User
    )
    //Principal ID of the current user
    principalId: containerApplicationIdentity.properties.principalId
  }
}

@description('Model deployments for OpenAI')
param modelDeploymentsParameters array = [
  {
    name: '${rootname}-gpt-4.1-mini'
    model: 'gpt-4.1-mini'
    capacity: 1000
    deployment: 'GlobalStandard'
    version: '2025-04-14'
    format: 'OpenAI'
  }
  /*
  {
    name: '${rootname}-gpt-4.1-nano'
    model: 'gpt-4.1-nano'
    capacity: 1
    deployment: 'GlobalStandard'
    version: '2025-04-14'
    format: 'OpenAI'
  }

  {
    name: '${rootname}-phi-4'
    model: 'Phi-4'
    version: '7'
    format: 'Microsoft'
    capacity: 1
    deployment: 'GlobalStandard'
    settings: {
      enableAutoToolChoice: true
      toolCallParser: 'default'
    }
  }*/
]

@batchSize(1)
resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = [
  for deployment in modelDeploymentsParameters: {
    parent: aiFoundry
    name: deployment.name
    sku: {
      capacity: deployment.capacity
      name: deployment.deployment
    }
    properties: {
      model: {
        format: deployment.format
        name: deployment.model
        version: deployment.version
      }
    }
  }
]

// Creates the Azure Foundry connection to your Azure App Insights resource
resource connection 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
  name: '${aiFoundry.name}-appinsights-connection'
  parent: aiFoundry
  properties: {
    category: 'AppInsights'
    target: applicationInsights.outputs.aiId
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: applicationInsights.outputs.connectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: applicationInsights.outputs.aiId
    }
  }
}

module apiManagement 'modules/api-management.bicep' = {
  name: 'api-management'
  params: {
    location: location
    serviceName: '${rootname}-api-mgmt'
    publisherName: 'Setlistfy Apps'
    publisherEmail: '${rootname}@contososuites.com'
    skuName: 'Basicv2'
    skuCount: 1
    aiName: applicationInsights.outputs.aiName
  }
  dependsOn: [
    eventHub
  ]
}

module setlistfmapi 'modules/api.bicep' = {
  name: 'setlistfm-api'
  params: {
    apimName: apiManagement.outputs.name
    apiName: 'setlistfm'
    apiPath: '/setlistfm'
    openApiJson: 'https://raw.githubusercontent.com/bmoussaud/setlistfy-agent/refs/heads/main/src/apim/openapi-setlistfm.json'
    openApiXml: 'https://raw.githubusercontent.com/bmoussaud/setlistfy-agent/refs/heads/main/src/apim/policy-setlistfm.xml'
    serviceUrlPrimary: 'https://api.setlist.fm/rest'
    aiLoggerName: apiManagement.outputs.aiLoggerName
  }
  dependsOn: [
    secretSetlistFMApiKey
    setlistFmNvApiKey
    keyVaultSecretUserRoleAssignment
  ]
}

module setlistFmNvApiKey 'modules/nvkv.bicep' = {
  name: 'setlisfm-api-key'
  params: {
    apimName: apiManagement.outputs.name
    keyName: 'setlisfm-api-key'
    keyVaultName: kv.name
    secretName: secretSetlistFMApiKey.name
  }
  dependsOn: [
    keyVaultSecretUserRoleAssignment //this role assignment is needed to allow the API Management service to access the Key Vault
  ]
}

@description('This is the built-in Key Vault Secrets Officer role. See https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user')
resource keyVaultSecretsUserRoleDefinition 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  scope: subscription()
  name: '4633458b-17de-408a-b874-0445c86b69e6'
}

@description('Assigns the API Management service the role to browse and read the keys of the Key Vault to the APIM')
resource keyVaultSecretUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(kv.id, apiManagement.name, keyVaultSecretsUserRoleDefinition.id)
  scope: kv
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleDefinition.id
    principalId: apiManagement.outputs.apiManagementIdentityPrincipalId
  }
}

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.properties.loginServer
output SPOTIFY_MCP_URL string = 'https://${spotifyMcpApp.outputs.fqdn}/sse'
output SETLISTFM_MCP_URL string = 'https://${setlistfmMcpApp.outputs.fqdn}/sse'
output SETLIST_AGENT_URL string = 'https://${setlistAgentpApp.outputs.fqdn}'

output AZURE_OPENAI_ENDPOINT string = aiFoundry.properties.customSubDomainName
output OAUTH_SPOTIFY_CLIENT_ID string = spotifyClientId
output OAUTH_SPOTIFY_CLIENT_SECRET string = spotifyClientSecret
output OAUTH_SPOTIFY_SCOPES string = 'user-read-private user-read-email user-library-read user-top-read playlist-read-private playlist-modify-public playlist-modify-private'

output PROJECT_ENDPOINT string = project.properties.endpoints['AI Foundry API']
output AZURE_AI_INFERENCE_ENDPOINT string = '${aiFoundry.properties.endpoints['Azure AI Model Inference API']}models'
output AZURE_AI_INFERENCE_API_KEY string = listKeys(aiFoundry.id, '2025-04-01-preview').key1
output MODEL_DEPLOYMENT_NAME string = modelDeploymentsParameters[0].name

output APPLICATIONINSIGHTS_CONNECTION_STRING string = applicationInsights.outputs.connectionString

output CHAINLIT_AUTH_SECRET string = chainlitAuthSecret
