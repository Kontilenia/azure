from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchField,
)
from azure.identity import DefaultAzureCredential
import os
from dotenv import load_dotenv

load_dotenv()

SEARCH_ENDPOINT = os.getenv("AI_SEARCH_ENDPOINT")  
INDEX_NAME = "pdf-chunks"

credential = DefaultAzureCredential()
client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)

index = SearchIndex(
    name=INDEX_NAME,
    fields=[
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,       # text-embedding-3-small
            vector_search_profile_name="hnsw-profile",
        ),
    ],
    vector_search=VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-config")],
    ),
)

result = client.create_or_update_index(index)
print(f"Index '{result.name}' created/updated")