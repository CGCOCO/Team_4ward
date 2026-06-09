import chromadb
import statistics


client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_collection(
    "kosha_rag_v2"
)

laws = collection.get(

    where={
        "source": "law"
    },

    include=[
        "documents",
        "metadatas"
    ]
)

lengths = [

    len(doc)

    for doc in laws["documents"]

]

print(
    "COUNT:",
    len(lengths)
)

print(
    "AVG:",
    round(
        statistics.mean(lengths),
        2
    )
)

print(
    "MAX:",
    max(lengths)
)

print(
    "MIN:",
    min(lengths)
)

sorted_docs = sorted(

    zip(
        lengths,
        laws["metadatas"]
    ),

    key=lambda x: x[0],

    reverse=True

)

print("\n")
print("=" * 80)
print("TOP 20 LONGEST")
print("=" * 80)

for length, meta in sorted_docs[:20]:

    print(
        meta["article"],
        length
    )