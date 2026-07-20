# Project Status

調査時点: 2026-07-20。静的確認、Backend unit test、Frontend production build、Alembic migration、Compose 起動と主要 HTTP endpoint を確認した。

## 現在地

MVP の主要部品は存在する。

- Server の CRUD、SSH 接続テスト、認証情報の Fernet 暗号化
- Server の定期 SSH 接続確認、online/offline 状態・応答時間・hardware/software inventory の保存と表示
- Job の CRUD、SSH script 実行、実行結果の DB 保存
- GitHub branch の定期確認、SHA 変更時のジョブ実行、private repository 用 PAT の暗号化保存
- 実行履歴 API と status・stdout/stderr・所要時間の model
- Vue/Vuetify の dashboard、Server、Job、Execution 画面
- PostgreSQL、FastAPI、Vue/Nginx の Compose 構成
- Alembic の初期 schema、サーバ監視、GitHub trigger migration

Python compile、Backend unit test、Frontend production build は成功した。空 DB と Alembic 未導入の旧 MVP DB の migration、Compose 上の Backend health・Jobs API・Frontend・Nginx proxy も確認した。実 GitHub repository の変更から実 SSH server までを通す End-to-End test は、外部接続先を使用していないため未実施である。Compose は廃止済みの `version` 属性を警告する。

## 既知課題

優先度順。

1. **Frontend/API 契約不一致**: Job response と Job 別履歴 URL、`timeout` status は整合させたが、Execution 一覧・詳細の Frontend は入れ子の Job 情報を期待し、API は平坦な response を返す。
2. **実行制御が未完成**: 実行 API は SSH 完了まで応答せず、WebSocket endpoint はない。cancel は DB status を変えるだけで SSH process を停止しない。
3. **定期処理は単一 worker 前提**: Backend process 内 scheduler のため、複数 worker ではサーバ確認と GitHub API request が重複する。GitHub 実行履歴は DB lock で重複を防ぐが、scheduler の leader election は未実装である。
4. **migration 運用の実地確認が限定的**: 開発用の空/旧 DB migration は確認したが、production data の backup/restore を含む rehearsal は未実施である。
5. **セキュリティ未完了**: 認証・認可がなく、SSH host key 検証を無効化している。Compose には開発用 secret/DB credential が直書きされている。
6. **品質ゲート不足**: Backend unit test はあるが、DB integration/Frontend/E2E test、Backend lint/type-check、coverage、CI workflow がない。README と旧 `memory-bank/` には古い記述が残る。

## 次の優先事項

1. OpenAPI を基準に残る Frontend/API 契約を揃え、主要 CRUD と実行フローの統合テストを追加する。
2. ジョブを request から分離し、task の所有・再起動時整合性・実 cancel を設計してから WebSocket を追加する。
3. Alembic migration の production rehearsal と CI 品質ゲートを整備する。
4. 認証・認可、SSH host key 検証、secret 管理を整えてから本番利用を検討する。
