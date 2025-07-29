import utils
from apimtypes import *
import os

# 1) User-defined parameters (change these as needed)
rg_location   = 'eastus2'
index         = 1
deployment    = INFRASTRUCTURE.SIMPLE_APIM
tags          = ['oauth-3rd-party', 'jwt', 'credential-manager', 'policy-fragment']       # ENTER DESCRIPTIVE TAG(S)
api_prefix    = 'oauth-3rd-party-'              # OPTIONAL: ENTER A PREFIX FOR THE APIS TO REDUCE COLLISION POTENTIAL WITH OTHER SAMPLES
# OAuth
client_id     = 'caf00b6f5a5747e6895ad912357fd11b'       # ENTER THE OAUTH CLIENT ID FOR THE BACKEND API
client_secret = '6dfe303ac16641bc971f482ea748441c'    # ENTER THE OAUTH CLIENT SECRET FOR THE BACKEND API

# 2) Service-defined parameters (please do not change these)
rg_name       = utils.get_infra_rg_name(deployment, index)
sample_folder = "/workspaces/setlistfy-agent/src/oauth-3rd-party"
nb_helper     = utils.NotebookHelper(sample_folder, rg_name, rg_location, deployment, [INFRASTRUCTURE.AFD_APIM_PE, INFRASTRUCTURE.APIM_ACA, INFRASTRUCTURE.SIMPLE_APIM], True)

if len(client_id) == 0 or len(client_secret) == 0:
    utils.print_error('Please set the SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables in the root .env file before running this notebook.')
    raise ValueError('Missing Spotify OAuth credentials')

# 3) Set up the named values
nvs: List[NamedValue] = [
    NamedValue(nb_helper.jwt_key_name, nb_helper.jwt_key_value_bytes_b64, True),
    NamedValue('MarketingMemberRoleId', Role.MARKETING_MEMBER)
]

utils.print_ok(f"Named values: {nvs}")

# 4) Define the APIs and their operations and policies

# Policies
pol_artist_get_xml  = utils.read_policy_xml('artist_get.xml', sample_name = sample_folder)

# Read the policy XML without modifications - it already uses correct APIM named value format
pol_spotify_api_xml = utils.read_and_modify_policy_xml('spotify_api.xml', {
    'jwt_signing_key': '{{' + nb_helper.jwt_key_name + '}}', 
    'marketing_member_role_id': '{{MarketingMemberRoleId}}'
}, sample_folder)  

# Define template parameters for the artists
blob_template_parameters = [
    {
        "name": "id",
        "description": "The Spotify ID of the artist",
        "type": "string",
        "required": True
    }
]

# Spotify
spotify_artist_get = GET_APIOperation2('artists-get', 'Artists', '/artists/{id}', 'Gets the artist by their ID', pol_artist_get_xml, templateParameters = blob_template_parameters)

# APIs Array
apis: List[API] = [
    API(f'{api_prefix}spotify', 'Spotify', f'/{api_prefix}spotify', 'This is the API for interactions with the Spotify REST API', policyXml = pol_spotify_api_xml, operations = [spotify_artist_get], tags = tags),
]

utils.print_ok(f"APIs: {apis}")
# Display API keys (client_id and client_secret) securely
utils.print_ok(f"API Client ID: {client_id}")
utils.print_ok(f"API Client Secret: {'*' * len(client_secret)} (hidden for security)")
for api in apis:
    utils.print_ok(f"API Name: {api.name}")
    utils.print_ok(f"Display Name: {api.displayName}")
    utils.print_ok(f"Path: {api.path}")
    utils.print_ok(f"Description: {api.description}")
    utils.print_ok(f"Description: {api.policyXml}")
    utils.print_ok(f"Tags: {api.tags}")
    utils.print_ok(f"Operations: {[op for op in api.operations]}")
utils.print_ok('Notebook initialized')

bicep_parameters = {
    'apis': {'value': [api.to_dict() for api in apis]},
    'namedValues': {'value': [nv.to_dict() for nv in nvs]},
    'clientId': {'value': client_id},
    'clientSecret': {'value': client_secret}
}

utils.print_ok(f"Bicep parameters: {bicep_parameters}")


bicep_parameters_format = {
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "parameters": bicep_parameters
}
import json
utils.print_ok(f"Bicep parameters format: {bicep_parameters_format}")
# Save the parameters to a file
bicep_parameters_file = os.path.join(sample_folder, 'bicep_parameters.json')
with open(bicep_parameters_file, 'w') as f:
    json.dump(bicep_parameters_format, f, indent=2)
utils.print_ok(f"Bicep parameters saved to {bicep_parameters_file}")
utils.print_ok('Bicep parameters file created successfully')
utils.print_ok('use VS CODE to decompile the json configuration into bicepparameters.bicepparam file')
