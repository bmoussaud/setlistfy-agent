// ------------------
//    PARAMETERS
// ------------------

@description('The name of the API Management instance.".')
param apimName string

@description('scopes for Spotify API')
param scopes string = 'user-read-recently-played'

// OAuth Parameters
@description('The OAuth client ID for Spotify API')
param clientId string

@description('The OAuth client secret for Spotify API')
@secure()
param clientSecret string

// ------------------
//    RESOURCES
// ------------------

// https://learn.microsoft.com/azure/templates/microsoft.apimanagement/service
resource apimService 'Microsoft.ApiManagement/service@2024-06-01-preview' existing = {
  name: apimName
}

// https://learn.microsoft.com/azure/templates/microsoft.apimanagement/service/authorizationproviders
resource spotifyAuthorizationProvider 'Microsoft.ApiManagement/service/authorizationProviders@2024-06-01-preview' = {
  name: 'spotify'
  parent: apimService
  properties: {
    displayName: 'spotify'
    identityProvider: 'oauth2pkce'
    oauth2: {
      redirectUrl: 'https://authorization-manager.consent.azure-apim.net/redirect/apim/${apimName}'
      grantTypes: {
        authorizationCode: {
          clientId: clientId
          clientSecret: clientSecret
          scopes: scopes
          authorizationUrl: 'https://accounts.spotify.com/authorize'
          refreshUrl: 'https://accounts.spotify.com/api/token'
          tokenUrl: 'https://accounts.spotify.com/api/token'
        }
      }
    }
  }
}

// https://learn.microsoft.com/en-us/azure/templates/microsoft.apimanagement/service/authorizationproviders/authorizations
resource spotifyAuthorization 'Microsoft.ApiManagement/service/authorizationProviders/authorizations@2024-06-01-preview' = {
  parent: spotifyAuthorizationProvider
  name: 'spotify-auth'
  properties: {
    authorizationType: 'OAuth2'
    oauth2grantType: 'AuthorizationCode'
  }
}

// https://learn.microsoft.com/en-us/azure/templates/microsoft.apimanagement/service/authorizationproviders/authorizations/accesspolicies
resource spotifyAccessPolicies 'Microsoft.ApiManagement/service/authorizationProviders/authorizations/accessPolicies@2024-06-01-preview' = {
  parent: spotifyAuthorization
  name: 'spotify-auth-access-policies'
  properties: {
    objectId: apimService.identity.principalId // APIM managed identity principal ID
    tenantId: tenant().tenantId
  }
}

// ------------------
//    MARK: OUTPUTS
// ------------------

output apimServiceId string = apimService.id
output apimServiceName string = apimService.name
output apimResourceGatewayURL string = apimService.properties.gatewayUrl
output spotifyOAuthRedirectUrl string = spotifyAuthorizationProvider.properties.oauth2.redirectUrl
