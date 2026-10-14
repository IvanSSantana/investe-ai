import hmac
import logging
import os
from datetime import datetime

from fastapi import Cookie, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from helpers.auth.api_key_generator import hash_api_key
from repository.api_key_repository import ApiKeyRecord, ApiKeyRepository
from repository.session_repository import SessionRecord, SessionRepository

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", scheme_name="APIKeyAuth", auto_error=False)
_admin_key_header = APIKeyHeader(name="X-Admin-Key", scheme_name="AdminKeyAuth", auto_error=False)

_api_key_repository = ApiKeyRepository()
_session_repository = SessionRepository()

def _is_api_key_valid(record: ApiKeyRecord | None) -> bool:
    if record is None or not record.active:
        return False
    
    if record.expires_at is not None:
        expires_at = record.expires_at.replace(tzinfo=None) if record.expires_at.tzinfo else record.expires_at
        if expires_at < datetime.now():
            return False
        
    return True

def _is_session_valid(record: SessionRecord | None) -> bool:
    if record is None:
        return False
    
    return record.expires_at >= datetime.now()

def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Blocks the request unless a valid, active, and non-expired API key is provided."""
    record = _api_key_repository.find_by_hash(hash_api_key(api_key)) if api_key else None

    if not _is_api_key_valid(record):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API inválida ou expirada.",
        )

def optional_api_key(api_key: str | None = Security(_api_key_header)) -> bool:
    """Never raises an exception. Returns True if a valid, active, and non-expired API key was provided."""
    if not api_key:
        return False

    record = _api_key_repository.find_by_hash(hash_api_key(api_key))
    return _is_api_key_valid(record)

def verify_admin_key(admin_key: str | None = Security(_admin_key_header)) -> None:
    """Blocks the request unless the administrator key (ADMIN_API_KEY environment variable) is provided."""
    expected = os.getenv("ADMIN_API_KEY")

    if not expected or not admin_key or not hmac.compare_digest(admin_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de administrador inválida ou ausente.",
        )

def verify_session(session: str | None = Cookie(default=None)) -> SessionRecord:
    """Blocks the request unless the session cookie is valid and not expired.
    Returns the SessionRecord (which contains user_id) for use in the endpoint."""
    record = _session_repository.find_by_token(session) if session else None

    if not _is_session_valid(record):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada. Faça login novamente.",
        )

    return record  # type: ignore

def verify_api_key_or_session(
    api_key: str | None = Security(_api_key_header),
    session: str | None = Cookie(default=None),
) -> str:
    """Authorizes via API key or user session — whichever is valid first.
    Returns the user_id when authenticated via session, or an empty string when authenticated via API key
    (admin/integration keys do not necessarily have an associated user_id)."""
    api_key_record = _api_key_repository.find_by_hash(hash_api_key(api_key)) if api_key else None
    if _is_api_key_valid(api_key_record):
        return api_key_record.user_id # type: ignore
    
    session_record = _session_repository.find_by_token(session) if session else None
    if _is_session_valid(session_record):
        return session_record.user_id  # type: ignore

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticação necessária: forneça uma chave de API válida ou faça login.",
    )