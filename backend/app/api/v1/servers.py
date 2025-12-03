"""
サーバ管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.schemas.server import (
    ServerCreate,
    ServerUpdate,
    ServerResponse,
    ServerTestRequest,
    ServerTestResponse
)
from app.services.server_service import ServerService, ServerNotFoundError
from app.api.deps import get_server_service

router = APIRouter()


@router.get("", response_model=List[ServerResponse])
async def list_servers(
    service: ServerService = Depends(get_server_service)
):
    """
    サーバ一覧を取得
    """
    servers = await service.get_all()
    return servers


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: int,
    service: ServerService = Depends(get_server_service)
):
    """
    サーバ詳細を取得
    """
    try:
        server = await service.get_by_id(server_id)
        return server
    except ServerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
    server_data: ServerCreate,
    service: ServerService = Depends(get_server_service)
):
    """
    サーバを作成
    """
    server = await service.create(server_data)
    return server


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: int,
    server_data: ServerUpdate,
    service: ServerService = Depends(get_server_service)
):
    """
    サーバを更新
    """
    try:
        server = await service.update(server_id, server_data)
        return server
    except ServerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: int,
    service: ServerService = Depends(get_server_service)
):
    """
    サーバを削除
    """
    try:
        await service.delete(server_id)
    except ServerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/test", response_model=ServerTestResponse)
async def test_server_connection(
    test_data: ServerTestRequest,
    service: ServerService = Depends(get_server_service)
):
    """
    SSH接続をテスト
    """
    success, message = await service.test_connection(
        host=test_data.host,
        port=test_data.port,
        username=test_data.username,
        auth_method=test_data.auth_method,
        password=test_data.password,
        private_key=test_data.private_key
    )
    
    return ServerTestResponse(
        success=success,
        message=message
    )
