# RoleUp

## 🎯 概要

**RoleUp** は、新人オペレーターから経験者まで幅広く活用できる、AIを活用したロールプレイ型トレーニングツールです。

チャット・コールセンター業務において、ロールプレイ練習の機会が不足しがちという現場課題に着目して開発しました。
チャット形式で顧客役AIと模擬対応を行い、対応終了後にAIが会話内容を分析して具体的なフィードバックを返します。

- **難易度を3段階**（初級・中級・上級）から選択でき、新人研修にも、経験者のスキルアップにも対応
- **実務頻出シナリオ**（解約引き止め・請求トラブル・クレーム対応など）を厳選して収録
- **RAG（検索拡張生成）** を採用し、社内マニュアルなどのPDFナレッジを参照しながら応答を生成
- トレーナー不在でも、いつでも・何度でも練習できる **自己学習型**の設計

## 🚀 デプロイ済みURL

**本番環境（Google Cloud Run）:**
https://roleup-498951365205.asia-northeast1.run.app

## 🎓 目的

- **新人オペレーターの研修** — 実際の顧客対応を想定したロールプレイを通じて、現場に出る前にスキルを身につけられる
- **練習機会不足の解消** — トレーナーや相手役がいなくても、いつでも・何度でも反復練習できる環境を提供する
- **経験者の応対品質向上** — 上級難易度のシナリオで難易度の高い対応を繰り返し練習し、さらなるスキルアップを図れる

## ✨ 工夫した点

- 💼 難易度ごとの顧客の態度設計に現場経験を活かした
- 📈 初級から上級まで段階的な難易度を設けることで新人から経験者まで幅広く対応できる設計にした
- 🎭 シナリオは実務で頻出の場面（解約・請求・クレーム・新規契約）を厳選した

## 📋 GitHub運用ルール

チーム開発を想定した運用ルールを定めています。詳細は [GITHUB_RULES.md](GITHUB_RULES.md) をご参照ください。

## 📁 ディレクトリ構成

```
roleup/
├── app/
│   ├── api.py         # FastAPIエントリーポイント（本番起動）・CORS設定
│   ├── api_routes.py  # FastAPI REST APIエンドポイント定義
│   ├── schemas.py     # APIリクエスト・レスポンスのPydantic型定義
│   ├── agent.py       # AI応答・フィードバック生成ロジック
│   ├── prompts.py     # プロンプト管理（ロールプレイ・フィードバック）
│   ├── rag.py         # PDFナレッジ読み込み・ベクトル検索
│   └── main.py        # Chainlit UI（ローカル開発・動作確認専用）
├── date/
│   └── pdfs/          # RAG用PDFナレッジ格納フォルダ
├── .chainlit/         # Chainlit設定ファイル
├── chainlit.md        # Chainlitウェルカムメッセージ
├── Dockerfile         # Dockerイメージビルド定義
├── GITHUB_RULES.md    # GitHub運用ルール
├── requirements.txt   # 依存パッケージ一覧
└── README.md
```

## 🛠️ 技術スタック

| 技術 | 用途 |
|---|---|
| Python | バックエンド全体 |
| FastAPI | REST API 司令塔（本番のエントリーポイント） |
| Chainlit | ローカル開発用チャットUI（動作確認専用） |
| LangChain | 会話管理・フィードバック生成 |
| langchain-openai | OpenAI APIとの連携 |
| langchain-community | FAISSベクトルストア連携 |
| OpenAI GPT-4o-mini | 顧客役AI・フィードバック生成 |
| FAISS | ベクトル検索（RAG） |
| PyMuPDF | PDFナレッジの読み込み |
| Docker | アプリケーションのコンテナ化・環境統一 |
| Google Cloud Run | サーバーレスコンテナデプロイ |
| Google Artifact Registry / GCR | コンテナイメージ管理 |
| Google Secret Manager | APIキーの安全な管理 |

## 🏗️ アーキテクチャ図

```mermaid
flowchart TD
    Frontend["🖥️ フロントエンド\n（React等）"]
    DevUser["👤 開発者\n（ローカル動作確認）"]
    OpenAI["☁️ OpenAI API\nGPT-4o-mini"]
    Chainlit["🖥️ Chainlit UI\nmain.py\n※ローカル開発専用"]

    subgraph CloudRun["☁️ Google Cloud Run（本番環境）"]
        subgraph Docker["🐳 Docker コンテナ"]
            API["⚡ FastAPI 司令塔\napi.py / api_routes.py / schemas.py"]
            Agent["🤖 AIエージェント\nagent.py"]
            Prompts["📝 プロンプト管理\nprompts.py"]
            RAG["🔍 RAG検索\nrag.py"]
            PDF["📄 PDFナレッジ\ndate/pdfs/"]
            FAISS["🗄️ FAISSベクトルDB"]
        end
    end

    Frontend -->|"HTTP リクエスト\n/api/v1/..."| API
    DevUser -->|"chainlit run app/main.py"| Chainlit
    Chainlit -->|直接呼び出し| Agent
    API -->|処理委譲| Agent
    Agent -->|プロンプト構築| Prompts
    Agent -->|ナレッジ検索| RAG
    RAG -->|PDF読み込み| PDF
    RAG -->|ベクトル検索| FAISS
    Agent -->|API呼び出し| OpenAI
    OpenAI -->|応答・フィードバック| Agent
    Agent -->|JSONレスポンス| API
    API -->|JSONレスポンス| Frontend
```

