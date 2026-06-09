import chromadb
import vertexai

from vertexai.language_models import TextEmbeddingModel


# =====================================================
# Vertex AI
# =====================================================
PROJECT_ID = "kun-kgp-mytnt831"
LOCATION = "us-central1"

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION
)

embedding_model = TextEmbeddingModel.from_pretrained(
    "text-embedding-005"
)


def get_embedding(text):

    embedding = embedding_model.get_embeddings(
        [text]
    )[0].values

    return embedding


# =====================================================
# ChromaDB
# =====================================================
client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_collection(
    name="kosha_rag_v2"
)


# =====================================================
# Count 확인
# =====================================================
print("VECTOR COUNT:")
print(collection.count())


# =====================================================
# Retrieval test
# =====================================================
query = "압착장치 사고 예방 방법"

query_embedding = get_embedding(query)

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3
)

print("\n===== RESULTS =====")

for doc, meta in zip(
    results["documents"][0],
    results["metadatas"][0]
):

    print("\n-------------------")
    print(meta)
    print(doc)