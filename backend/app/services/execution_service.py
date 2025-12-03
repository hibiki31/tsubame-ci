"""
ジョブ実行サービス
ジョブの実行と実行履歴の管理
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime

from app.models.execution import JobExecution, ExecutionStatus
from app.services.job_service import JobService, JobNotFoundError
from app.services.ssh_service import ssh_service, SSHConnectionError, SSHExecutionError


class ExecutionNotFoundError(Exception):
    """実行履歴が見つからない"""
    pass


class ExecutionService:
    """ジョブ実行サービス"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_service = JobService(db)
    
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        include_job: bool = False
    ) -> List[JobExecution]:
        """
        実行履歴を取得（最新順）
        
        Args:
            limit: 取得件数
            offset: オフセット
            include_job: ジョブ情報を含めるか
            
        Returns:
            実行履歴のリスト
        """
        query = (
            select(JobExecution)
            .order_by(desc(JobExecution.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        if include_job:
            query = query.options(selectinload(JobExecution.job))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_id(
        self,
        execution_id: int,
        include_job: bool = False
    ) -> JobExecution:
        """
        IDで実行履歴を取得
        
        Args:
            execution_id: 実行ID
            include_job: ジョブ情報を含めるか
            
        Returns:
            実行履歴オブジェクト
            
        Raises:
            ExecutionNotFoundError: 実行履歴が見つからない
        """
        query = select(JobExecution).where(JobExecution.id == execution_id)
        
        if include_job:
            query = query.options(selectinload(JobExecution.job))
        
        result = await self.db.execute(query)
        execution = result.scalar_one_or_none()
        
        if not execution:
            raise ExecutionNotFoundError(f"実行ID {execution_id} が見つかりません")
        
        return execution
    
    async def get_by_job_id(
        self,
        job_id: int,
        limit: int = 50
    ) -> List[JobExecution]:
        """
        ジョブIDで実行履歴を取得
        
        Args:
            job_id: ジョブID
            limit: 取得件数
            
        Returns:
            実行履歴のリスト
        """
        result = await self.db.execute(
            select(JobExecution)
            .where(JobExecution.job_id == job_id)
            .order_by(desc(JobExecution.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create_and_execute(self, job_id: int) -> JobExecution:
        """
        ジョブを実行し、実行履歴を作成
        
        Args:
            job_id: 実行するジョブID
            
        Returns:
            実行履歴オブジェクト
            
        Raises:
            JobNotFoundError: ジョブが見つからない
        """
        # ジョブとサーバ情報を取得
        job = await self.job_service.get_by_id(job_id, include_server=True)
        
        # 実行履歴レコードを作成
        execution = JobExecution(
            job_id=job_id,
            status=ExecutionStatus.PENDING,
        )
        
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        
        # 非同期でジョブを実行
        try:
            # ステータスを実行中に更新
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.utcnow()
            await self.db.commit()
            
            # SSH経由でスクリプト実行
            exit_code, stdout, stderr = await ssh_service.execute_script(
                server=job.server,
                script=job.script
            )
            
            # 実行結果を保存
            execution.status = (
                ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED
            )
            execution.exit_code = exit_code
            execution.stdout = stdout
            execution.stderr = stderr
            execution.finished_at = datetime.utcnow()
            
        except SSHConnectionError as e:
            # SSH接続エラー
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.finished_at = datetime.utcnow()
            
        except SSHExecutionError as e:
            # SSH実行エラー（タイムアウト等）
            if "タイムアウト" in str(e):
                execution.status = ExecutionStatus.TIMEOUT
            else:
                execution.status = ExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.finished_at = datetime.utcnow()
            
        except Exception as e:
            # 予期しないエラー
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"予期しないエラー: {str(e)}"
            execution.finished_at = datetime.utcnow()
        
        finally:
            await self.db.commit()
            await self.db.refresh(execution)
        
        return execution
    
    async def cancel_execution(self, execution_id: int) -> JobExecution:
        """
        実行をキャンセル（将来的な実装）
        
        Args:
            execution_id: 実行ID
            
        Returns:
            更新された実行履歴
            
        Raises:
            ExecutionNotFoundError: 実行履歴が見つからない
        """
        execution = await self.get_by_id(execution_id)
        
        # 実行中の場合のみキャンセル可能
        if execution.status == ExecutionStatus.RUNNING:
            execution.status = ExecutionStatus.CANCELLED
            execution.finished_at = datetime.utcnow()
            execution.error_message = "ユーザーによってキャンセルされました"
            
            await self.db.commit()
            await self.db.refresh(execution)
        
        return execution
