/**
 * @module backend-pool-v1
 * @description This module defines the Azure API Management (APIM) backend pool using Bicep.
 */


// ------------------------------
//    PARAMETERS
// ------------------------------

@description('The name of the API Management instance.')
param apimName string

@description('The name of the backend pool')
param backendPoolName string

@description('The description of the backend pool.')
param backendPoolDescription string = 'Backend pool'

@description('The backends to add to the backend pool.')
param backends array = []


// ------------------------------
//    RESOURCES
// ------------------------------

// https://learn.microsoft.com/azure/templates/microsoft.apimanagement/service
resource apimService 'Microsoft.ApiManagement/service@2024-06-01-preview' existing = {
  name: apimName
}

// https://learn.microsoft.com/azure/templates/microsoft.apimanagement/service/backends
resource backendPool1 'Microsoft.ApiManagement/service/backends@2024-06-01-preview' = {
  name: backendPoolName
  parent: apimService
  // BCP035: protocol and url are not needed in the Pool type. This is an incorrect error.
  #disable-next-line BCP035
  properties: {
    description: backendPoolDescription
    type: 'Pool'
    pool: {
      services: [for (backend, i) in backends: {
        id: '/backends/${backend.name}'
        priority: backend.priority
        weight: backend.weight
      }]
    }
  }
}


// ------------------------------
//    OUTPUTS
// ------------------------------
