import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()
# Format: "https://resource_name.ai.azure.com/api/projects/project_name"
PROJECT_ENDPOINT = os.getenv("AZURE_PROJECT_ENDPOINT")
AI_SEARCH_CONNECTION_NAME = os.getenv("AI_SEARCH_CONNECTION_NAME")

project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

connection = project.connections.get(AI_SEARCH_CONNECTION_NAME)
print(connection.id)