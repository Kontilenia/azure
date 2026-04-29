from azure.search.documents import SearchClient
from azure.identity import DefaultAzureCredential
import os
import json
from dotenv import load_dotenv

load_dotenv()

SEARCH_ENDPOINT = os.getenv("AI_SEARCH_ENDPOINT")
INDEX_NAME = "pdf-chunks"
INPUT_PATH = "data/documents.json"

with open(INPUT_PATH, "r", encoding="utf-8") as f:
    documents = json.load(f)

credential = DefaultAzureCredential()
client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)

# Upload in batches of 1000 (Azure AI Search limit per request)
BATCH_SIZE = 1000
for i in range(0, len(documents), BATCH_SIZE):
    batch = documents[i:i + BATCH_SIZE]
    result = client.upload_documents(documents=batch)
    succeeded = sum(1 for r in result if r.succeeded)
    print(f"Batch {i // BATCH_SIZE + 1}: {succeeded}/{len(batch)} documents uploaded")