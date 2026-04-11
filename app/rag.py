# RAG（PDFの読み込み・検索）を管理するファイル
import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# PDFが保存されているフォルダのパス
PDF_DIR = "date/pdfs"

# ベクトルDBを構築する関数
def build_vectorstore():

    documents = []

    # PDFフォルダ内のファイルを全て読み込む
    for filename in os.listdir(PDF_DIR):
        if filename.endswith(".pdf"):
            filepath = os.path.join(PDF_DIR, filename)
            loader = PyMuPDFLoader(filepath)
            docs = loader.load()
            documents.extend(docs)
            print(f"読み込み完了：{filename}")

    # テキストを適切なサイズに分割する
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,      # 1チャンクの最大文字数
        chunk_overlap=50,    # チャンク間の重複文字数
    )
    split_docs = text_splitter.split_documents(documents)
    print(f"チャンク数：{len(split_docs)}")

    # OpenAIのEmbeddingでベクトル化してFAISSに保存
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(split_docs, embeddings)
    print("ベクトルDB構築完了")

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