## ⚙️ セットアップ手順

```bash
git clone https://github.com/biguver-cloud/roleup.git
cd roleup
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # .env を開いて OPENAI_API_KEY を入力
```

> `date/pdfs/` にRAG用のPDFを配置してから起動してください。

**FastAPI で起動する場合（本番と同じ構成）**

```bash
cd app
uvicorn api:app --reload     # http://localhost:8000
```

| インターフェース | URL | 説明 |
|---|---|---|
| Swagger UI | `http://localhost:8000/docs` | REST APIの動作確認・テスト画面 |
| OpenAPI JSON | `http://localhost:8000/openapi.json` | API仕様書（JSON） |

**Chainlit で起動する場合（ローカル動作確認用）**

```bash
chainlit run app/main.py     # http://localhost:8000
```

**Docker を使う場合**

```bash
docker build -t roleup .
docker run --env-file .env -p 8080:8080 roleup
```

**Google Cloud Run にデプロイする場合**

```bash
# Cloud Build でイメージをビルド・プッシュ
gcloud builds submit . --config cloudbuild.yaml --project YOUR_PROJECT_ID

# Cloud Run にデプロイ
gcloud run deploy roleup \
  --image asia.gcr.io/YOUR_PROJECT_ID/roleup:latest \
  --region asia-northeast1 \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets "OPENAI_API_KEY=OPENAI_API_KEY:latest" \
  --memory 1Gi \
  --min-instances 1 \
  --timeout 3600
```

> Secret Manager に `OPENAI_API_KEY` を事前に登録してください。

## 🚀 使い方

### REST API で使う場合（本番・推奨）

`http://localhost:8000/docs` をブラウザで開くとSwagger UIが表示され、画面上でAPIを試せます。

**APIエンドポイント一覧**

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/v1/health` | サーバーの死活確認 |
| GET | `/api/v1/options` | 難易度・シナリオの選択肢を取得 |
| POST | `/api/v1/sessions` | セッション作成（会話の開始準備） |
| POST | `/api/v1/sessions/{id}/start` | 難易度・シナリオを選択して顧客役AIの第一声を取得 |
| POST | `/api/v1/sessions/{id}/messages` | メッセージを送信して顧客役AIの返答を取得 |
| POST | `/api/v1/sessions/{id}/feedback` | 会話全体のフィードバックを取得 |

### Chainlit UI で使う場合（ローカル開発・動作確認専用）

1. 🎚️ 難易度を選択する（初級・中級・上級）
2. 📋 シナリオを選択する（解約引き止め・請求トラブルなど）
3. 💬 顧客役AIとチャットで模擬対応を行う
4. ✅ 「対応終了」と入力するとフィードバックが表示される


▼ 起動時の画面

<img width="1919" height="864" alt="スクリーンショット 2026-04-19 182437" src="https://github.com/user-attachments/assets/9491189e-272e-44b0-807d-7571120d69e6" />

▼ シミュレーション実行中の画面

<img width="1900" height="647" alt="スクリーンショット 2026-04-15 153909" src="https://github.com/user-attachments/assets/a8f7b12c-f4ff-4e7d-a493-08eae4c75dbf" />

▼ フィードバック表示画面

<img width="1899" height="708" alt="スクリーンショット 2026-04-15 154007" src="https://github.com/user-attachments/assets/32844a13-ecc9-432d-81fc-6a7ac5815403" />

## 🖥️ 使用環境

| 項目 | 内容 |
|---|---|
| OS | Windows 11（Windows環境で開発・動作確認） |
| Python | 3.11 |
| フレームワーク | Chainlit / FastAPI |
| LLM | OpenAI API（LangChain経由） |
| ベクトルDB | FAISS |
| コンテナ | Docker |
| 主なライブラリ | LangChain, langchain-openai, langchain-community, PyMuPDF, FAISS |
| デプロイ | Google Cloud Run（asia-northeast1） |

## 🔮 今後の拡張予定

- 🏥 業種別シナリオの追加（医療・金融・ECなど）
- 📊 セッションごとのスコア履歴表示
- 👥 育成担当者向けの受講者管理画面

## 👤 Author

[biguver-cloud](https://github.com/biguver-cloud)

## 📄 License

This project is for educational and demonstration purposes only.

本プロジェクトは **学習・ポートフォリオ目的** です。
実在の企業・サービスは含まれていません。

実運用時に追加で必要な対応：

- 🔐 認証・認可
- 📋 ログ管理
- 🙈 個人情報マスキング
- 🛡️ プロンプト・回答制御の強化
