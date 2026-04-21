import json
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AISearchIndexResource,
    AzureAISearchQueryType,
    AzureAISearchTool,
    AzureAISearchToolResource,
    BingGroundingSearchConfiguration,
    BingGroundingSearchToolParameters,
    BingGroundingTool,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

PROJECT_ENDPOINT = os.getenv("AZURE_PROJECT_ENDPOINT")
SEARCH_CONNECTION_NAME = os.getenv("AI_SEARCH_CONNECTION_NAME")
SEARCH_INDEX_NAME = os.getenv("AI_SEARCH_INDEX_NAME")
BING_CONNECTION_NAME = os.getenv("BING_CONNECTION_NAME")
AGENT_NAME = os.getenv("AGENT_NAME")

# Global clients and agent name — initialised at startup
_project: AIProjectClient | None = None
_openai = None
_agent_name: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _project, _openai, _agent_name

    _project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    _openai = _project.get_openai_client()

    # Resolve connection IDs for Azure AI Search and Bing
    azs_connection = _project.connections.get(SEARCH_CONNECTION_NAME)
    azs_connection_id = azs_connection.id
    
    bing_connection = _project.connections.get(BING_CONNECTION_NAME)
    bing_connection_id = bing_connection.id

    # Create (or update) the agent — idempotent via create_version
    agent = _project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model="gpt-4.1-mini",
            instructions=(
                "You are a helpful assistant with access to both indexed documents and "
                "real-time web search. Use the Azure AI Search tool to retrieve information from indexed "
                "documents and the Bing Grounding tool for current information from the web. "
                "Always provide citations for your answers using the format: `[message_idx:search_idx†source]`."
            ),
            tools=[
                AzureAISearchTool(
                    azure_ai_search=AzureAISearchToolResource(
                        indexes=[
                            AISearchIndexResource(
                                project_connection_id=azs_connection_id,
                                index_name=SEARCH_INDEX_NAME,
                                query_type=AzureAISearchQueryType.SIMPLE,
                            )
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
        description="A helpful RAG agent backed by Azure AI Search and Bing Grounding.",
    )
    _agent_name = agent.name
    print(f"Agent ready: {_agent_name} (id: {agent.id}, version: {agent.version})")
    yield


app = FastAPI(title="AI Search Agent API", lifespan=lifespan)


# ── Request / Response models ────────────────────────────────────────────────


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ConversationResponse(BaseModel):
    conversation_id: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/conversation", response_model=ConversationResponse)
def create_conversation():
    """Start a new multi-turn conversation and return its ID."""
    try:
        conversation = _openai.conversations.create()
        return ConversationResponse(conversation_id=conversation.id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/chat")
def chat(request: ChatRequest):
    """Stream the agent's response as Server-Sent Events."""

    def event_stream() -> AsyncGenerator[str, None]:
        try:
            stream = _openai.responses.create(
                stream=True,
                tool_choice="required",
                conversation=request.conversation_id,
                input=request.message,
                extra_body={
                    "agent_reference": {
                        "name": _agent_name,
                        "type": "agent_reference",
                    }
                },
            )

            for event in stream:
                if event.type == "response.output_text.delta":
                    payload = json.dumps({"type": "delta", "text": event.delta})
                    yield f"data: {payload}\n\n"

                elif event.type == "response.output_item.done":
                    if event.item.type == "message":
                        item = event.item
                        if item.content and item.content[-1].type == "output_text":
                            text_content = item.content[-1]
                            for annotation in text_content.annotations:
                                if annotation.type == "url_citation":
                                    payload = json.dumps(
                                        {
                                            "type": "citation",
                                            "url": annotation.url,
                                            "start_index": annotation.start_index,
                                            "end_index": annotation.end_index,
                                        }
                                    )
                                    yield f"data: {payload}\n\n"

                elif event.type == "response.completed":
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            error_payload = json.dumps({"type": "error", "message": str(exc)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
