"""ジョブ間で共有する GitHub PAT の管理 API。"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_github_token_service
from app.schemas.github_token import GitHubTokenResponse, GitHubTokenUpdate
from app.services.github_token_service import (
    GitHubTokenInUseError,
    GitHubTokenService,
)


router = APIRouter()


@router.get("", response_model=GitHubTokenResponse)
async def get_github_token(
    service: GitHubTokenService = Depends(get_github_token_service),
) -> GitHubTokenResponse:
    """共有 PAT の値を露出せず、設定状態だけを返す。"""

    token = await service.get()
    return GitHubTokenResponse(
        configured=token is not None,
        updated_at=token.updated_at if token else None,
    )


@router.put("", response_model=GitHubTokenResponse)
async def update_github_token(
    token_data: GitHubTokenUpdate,
    service: GitHubTokenService = Depends(get_github_token_service),
) -> GitHubTokenResponse:
    """共有 PAT を暗号化して登録または更新する。"""

    token = await service.upsert(token_data.token)
    return GitHubTokenResponse(configured=True, updated_at=token.updated_at)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_github_token(
    service: GitHubTokenService = Depends(get_github_token_service),
) -> None:
    """参照ジョブがない場合だけ共有 PAT を削除する。"""

    try:
        await service.delete()
    except GitHubTokenInUseError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
