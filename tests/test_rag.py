"""
RAG のベクトルDB（rag.py）のテスト

OpenAI の API は呼ばず、保存済みのインデックスの状態と、読み込み処理の分岐を確認する。
"""

import os

import pytest

import rag


# =============================================================================
# 保存済みのインデックス（date/faiss_index/）
# =============================================================================
class TestSavedIndex:

    def test_インデックスのファイルがある(self):
        for filename in ["index.faiss", "index.pkl", "manifest.json"]:
            assert os.path.exists(os.path.join(rag.INDEX_DIR, filename))

    def test_インデックスが現在のPDFと設定から作成されている(self):
        # PDF を追加・更新したり、Embedding モデルやチャンク分割の設定を変えたりしたのに
        # インデックスを作り直していない場合に失敗する。
        # 失敗したら python scripts/build_index.py を実行してコミットすること。
        assert rag.load_manifest() == rag.build_manifest()


# =============================================================================
# load_vectorstore
# =============================================================================
class TestLoadVectorstore:

    @pytest.fixture
    def calls(self, monkeypatch):
        """インデックスの読み込み・構築・保存を偽物に差し替え、呼ばれた処理を記録する"""
        calls = []
        monkeypatch.setattr(rag.FAISS, "load_local", lambda *a, **k: calls.append("load") or "loaded")
        monkeypatch.setattr(rag, "build_vectorstore", lambda: calls.append("build") or "built")
        monkeypatch.setattr(rag, "save_vectorstore", lambda vs: calls.append("save"))
        monkeypatch.setattr(rag, "OpenAIEmbeddings", lambda **k: None)
        return calls

    def test_インデックスが最新なら読み込むだけで構築しない(self, calls):
        assert rag.load_vectorstore() == "loaded"
        assert calls == ["load"]

    def test_インデックスが無い場合はPDFから構築して保存する(self, calls, monkeypatch):
        monkeypatch.setattr(rag, "load_manifest", lambda: None)

        assert rag.load_vectorstore() == "built"
        assert calls == ["build", "save"]

    def test_インデックスが古い場合はPDFから構築して保存する(self, calls, monkeypatch):
        outdated = {**rag.build_manifest(), "embedding_model": "古いモデル"}
        monkeypatch.setattr(rag, "load_manifest", lambda: outdated)

        assert rag.load_vectorstore() == "built"
        assert calls == ["build", "save"]
