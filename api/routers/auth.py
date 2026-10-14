import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.dependencies.auth import verify_admin_key, verify_session
from communication.dtos import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from helpers.auth.api_key_generator import generate_api_key
from helpers.auth.password_hasher import hash_password, verify_password
from repository.api_key_repository import ApiKeyRepository
from repository.session_repository import SessionRecord, SessionRepository
from repository.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

admin_router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth-admin"],
    dependencies=[Depends(verify_admin_key)],
)

SESSION_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest) -> UserResponse:
    """Cria uma nova conta de usuário. A senha nunca é armazenada em texto plano."""
    user_repository = UserRepository()

    if user_repository.find_by_email(payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta cadastrada com este e-mail.",
        )

    user = user_repository.create(
        user_id=str(uuid4()),
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    logger.info(f"User registered: user_id={user.user_id}")

    return UserResponse(user_id=user.user_id, email=user.email, created_at=user.created_at)

@router.post("/login", response_model=UserResponse)
def login(payload: UserLoginRequest, response: Response) -> UserResponse:
    """Autentica o usuário e inicia uma sessão via cookie httpOnly."""
    user_repository = UserRepository()
    user = user_repository.find_by_email(payload.email)

    if user is None or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        )

    session = SessionRepository().create(user_id=user.user_id)

    response.set_cookie(
        key="session",
        value=session.session_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=SESSION_COOKIE_MAX_AGE,
        path="/",
    )

    logger.info(f"User logged in: user_id={user.user_id}")

    return UserResponse(user_id=user.user_id, email=user.email, created_at=user.created_at)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, session_record: SessionRecord = Depends(verify_session)) -> None:
    """Invalida a sessão atual e remove o cookie."""
    SessionRepository().delete(session_record.session_token)
    response.delete_cookie(key="session", path="/")
    logger.info(f"User logged out: user_id={session_record.user_id}")

@router.get("/me", response_model=UserResponse)
def get_current_user(session_record: SessionRecord = Depends(verify_session)) -> UserResponse:
    """Retorna os dados do usuário autenticado pela sessão atual."""
    user = UserRepository().find_by_id(session_record.user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    return UserResponse(user_id=user.user_id, email=user.email, created_at=user.created_at)


@router.post("/keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_own_api_key(
    payload: ApiKeyCreateRequest,
    session_record: SessionRecord = Depends(verify_session),
) -> ApiKeyCreateResponse:
    """Gera uma nova chave de API para o próprio usuário autenticado (uso em integrações externas)."""
    repository = ApiKeyRepository()
    plaintext_key, key_id, key_hash = generate_api_key()

    record = repository.create(
        key_id=key_id,
        key_hash=key_hash,
        name=payload.name,
        expires_at=payload.expires_at,
        user_id=session_record.user_id,
    )

    logger.info(f"API key created by user: key_id={record.key_id}, user_id={session_record.user_id}")

    return ApiKeyCreateResponse(
        key_id=record.key_id,
        api_key=plaintext_key,
        name=record.name,
        created_at=record.created_at,
        expires_at=record.expires_at,
    )

@router.delete("/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_own_api_key(key_id: str, session_record: SessionRecord = Depends(verify_session)) -> None:
    """Revoga (soft-delete) uma chave de API pertencente ao usuário autenticado."""
    repository = ApiKeyRepository()
    record = repository.find_by_key_id(key_id)  # ver nota abaixo

    if record is None or record.user_id != session_record.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chave de API não encontrada para este usuário com key_id '{key_id}'.",
        )

    repository.revoke(key_id)
    logger.info(f"API key revoked by user: key_id={key_id}, user_id={session_record.user_id}")

@admin_router.post("/admin/keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key_as_admin(payload: ApiKeyCreateRequest) -> ApiKeyCreateResponse:
    """Gera uma nova chave de API sem dono (user_id nulo)."""
    repository = ApiKeyRepository()
    plaintext_key, key_id, key_hash = generate_api_key()

    record = repository.create(
        key_id=key_id,
        key_hash=key_hash,
        name=payload.name,
        expires_at=payload.expires_at,
        user_id=None,
    )

    logger.info(f"API key created by admin: key_id={record.key_id}, name='{record.name}'")

    return ApiKeyCreateResponse(
        key_id=record.key_id,
        api_key=plaintext_key,
        name=record.name,
        created_at=record.created_at,
        expires_at=record.expires_at,
    )

@admin_router.delete("/admin/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key_as_admin(key_id: str) -> None:
    """Faz um soft-revoke de qualquer chave de API por key_id. O record é mantido para auditoria."""
    repository = ApiKeyRepository()
    revoked = repository.revoke(key_id)

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chave API não encontrada com key_id '{key_id}'.",
        )

    logger.info(f"API key revoked by admin: key_id={key_id}")