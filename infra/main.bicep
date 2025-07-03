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
param isLatestImageExist bool = false

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

resource azrKeyVaultContributor 'Microsoft.ManagedIdentity/userAssignedIdentities@2018-11-30' = {
  name: '${rootname}-keyvault-user'
  location: location
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
      '${azrKeyVaultContributor.id}': {}
    }
  }
}

resource uaiAcrPull 'Microsoft.ManagedIdentity/userAssignedIdentities@2022-01-31-preview' = {
  name: '${rootname}-acr-pull'
  location: location
}

@description('This allows the managed identity of the container app to access the registry, note scope is applied to the wider ResourceGroup not the ACR')
resource uaiRbacAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, uaiAcrPull.id, 'ACR Pull Role RG')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: uaiAcrPull.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

module setlistfmMcpAppFetchLatestImage './modules/fetch-container-image.bicep' = {
  name: 'setlistfm-mcp-fetch-image'
  params: {
    exists: isLatestImageExist
    name: 'setlistfm-mcp'
  }
}

resource setlistfmMcpApp 'Microsoft.App/containerApps@2024-10-02-preview' = {
  name: 'setlistfm-mcp'
  location: location
  tags: { 'azd-service-name': 'setlistfm-mcp-server', 'azd-env-name': environmentName }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${uaiAcrPull.id}': {}
      '${azrKeyVaultContributor.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          exposeHeaders: ['*']
          allowCredentials: false
        }
      }
      registries: [
        {
          identity: uaiAcrPull.id
          server: acr.properties.loginServer
        }
      ]
      secrets: [
        {
          name: 'setlistfm-api-key'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/SETLISTFM-API-KEY'
          identity: azrKeyVaultContributor.id
        }
        {
          name: 'applicationinsights-connectionstring'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/APPLICATIONINSIGHTS-CONNECTIONSTRING'
          identity: azrKeyVaultContributor.id
        }
      ]
    }

    template: {
      containers: [
        {
          name: 'setlistfm-mcp'
          image: setlistfmMcpAppFetchLatestImage.outputs.?containers[?0].?image ?? 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: [
            {
              name: 'SETLISTFM_API_KEY'
              secretRef: 'setlistfm-api-key'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'applicationinsights-connectionstring'
            }
          ]
          /* probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/liveness'
                port: 80
                scheme: 'HTTP'
              }
              initialDelaySeconds: 15
              periodSeconds: 20
              failureThreshold: 3
              timeoutSeconds: 5
            }
            {
              type: 'Readiness'

              httpGet: {
                path: '/readiness'
                port: 80
                scheme: 'HTTP'
              }
              failureThreshold: 3
              timeoutSeconds: 5
            }
            {
              type: 'Startup'
              httpGet: {
                path: '/startup'
                port: 80
                scheme: 'HTTP'
              }
              failureThreshold: 3
              timeoutSeconds: 2
            }
          ] */
        }
      ]
      scale: {
        minReplicas: 1
      }
    }
  }
  dependsOn: [
    uaiRbacAcrPull
    keyVaultContributorRoleAssignment
  ]
}

module spotifyMcpAppFetchLatestImage './modules/fetch-container-image.bicep' = {
  name: 'spotify-mcp-fetch-image'
  params: {
    exists: isLatestImageExist
    name: 'spotify-mcp'
  }
}

resource spotifyMcpApp 'Microsoft.App/containerApps@2024-10-02-preview' = {
  name: 'spotify-mcp'
  location: location
  tags: { 'azd-service-name': 'spotify-mcp-server', 'azd-env-name': environmentName }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${uaiAcrPull.id}': {}
      '${azrKeyVaultContributor.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          exposeHeaders: ['*']
          allowCredentials: false
        }
      }
      registries: [
        {
          identity: uaiAcrPull.id
          server: acr.properties.loginServer
        }
      ]
      secrets: [
        {
          name: 'applicationinsights-connectionstring'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/APPLICATIONINSIGHTS-CONNECTIONSTRING'
          identity: azrKeyVaultContributor.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'spotify-mcp'
          image: spotifyMcpAppFetchLatestImage.outputs.?containers[?0].?image ?? 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: [
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'applicationinsights-connectionstring'
            }
          ]
          /* probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/liveness'
                port: 80
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/readiness'
                port: 80
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              failureThreshold: 3
            }
          ] */
        }
      ]
      scale: {
        minReplicas: 1
      }
    }
  }
  dependsOn: [
    uaiRbacAcrPull
    keyVaultContributorRoleAssignment
  ]
}

