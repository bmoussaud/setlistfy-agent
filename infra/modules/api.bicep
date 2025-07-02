param apimName string
param apiName string
param apiPath string
param openApiJson string
param openApiXml string
param serviceUrlPrimary string

param aiLoggerName string

resource parentAPIM 'Microsoft.ApiManagement/service@2023-03-01-preview' existing = {
  name: apimName
}

resource aiLogger 'Microsoft.ApiManagement/service/loggers@2022-08-01' existing = {
  name: aiLoggerName
  parent: parentAPIM
}

resource starterProduct 'Microsoft.ApiManagement/service/products@2023-03-01-preview' existing = {
  name: 'Starter'
  parent: parentAPIM
}

resource unlimitedProduct 'Microsoft.ApiManagement/service/products@2023-03-01-preview' existing = {
  name: 'Unlimited'
  parent: parentAPIM
}

resource primarybackend 'Microsoft.ApiManagement/service/backends@2023-03-01-preview' = {
  name: '${apiName}-backend'
  parent: parentAPIM
  properties: {
    description: '$apiName endpoint'
    protocol: 'http'
    url: serviceUrlPrimary
  }
}

resource api 'Microsoft.ApiManagement/service/apis@2023-03-01-preview' = {
  parent: parentAPIM
  name: apiName
  properties: {
    format: 'openapi+json-link'
    value: openApiJson
    path: apiPath
    protocols: [
      'https'
    ]
    subscriptionKeyParameterNames: {
      header: 'api-key'
      query: 'api-key'
    }
    subscriptionRequired: true
  }
}

resource APIunlimitedProduct 'Microsoft.ApiManagement/service/products/apis@2023-05-01-preview' = {
  name: apiName
  parent: unlimitedProduct
  dependsOn: [api]
}

resource APIstarterProduct 'Microsoft.ApiManagement/service/products/apis@2023-05-01-preview' = {
  name: apiName
  parent: starterProduct
  dependsOn: [api]
}

resource apiPolicy 'Microsoft.ApiManagement/service/apis/policies@2024-06-01-preview' = {
  parent: api
  name: 'policy'
  properties: {
    format: 'xml-link'
    value: openApiXml
  }
}

resource apiDiagnostics 'Microsoft.ApiManagement/service/apis/diagnostics@2024-06-01-preview' = {
  parent: api
  name: 'applicationinsights'
  properties: {
    alwaysLog: 'allErrors'
    loggerId: aiLogger.id
    //metrics: true + verbosity: information equals Support custom metrics <<<< not enough information :(
    metrics: true
    verbosity: 'information'
    sampling: {
      samplingType: 'fixed'
      percentage: 100
    }
    frontend: {
      request: {
        headers: []
        body: {
          bytes: 0
        }
      }
      response: {
        headers: []
        body: {
          bytes: 0
        }
      }
    }
    backend: {
      request: {
        headers: []
        body: {
          bytes: 0
        }
      }
      response: {
        headers: []
        body: {
          bytes: 0
        }
      }
    }
  }
}

//resource adminUser 'Microsoft.ApiManagement/service/users/subscriptions@2023-05-01-preview' existing = {
//  name: '/users/1'
//}

/*
resource apiSubscription 'Microsoft.ApiManagement/service/subscriptions@2023-03-01-preview' = {
  name: apiSubscriptionName
  parent: parentAPIM
  properties: {
    allowTracing: false
    displayName: apiSubscriptionName
    ownerId: adminUser.id
    scope: api.id
    state: 'active'
  }
}
*/

//output apiSubscription string = apiSubscription.listSecrets().primaryKey
