@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string = 'francecentral'

@description('Location for AI Foundry resources.')
param aiFoundryLocation string = 'swedencentral' //'westus' 'switzerlandnorth' swedencentral

@description('Name of the resource group to deploy to.')
param rootname string = 'mysetlistagent'

@description('Spotify Client ID for MCP Spotify microservice.')
param spotifyClientId string

@description('Spotify Client Secret for MCP Spotify microservice.')
@secure()
param spotifyClientSecret string

@description('SetlistFM API Key for MCP SetlistFM microservice.')
@secure()
param setlistfmApiKey string

@description('Indicates if the latest image for the Spotify MCP microservice exists in the ACR.')
param isLatestImageExist bool = false

var chainlitAuthSecret = 'v.tT081gp@T9$mRHr4XWs/uk2R8mqI5dSo@R2AO_Rj63t5P$3T,x4aN,Shpo@~'

// tags that should be applied to all resources.
var tags = {
  // Tag all resources with the environment name.
  'azd-env-name': environmentName
}

#disable-next-line no-unused-vars
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

module setlistFmApi 'modules/apim/v1/api.bicep' = {
  name: 'setlistfm-api'
  params: {
    apimName: apiManagement.outputs.name
    appInsightsId: applicationInsights.outputs.aiId
    appInsightsInstrumentationKey: applicationInsights.outputs.instrumentationKey
    api: {
      name: 'setlistfm'
      description: 'SetlistFM API'
      displayName: 'SetlistFM API'
      path: '/setlistfm'
      serviceUrl: 'https://api.setlist.fm/rest'
      subscriptionRequired: true
      tags: ['setlistfm', 'api', 'music', 'setlist']
      policyXml: loadTextContent('../src/apim/setlistfm/policy-setlistfm.xml')
      openApiJson: loadTextContent('../src/apim/setlistfm/openapi-setlistfm.json')
    }
  }
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

module spotifyApi 'modules/apim/v1/api.bicep' = {
  name: 'spotify-api'
  params: {
    apimName: apiManagement.outputs.name
    appInsightsId: applicationInsights.outputs.aiId
    appInsightsInstrumentationKey: applicationInsights.outputs.instrumentationKey
    api: {
      name: 'spotify'
      description: 'Spotify API'
      displayName: 'Spotify API'
      path: '/spotify'
      serviceUrl: 'https://api.spotify.com/v1'
      subscriptionRequired: true
      tags: ['spotify', 'api', 'music', 'setlist']
      policyXml: loadTextContent('../src/apim/spotify/policy-spotify.xml')
      openApiJson: loadYamlContent('../src/apim/spotify/sonallux-spotify-open-api.yml')
    }
  }
}

module oauthSpotify 'modules/api-mgt-oauth.bicep' = {
  name: 'oauth-spotify'
  params: {
    apimName: apiManagement.outputs.name
    clientId: spotifyClientId
    clientSecret: spotifyClientSecret
    scopes: 'user-read-private user-read-email user-library-read user-top-read playlist-read-private playlist-modify-public playlist-modify-private user-follow-read user-follow-modify streaming'
  }
}

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
        value: aiFoundry.outputs.aiFoundryInferenceKey
      }
      {
        name: 'AZURE_AI_INFERENCE_ENDPOINT'
        value: aiFoundry.outputs.aiFoundryInferenceEndpoint
      }
      {
        name: 'MODEL_DEPLOYMENT_NAME'
        value: aiFoundry.outputs.defaultModelDeploymentName
      }
      {
        name: 'PROJECT_ENDPOINT'
        value: aiFoundry.outputs.aiFoundryEndpoint
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

module setlistfmAgentApp 'modules/mcp-container-app.bicep' = {
  name: 'setlistfm-agent'
  params: {
    name: 'setlistfm-agent'
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
        name: 'PROJECT_ENDPOINT'
        value: aiFoundryProject.outputs.projectEndpoint
      }
      {
        name: 'MODEL_DEPLOYMENT_NAME'
        value: aiFoundry.outputs.defaultModelDeploymentName
      }
      {
        name: 'AZURE_CLIENT_ID'
        value: containerApplicationIdentity.properties.clientId
      }
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        secretRef: 'applicationinsights-connectionstring'
      }
      {
        name: 'SETLISTFM_API_KEY'
        secretRef: 'setlistfm-api-key'
      }
      {
        name: 'AZURE_LOG_LEVEL'
        value: 'INFO'
      }
      {
        name: 'AZURE_MONITOR_OPENTELEMETRY_ENABLED'
        value: 'true'
      }
      {
        name: 'AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED'
        value: 'true'
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
    projectName: aiFoundry.outputs.aiFoundryName
    applicationInsightsName: applicationInsights.outputs.aiName
  }
}

