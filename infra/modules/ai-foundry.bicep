// Module: AI Foundry Model (placeholder)
param name string
param location string

@description('Model deployments for OpenAI')
param modelDeploymentsParameters array

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: name
  location: location
  tags: {
    'azd-service-name': 'ai-foundry'
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
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
    //disableLocalAuth: true
  }
}

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

output aiFoundryId string = aiFoundry.id

output modelDeploymentsName string = modelDeploymentsParameters[0].name
output aiFoundryName string = aiFoundry.name
output aiFoundryEndpoint string = aiFoundry.properties.endpoint
output aiFoundryLocation string = aiFoundry.location
output aiFoundryInferenceEndpoint string = '${aiFoundry.properties.endpoints['Azure AI Model Inference API']}models'
output defaultModelDeploymentName string = modelDeploymentsParameters[0].name
output aiFoundryInferenceKey string = listKeys(aiFoundry.id, '2025-04-01-preview').key1
