@description('The location into which the API Management resources should be deployed.')
param location string

@description('The name of the API Management service instance to create. This must be globally unique.')
param serviceName string

@description('The name of the API publisher. This information is used by API Management.')
param publisherName string

@description('The email address of the API publisher. This information is used by API Management.')
param publisherEmail string

param aiName string

//param eventHubNamespaceName string
//param eventHubName string

@description('The name of the SKU to use when creating the API Management service instance. This must be a SKU that supports virtual network integration.')
param skuName string

@description('The number of worker instances of your API Management service that should be provisioned.')
param skuCount int

resource aiParent 'Microsoft.Insights/components@2020-02-02-preview' existing = {
  name: aiName
}

resource apiManagementService 'Microsoft.ApiManagement/service@2023-03-01-preview' = {
  name: serviceName
  location: location
  sku: {
    name: skuName
    capacity: skuCount
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publisherName: publisherName
    publisherEmail: publisherEmail
  }
}

resource aiLogger 'Microsoft.ApiManagement/service/loggers@2022-08-01' = {
  name: 'aiLogger'
  parent: apiManagementService
  properties: {
    loggerType: 'applicationInsights'
    description: 'Application Insights logger'
    credentials: {
      instrumentationKey: aiParent.properties.InstrumentationKey
    }
  }
}
//define a new product 'Starter' with a subscription required
resource starterProduct 'Microsoft.ApiManagement/service/products@2023-03-01-preview' = {
  name: 'Starter'
  parent: apiManagementService
  properties: {
    displayName: 'Starter'
    description: 'Starter product'
    terms: 'Subscription is required for this product.'
  }
}

//define a new Product 'Unlimited' with no subscription required
resource unlimitedProduct 'Microsoft.ApiManagement/service/products@2023-03-01-preview' = {
  name: 'Unlimited'
  parent: apiManagementService
  properties: {
    displayName: 'Unlimited'
    description: 'Unlimited product'
    terms: 'No subscription required for this product.'
  }
}

/*
resource adminUser 'Microsoft.ApiManagement/service/users/subscriptions@2023-05-01-preview' existing = {
  name: '/users/1'
}

resource apiAdminSubscription 'Microsoft.ApiManagement/service/subscriptions@2023-03-01-preview' = {
  name: 'azure-rambi-admin-sub'
  parent: apiManagementService
  properties: {
    allowTracing: false
    displayName: 'azure-rambi-admin-sub'
    ownerId: adminUser.id
    state: 'active'
    scope: '/apis'
  }
}
  */
resource allAPIsSubscription 'Microsoft.ApiManagement/service/subscriptions@2023-03-01-preview' = {
  name: 'allAPIs'
  parent: apiManagementService
  properties: {
    allowTracing: false
    displayName: 'Built-in all-access subscription'
    //ownerId: 
    state: 'active'
    scope: '/apis'
  }
}

//Allow the customs metrics at the application insight level.
//https://learn.microsoft.com/en-us/azure/api-management/api-management-howto-app-insights?tabs=rest#emit-custom-metrics
resource applicationinsights 'Microsoft.ApiManagement/service/diagnostics@2023-03-01-preview' = {
  name: 'applicationinsights'
  parent: apiManagementService
  properties: {
    metrics: true
    loggerId: aiLogger.id
  }
}

//output apiManagementInternalIPAddress string = apiManagementService.properties.publicIPAddresses[0]
output apiManagementIdentityPrincipalId string = apiManagementService.identity.principalId
output name string = apiManagementService.name
output apiManagementProxyHostName string = apiManagementService.properties.hostnameConfigurations[0].hostName
//output apiManagementDeveloperPortalHostName string = replace(apiManagementService.properties.developerPortalUrl, 'https://', '')
output aiLoggerId string = aiLogger.id
output apiAdminSubscriptionKey string = allAPIsSubscription.listSecrets().primaryKey