module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'aiFoundryModel'
  params: {
    name: 'foundry-${rootname}-${aiFoundryLocation}-${environmentName}'
    location: aiFoundryLocation
    modelDeploymentsParameters: [
      {
        name: '${rootname}-gpt-4.1-mini'
        model: 'gpt-4.1-mini'
        capacity: 1000
        deployment: 'GlobalStandard'
        version: '2025-04-14'
        format: 'OpenAI'
      }
    ]
  }
}

/*
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
*/

module aiFoundryProject 'modules/ai-foundry-project.bicep' = {
  name: 'aiFoundryProject'
  params: {
    location: aiFoundryLocation
    aiFoundryName: aiFoundry.outputs.aiFoundryName
    aiProjectName: 'prj-${rootname}-${aiFoundryLocation}-${environmentName}'
    aiProjectFriendlyName: 'Setlistfy Project ${environmentName}'
    aiProjectDescription: 'Agents to help to manage setlist and music events.'

    applicationInsightsName: applicationInsights.outputs.name
    bingSearchServiceName: bingSearch.outputs.bingSearchServiceName
    customKey: {
      name: setlistFmApi.outputs.apiName
      target: 'https://${apiManagement.outputs.apiManagementProxyHostName}/${setlistFmApi.outputs.apiPath}'
      authKey: setlistFmApi.outputs.subscriptionPrimaryKey
    }
  }
}

/*
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
*/

module bingSearch 'modules/bing-search.bicep' = {
  name: 'bing-search'
  params: {
    bingSearchServiceName: 'bing-${rootname}-${environmentName}'
  }
}

