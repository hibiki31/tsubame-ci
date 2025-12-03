"""
データベース接続設定
SQLAlchemy 2.0 非同期エンジンを使用
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings


# 非同期エンジンの作成
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # デバッグモードでSQLログを出力
    future=True,
)

# セッションファクトリ
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """SQLAlchemyモデルのベースクラス"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    データベースセッションの依存性注入
    FastAPIのDependsで使用する
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    データベースの初期化
    開発環境でテーブルを作成する
    本番環境ではAlembicマイグレーションを使用
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
