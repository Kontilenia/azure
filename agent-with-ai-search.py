import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AzureAISearchTool,
    PromptAgentDefinition,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
)

load_dotenv()

PROJECT_ENDPOINT = os.getenv("AZURE_PROJECT_ENDPOINT")
SEARCH_CONNECTION_NAME = os.getenv("AI_SEARCH_CONNECTION_NAME")
SEARCH_INDEX_NAME = os.getenv("AI_SEARCH_INDEX_NAME")

# Create clients to call Foundry API
project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)
openai = project.get_openai_client()

# Resolve the connection ID from the connection name
azs_connection = project.connections.get(SEARCH_CONNECTION_NAME)
connection_id = azs_connection.id

# Create an agent with the Azure AI Search tool
agent = project.agents.create_version(
    agent_name="MyAgent",
    definition=PromptAgentDefinition(
        model="gpt-4.1-mini",
        instructions="""You are a helpful assistant. You must always provide citations for
        answers using the tool and render them as: `[message_idx:search_idx†source]`.""",
        tools=[
            AzureAISearchTool(
                azure_ai_search=AzureAISearchToolResource(
                    indexes=[
                        AISearchIndexResource(
                            project_connection_id=connection_id,
                            index_name=SEARCH_INDEX_NAME,
                            query_type=AzureAISearchQueryType.SIMPLE,
                        ),
                    ]
                )
            )
        ],
    ),
    description="You are a helpful agent.",
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

# Prompt user for a question to send to the agent
user_input = input("Enter your question (or press Enter for default): \n").strip()
if not user_input:
    user_input = "What do you know about Athens?"

# Stream the response from the agent
stream_response = openai.responses.create(
    stream=True,
    tool_choice="required",
    input=user_input,
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)

# Process the streaming response and print citations
for event in stream_response:
    if event.type == "response.output_text.delta":
        print(event.delta, end="")
    elif event.type == "response.output_item.done":
        if event.item.type == "message":
            item = event.item
            if item.content[-1].type == "output_text":
                text_content = item.content[-1]
                for annotation in text_content.annotations:
                    if annotation.type == "url_citation":
                        print(
                            f"URL Citation: {annotation.url}, "
                            f"Start index: {annotation.start_index}, "
                            f"End index: {annotation.end_index}"
                        )
    elif event.type == "response.completed":
        print(f"\nFull response: {event.response.output_text}")