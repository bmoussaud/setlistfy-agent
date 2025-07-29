/**
 * @module backend-v1
 * @description This module defines the Azure API Management (APIM) backend resources using Bicep.
 */


// ------------------------------
//    PARAMETERS
// ------------------------------

@description('The name of the API Management instance.')
param apimName string

@description('The name of the backend.')
param backendName string

@description('The URL of the backend service (e.g., ACA public FQDN).')
param url string


// ------------------------------
//    RESOURCES
// ------------------------------

// https://learn.microsoft.com/azure/templates/microsoft.apimanagement/service
resource apimService 'Microsoft.ApiManagement/service@2024-06-01-preview' existing = {
  name: apimName
}

// https://learn.microsoft.com/azure/templates/microsoft.apimanagement/service/backends
resource backend 'Microsoft.ApiManagement/service/backends@2024-06-01-preview' = {
  name: backendName
  parent: apimService
  properties: {
    url: url
    description: 'This is the backend for ${backendName}'
    protocol: 'http'
    circuitBreaker: {
      rules: [
        {
          failureCondition: {
            count: 1
            errorReasons: [
              'Server errors'
            ]
            interval: 'PT5M'
            statusCodeRanges: [
              {
                min: 429
                max: 429
              }
            ]
          }
          name: 'backend-circuit-breaker'
          tripDuration: 'PT1M'
          acceptRetryAfter: true
        }
      ]
    }
  }
}


// ------------------------------
//    OUTPUTS
// ------------------------------

output backendId string = backend.id
output backendName string = backend.name
