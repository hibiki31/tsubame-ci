# Documentation

tsubame-ci の短い開発資料。必要な文書だけを読むための入口である。

| 文書 | 読む場面 |
| --- | --- |
| [architecture.md](architecture.md) | 構成、責務、データフローを確認する |
| [development.md](development.md) | 起動、変更手順、検証方法を確認する |
| [status.md](status.md) | 現在地、既知課題、次の優先事項を確認する |

判断の優先順位は、実行結果・テスト → コード・設定 → `docs/` → `README.md` → `memory-bank/`・`.clinerules` とする。後二者は 2025-12-03 頃の履歴資料で、一部が実装と一致しない。

## 概要

- Backend: Python 3.11 / FastAPI / SQLAlchemy async / PostgreSQL / asyncssh
- Frontend: Vue 3 / TypeScript / Vuetify / Pinia / Axios / Vite
- Runtime: Docker Compose、Nginx。UI は `http://localhost:30682`、API は `http://localhost:8000`。
- 主機能: SSH 接続先、ジョブ、実行履歴の管理、GitHub branch ポーリングトリガー、Web ダッシュボード。
