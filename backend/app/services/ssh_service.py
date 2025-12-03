"""
SSH接続サービス
asyncsshを使用してリモートサーバに接続し、スクリプトを実行
"""
import asyncssh
from typing import Optional, Tuple
import asyncio
from datetime import datetime

from app.core.config import settings
from app.core.security import credential_encryptor
from app.models.server import Server, AuthMethod


class SSHConnectionError(Exception):
    """SSH接続エラー"""
    pass


class SSHExecutionError(Exception):
    """SSH実行エラー"""
    pass


class SSHService:
    """SSH接続とスクリプト実行を管理するサービス"""
    
    def __init__(self):
        self.timeout = settings.ssh_timeout
        self.connect_timeout = settings.ssh_connect_timeout
    
    async def test_connection(
        self,
        host: str,
        port: int,
        username: str,
        auth_method: AuthMethod,
        password: Optional[str] = None,
        private_key: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        SSH接続テスト
        
        Args:
            host: ホスト名またはIPアドレス
            port: SSHポート
            username: ユーザー名
            auth_method: 認証方式
            password: パスワード（auth_method=passwordの場合）
            private_key: 秘密鍵（auth_method=keyの場合）
            
        Returns:
            (成功フラグ, メッセージ) のタプル
        """
        try:
            conn = await self._create_connection(
                host=host,
                port=port,
                username=username,
                auth_method=auth_method,
                password=password,
                private_key=private_key
            )
            
            # 簡単なコマンドを実行して接続を確認
            result = await conn.run("echo 'connection test'", check=True)
            await conn.close()
            
            return True, "接続に成功しました"
            
        except asyncssh.Error as e:
            return False, f"SSH接続エラー: {str(e)}"
        except asyncio.TimeoutError:
            return False, f"接続タイムアウト（{self.connect_timeout}秒）"
        except Exception as e:
            return False, f"予期しないエラー: {str(e)}"
    
    async def execute_script(
        self,
        server: Server,
        script: str
    ) -> Tuple[int, str, str]:
        """
        サーバ上でスクリプトを実行
        
        Args:
            server: 実行先サーバ
            script: 実行するスクリプト
            
        Returns:
            (終了コード, 標準出力, 標準エラー出力) のタプル
            
        Raises:
            SSHConnectionError: 接続エラー
            SSHExecutionError: 実行エラー
        """
        try:
            # 認証情報を復号化
            password = None
            private_key = None
            
            if server.auth_method == AuthMethod.PASSWORD:
                if server.password_encrypted:
                    password = credential_encryptor.decrypt(server.password_encrypted)
            else:
                if server.private_key_encrypted:
                    private_key = credential_encryptor.decrypt(server.private_key_encrypted)
            
            # SSH接続
            conn = await self._create_connection(
                host=server.host,
                port=server.port,
                username=server.username,
                auth_method=server.auth_method,
                password=password,
                private_key=private_key
            )
            
            # スクリプト実行（タイムアウト付き）
            try:
                result = await asyncio.wait_for(
                    conn.run(script, check=False),
                    timeout=self.timeout
                )
                
                exit_code = result.exit_status if result.exit_status is not None else 0
                stdout = result.stdout if result.stdout else ""
                stderr = result.stderr if result.stderr else ""
                
                await conn.close()
                
                return exit_code, stdout, stderr
                
            except asyncio.TimeoutError:
                await conn.close()
                raise SSHExecutionError(f"スクリプト実行がタイムアウトしました（{self.timeout}秒）")
            
        except asyncssh.Error as e:
            raise SSHConnectionError(f"SSH接続エラー: {str(e)}")
        except SSHConnectionError:
            raise
        except SSHExecutionError:
            raise
        except Exception as e:
            raise SSHExecutionError(f"予期しないエラー: {str(e)}")
    
    async def _create_connection(
        self,
        host: str,
        port: int,
        username: str,
        auth_method: AuthMethod,
        password: Optional[str] = None,
        private_key: Optional[str] = None
    ) -> asyncssh.SSHClientConnection:
        """
        SSH接続を確立
        
        Args:
            host: ホスト名またはIPアドレス
            port: SSHポート
            username: ユーザー名
            auth_method: 認証方式
            password: パスワード
            private_key: 秘密鍵
            
        Returns:
            SSH接続オブジェクト
            
        Raises:
            SSHConnectionError: 接続エラー
        """
        try:
            # 認証方式に応じて接続パラメータを設定
            connect_kwargs = {
                "host": host,
                "port": port,
                "username": username,
                "known_hosts": None,  # 開発環境用（本番では適切に設定）
                "connect_timeout": self.connect_timeout,
            }
            
            if auth_method == AuthMethod.PASSWORD:
                if not password:
                    raise SSHConnectionError("パスワードが指定されていません")
                connect_kwargs["password"] = password
            else:
                if not private_key:
                    raise SSHConnectionError("秘密鍵が指定されていません")
                # 秘密鍵文字列からキーオブジェクトを作成
                try:
                    key = asyncssh.import_private_key(private_key)
                    connect_kwargs["client_keys"] = [key]
                except Exception as e:
                    raise SSHConnectionError(f"秘密鍵の読み込みに失敗: {str(e)}")
            
            # 接続確立
            conn = await asyncio.wait_for(
                asyncssh.connect(**connect_kwargs),
                timeout=self.connect_timeout
            )
            
            return conn
            
        except asyncio.TimeoutError:
            raise SSHConnectionError(f"接続タイムアウト（{self.connect_timeout}秒）")
        except asyncssh.Error as e:
            raise SSHConnectionError(f"SSH接続エラー: {str(e)}")
        except Exception as e:
            raise SSHConnectionError(f"予期しないエラー: {str(e)}")


# シングルトンインスタンス
ssh_service = SSHService()
