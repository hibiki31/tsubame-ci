"""
SSH接続サービス
asyncsshを使用してリモートサーバに接続し、スクリプトを実行
"""
import asyncssh
from dataclasses import dataclass
from typing import Optional, Tuple
import asyncio
import time

from app.core.config import settings
from app.core.security import credential_encryptor
from app.models.server import Server, AuthMethod


class SSHConnectionError(Exception):
    """SSH接続エラー"""
    pass


class SSHExecutionError(Exception):
    """SSH実行エラー"""
    pass


@dataclass(frozen=True)
class ServerInspectionResult:
    """SSH接続確認と構成情報取得の結果"""
    latency_ms: int
    hardware_info: dict[str, str | int]
    software_info: dict[str, str]
    warning: Optional[str] = None


INVENTORY_COMMAND = r"""
tsubame_emit() { printf 'TSUBAME_%s=%s\n' "$1" "$2"; }
tsubame_emit HOSTNAME "$(hostname 2>/dev/null | head -n 1)"
tsubame_emit ARCHITECTURE "$(uname -m 2>/dev/null | head -n 1)"
tsubame_emit CPU_MODEL "$(awk -F: '/model name|Hardware/ {value=$2; sub(/^[[:space:]]+/, "", value); print value; exit}' /proc/cpuinfo 2>/dev/null)"
tsubame_emit CPU_CORES "$(getconf _NPROCESSORS_ONLN 2>/dev/null)"
tsubame_emit MEMORY_TOTAL_BYTES "$(awk '/^MemTotal:/ {printf "%.0f", $2 * 1024}' /proc/meminfo 2>/dev/null)"
tsubame_emit DISK_TOTAL_BYTES "$(df -Pk / 2>/dev/null | awk 'NR == 2 {printf "%.0f", $2 * 1024}')"
tsubame_emit OS_NAME "$(awk -F= '/^NAME=/ {value=$2; gsub(/^\"|\"$/, "", value); print value; exit}' /etc/os-release 2>/dev/null)"
tsubame_emit OS_VERSION "$(awk -F= '/^VERSION=/ {value=substr($0, index($0, "=") + 1); gsub(/^\"|\"$/, "", value); print value; exit}' /etc/os-release 2>/dev/null)"
tsubame_emit KERNEL "$(uname -sr 2>/dev/null | head -n 1)"
if command -v apt-get >/dev/null 2>&1; then pm=apt; elif command -v dnf >/dev/null 2>&1; then pm=dnf; elif command -v yum >/dev/null 2>&1; then pm=yum; elif command -v apk >/dev/null 2>&1; then pm=apk; elif command -v pacman >/dev/null 2>&1; then pm=pacman; else pm=unknown; fi
tsubame_emit PACKAGE_MANAGER "$pm"
if command -v python3 >/dev/null 2>&1; then tsubame_emit PYTHON_VERSION "$(python3 --version 2>&1 | head -n 1)"; fi
if command -v docker >/dev/null 2>&1; then tsubame_emit DOCKER_VERSION "$(docker --version 2>&1 | head -n 1)"; fi
if command -v git >/dev/null 2>&1; then tsubame_emit GIT_VERSION "$(git --version 2>&1 | head -n 1)"; fi
"""


