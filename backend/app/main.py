"""
tsubame-ci FastAPI アプリケーション
メインエントリーポイント
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import servers, jobs, executions
from app.services.github_polling_service import GitHubPollingService
from app.services.server_monitor import server_monitor
from app import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションのライフサイクル管理
    起動時と終了時の処理を定義
    """
    # 起動時の処理
    if settings.debug:
        # 開発環境ではテーブルを自動作成
        # 本番環境ではAlembicマイグレーションを使用
        await init_db()

    github_poller = None
    try:
        if settings.server_monitor_enabled:
            server_monitor.start()
        if settings.github_polling_enabled:
            github_poller = GitHubPollingService()
            await github_poller.start()
            app.state.github_poller = github_poller
        yield
    finally:
        if github_poller:
            await github_poller.stop()
        await server_monitor.stop()


# FastAPIアプリケーションの作成
app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="SSH経由でリモートサーバのスクリプトを実行するCI/CDツール",
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ルーターの登録
app.include_router(
    servers.router,
    prefix=f"/api/{settings.api_version}/servers",
    tags=["servers"]
)

app.include_router(
    jobs.router,
    prefix=f"/api/{settings.api_version}/jobs",
    tags=["jobs"]
)

app.include_router(
    executions.router,
    prefix=f"/api/{settings.api_version}/executions",
    tags=["executions"]
)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": settings.app_name,
        "version": __version__,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
