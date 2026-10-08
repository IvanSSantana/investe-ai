import hmac
import logging
import os
from datetime import datetime

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from helpers.auth.api_key_generator import hash_api_key
from repository.api_key_repository import ApiKeyRecord, ApiKeyRepository

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", scheme_name="APIKeyAuth", auto_error=False)
_admin_key_header = APIKeyHeader(name="X-Admin-Key", scheme_name="AdminKeyAuth", auto_error=False)

_repository = ApiKeyRepository()

def _is_valid(record: ApiKeyRecord | None) -> bool:
    if record is None or not record.active:
        return False
    
    if record.expires_at is not None:
        expires_at = record.expires_at.replace(tzinfo=None) if record.expires_at.tzinfo else record.expires_at
        if expires_at < datetime.now():
            return False
        
    return True

def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Bloqueia a requisição a menos que uma chave de API válida, ativa e não expirada seja fornecida."""
    record = _repository.find_by_hash(hash_api_key(api_key)) if api_key else None

    if not _is_valid(record):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API inválida ou expirada.",
        )

def optional_api_key(api_key: str | None = Security(_api_key_header)) -> bool:
    """Nunca lança exceção. Retorna True se uma chave de API válida, ativa e não expirada foi fornecida."""
    if not api_key:
        return False

    record = _repository.find_by_hash(hash_api_key(api_key))
    return _is_valid(record)

def verify_admin_key(admin_key: str | None = Security(_admin_key_header)) -> None:
    """Bloqueia a requisição a menos que a chave de administrador (variável de ambiente ADMIN_API_KEY) seja fornecida."""
    expected = os.getenv("ADMIN_API_KEY")

    if not expected or not admin_key or not hmac.compare_digest(admin_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de administrador inválida ou ausente.",
        )