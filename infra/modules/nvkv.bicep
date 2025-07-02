param apimName string
param keyName string
param secretName string
param keyVaultName string

resource parentAPIM 'Microsoft.ApiManagement/service@2023-03-01-preview' existing = {
  name: apimName
}

resource kv 'Microsoft.KeyVault/vaults@2021-10-01' existing = {
  name: keyVaultName
}

resource apiKey 'Microsoft.ApiManagement/service/namedValues@2021-08-01' = {
  name: keyName
  parent: parentAPIM
  properties: {
    displayName: keyName
    secret: true
    keyVault: {
      secretIdentifier: '${kv.properties.vaultUri}secrets/${secretName}'
    }
  }
}
