# Project Status

調査時点: 2026-07-24。静的確認、Backend unit test、Frontend production build、Alembic migration、Compose 起動と主要 HTTP endpoint を確認した。

## 現在地

MVP の主要部品は存在する。

- Server の CRUD、SSH 接続テスト、認証情報の Fernet 暗号化
- Server の定期 SSH 接続確認、online/offline 状態・応答時間・hardware/software inventory の保存と表示
- Job の CRUD、SSH script 実行、実行結果の DB 保存
- 手動/GitHub 実行を request から分離するアプリ内 tracker、対象サーバ上の detached runner と永続ログ spool、Backend 再起動後の `running` 再追跡
- 一時的な SSH 通信断の再接続、byte offset による stdout/stderr の欠損・重複防止、リモート PID と開始時刻を照合する cancel
- GitHub branch の定期確認、SHA 変更時のジョブ実行、private repository 用 PAT の暗号化保存
- 実行履歴 API と status・stdout/stderr・所要時間の model
- Vue/Vuetify の dashboard、Server、Job、Execution 画面
- PostgreSQL、FastAPI、Vue/Nginx の Compose 構成
- Alembic の初期 schema、サーバ監視、GitHub trigger migration

Python compile、Backend unit test、Frontend production build は成功した。空 DB と Alembic 未導入の旧 MVP DB の migration、Compose 上の Backend health・Jobs API・Frontend・Nginx proxy も確認した。detached runner、UTF-8 chunk、offset 競合、再投入、SSH 再試行は unit test で確認したが、実 SSH server を使った Backend 再起動・通信断から画面までの End-to-End test は未実施である。

## 既知課題

優先度順。

1. **実 SSH recovery の E2E がない**: detached runner と再接続 protocol は unit test 済みだが、実 target server での Backend 強制停止、長時間通信断、cancel、target OS 再起動を通した E2E test はない。target OS/process/filesystem の消失時はジョブ継続できず `failed` へ収束する。
2. **リモート spool の retention がない**: ログ欠損を避けるため `~/.local/state/tsubame-ci/executions/` を自動削除しない。容量監視と安全な retention/cleanup 機能が必要である。
3. **定期処理は単一 worker 前提**: 複数 worker ではサーバ確認と GitHub API request が重複する。実行は remote claim と DB offset lock で二重実行・二重ログを抑えるが、scheduler の leader election は未実装である。
4. **migration 運用の実地確認が限定的**: 開発用の空/旧 DB migration は確認したが、production data の backup/restore を含む rehearsal は未実施である。
5. **セキュリティ未完了**: 認証・認可がなく、SSH host key 検証を無効化している。Compose には開発用 secret/DB credential が直書きされている。
6. **品質ゲート不足**: Backend unit test はあるが、DB integration/Frontend/E2E test、Backend lint/type-check、coverage、CI workflow がない。README と旧 `memory-bank/` には古い記述が残る。

## 次の優先事項

1. 実 target server で実行フローの DB integration/E2E test を追加し、Backend 強制停止と SSH 通信断中も process とログが継続・復旧することを確認する。
2. リモート spool の容量表示と、DB terminal commit 後だけを対象にした retention/cleanup を追加する。
3. Alembic migration の production rehearsal と CI 品質ゲートを整備する。
4. 認証・認可、SSH host key 検証、secret 管理を整えてから本番利用を検討する。
