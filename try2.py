# Before running the sample:
#    pip install azure-ai-projects>=2.0.0

import os

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

PROJECT_ENDPOINT = os.getenv("AZURE_PROJECT_ENDPOINT")

project_client = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

my_agent = "third-test"
my_version = "1"

openai_client = project_client.get_openai_client()

# Reference the agent to get a response
response = openai_client.responses.create(
    input=[{"role": "user", "content": "Tell me what you can help with."}],
    extra_body={"agent_reference": {"name": my_agent, "version": my_version, "type": "agent_reference"}},
)

print(f"Response output: {response.output_text}")