#!/usr/bin/env python3
"""
Script to fetch deployments from Azure AI Foundry
"""
import os
import json
import requests
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential

# Get variables from .env file
PROJECT_ENDPOINT = "https://setlistfyagent-swedencentral-ai-foundry.services.ai.azure.com/api/projects/setlist-agent-swedencentral"
API_VERSION = "v1"

def get_token():
    """Get token using DefaultAzureCredential or InteractiveBrowserCredential"""
    try:
        # Try DefaultAzureCredential first
        credential = DefaultAzureCredential()
        token = credential.get_token("https://ai.azure.com/.default")
        return token.token
    except Exception as e:
        print(f"DefaultAzureCredential failed: {e}")
        # If DefaultAzureCredential fails, try InteractiveBrowserCredential
        credential = InteractiveBrowserCredential()
        token = credential.get_token("https://ai.azure.com/.default")
        return token.token

def main():
    """Main function to get deployments"""
    try:
        # Get token
        token = get_token()
        
        # Make API call
        url = f"{PROJECT_ENDPOINT}/deployments?api-version={API_VERSION}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        print(f"Making request to: {url}")
        response = requests.get(url, headers=headers)
        
        # Print response
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.text}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
