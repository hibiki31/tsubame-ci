# Architecture

## 全体像

```text
Browser → Nginx/Vue → FastAPI → PostgreSQL
                         ├── SSH → Linux server
                         └── polling → GitHub REST API
```

Frontend は `/api/v1` を同一 origin へ送り、開発時は Vite、本番 image では Nginx が Backend へ proxy する。Backend は SSH と GitHub の認証情報を暗号化して DB に保存し、使用時だけ復号する。

## 責務

```text
backend/app/
├── api/v1/       HTTP route と例外の HTTP 変換
├── services/     CRUD、SSH 接続、監視、ジョブ実行
├── models/       SQLAlchemy model
├── schemas/      Pydantic の API 契約
├── core/         設定、DB session、暗号化
└── main.py       app、CORS、router、scheduler lifecycle

frontend/src/
├── views/        route 単位の画面
├── components/   共有 UI
├── stores/       Pinia の状態と action
├── services/     Axios client
├── types/        API 対応型
└── router/       画面 route
```

依存方向は Backend が `route → service → model`、Frontend が `view → store → API client`。共有契約を画面内へ再定義しない。

## データと実行

- `Server` は接続先と暗号化済み password/private key に加え、直近の接続状態、応答時間、確認エラー、hardware/software inventory を持つ。削除時に Job を cascade 削除する。
- `Job` は script と `server_id` に加え、任意で GitHub repository・branch・暗号化済み PAT・最後に確認した commit SHA を持つ。
- `JobExecution` は status、stdout/stderr、exit code、開始・終了時刻、実行元（手動/GitHub）とトリガー元 commit SHA を持つ。実行後の Job 編集に影響されないよう、実行時の server ID と script も snapshot として保存する。
- 手動実行 API は `pending` の履歴を作成して直ちに返し、アプリ内の `ExecutionRunner` が専用 DB session で処理する。GitHub trigger も同じ runner へ投入する。
- runner は DB row を lock し、一意な `remote_execution_id` を DB へ commit してから対象サーバへ接続する。この順序により、リモート起動前後のどこで Backend が停止しても同じ ID から再開できる。
- 対象サーバの `~/.local/state/tsubame-ci/executions/<remote_execution_id>/` に script、runner、stdout、stderr、PID、PID の `/proc` start time、状態、終了コードを mode 0700/0600 で置く。`nohup setsid` で起動した POSIX shell runner が原子的な `claimed/` directory を取得して一度だけ script を実行する。SSH session と Backend process が終了しても、同じ process group とリモートログは残る。
- Backend は SFTP で stdout/stderr を byte offset から差分取得し、ログと次 offset を同一 DB transaction へ保存する。複数 tracker や commit 直前の停止でも、offset が一致する差分だけを追記するためログを重複させない。UTF-8 の複数 byte 文字を chunk 境界で分断しない。
- SSH 接続は1回の同期ごとに張り直し、keepalive と操作 timeout を使う。通信断は実行失敗にせず `tracking_error` を記録して指数 backoff で再接続する。リモート側の spool が正本なので、切断中の stdout/stderr も復旧後に回収できる。
- Backend 起動時は `pending` と `running` を再投入する。`running` は保存済み remote ID、server snapshot、log offset から再追跡する。旧方式で作られ remote ID がない `running` は復元不能として `failed` へ収束させ、実行中のまま放置しない。
- cancel は要求日時を先に DB へ保存し、再接続できるまでリモート停止を再試行する。PID と `/proc` start time の両方が一致するときだけ process group へ TERM を送り、PID 再利用による別 process の停止を避ける。
- Frontend の実行詳細は `pending` / `running` の間、約2秒ごとに API を再取得して状態と同期済みログを表示する。

この方式は target Linux server の filesystem と process が継続していることを前提とする。target OS 自体の再起動、home directory の消失、管理者による spool/PID の削除までは実行継続を保証しない。その場合も runner 消失を検出して履歴を `failed` へ収束させる。リモート spool はログ欠損を避けるため自動削除しない。

## サーバ監視

Backend の lifespan で `ServerMonitor` を起動し、`SERVER_CHECK_INTERVAL_SECONDS` ごとに登録サーバを確認する。起動直後にも一度実行する。確認対象は設定した concurrency まで並列化し、サーバごとに独立した DB session を使う。

```text
ServerMonitor → ServerService → SSHService → Linux server
                     └── status / latency / inventory → PostgreSQL
```

- 保存済み認証情報を復号し、SSH 接続成功までの時間を計測する。
- 同じ SSH 接続で hostname、architecture、CPU、memory、root disk、OS、kernel、package manager、Python、Docker、Git を読み取る。
- 接続失敗時は `offline` とエラーを保存するが、最後に成功した inventory は障害調査用に残す。
- API は即時確認と自動監視設定の取得を提供する。

## GitHub branch ポーリング

- `GITHUB_POLL_INTERVAL_SECONDS` ごとに、`github_poll` を設定した Job の branch HEAD を GitHub REST API で確認する。受信用 port や webhook の外部公開は不要。
- 初回確認は現在の HEAD SHA を基準として保存するだけで実行しない。以後 SHA が変化したときだけ `pending` の履歴を作成し、SSH 実行をアプリ内 task へ投入する。
- SHA 更新と実行履歴作成は Job row の lock 下で同一 transaction にする。複数 Backend が同時確認しても、同一 SHA の実行履歴は重複作成しない。
- SHA 保存後から task 開始前にプロセスが停止しても、次回起動時に `pending` の GitHub 実行履歴を再投入する。
- PAT は Fernet で暗号化し、API には設定有無だけを返す。private repository は対象 repository の Contents 読み取り権限を持つ fine-grained PAT を使用する。
- GitHub API の ETag を保持する。確認失敗時はジョブを実行せず、最終確認日時と安全なエラー文を Job に記録する。

両 scheduler は Backend process 内で動く。複数 worker ではサーバ確認と GitHub API request が worker 数だけ発生するため、通常は単一 worker とする。複数 Backend で GitHub polling を行っても DB lock で実行履歴の重複は防ぐが、API request 自体を一台へ限定する場合は一台だけ `GITHUB_POLLING_ENABLED=True` にする。

API の正確な route/schema は FastAPI の `/docs` と `/openapi.json` を正本とする。主要 prefix は `/api/v1/servers`、`/api/v1/jobs`、`/api/v1/executions`。

## 設定と永続化

- 必須環境変数は `DATABASE_URL`、`SECRET_KEY`、`ENCRYPTION_KEY`。全項目は `backend/.env.example` と `backend/app/core/config.py` を参照する。
- Alembic は `0001 initial → 0002 server monitoring → 0003 GitHub trigger → 0004 resumable remote executions` の単一 chain で管理する。Docker 起動時は `backend/scripts/migrate.py` が空 DB、従来の `create_all()` DB、旧 trigger 開発 revision を判定して適用する。
- Debug 起動時の `Base.metadata.create_all()` は新規 table の作成だけを行い、既存 table へ column を追加しない。起動前に migration を適用する。
- Compose の DB volume は `postgres_data`。実データを伴う破壊的操作は行わない。
