"""
Routes d'authentification pour Notary Assistant.

Endpoints:
- POST /api/auth/login - Connexion utilisateur
- POST /api/auth/register - Inscription utilisateur
- POST /api/auth/forgot-password - Demande de réinitialisation
- POST /api/auth/reset-password - Réinitialisation du mot de passe
- GET /api/auth/me - Utilisateur courant
- POST /api/auth/logout - Déconnexion
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from services.surreal_service import get_surreal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# OAuth2 scheme for token-based auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# In-memory store for reset tokens (in production, use Redis or database)
# Format: {token: {"email": str, "expires": datetime}}
reset_tokens: dict[str, dict] = {}

# Store for active sessions (in production, use Redis)
active_sessions: dict[str, str] = {}  # token -> user_id


# ============================================================================
# Pydantic Models
# ============================================================================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str = "notaire"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordResponse(BaseModel):
    message: str


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse


# ============================================================================
# Helper Functions
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password using SHA256 (in production, use bcrypt)."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(plain_password) == hashed_password


def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def create_access_token(user_id: str) -> str:
    """Create an access token (simplified - in production use JWT)."""
    return f"token_{user_id}_{secrets.token_hex(16)}"


async def send_reset_email(email: str, token: str):
    """
    Send password reset email.

    In production, integrate with an email service like:
    - SendGrid
    - Mailgun
    - AWS SES
    - SMTP

    For now, we just log the reset link.
    """
    reset_url = f"http://localhost:3000/reset-password?token={token}"

    logger.info(f"""
    ============================================
    PASSWORD RESET EMAIL (Demo Mode)
    ============================================
    To: {email}
    Subject: Réinitialisation de votre mot de passe - Notary Assistant

    Bonjour,

    Vous avez demandé à réinitialiser votre mot de passe.
    Cliquez sur le lien ci-dessous pour créer un nouveau mot de passe:

    {reset_url}

    Ce lien expire dans 1 heure.

    Si vous n'avez pas fait cette demande, ignorez cet email.

    Cordialement,
    L'équipe Notary Assistant
    ============================================
    """)


async def get_user_by_email(email: str) -> Optional[dict]:
    """Get user from SurrealDB by email."""
    try:
        service = get_surreal_service()
        # Ensure we're connected
        if not service.db:
            await service.connect()

        result = await service.query(
            "SELECT * FROM user WHERE email = $email AND actif = true",
            {"email": email}
        )

        # SurrealDB returns results in different formats depending on version
        # It can be: [user1, user2] or [{"result": [user1, user2]}]
        if result and len(result) > 0:
            first_item = result[0]
            # Check if it's wrapped in {"result": [...]}
            if isinstance(first_item, dict) and "result" in first_item:
                users = first_item.get("result", [])
                return users[0] if users else None
            # Direct list of users
            elif isinstance(first_item, dict):
                return first_item
        return None
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return None


async def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user from SurrealDB by ID."""
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        result = await service.select(user_id)

        if result:
            # result can be a list or a single item
            if isinstance(result, list):
                return result[0] if len(result) > 0 else None
            return result
        return None
    except Exception as e:
        logger.error(f"Error getting user by id: {e}")
        return None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authentifie un utilisateur et retourne un token d'accès.

    Pour les tests, utilisez:
    - Email: notaire@test.com
    - Mot de passe: notaire123
    """
    email = form_data.username.lower()
    password = form_data.password

    # Check if user exists in SurrealDB
    user = await get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user ID (SurrealDB returns id as object or string)
    user_id = user.get("id")
    if isinstance(user_id, dict):
        user_id = f"{user_id.get('tb', 'user')}:{user_id.get('id', {}).get('String', '')}"
    elif hasattr(user_id, '__str__'):
        user_id = str(user_id)

    # Create access token
    access_token = create_access_token(user_id)

    # Store session
    active_sessions[access_token] = user_id

    logger.info(f"User logged in: {email}")

    return Token(access_token=access_token)


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    """
    Crée un nouveau compte utilisateur.
    """
    email = request.email.lower()
    name = request.name.strip()
    password = request.password

    # Validate name
    if len(name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nom doit contenir au moins 2 caractères"
        )

    # Validate password
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins 8 caractères"
        )

    # Check if email already exists
    existing_user = await get_user_by_email(email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà associé à un compte"
        )

    # Create new user in SurrealDB
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        user_id = secrets.token_hex(8)
        new_user = await service.create("user", {
            "email": email,
            "nom": name,
            "prenom": "",
            "password_hash": hash_password(password),
            "role": "notaire",
            "actif": True,
        }, record_id=user_id)

        logger.info(f"New user registered: {email}")

        # Get the created user ID
        created_id = new_user.get("id") if isinstance(new_user, dict) else f"user:{user_id}"
        if isinstance(created_id, dict):
            created_id = f"{created_id.get('tb', 'user')}:{created_id.get('id', {}).get('String', user_id)}"
        elif hasattr(created_id, '__str__'):
            created_id = str(created_id)

        return RegisterResponse(
            message="Compte créé avec succès",
            user=UserResponse(
                id=created_id,
                email=email,
                name=name,
                role="notaire"
            )
        )
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du compte"
        )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Envoie un email de réinitialisation de mot de passe.

    Note: Pour des raisons de sécurité, cette endpoint retourne toujours
    un succès même si l'email n'existe pas.
    """
    email = request.email.lower()

    # Check if user exists (but don't reveal this to the client)
    user = await get_user_by_email(email)

    if user:
        # Generate reset token
        token = generate_token()

        # Store token with expiration (1 hour)
        reset_tokens[token] = {
            "email": email,
            "expires": datetime.utcnow() + timedelta(hours=1)
        }

        # Send reset email
        await send_reset_email(email, token)

        logger.info(f"Password reset requested for: {email}")
    else:
        # Log but don't reveal to client
        logger.info(f"Password reset requested for unknown email: {email}")

    # Always return success (security best practice)
    return ForgotPasswordResponse(
        message="Si un compte existe avec cette adresse email, vous recevrez un lien de réinitialisation."
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Réinitialise le mot de passe avec un token valide.
    """
    token = request.token
    new_password = request.new_password

    # Validate password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins 8 caractères"
        )

    # Check if token exists and is valid
    token_data = reset_tokens.get(token)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le lien de réinitialisation est invalide"
        )

    # Check if token has expired
    if datetime.utcnow() > token_data["expires"]:
        # Remove expired token
        del reset_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le lien de réinitialisation a expiré"
        )

    email = token_data["email"]

    # Update password in SurrealDB
    try:
        service = get_surreal_service()
        if not service.db:
            await service.connect()

        await service.query(
            "UPDATE user SET password_hash = $password_hash, updated_at = time::now() WHERE email = $email",
            {"email": email, "password_hash": hash_password(new_password)}
        )
        logger.info(f"Password reset successful for: {email}")
    except Exception as e:
        logger.error(f"Failed to update password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour du mot de passe"
        )

    # Remove used token
    del reset_tokens[token]

    return ResetPasswordResponse(
        message="Votre mot de passe a été réinitialisé avec succès"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    """
    Retourne les informations de l'utilisateur connecté.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token is valid
    user_id = active_sessions.get(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Find user by ID in SurrealDB
    user = await get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé"
        )

    return UserResponse(
        id=str(user.get("id", user_id)),
        email=user.get("email", ""),
        name=user.get("nom", ""),
        role=user.get("role", "notaire")
    )


@router.post("/logout")
async def logout(token: Optional[str] = Depends(oauth2_scheme)):
    """
    Déconnecte l'utilisateur en invalidant son token.
    """
    if token and token in active_sessions:
        del active_sessions[token]
        logger.info("User logged out")

    return {"message": "Déconnexion réussie"}
