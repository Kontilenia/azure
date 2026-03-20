import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

load_dotenv()

project_endpoint = os.getenv("AIPROJECT_ENDPOINT")
agent_name = os.getenv("AGENT_NAME")
model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")

# Create project client to call Foundry API
project = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),
)

# Create an agent with a model and instructions
agent = project.agents.create_version(
    agent_name=agent_name,
    definition=PromptAgentDefinition(
        model=model_deployment_name,  # supports all Foundry direct models"
        instructions="You are a helpful assistant that answers general questions",
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")
