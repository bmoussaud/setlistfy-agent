

param apis = [
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
    policyXml: '<!--\n    Spotify API All Operations\n    \n    This policy uses APIM Credential Manager to handle OAuth authentication with the Spotify REST API.\n    The credential manager automatically handles token acquisition and refresh.\n-->\n<policies>\n    <inbound>\n        <base />\n        <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized" output-token-variable-name="jwt">\n            <issuer-signing-keys>\n                <key>{{JwtSigningKey-/workspaces/setlistfy-agent/src/oauth-3rd-party-1753777378}}</key>\n            </issuer-signing-keys>\n            <required-claims>\n                <claim name="roles" match="all">\n                    <value>{{MarketingMemberRoleId}}</value>\n                </claim>\n            </required-claims>\n        </validate-jwt>\n\n        <!-- Get OAuth token using Credential Manager -->\n        <get-authorization-context provider-id="spotify" authorization-id="spotify-auth" context-variable-name="auth-context" identity-type="managed" ignore-error="false" />\n        \n        <!-- Set Authorization header with OAuth token -->\n        <set-header name="Authorization" exists-action="override">\n            <value>@("Bearer " + ((Authorization)context.Variables.GetValueOrDefault("auth-context"))?.AccessToken)</value>\n        </set-header>\n        \n        <!-- Set backend service to Spotify API -->\n        <set-backend-service base-url="https://api.spotify.com/v1" />\n    </inbound>\n    <backend>\n        <base />\n    </backend>\n    <outbound>\n        <base />\n        <!-- Remove Authorization header from response for security -->\n        <set-header name="Authorization" exists-action="delete" />\n    </outbound>\n    <on-error>\n        <base />\n        <!-- Handle OAuth authorization errors -->\n        <choose>\n            <when condition="@(context.LastError.Source == "get-authorization-context")">\n                <set-status code="401" reason="OAuth Authorization Failed" />\n                <set-body>@{\n                    return new JObject(\n                        new JProperty("error", "oauth_authorization_failed"),\n                        new JProperty("error_description", "Failed to acquire OAuth token from Spotify"),\n                        new JProperty("timestamp", DateTime.UtcNow),\n                        new JProperty("requestId", context.RequestId)\n                    ).ToString();\n                }</set-body>\n            </when>\n        </choose>\n    </on-error>\n</policies>'
    tags: [
      'oauth-3rd-party'
      'jwt'
      'credential-manager'
      'policy-fragment'
    ]
    productNames: []
  }
]

param namedValues = [
  {
    name: 'JwtSigningKey-/workspaces/setlistfy-agent/src/oauth-3rd-party-1753777378'
    value: 'VUpwY3lvOEJPZUxOZjBtQjlIY3Y4alJDMHY1aEt4dHp2RW9XQVFCeXJ1MzloOEhaYzh5TnNCZ3JZWUZYRVhES3pqelhsZHVGZ2pwcHFFS1A3OVh1dnpnYlRINA=='
    isSecret: true
  }
  {
    name: 'MarketingMemberRoleId'
    value: 'b2c3d4e5-f6g7-8h9i-0j1k-2l3m4n5o6p7q'
    isSecret: false
  }
]

param clientId = 'caf00b6f5a5747e6895ad912357fd11b'

param clientSecret = '6dfe303ac16641bc971f482ea748441c'
