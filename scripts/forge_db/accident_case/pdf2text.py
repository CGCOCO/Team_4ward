import os
import re
import fitz
import chromadb
import vertexai

from vertexai.language_models import TextEmbeddingModel


# =====================================================
# Vertex AI 초기화
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


# =====================================================
# ChromaDB 초기화
# =====================================================
client = chromadb.PersistentClient(
    path="./chroma_db"
)

# 기존 collection 삭제 후 재생성
try:
    client.delete_collection("kosha_rag")
except:
    pass

collection = client.get_or_create_collection(
    name="kosha_rag"
)


# =====================================================
# Embedding 함수
# =====================================================
def get_embedding(text):

    embedding = embedding_model.get_embeddings(
        [text]
    )[0].values

    return embedding


# =====================================================
# PDF block 추출
# =====================================================
def extract_blocks(pdf_path):

    doc = fitz.open(pdf_path)

    all_blocks = []

    for page in doc:

        blocks = page.get_text("blocks")

        blocks = sorted(
            blocks,
            key=lambda b: (b[1], b[0])
        )

        for block in blocks:

            x0, y0, x1, y1, text, *_ = block

            text = text.strip()

            if not text:
                continue

            all_blocks.append(text)

    return all_blocks


# =====================================================
# section parsing
# =====================================================
def parse_pdf(pdf_path):

    blocks = extract_blocks(pdf_path)

    parsed = {
        "재해개요": "",
        "발생원인": "",
        "예방대책": ""
    }

    current_section = None

    for text in blocks:

        # ---------------------------------
        # footer 제거
        # ---------------------------------
        if "본OPS" in text:
            continue

        # ---------------------------------
        # section detect
        # ---------------------------------
        if text == "재해개요":

            current_section = "재해개요"
            continue

        elif text == "발생원인":

            current_section = "발생원인"
            continue

        elif text == "예방대책":

            current_section = "예방대책"
            continue

        # ---------------------------------
        # section 내용 추가
        # ---------------------------------
        if current_section:

            text = text.replace("►", "")

            parsed[current_section] += (
                " " + text
            )

    # ---------------------------------
    # formatting
    # ---------------------------------
    for key in parsed:

        parsed[key] = re.sub(
            r"\s+",
            " ",
            parsed[key]
        ).strip()

    return parsed


# =====================================================
# Vector DB 저장
# =====================================================
def save_to_vectordb(
    industry,
    filename,
    section,
    text
):

    # 빈 section skip
    if not text.strip():
        return

    vector_id = (
        f"{industry}_{filename}_{section}"
    )

    embedding = get_embedding(text)

    collection.add(

        ids=[vector_id],

        embeddings=[embedding],

        documents=[text],

        metadatas=[{
            "industry": industry,
            "filename": filename,
            "section": section
        }]
    )


# =====================================================
# 전체 ingestion
# =====================================================
ROOT_DIR = "./kosha_pdfs"

total_vectors = 0

for industry in os.listdir(ROOT_DIR):

    industry_path = os.path.join(
        ROOT_DIR,
        industry
    )

    if not os.path.isdir(industry_path):
        continue

    print(f"\n[INFO] {industry}")

    for file in os.listdir(industry_path):

        if not file.endswith(".pdf"):
            continue

        pdf_path = os.path.join(
            industry_path,
            file
        )

        try:

            print(f"Processing: {file}")

            filename = os.path.splitext(
                file
            )[0]

            parsed = parse_pdf(pdf_path)

            # ---------------------------------
            # section별 저장
            # ---------------------------------
            for section, text in parsed.items():

                if text.strip():

                    save_to_vectordb(
                        industry=industry,
                        filename=filename,
                        section=section,
                        text=text
                    )

                    total_vectors += 1

        except Exception as e:

            print(
                f"[ERROR] {file}: {e}"
            )

print("\n=================================")
print(f"TOTAL VECTORS: {total_vectors}")
print("DONE")
print("=================================")