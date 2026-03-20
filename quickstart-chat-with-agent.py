import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


# Format: "https://resource_name.ai.azure.com/api/projects/project_name"
load_dotenv()

project_endpoint = os.getenv("AIPROJECT_ENDPOINT")
agent_name = os.getenv("AGENT_NAME")

# Create project and openai clients to call Foundry API
project = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),
)
openai = project.get_openai_client()

# Create a conversation for multi-turn chat
conversation = openai.conversations.create()

# Chat with the agent to answer questions
response = openai.responses.create(
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
    input="What is the size of France in square miles?",
)
print(response.output_text)

# Ask a follow-up question in the same conversation
response = openai.responses.create(
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
    input="And what is the capital city?",
)
print(response.output_text)
