from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

load_dotenv()
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
PDF_PATH = "data/azure-cloud-adoption-framework.pdf"
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 500
MODEL_DEPLOYMENT_NAME = os.getenv("EMBEDDING_MODEL_DEPLOYMENT_NAME")
OUTPUT_PATH = "data/documents.json"

# Load and extract text from the first 5 pages
loader = PyMuPDFLoader(PDF_PATH)
text_per_page = loader.load()[:5] # Keep only 5 pages for testing
text = "\n".join(map(lambda page: page.page_content, text_per_page)) # Ignore all metadata

# Split into chunks
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)
chunks = splitter.split_text(text)
print(f"Created {len(chunks)} chunks")

# Create embeddings for all chunks in a single batched API call
token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

client = OpenAI(
    base_url=OPENAI_ENDPOINT,
    api_key=token_provider,
)

response = client.embeddings.create(
    model=MODEL_DEPLOYMENT_NAME,
    input=chunks,
)

# Format as Azure AI Search documents
# Required fields: "id" (string key), "content" (text), "contentVector" (float array)
documents = [
    {
        "id": str(i),
        "content": chunks[i],
        "contentVector": item.embedding,
    }
    for i, item in enumerate(response.data)
]

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(documents, f, ensure_ascii=False, indent=2)

print(f"Saved {len(documents)} documents to {OUTPUT_PATH}")
print(f"Vector dimensions: {len(documents[0]['contentVector'])}")