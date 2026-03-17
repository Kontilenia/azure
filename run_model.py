from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

PROJECT_ENDPOINT  = "https://KontileniaTestFoundry.openai.azure.com/openai/v1/"
DEPLOYMENT_NAME = "gpt-4o-mini-t"
token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

client = OpenAI(
    base_url=PROJECT_ENDPOINT,
    api_key=token_provider
)

completion = client.chat.completions.create(
    model=DEPLOYMENT_NAME,
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
    temperature=0.1,
)

print(completion.choices[0].message)