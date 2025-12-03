"""
サーバサービス
サーバ情報のCRUD操作を管理
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.server import Server, AuthMethod
from app.schemas.server import ServerCreate, ServerUpdate
from app.core.security import credential_encryptor
from app.services.ssh_service import ssh_service


class ServerNotFoundError(Exception):
    """サーバが見つからない"""
    pass


class ServerService:
    """サーバ管理サービス"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all(self) -> List[Server]:
        """
        全サーバを取得
        
        Returns:
            サーバのリスト
        """
        result = await self.db.execute(select(Server))
        return list(result.scalars().all())
    
    async def get_by_id(self, server_id: int) -> Server:
        """
        IDでサーバを取得
        
        Args:
            server_id: サーバID
            
        Returns:
            サーバオブジェクト
            
        Raises:
            ServerNotFoundError: サーバが見つからない
        """
        result = await self.db.execute(
            select(Server).where(Server.id == server_id)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            raise ServerNotFoundError(f"サーバID {server_id} が見つかりません")
        
        return server
    
    async def create(self, server_data: ServerCreate) -> Server:
        """
        サーバを作成
        
        Args:
            server_data: サーバ作成データ
            
        Returns:
            作成されたサーバ
        """
        # 認証情報を暗号化
        password_encrypted = None
        private_key_encrypted = None
        
        if server_data.auth_method == AuthMethod.PASSWORD:
            if server_data.password:
                password_encrypted = credential_encryptor.encrypt(server_data.password)
        else:
            if server_data.private_key:
                private_key_encrypted = credential_encryptor.encrypt(server_data.private_key)
        
        # サーバオブジェクトを作成
        server = Server(
            name=server_data.name,
            description=server_data.description,
            host=server_data.host,
            port=server_data.port,
            username=server_data.username,
            auth_method=server_data.auth_method,
            password_encrypted=password_encrypted,
            private_key_encrypted=private_key_encrypted
        )
        
        self.db.add(server)
        await self.db.commit()
        await self.db.refresh(server)
        
        return server
    
    async def update(self, server_id: int, server_data: ServerUpdate) -> Server:
        """
        サーバを更新
        
        Args:
            server_id: サーバID
            server_data: 更新データ
            
        Returns:
            更新されたサーバ
            
        Raises:
            ServerNotFoundError: サーバが見つからない
        """
        server = await self.get_by_id(server_id)
        
        # 更新データを適用
        update_dict = server_data.model_dump(exclude_unset=True)
        
        # 認証情報の更新処理
        if "password" in update_dict and update_dict["password"]:
            server.password_encrypted = credential_encryptor.encrypt(update_dict["password"])
            del update_dict["password"]
        
        if "private_key" in update_dict and update_dict["private_key"]:
            server.private_key_encrypted = credential_encryptor.encrypt(update_dict["private_key"])
            del update_dict["private_key"]
        
        # その他のフィールドを更新
        for key, value in update_dict.items():
            if hasattr(server, key):
                setattr(server, key, value)
        
        await self.db.commit()
        await self.db.refresh(server)
        
        return server
    
    async def delete(self, server_id: int) -> None:
        """
        サーバを削除
        
        Args:
            server_id: サーバID
            
        Raises:
            ServerNotFoundError: サーバが見つからない
        """
        server = await self.get_by_id(server_id)
        
        await self.db.delete(server)
        await self.db.commit()
    
    async def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        auth_method: AuthMethod,
        password: Optional[str] = None,
        private_key: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        SSH接続テスト
        
        Args:
            host: ホスト名またはIPアドレス
            port: SSHポート
            username: ユーザー名
            auth_method: 認証方式
            password: パスワード
            private_key: 秘密鍵
            
        Returns:
            (成功フラグ, メッセージ) のタプル
        """
        return await ssh_service.test_connection(
            host=host,
            port=port,
            username=username,
            auth_method=auth_method,
            password=password,
            private_key=private_key
        )
