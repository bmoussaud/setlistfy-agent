param kvName string
param projectName string
param applicationInsightsName string

resource kv 'Microsoft.KeyVault/vaults@2024-04-01-preview' existing = {
  name: kvName
}

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: projectName
}

resource ai 'Microsoft.Insights/components@2020-02-02-preview' existing = {
  name: applicationInsightsName
}

@description('This is the built-in Key Vault Secrets Officer role. See https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/security#key-vault-secrets-user')
resource keyVaultSecretsUserRoleDefinition 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  scope: subscription()
  name: '4633458b-17de-408a-b874-0445c86b69e6'
}

//https://praveenkumarsreeram.com/2024/12/12/introducing-az-deployer-objectid-in-bicep-track-object-principle-id-of-user-managed-identity/
//https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/bicep-functions-deployment#deployer
//Not implemented yet in AZD https://github.com/Azure/azure-dev/issues/4620
@description('Assigns the API Management service the role to browse and read the keys of the Key Vault to the deployer')
//seful to check information about the KN in the Azure portal 
resource keyVaultSecretUserRoleAssignmentOnDeployer 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(kv.id, 'Deployer', keyVaultSecretsUserRoleDefinition.id)
  scope: kv
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleDefinition.id
    //Principal ID of the current user
    principalId: az.deployer().objectId
  }
}

resource contributor 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  scope: subscription()
  name: 'b24988ac-6180-42a0-ab88-20f7382dd24c' // Project Reader role
}

resource monitoringMetricsPublisher 'Microsoft.Authorization/roleDefinitions@2018-01-01-preview' existing = {
  scope: subscription()
  name: '3913510d-42f4-4e42-8a64-420c390055eb' // Monitoring Metrics Publisher role
}

//allow the deployer to manage the AI Foundry instance
//https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/cognitive-services-account-contributor
resource aiFoundryRoleAssignmentOnDeployer 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(aiFoundry.id, 'Deployer', contributor.id)
  scope: aiFoundry
  properties: {
    roleDefinitionId: contributor.id
    //Principal ID of the current user
    principalId: az.deployer().objectId
  }
}

//allow the deployer to send metrics to the Application Insights instance
//https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/monitoring-metrics-publisher
resource aiRoleAssignmentOnDeployer 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(ai.id, 'Deployer', monitoringMetricsPublisher.id)
  scope: ai
  properties: {
    roleDefinitionId: monitoringMetricsPublisher.id
    //Principal ID of the current user
    principalId: az.deployer().objectId
  }
}
