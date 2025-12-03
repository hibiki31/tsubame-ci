"""
セキュリティ関連の機能
- SSH認証情報の暗号化/復号化
- パスワードのハッシュ化
- JWTトークンの生成/検証
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64

from app.core.config import settings


# パスワードハッシュ化コンテキスト
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CredentialEncryptor:
    """認証情報の暗号化/復号化クラス"""
    
    def __init__(self, encryption_key: str):
        """
        Args:
            encryption_key: Fernet暗号化キー（base64エンコードされた32バイト）
        """
        # キーが適切な形式かチェック
        try:
            key_bytes = encryption_key.encode()
            # 既にbase64エンコードされている場合
            if len(key_bytes) == 44 and key_bytes.endswith(b'='):
                self.fernet = Fernet(key_bytes)
            else:
                # base64エンコードされていない場合は変換
                encoded_key = base64.urlsafe_b64encode(key_bytes.ljust(32)[:32])
                self.fernet = Fernet(encoded_key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")
    
    def encrypt(self, data: str) -> str:
        """
        文字列を暗号化
        
        Args:
            data: 暗号化する文字列
            
        Returns:
            暗号化された文字列（base64エンコード）
        """
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        暗号化された文字列を復号化
        
        Args:
            encrypted_data: 暗号化された文字列
            
        Returns:
            復号化された文字列
        """
        return self.fernet.decrypt(encrypted_data.encode()).decode()


# 認証情報暗号化のシングルトンインスタンス
credential_encryptor = CredentialEncryptor(settings.encryption_key)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    パスワードの検証
    
    Args:
        plain_password: 平文パスワード
        hashed_password: ハッシュ化されたパスワード
        
    Returns:
        パスワードが一致する場合True
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    パスワードのハッシュ化
    
    Args:
        password: 平文パスワード
        
    Returns:
        ハッシュ化されたパスワード
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWTアクセストークンの生成
    
    Args:
        data: トークンに含めるデータ
        expires_delta: 有効期限（デフォルト: 設定値）
        
    Returns:
        JWTトークン
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    JWTトークンのデコード
    
    Args:
        token: JWTトークン
        
    Returns:
        トークンのペイロード、無効な場合はNone
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None
