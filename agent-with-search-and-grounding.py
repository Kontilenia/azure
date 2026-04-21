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
    BingGroundingTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration,
)

load_dotenv()

PROJECT_ENDPOINT = os.getenv("AZURE_PROJECT_ENDPOINT")
SEARCH_CONNECTION_NAME = os.getenv("AI_SEARCH_CONNECTION_NAME")
SEARCH_INDEX_NAME = os.getenv("AI_SEARCH_INDEX_NAME")
BING_CONNECTION_NAME = os.getenv("BING_CONNECTION_NAME")
AGENT_NAME = os.getenv("AGENT_NAME")

# Create clients to call Foundry API
project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)
openai = project.get_openai_client()

# Resolve the connection IDs from the connection names
azs_connection = project.connections.get(SEARCH_CONNECTION_NAME)
azs_connection_id = azs_connection.id

bing_connection = project.connections.get(BING_CONNECTION_NAME)
bing_connection_id = bing_connection.id

print(f"Connections resolved successfully")

# Create an agent with both Azure AI Search and Bing Grounding tools
agent = project.agents.create_version(
    agent_name=AGENT_NAME,
    definition=PromptAgentDefinition(
        model="gpt-4.1-mini",
        instructions="""You are a helpful assistant with access to both indexed documents and 
        real-time web search. Use the Azure AI Search tool to retrieve information from indexed 
        documents and the Bing Grounding tool for current information from the web. 
        Always provide citations for your answers using the format: `[message_idx:search_idx†source]`.""",
        tools=[
            AzureAISearchTool(
                azure_ai_search=AzureAISearchToolResource(
                    indexes=[
                        AISearchIndexResource(
                            project_connection_id=azs_connection_id,
                            index_name=SEARCH_INDEX_NAME,
                            query_type=AzureAISearchQueryType.SIMPLE,
                        ),
                    ]
                )
            ),
            BingGroundingTool(
                bing_grounding=BingGroundingSearchToolParameters(
                    search_configurations=[
                        BingGroundingSearchConfiguration(
                            project_connection_id=bing_connection_id
                        )
                    ]
                )
            ),
        ],
    ),
    description="Agent with both Azure AI Search and Bing Grounding capabilities",
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

# Prompt user for a question to send to the agent
user_input = input("Enter your question (or press Enter for default): \n").strip()
if not user_input:
    user_input = "What do you know about the 7 phases of CAF methodologies? What are the latest trends in this area?"  # Example question that can benefit from both tools

# Stream the response from the agent
stream_response = openai.responses.create(
    stream=True,
    tool_choice="required",
    input=user_input,
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)

# Process the streaming response and print citations
print("\nAgent Response:")
print("-" * 80)
for event in stream_response:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
    elif event.type == "response.output_item.done":
        if event.item.type == "message":
            item = event.item
            if item.content[-1].type == "output_text":
                text_content = item.content[-1]
                if text_content.annotations:
                    print("\n" + "-" * 80)
                    print("Citations:")
                    for annotation in text_content.annotations:
                        if annotation.type == "url_citation":
                            print(
                                f"  - URL: {annotation.url} "
                                f"(Start: {annotation.start_index}, End: {annotation.end_index})"
                            )
    elif event.type == "response.completed":
        print("\n" + "-" * 80)
        print(f"Full response: {event.response.output_text}")
