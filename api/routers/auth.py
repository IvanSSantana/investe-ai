import logging

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies.auth import verify_admin_key
from communication.dtos import ApiKeyCreateRequest, ApiKeyCreateResponse
from helpers.auth.api_key_generator import generate_api_key
from repository.api_key_repository import ApiKeyRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
    dependencies=[Depends(verify_admin_key)],
)

@router.post("/keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(payload: ApiKeyCreateRequest) -> ApiKeyCreateResponse:
    """Gera uma nova chave API. A chave em texto plano é retornada apenas nesta resposta — ela nunca é armazenada."""
    repository = ApiKeyRepository()
    plaintext_key, key_id, key_hash = generate_api_key()

    record = repository.create(
        key_id=key_id,
        key_hash=key_hash,
        name=payload.name,
        expires_at=payload.expires_at,
    )

    logger.info(f"API key created: key_id={record.key_id}, name='{record.name}'")

    return ApiKeyCreateResponse(
        key_id=record.key_id,
        api_key=plaintext_key,
        name=record.name,
        created_at=record.created_at,
        expires_at=record.expires_at,
    )

@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(key_id: str) -> None:
    """Faz um soft-revoke de uma chave API por key_id. O record é mantido para propósito de auditoria."""
    repository = ApiKeyRepository()
    revoked = repository.revoke(key_id)

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chave API não encontrada com key_id '{key_id}'.",
        )

    logger.info(f"API key revoked: key_id={key_id}")