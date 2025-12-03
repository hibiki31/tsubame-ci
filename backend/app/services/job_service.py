"""
ジョブサービス
ジョブ定義のCRUD操作を管理
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate
from app.services.server_service import ServerService, ServerNotFoundError


class JobNotFoundError(Exception):
    """ジョブが見つからない"""
    pass


class JobService:
    """ジョブ管理サービス"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.server_service = ServerService(db)
    
    async def get_all(self, include_server: bool = False) -> List[Job]:
        """
        全ジョブを取得
        
        Args:
            include_server: サーバ情報を含めるか
            
        Returns:
            ジョブのリスト
        """
        query = select(Job)
        
        if include_server:
            query = query.options(selectinload(Job.server))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_id(self, job_id: int, include_server: bool = False) -> Job:
        """
        IDでジョブを取得
        
        Args:
            job_id: ジョブID
            include_server: サーバ情報を含めるか
            
        Returns:
            ジョブオブジェクト
            
        Raises:
            JobNotFoundError: ジョブが見つからない
        """
        query = select(Job).where(Job.id == job_id)
        
        if include_server:
            query = query.options(selectinload(Job.server))
        
        result = await self.db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            raise JobNotFoundError(f"ジョブID {job_id} が見つかりません")
        
        return job
    
    async def get_by_server_id(self, server_id: int) -> List[Job]:
        """
        サーバIDでジョブを取得
        
        Args:
            server_id: サーバID
            
        Returns:
            ジョブのリスト
        """
        result = await self.db.execute(
            select(Job).where(Job.server_id == server_id)
        )
        return list(result.scalars().all())
    
    async def create(self, job_data: JobCreate) -> Job:
        """
        ジョブを作成
        
        Args:
            job_data: ジョブ作成データ
            
        Returns:
            作成されたジョブ
            
        Raises:
            ServerNotFoundError: サーバが見つからない
        """
        # サーバの存在確認
        await self.server_service.get_by_id(job_data.server_id)
        
        # ジョブオブジェクトを作成
        job = Job(
            name=job_data.name,
            description=job_data.description,
            script=job_data.script,
            server_id=job_data.server_id
        )
        
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        return job
    
    async def update(self, job_id: int, job_data: JobUpdate) -> Job:
        """
        ジョブを更新
        
        Args:
            job_id: ジョブID
            job_data: 更新データ
            
        Returns:
            更新されたジョブ
            
        Raises:
            JobNotFoundError: ジョブが見つからない
            ServerNotFoundError: サーバが見つからない
        """
        job = await self.get_by_id(job_id)
        
        # 更新データを適用
        update_dict = job_data.model_dump(exclude_unset=True)
        
        # サーバIDの変更がある場合は存在確認
        if "server_id" in update_dict:
            await self.server_service.get_by_id(update_dict["server_id"])
        
        # フィールドを更新
        for key, value in update_dict.items():
            if hasattr(job, key):
                setattr(job, key, value)
        
        await self.db.commit()
        await self.db.refresh(job)
        
        return job
    
    async def delete(self, job_id: int) -> None:
        """
        ジョブを削除
        
        Args:
            job_id: ジョブID
            
        Raises:
            JobNotFoundError: ジョブが見つからない
        """
        job = await self.get_by_id(job_id)
        
        await self.db.delete(job)
        await self.db.commit()