class SSHService:
    """SSH接続とスクリプト実行を管理するサービス"""
    
    def __init__(self):
        self.timeout = settings.ssh_timeout
        self.connect_timeout = settings.ssh_connect_timeout
        self.inventory_timeout = settings.server_inventory_timeout

    @staticmethod
    def _server_credentials(server: Server) -> tuple[Optional[str], Optional[str]]:
        """保存済みサーバから復号した認証情報を得る"""
        password = None
        private_key = None

        if server.auth_method == AuthMethod.PASSWORD:
            if server.password_encrypted:
                password = credential_encryptor.decrypt(server.password_encrypted)
        elif server.private_key_encrypted:
            private_key = credential_encryptor.decrypt(server.private_key_encrypted)

        return password, private_key

    @staticmethod
    def _parse_inventory(output: str) -> tuple[dict[str, str | int], dict[str, str]]:
        """監視コマンドのマーカー付き出力をAPI用の辞書へ変換する"""
        values: dict[str, str] = {}
        for line in output.splitlines():
            if not line.startswith("TSUBAME_") or "=" not in line:
                continue
            key, value = line.removeprefix("TSUBAME_").split("=", 1)
            if value:
                values[key] = value.strip()

        def integer_value(key: str) -> Optional[int]:
            try:
                return int(values[key])
            except (KeyError, ValueError):
                return None

        hardware: dict[str, str | int | None] = {
            "hostname": values.get("HOSTNAME"),
            "architecture": values.get("ARCHITECTURE"),
            "cpu_model": values.get("CPU_MODEL"),
            "cpu_cores": integer_value("CPU_CORES"),
            "memory_total_bytes": integer_value("MEMORY_TOTAL_BYTES"),
            "disk_total_bytes": integer_value("DISK_TOTAL_BYTES"),
        }
        software: dict[str, Optional[str]] = {
            "os_name": values.get("OS_NAME"),
            "os_version": values.get("OS_VERSION"),
            "kernel": values.get("KERNEL"),
            "package_manager": values.get("PACKAGE_MANAGER"),
            "python_version": values.get("PYTHON_VERSION"),
            "docker_version": values.get("DOCKER_VERSION"),
            "git_version": values.get("GIT_VERSION"),
        }

        return (
            {key: value for key, value in hardware.items() if value is not None},
            {key: value for key, value in software.items() if value is not None},
        )

    async def inspect_server(self, server: Server) -> ServerInspectionResult:
        """SSH接続を確認し、同じ接続でサーバ構成情報を取得する"""
        password, private_key = self._server_credentials(server)
        started_at = time.monotonic()
        conn = await self._create_connection(
            host=server.host,
            port=server.port,
            username=server.username,
            auth_method=server.auth_method,
            password=password,
            private_key=private_key,
        )
        latency_ms = max(0, round((time.monotonic() - started_at) * 1000))

        try:
            try:
                result = await asyncio.wait_for(
                    conn.run(INVENTORY_COMMAND, check=False),
                    timeout=self.inventory_timeout,
                )
                hardware_info, software_info = self._parse_inventory(result.stdout or "")
                warning = None
                if not hardware_info and not software_info:
                    warning = "接続には成功しましたが、構成情報を取得できませんでした"
                return ServerInspectionResult(
                    latency_ms=latency_ms,
                    hardware_info=hardware_info,
                    software_info=software_info,
                    warning=warning,
                )
            except asyncio.TimeoutError:
                return ServerInspectionResult(
                    latency_ms=latency_ms,
                    hardware_info={},
                    software_info={},
                    warning=f"接続には成功しましたが、構成情報の取得が{self.inventory_timeout}秒でタイムアウトしました",
                )
        finally:
            conn.close()
            await conn.wait_closed()
    
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
            
            try:
                # 簡単なコマンドを実行して接続を確認
                await conn.run("echo 'connection test'", check=True)
            finally:
                conn.close()
                await conn.wait_closed()
            
            return True, "接続に成功しました"
            
        except SSHConnectionError as e:
            return False, str(e)
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
            password, private_key = self._server_credentials(server)
            
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

                return exit_code, stdout, stderr

            except asyncio.TimeoutError:
                raise SSHExecutionError(f"スクリプト実行がタイムアウトしました（{self.timeout}秒）")
            finally:
                conn.close()
                await conn.wait_closed()
            
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
        except SSHConnectionError:
            raise
        except Exception as e:
            raise SSHConnectionError(f"予期しないエラー: {str(e)}")


# シングルトンインスタンス
ssh_service = SSHService()
