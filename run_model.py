import os
from dotenv import load_dotenv
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

load_dotenv()

project_endpoint  = os.getenv("AIPROJECT_ENDPOINT")
deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")
token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

client = OpenAI(
    base_url=project_endpoint,
    api_key=token_provider
)

completion = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
    temperature=0.1,
)

print(completion.choices[0].message)