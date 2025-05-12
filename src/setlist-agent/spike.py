import os
from openai import AzureOpenAI

endpoint = "https://setlistfyagent-ai-westus.cognitiveservices.azure.com/"
model_name = "gpt-4o"
deployment = "setlistfyagent-gpt-4o"

subscription_key = "6j48I4FppVi02xsolCYvvtGFLEuC45G3Jss7224swTbJGKFUSI8nJQQJ99BGAC4f1cMXJ3w3AAAAACOGeKnS"
api_version = "2024-12-01-preview"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "I am going to Paris, what should I see?",
        }
    ],
    max_tokens=4096,
    temperature=1.0,
    top_p=1.0,
    model=deployment
)

print(response.choices[0].message.content)
