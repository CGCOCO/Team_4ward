import json
import chromadb
import vertexai

from vertexai.language_models import TextEmbeddingModel


# =========================================
# Vertex AI Init
# =========================================

vertexai.init(
    project="kun-kgp-mytnt831",
    location="us-central1"
)

embedding_model = TextEmbeddingModel.from_pretrained(
    "text-embedding-005"
)


# =========================================
# ChromaDB 연결
# =========================================

client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_or_create_collection(
    "kosha_rag_v2"
)


# =========================================
# JSON 로드
# =========================================

with open("lawData.json", "r", encoding="utf-8") as f:
    data = json.load(f)

articles = data["법령"]["조문"]["조문단위"]


# =========================================
# 모든 타입 flatten
# =========================================

def flatten_text(value):

    # 문자열
    if isinstance(value, str):
        return value

    # 리스트
    elif isinstance(value, list):

        results = []

        for item in value:
            results.append(flatten_text(item))

        return "\n".join(results)

    # 딕셔너리
    elif isinstance(value, dict):

        results = []

        for v in value.values():
            results.append(flatten_text(v))

        return "\n".join(results)

    # 기타
    else:
        return str(value)


# =========================================
# 조문 flatten
# =========================================

def flatten_article(article):

    parts = []

    # 조문내용
    if "조문내용" in article:
        parts.append(
            flatten_text(article["조문내용"])
        )

    # 항 처리
    if "항" in article:

        clauses = article["항"]

        if not isinstance(clauses, list):
            clauses = [clauses]

        for clause in clauses:

            # 항내용
            if "항내용" in clause:
                parts.append(
                    flatten_text(clause["항내용"])
                )

            # 호 처리
            if "호" in clause:

                items = clause["호"]

                if not isinstance(items, list):
                    items = [items]

                for item in items:

                    # 호내용
                    if "호내용" in item:
                        parts.append(
                            flatten_text(item["호내용"])
                        )

                    # 목 처리
                    if "목" in item:

                        subitems = item["목"]

                        if not isinstance(subitems, list):
                            subitems = [subitems]

                        for subitem in subitems:

                            # 목내용
                            if "목내용" in subitem:
                                parts.append(
                                    flatten_text(subitem["목내용"])
                                )

    return "\n".join(parts)


# =========================================
# 전체 조문 처리
# =========================================

count = 0

for article in articles:

    try:

        # 조문만 사용
        if article.get("조문여부") != "조문":
            continue

        article_no = article.get("조문번호")

        if not article_no:
            continue

        doc_id = f"law_{article_no}"

        print(f"processing: 제{article_no}조")

        # flatten
        doc_text = flatten_article(article)

        # 빈 문서 skip
        if len(doc_text.strip()) < 10:
            continue

        # embedding 생성
        embedding = embedding_model.get_embeddings(
            [doc_text]
        )[0].values

        # metadata
        metadata = {
            "source": "law",
            "article": f"제{article_no}조"
        }

        # =========================================
        # 바로 insert
        # =========================================

        collection.add(
            documents=[doc_text],
            metadatas=[metadata],
            ids=[doc_id],
            embeddings=[embedding]
        )

        count += 1

        print(f"[{count}] inserted: {doc_id}")

    except Exception as e:

        print(f"\nERROR at 제{article_no}조")
        print(e)

        continue


# =========================================
# 완료
# =========================================

print("\n")
print("=" * 50)
print("DONE")
print("=" * 50)

print(f"Total inserted: {count}")
print(f"Collection count: {collection.count()}")