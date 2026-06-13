import chromadb

client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_collection(
    "kosha_rag_v2"
)

laws = collection.get(
    where={"source": "law"},
    include=["metadatas"]
)

accidents = collection.get(
    where={"source": "accident_case"},
    include=["metadatas"]
)

print("=" * 50)
print("DATABASE STATISTICS")
print("=" * 50)

print(
    f"법령 개수     : {len(laws['ids'])}"
)

print(
    f"사고사례 개수 : {len(accidents['ids'])}"
)

print(
    f"전체 개수     : {len(laws['ids']) + len(accidents['ids'])}"
)

print("=" * 50)