resource setlistAgentpApp 'Microsoft.App/containerApps@2024-10-02-preview' = {
  name: 'setlist-agent'
  location: location
  tags: { 'azd-service-name': 'setlist-agent', 'azd-env-name': environmentName }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${uaiAcrPull.id}': {}
      '${azrKeyVaultContributor.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          exposeHeaders: ['*']
          allowCredentials: false
        }
      }
      registries: [
        {
          identity: uaiAcrPull.id
          server: acr.properties.loginServer
        }
      ]
      secrets: [
        {
          name: 'spotify-client-id'
          keyVaultUrl: secretSpotifyClientId.properties.secretUri
          identity: azrKeyVaultContributor.id
        }
        {
          name: 'spotify-client-secret'
          keyVaultUrl: secretSpotifyClientSecret.properties.secretUri
          identity: azrKeyVaultContributor.id
        }

        {
          name: 'applicationinsights-connectionstring'
          keyVaultUrl: '${kv.properties.vaultUri}secrets/APPLICATIONINSIGHTS-CONNECTIONSTRING'
          identity: azrKeyVaultContributor.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'setlist-agent'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: [
            {
              name: 'AZURE_AI_INFERENCE_API_KEY'
              value: listKeys(aiFoundry.id, '2025-04-01-preview').key1
            }
            {
              name: 'AZURE_AI_INFERENCE_ENDPOINT'
              value: '${aiFoundry.properties.endpoints['Azure AI Model Inference API']}/models'
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT_NAME'
              value: modelDeploymentsParameters[0].name
            }
            {
              name: 'PROJECT_ENDPOINT'
              value: project.properties.endpoints['AI Foundry API']
            }
            {
              name: 'SPOTIFY_MCP_URL_2'
              value: 'https://${spotifyMcpApp.properties.configuration.ingress.fqdn}/sse'
            }
            {
              name: 'SETLISTFM_MCP_URL_2'
              value: 'https://${setlistfmMcpApp.properties.configuration.ingress.fqdn}/sse'
            }
            {
              name: 'SPOTIFY_MCP_URL'
              value: 'http://${spotifyMcpApp.name}/sse'
            }
            {
              name: 'SETLISTFM_MCP_URL'
              value: 'http://${setlistfmMcpApp.name}/sse'
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
          ]
        }
      ]
      scale: {
        minReplicas: 1
      }
    }
  }
  dependsOn: [
    uaiRbacAcrPull
    keyVaultContributorRoleAssignment
  ]
}

// Assign the Key Vault Secrets Officer role to the managed identity
resource keyVaultContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(kv.id, azrKeyVaultContributor.id, 'Key Vault Contributor Role')
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets Officer
    )
    principalId: azrKeyVaultContributor.properties.principalId
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
  name: '${rootname}-${aiFoundryLocation}-ai-foundry'
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
    customSubDomainName: '${rootname}-${aiFoundryLocation}-ai-foundry'
    publicNetworkAccess: 'Enabled'

    //disableLocalAuth: true
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiFoundry
  name: 'setlist-agent-${aiFoundryLocation}'
  location: aiFoundryLocation
  properties: {
    description: 'a world of music'
    displayName: 'setlist-agent'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

@description('Model deployments for OpenAI')
param modelDeploymentsParameters array = [
  {
    name: '${rootname}-gpt-4o'
    model: 'gpt-4o'
    capacity: 120
    deployment: 'Standard'
    version: '2024-11-20'
  }
  {
    name: '${rootname}-gpt-4o-global'
    model: 'gpt-4o'
    capacity: 50
    deployment: 'GlobalStandard'
    version: '2024-11-20'
  }
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
        format: 'OpenAI'
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
output SPOTIFY_MCP_URL string = 'https://${spotifyMcpApp.properties.configuration.ingress.fqdn}/sse'
output SETLISTFM_MCP_URL string = 'https://${setlistfmMcpApp.properties.configuration.ingress.fqdn}/sse'
output SETLIST_AGENT_URL string = 'https://${setlistAgentpApp.properties.configuration.ingress.fqdn}'

output AZURE_OPENAI_ENDPOINT string = aiFoundry.properties.customSubDomainName
output OAUTH_SPOTIFY_CLIENT_ID string = spotifyClientId
output OAUTH_SPOTIFY_CLIENT_SECRET string = spotifyClientSecret
output OAUTH_SPOTIFY_SCOPES string = 'user-read-private user-read-email user-library-read user-top-read playlist-read-private playlist-modify-public playlist-modify-private'

output AZURE_OPENAI_CHAT_DEPLOYMENT_NAME string = modelDeploymentsParameters[0].name
output AZURE_OPENAI_MODEL string = modelDeploymentsParameters[0].model
output AZURE_OPENAI_API_VERSION string = modelDeploymentsParameters[0].version
//output AZURE_OPENAI_API_KEY string = '-2'

output PROJECT_ENDPOINT string = project.properties.endpoints['AI Foundry API']
output AZURE_AI_INFERENCE_ENDPOINT string = '${aiFoundry.properties.endpoints['Azure AI Model Inference API']}models'
output AZURE_AI_INFERENCE_API_KEY string = listKeys(aiFoundry.id, '2025-04-01-preview').key1
output MODEL_DEPLOYMENT_NAME string = modelDeploymentsParameters[0].name

output APPLICATIONINSIGHTS_CONNECTION_STRING string = applicationInsights.outputs.connectionString
output CHAINLIT_AUTH_SECRET string = chainlitAuthSecret
