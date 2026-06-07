"""
API Auth — JWT-based authentication reading from existing auth_config.yaml.
Uses the same bcrypt credential store as the original Streamlit auth.
Does NOT modify any existing data, memory, reports, or logs.
"""
import os
import yaml
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ── Config ────────────────────────────────────────────
AUTH_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'ui', 'auth_config.yaml')
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dsmi-agent-jwt-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security = HTTPBearer()

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


# ── YAML Config Helpers ───────────────────────────────
def _load_config() -> dict:
    """Load the auth YAML config (same file as Streamlit auth)."""
    if not os.path.exists(AUTH_CONFIG_PATH):
        default_config = {
            'credentials': {
                'usernames': {
                    'admin': {
                        'email': 'admin@demo.com',
                        'name': 'Admin User',
                        'password': get_password_hash('admin123'),
                        'role': 'admin'
                    }
                }
            },
            'cookie': {
                'expiry_days': 30,
                'key': 'dsmi_agent_signature',
                'name': 'dsmi_agent_cookie'
            },
            'pre-authorized': {'emails': []}
        }
        os.makedirs(os.path.dirname(AUTH_CONFIG_PATH), exist_ok=True)
        with open(AUTH_CONFIG_PATH, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)

    with open(AUTH_CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)


def _save_config(config: dict):
    """Persist config back to YAML (for registration)."""
    with open(AUTH_CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


# ── Core Auth Functions ───────────────────────────────
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate against the YAML credential store."""
    config = _load_config()
    users = config.get('credentials', {}).get('usernames', {})
    user = users.get(username)
    if not user:
        return None
    if not verify_password(password, user['password']):
        return None
    return {
        'username': username,
        'name': user.get('name', username),
        'email': user.get('email', ''),
    }


def register_user(username: str, password: str, name: str, email: str) -> dict:
    """Register a new user into the YAML credential store."""
    config = _load_config()
    users = config.get('credentials', {}).get('usernames', {})
    
    if username in users:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    users[username] = {
        'email': email,
        'name': name,
        'password': get_password_hash(password),
        'role': 'user'
    }
    _save_config(config)
    return {'username': username, 'name': name, 'email': email}


# ── JWT Token Helpers ─────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """FastAPI dependency — extracts and validates the JWT from the Authorization header."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    config = _load_config()
    users = config.get('credentials', {}).get('usernames', {})
    user = users.get(username)
    if user is None:
        raise credentials_exception

    return {
        'username': username,
        'name': user.get('name', username),
        'email': user.get('email', ''),
    }
