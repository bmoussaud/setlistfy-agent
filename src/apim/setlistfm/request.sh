#!/bin/bash

export CLIENT_SECRET=XXXXX
curl -X POST "https://login.microsoftonline.com/be38c437-5790-4e3a-bb56-4811371e35ea/oauth2/v2.0/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&client_id=9cfd535a-7dd2-4688-8ff3-6875cba5f6d6&client_secret=${CLIENT_SECRET}&scope=api://3f5d529d-d685-4d84-bb6b-c3707b3116d9/.default" > response.json
TOKEN=$(jq '.access_token' response.json | tr -d '"' )
echo "Access Token: ${TOKEN}"

curl -X GET "https://setlistfyagent-api-management-dev.azure-api.net/setlistfm/1.0/search/artists?artistName=Muse&p=1&sort=sortName" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json"