# RAG（PDFの読み込み・検索）を管理するファイル
import hashlib
import json
import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "date")

# PDFが保存されているフォルダのパス（このファイルからの絶対パス）
PDF_DIR = os.path.join(DATA_DIR, "pdfs")

# 事前に作成したベクトルDB（FAISSのインデックス）の保存先
INDEX_DIR = os.path.join(DATA_DIR, "faiss_index")
MANIFEST_PATH = os.path.join(INDEX_DIR, "manifest.json")

# Embeddingモデルとチャンク分割の設定（変更した場合はインデックスの作り直しが必要）
EMBEDDING_MODEL = "text-embedding-ada-002"
CHUNK_SIZE = 500      # 1チャンクの最大文字数
CHUNK_OVERLAP = 50    # チャンク間の重複文字数


def _pdf_filenames() -> list[str]:
    return sorted(f for f in os.listdir(PDF_DIR) if f.endswith(".pdf"))


def build_manifest() -> dict:
    """インデックスの作成条件（PDFのハッシュ値・モデル・分割設定）をまとめる"""
    pdfs = {}
    for filename in _pdf_filenames():
        with open(os.path.join(PDF_DIR, filename), "rb") as f:
            pdfs[filename] = hashlib.sha256(f.read()).hexdigest()

    return {
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "pdfs": pdfs,
    }


def load_manifest() -> dict | None:
    if not os.path.exists(MANIFEST_PATH):
        return None
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


# ベクトルDBを構築する関数（Embedding API を呼び出す）
def build_vectorstore():

    documents = []

    # PDFフォルダ内のファイルを全て読み込む
    for filename in _pdf_filenames():
        filepath = os.path.join(PDF_DIR, filename)
        loader = PyMuPDFLoader(filepath)
        docs = loader.load()
        documents.extend(docs)
        print(f"読み込み完了：{filename}")

    # テキストを適切なサイズに分割する
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    split_docs = text_splitter.split_documents(documents)
    print(f"チャンク数：{len(split_docs)}")

    # OpenAIのEmbeddingでベクトル化してFAISSに保存
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    vectorstore = FAISS.from_documents(split_docs, embeddings)
    print("ベクトルDB構築完了")

    return vectorstore


# ベクトルDBをインデックスとして保存する関数
def save_vectorstore(vectorstore) -> None:
    vectorstore.save_local(INDEX_DIR)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(build_manifest(), f, ensure_ascii=False, indent=2)
        f.write("\n")


# ベクトルDBを用意する関数（起動時に呼ぶ）
def load_vectorstore():

    # PDFや設定が変わっていなければ、保存済みのインデックスを読み込むだけで済む
    if load_manifest() == build_manifest():
        # load_local は pickle を使うため許可が必要。
        # 読み込むのはこのリポジトリで作成したインデックスだけなので問題ない
        vectorstore = FAISS.load_local(
            INDEX_DIR,
            OpenAIEmbeddings(model=EMBEDDING_MODEL),
            allow_dangerous_deserialization=True,
        )
        print("保存済みのベクトルDBを読み込みました")
        return vectorstore

    # インデックスが無い・古い場合は PDF から構築する
    print("保存済みのベクトルDBが無いか古いため、PDFから構築します")
    vectorstore = build_vectorstore()
    save_vectorstore(vectorstore)
    return vectorstore


# ナレッジを検索する関数
def search_knowledge(vectorstore, query: str, k: int = 3) -> str:

    # クエリに関連するチャンクを検索
    results = vectorstore.similarity_search(query, k=k)

    # 検索結果を一つの文字列にまとめる
    knowledge_text = ""
    for i, doc in enumerate(results):
        knowledge_text += f"【参考情報{i+1}】\n{doc.page_content}\n\n"

    return knowledge_text
