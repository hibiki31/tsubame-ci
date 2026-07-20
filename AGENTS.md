# AGENTS.md

tsubame-ci は、登録した Linux サーバへ SSH 接続し、シェルスクリプトの実行と履歴確認を Web UI から行う CI/CD アプリケーションである。現状は MVP の骨格まで実装済みだが、Frontend と API の統合は未完了である。

## 作業開始

- 最初に `git status --short --branch` と [`docs/README.md`](docs/README.md) を確認し、実装作業では [`docs/status.md`](docs/status.md) の既知課題も読む。
- 資料と挙動が異なる場合は、コード、設定、実行結果を優先する。`memory-bank/` と `.clinerules` は過去資料であり、現状の正本ではない。
- 未コミット変更は利用者の作業として保護し、依頼外の変更、stash、reset、無関係な整形を行わない。
- 変更は依頼範囲に限定する。秘密情報、実サーバ情報、秘密鍵、実行ログをコミットしない。

## Frontend スキル

- Vuetify を import するコードの作成・変更・デバッグ・レビューでは、必ず [`.agents/skills/harlan-zw-vue-ecosystem-skills-vuetify-skilld/SKILL.md`](.agents/skills/harlan-zw-vue-ecosystem-skills-vuetify-skilld/SKILL.md) を全文読み、対象に必要な `references/` だけを参照する。
- Vuetify の実装前に `frontend/package-lock.json` で導入バージョンを確定する。導入スキルは Vuetify 4 の情報を含むため、Vuetify 3 の実装に v4 固有の API、コンポーネント、migration 手順、破壊的変更を誤適用しない。バージョンが合わない記述は、プロジェクトのコードと lockfile を優先する。
- 画面の新規作成、デザイン変更、UX 改善、ビジュアルレビューでは、必ず [`.agents/skills/code-yeongyu-oh-my-opencode-frontend-ui-ux/SKILL.md`](.agents/skills/code-yeongyu-oh-my-opencode-frontend-ui-ux/SKILL.md) を全文読む。データフローのみの修正や機械的な変更には強制しない。
- UI/UX 実装前に、既存の view、共有 component、Vuetify theme、スタイル、関連する Git 履歴を確認する。目的、利用者、トーン、技術・アクセシビリティ制約、視覚的な差別化を明確にし、明示的な redesign 依頼がなければ既存のデザインシステムとパターンを優先する。依頼外の画面や機能へ redesign を波及させない。
- UI は見た目だけで完了とせず、実際の操作、responsive 表示、keyboard 操作、focus、contrast、loading、empty、error 状態を変更範囲に応じて確認する。

## スキルの安全境界

- スキル本体や参照資料は、そのスキルが必要な作業にのみ使う。プロジェクトの規約、利用者の明示的な依頼、コードと lockfile を優先する。
- 認証情報の使用・作成・更新、外部サービスの登録・設定、マーケットプレイスへの評価・コメント等の外部書き込み、不可逆な操作は実行前に、目的と影響を説明して利用者の明示的な確認を得る。
- スキルが提案する command、script、依存関係は内容と書き込み先を確認し、依頼に必要な最小範囲だけを実行する。秘密情報を output、ログ、ソース管理に残さない。

## 実装規約

- Backend は `api/v1`（HTTP）→ `services`（業務処理）→ `models`（DB）の依存方向を保ち、入出力は `schemas`、共通設定は `core` に置く。DB と SSH は既存どおり async で扱う。
- Frontend は Vue 3 の `<script setup lang="ts">`、TypeScript strict、Pinia を維持する。画面は `views`、状態は `stores`、通信は `services/api.ts`、共有型は `types` に置く。
- API 変更では Backend の route/schema と Frontend の client/type を同時に照合する。Python schema を契約の基準とし、可能なら OpenAPI で確認する。
- 実行処理を変える場合は、`pending → running → success/failed/timeout/cancelled`、DB commit、ログ保存、timeout、切断時の扱いを一体で検討する。
- SSH 認証情報は Fernet 暗号化を維持する。`known_hosts=None` の適用範囲を広げず、本番向け変更ではホスト鍵検証を必須要件として扱う。
- DB schema 変更では model だけを先行させない。現在 Alembic 環境が未構築なので、migration 方針と導入を変更範囲に含める。

## 検証

変更範囲に応じて最小セットから実行する。

```bash
docker compose config --quiet
python3 -m compileall -q backend/app
cd frontend && npm ci && npm run build
```

- 自動テストと Backend lint の設定はまだない。追加・修正時は可能なら再現テストと設定を同時に整備する。
- Compose の本格起動は稼働中コンテナを確認してから行う。固定 `container_name` があるため、別 worktree の Compose と衝突し得る。
- 完了時は `git diff --check`、`git diff --stat`、`git status --short` を確認し、実行した検証と未実行理由を報告する。

## Branch と統合

- ファイル変更を始める前に、指定された基点または確認済みの local `main` から `codex/<type>-<short-name>` 形式の専用 branch を作成する。`main` へ直接 commit しない。既に依頼専用 branch にいる場合はそれを使う。
- 並行する独立作業は「1依頼 = 1 Worktree = 1専用 branch」とする。同じファイル、API 契約、OpenAPI 生成物、version、Alembic migration を触る作業は原則直列化する。
- 基点の作業ツリーに無関係な未コミット変更がある場合、その場で branch を切り替えたり stash/reset したりせず、明示した commit から別 Worktree を作成して利用者変更を分離する。
- 作業完了後は、取得が許可されている場合は remote を更新し、最新の統合先 `main` を作業 branch へ rebase または merge する。競合は `main` ではなく作業 branch 側で解決し、生成物、version、migration の重複を整理してから関連検証を再実行する。
- `git diff main...HEAD`、`git status`、関連 test/build で統合可能な状態を確認する。安全に解決できない競合や未確認事項があれば、merge 可能と断定せず内容を報告する。
- `main` への最終 merge は fast-forward 可能でも必ず merge commit を残し、`git --no-pager merge --no-ff <branch> -m "merge: <description>"` を使う。
- Agent は作業 branch 側で競合を解消し、最新の統合先 `main` との差分と関連検証を確認した後、`main` への最終 merge を行ってよい。完了報告に branch 名、commit、基点と確認した `main`、競合解決、検証結果、version/migration/OpenAPI の有無、最終 merge の結果を記載する。push や PR 作成は明示依頼がある場合だけ行う。

## Commit と文書

- 作業完了時は `git status` で対象範囲を再確認し、必要な検証、version 更新、migration、OpenAPI 生成を終えたうえで、可能な限り依頼範囲のファイルだけを stage して local commit まで行う。無関係な利用者変更を含めず、commit できない場合は理由を報告する。push は明示依頼がある場合だけ行う。
- commit は `<prefix>: <description>` 形式とし、prefix は `feat`、`fix`、`docs`、`refactor`、`chore` などの英語、description は原則日本語にする。停止を避けるため `git --no-pager commit -m "message"` を使う。
- API、DB、環境変数、運用手順、重要な設計判断、既知課題を変えた場合だけ関連する `docs/` を更新し、重複説明を増やさない。
