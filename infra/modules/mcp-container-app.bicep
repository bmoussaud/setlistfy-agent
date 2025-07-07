@description('Parameters for deploying an MCP microservice as a Container App')
param name string
param location string
param managedEnvironmentId string
param acrLoginServer string
param identityId string
param secrets array
param envVars array

param isLatestImageExist bool = false

module fetchLatestImage 'fetch-container-image.bicep' = {
  name: '${name}-fetch-image'
  params: {
    exists: isLatestImageExist
    name: 'spotify-mcp-server'
  }
}

resource mcpApp 'Microsoft.App/containerApps@2024-10-02-preview' = {
  name: name
  location: location
  tags: { 'azd-service-name': name }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: managedEnvironmentId
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
          identity: identityId
          server: acrLoginServer
        }
      ]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: name
          image: fetchLatestImage.outputs.?containers[?0].?image ?? 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: envVars
        }
      ]
      scale: {
        minReplicas: 1
      }
    }
  }
}

output containerAppName string = mcpApp.name
output fqdn string = mcpApp.properties.configuration.ingress.fqdn
