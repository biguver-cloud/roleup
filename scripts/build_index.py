# RAG用のベクトルDB（FAISSのインデックス）を作成して date/faiss_index/ に保存するスクリプト
#
# PDF を追加・更新したとき、または Embedding モデルやチャンク分割の設定を変えたときに実行する。
#   python scripts/build_index.py
# 実行には OpenAI の API キー（.env の OPENAI_API_KEY）が必要。
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))
load_dotenv()

from rag import INDEX_DIR, build_vectorstore, save_vectorstore  # noqa: E402

if __name__ == "__main__":
    save_vectorstore(build_vectorstore())
    print(f"インデックスを保存しました：{os.path.abspath(INDEX_DIR)}")
