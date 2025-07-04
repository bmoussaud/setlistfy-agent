#!/usr/bin/env python3
"""
Script to update the Phi-4 model deployment configuration in Azure AI Foundry
"""
import os
import json
import requests
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential

# Get variables from .env file
PROJECT_ENDPOINT = "https://setlistfyagent-swedencentral-ai-foundry.services.ai.azure.com/api/projects/setlist-agent-swedencentral"
API_VERSION = "v1"
# Update to match your Phi-4 deployment name
MODEL_DEPLOYMENT_NAME = "setlistfyagent-phi-4"


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


def update_phi4_deployment():
    """Update the Phi-4 deployment with tool configuration"""
    try:
        # Get token
        token = get_token()

        # Define the update payload
        update_payload = {
            "settings": {
                "enableAutoToolChoice": True,
                "toolCallParser": "default"
            }
        }

        # Make API call to update the deployment
        url = f"{PROJECT_ENDPOINT}/deployments/{MODEL_DEPLOYMENT_NAME}?api-version={API_VERSION}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        print(f"Making PATCH request to: {url}")
        print(f"With payload: {json.dumps(update_payload, indent=2)}")

        response = requests.patch(url, headers=headers, json=update_payload)

        # Print response
        print(f"Status code: {response.status_code}")
        if response.status_code in [200, 201, 202, 204]:
            print("Successfully updated Phi-4 deployment configuration")
            print(json.dumps(response.json() if response.content else {}, indent=2))
        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    update_phi4_deployment()
