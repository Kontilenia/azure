import os
from dotenv import load_dotenv
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

load_dotenv()

project_endpoint  = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")
token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

client = OpenAI(
    base_url=project_endpoint,
    api_key=token_provider
)

response = client.responses.create(
    model=deployment_name,
    input="What is the capital of France?",
)

print(f"answer: {response.output[1].content[0].text}")