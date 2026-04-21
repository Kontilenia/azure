import json
import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Search Agent", page_icon="🤖", layout="centered")
st.title("AI Search Agent")


# ── Session state ────────────────────────────────────────────────────────────

def init_session():
    """Create a new backend conversation and initialise state."""
    if "conversation_id" not in st.session_state:
        try:
            resp = httpx.post(f"{BACKEND_URL}/conversation", timeout=30)
            resp.raise_for_status()
            st.session_state.conversation_id = resp.json()["conversation_id"]
        except Exception as exc:
            st.error(f"Could not connect to the backend: {exc}")
            st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []  # list of {"role": str, "content": str, "citations": list}


init_session()


# ── Render chat history ───────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("citations"):
            with st.expander(f"Sources ({len(msg['citations'])})"):
                for i, cite in enumerate(msg["citations"], 1):
                    st.markdown(f"**[{i}]** [{cite['url']}]({cite['url']})")


# ── Chat input ────────────────────────────────────────────────────────────────

if user_input := st.chat_input("Ask a question…"):
    # Add user message to history and render it immediately
    st.session_state.messages.append({"role": "user", "content": user_input, "citations": []})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Stream assistant response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_text = ""
        citations = []

        try:
            with httpx.Client(timeout=None) as client:
                with client.stream(
                    "POST",
                    f"{BACKEND_URL}/chat",
                    json={
                        "conversation_id": st.session_state.conversation_id,
                        "message": user_input,
                    },
                ) as stream:
                    for line in stream.iter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[len("data: "):]
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        if event["type"] == "delta":
                            full_text += event["text"]
                            response_placeholder.markdown(full_text + "▌")

                        elif event["type"] == "citation":
                            citations.append({"url": event["url"]})

                        elif event["type"] == "done":
                            response_placeholder.markdown(full_text)
                            break

                        elif event["type"] == "error":
                            st.error(f"Backend error: {event['message']}")
                            break

        except Exception as exc:
            st.error(f"Request failed: {exc}")
            full_text = full_text or "_(no response)_"
            response_placeholder.markdown(full_text)

        if citations:
            with st.expander(f"Sources ({len(citations)})"):
                for i, cite in enumerate(citations, 1):
                    st.markdown(f"**[{i}]** [{cite['url']}]({cite['url']})")

    # Persist assistant message
    st.session_state.messages.append(
        {"role": "assistant", "content": full_text, "citations": citations}
    )