module apiManagement 'modules/api-management.bicep' = {
  name: 'api-management'
  params: {
    location: location
    serviceName: '${rootname}-api-management-${environmentName}'
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

/*
module spotifyAuth 'modules/api-mgt-oauth.bicep' = {
  name: 'spotify-auth'
  params: {
    apimName: apiManagement.outputs.name

    appInsightsName: applicationInsights.outputs.name
    clientId: 'caf00b6f5a5747e6895ad912357fd11b'
    clientSecret: '6dfe303ac16641bc971f482ea748441c'
    namedValues: [
      {
        name: 'JwtSigningKey-spotify-auth-2'
        value: 'VUpwY3lvOEJPZUxOZjBtQjlIY3Y4alJDMHY1aEt4dHp2RW9XQVFCeXJ1MzloOEhaYzh5TnNCZ3JZWUZYRVhES3pqelhsZHVGZ2pwcHFFS1A3OVh1dnpnYlRINA=='
        isSecret: true
      }
      {
        name: 'MarketingMemberRoleId'
        value: 'b2c3d4e5-f6g7-8h9i-0j1k-2l3m4n5o6p7q'
        isSecret: false
      }
    ]
    apis: [
      {
        name: 'oauth-3rd-party-spotify'
        displayName: 'Spotify'
        path: '/oauth-3rd-party-spotify'
        description: 'This is the API for interactions with the Spotify REST API'
        operations: [
          {
            name: 'artists-get'
            displayName: 'Artists'
            urlTemplate: '/artists/{id}'
            description: 'Gets the artist by their ID'
            method: 'GET'
            policyXml: '<!--\n    This policy retrieves artist information from Spotify.\n-->\n<policies>\n    <inbound>\n        <base />\n        <rewrite-uri template="/artists/{id}" copy-unmatched-params="false" />\n    </inbound>\n    <backend>\n        <base />\n    </backend>\n    <outbound>\n        <base />\n    </outbound>\n    <on-error>\n        <base />\n    </on-error>\n</policies>'
            templateParameters: [
              {
                name: 'id'
                description: 'The Spotify ID of the artist'
                type: 'string'
                required: true
              }
            ]
          }
        ]
        serviceUrl: null
        subscriptionRequired: true
        policyXml: '<!--\n    Spotify API All Operations\n    \n    This policy uses APIM Credential Manager to handle OAuth authentication with the Spotify REST API.\n    The credential manager automatically handles token acquisition and refresh.\n-->\n<policies>\n    <inbound>\n        <base />\n        <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized" output-token-variable-name="jwt">\n            <issuer-signing-keys>\n                <key>{{JwtSigningKey-spotify-auth}}</key>\n            </issuer-signing-keys>\n                   </validate-jwt>\n\n        <!-- Get OAuth token using Credential Manager -->\n        <get-authorization-context provider-id="spotify" authorization-id="spotify-auth" context-variable-name="auth-context" identity-type="managed" ignore-error="false" />\n        \n        <!-- Set Authorization header with OAuth token -->\n        <set-header name="Authorization" exists-action="override">\n            <value>@("Bearer " + ((Authorization)context.Variables.GetValueOrDefault("auth-context"))?.AccessToken)</value>\n        </set-header>\n        \n        <!-- Set backend service to Spotify API -->\n        <set-backend-service base-url="https://api.spotify.com/v1" />\n    </inbound>\n    <backend>\n        <base />\n    </backend>\n    <outbound>\n        <base />\n        <!-- Remove Authorization header from response for security -->\n        <set-header name="Authorization" exists-action="delete" />\n    </outbound>\n    <on-error>\n        <base />\n        <!-- Handle OAuth authorization errors -->\n        <choose>\n            <when condition="@(context.LastError.Source == "get-authorization-context")">\n                <set-status code="401" reason="OAuth Authorization Failed" />\n                <set-body>@{\n                    return new JObject(\n                        new JProperty("error", "oauth_authorization_failed"),\n                        new JProperty("error_description", "Failed to acquire OAuth token from Spotify"),\n                        new JProperty("timestamp", DateTime.UtcNow),\n                        new JProperty("requestId", context.RequestId)\n                    ).ToString();\n                }</set-body>\n            </when>\n        </choose>\n    </on-error>\n</policies>'
        tags: [
          'oauth-3rd-party'
          'jwt'
          'credential-manager'
          'policy-fragment'
        ]
        productNames: []
      }
    ]
  }
}

output spotifyOAuthRedirectUrl string = spotifyAuth.outputs.spotifyOAuthRedirectUrl
output apim_name string = spotifyAuth.outputs.apimServiceName
output apimResourceGatewayURL string = spotifyAuth.outputs.apimResourceGatewayURL
*/
/*
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
  */

output spotifyOAuthRedirectUrl string = oauthSpotify.outputs.spotifyOAuthRedirectUrl
output apim_name string = oauthSpotify.outputs.apimServiceName
output apimResourceGatewayURL string = oauthSpotify.outputs.apimResourceGatewayURL

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.properties.loginServer
output SPOTIFY_MCP_URL string = 'https://${spotifyMcpApp.outputs.fqdn}/sse'
output SETLISTFM_MCP_URL string = 'https://${setlistfmMcpApp.outputs.fqdn}/sse'
output SETLIST_AGENT_URL string = 'https://${setlistAgentpApp.outputs.fqdn}'
output SETLISTFM_AGENT_URL string = 'https://${setlistfmAgentApp.outputs.fqdn}'

//output AZURE_OPENAI_ENDPOINT string = aiFoundry.properties.customSubDomainName
output OAUTH_SPOTIFY_CLIENT_ID string = spotifyClientId
output OAUTH_SPOTIFY_CLIENT_SECRET string = spotifyClientSecret
output OAUTH_SPOTIFY_SCOPES string = 'user-read-private user-read-email user-library-read user-top-read playlist-read-private playlist-modify-public playlist-modify-private'

output PROJECT_ENDPOINT string = aiFoundryProject.outputs.projectEndpoint
output AZURE_AI_INFERENCE_ENDPOINT string = aiFoundry.outputs.aiFoundryInferenceEndpoint
output AZURE_AI_INFERENCE_API_KEY string = aiFoundry.outputs.aiFoundryInferenceKey
output MODEL_DEPLOYMENT_NAME string = aiFoundry.outputs.defaultModelDeploymentName

output APPLICATIONINSIGHTS_CONNECTION_STRING string = applicationInsights.outputs.connectionString

output CHAINLIT_AUTH_SECRET string = chainlitAuthSecret
output AZURE_CLIENT_ID string = containerApplicationIdentity.properties.clientId
output AZURE_LOG_LEVEL string = 'DEBUG'
output SETLISTFM_API_KEY string = setlistfmApiKey
