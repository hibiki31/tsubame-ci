# tsubame-ci

JenkinsのようなWEBダッシュボードを備えたCI/CDアプリケーション。SSH経由でLinuxサーバに接続し、シェルスクリプトを実行します。

## 技術スタック

### バックエンド
- **FastAPI** - 高速な非同期Webフレームワーク
- **PostgreSQL** - リレーショナルデータベース
- **SQLAlchemy 2.0** - 非同期ORM
- **asyncssh** - SSH接続とスクリプト実行
- **Pydantic** - データバリデーション

### フロントエンド（今後実装予定）
- **Vue3** - プログレッシブJavaScriptフレームワーク
- **TypeScript** - 型安全な開発
- **Vuetify3** - マテリアルデザインUIコンポーネント
- **Pinia** - 状態管理

## 機能

### 実装済み
- ✅ サーバ管理（CRUD）
- ✅ SSH接続テスト
- ✅ ジョブ定義管理（CRUD）
- ✅ ジョブ実行機能
- ✅ 実行履歴の保存と閲覧
- ✅ 認証情報の暗号化保存

### 今後実装予定
- ⏳ WebSocketによるリアルタイムログストリーミング
- ⏳ フロントエンドUI
- ⏳ ユーザー認証・認可
- ⏳ スケジュール実行
- ⏳ 通知機能（メール/Slack）

## セットアップ

### 前提条件
- Docker & Docker Compose
- Python 3.11+ （ローカル開発の場合）

### Docker Composeで起動

1. リポジトリをクローン
```bash
git clone https://github.com/hibiki31/tsubame-ci.git
cd tsubame-ci
```

2. Docker Composeで起動
```bash
docker-compose up -d
```

3. ブラウザでアクセス
- API: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs

### ローカル開発

#### バックエンド

1. 仮想環境を作成
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 依存関係をインストール
```bash
pip install -r requirements.txt
```

3. 環境変数を設定
```bash
cp .env.example .env
# .envファイルを編集して適切な値を設定
```

4. PostgreSQLを起動（Docker使用）
```bash
docker-compose up -d db
```

5. アプリケーションを起動
```bash
uvicorn app.main:app --reload
```

## API エンドポイント

### サーバ管理
- `GET /api/v1/servers` - サーバ一覧
- `POST /api/v1/servers` - サーバ作成
- `GET /api/v1/servers/{id}` - サーバ詳細
- `PUT /api/v1/servers/{id}` - サーバ更新
- `DELETE /api/v1/servers/{id}` - サーバ削除
- `POST /api/v1/servers/test` - SSH接続テスト

### ジョブ管理
- `GET /api/v1/jobs` - ジョブ一覧
- `POST /api/v1/jobs` - ジョブ作成
- `GET /api/v1/jobs/{id}` - ジョブ詳細
- `PUT /api/v1/jobs/{id}` - ジョブ更新
- `DELETE /api/v1/jobs/{id}` - ジョブ削除

### 実行履歴
- `GET /api/v1/executions` - 実行履歴一覧
- `POST /api/v1/executions` - ジョブ実行
- `GET /api/v1/executions/{id}` - 実行履歴詳細
- `POST /api/v1/executions/{id}/cancel` - 実行キャンセル

詳細は http://localhost:8000/docs を参照

## アーキテクチャ

```
tsubame-ci/
├── backend/              # FastAPI バックエンド
│   ├── app/
│   │   ├── api/         # APIエンドポイント
│   │   ├── core/        # コア設定
│   │   ├── models/      # データベースモデル
│   │   ├── schemas/     # Pydanticスキーマ
│   │   ├── services/    # ビジネスロジック
│   │   └── main.py      # エントリーポイント
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/            # Vue3 フロントエンド（今後実装）
├── docker-compose.yml
└── README.md
```

## セキュリティ

- SSH認証情報（パスワード、秘密鍵）はFernet暗号化して保存
- 環境変数で暗号化キーを管理
- 本番環境では適切な秘密管理ツール（Vault等）の使用を推奨

## ライセンス

MIT License

## 開発者

開発に関する質問や提案は Issue または Pull Request でお願いします。
