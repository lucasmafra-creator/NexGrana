import hashlib, hmac, secrets, time
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
import jwt
from .config import settings
router=APIRouter()
_attempts={}

def hash_password(password):
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),310000).hex()
    return f'{salt}${digest}'

def verify_password(password, stored):
    try:
        salt,digest=stored.split('$',1)
        return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),310000).hex(),digest)
    except ValueError:
        return False

class Login(BaseModel):
    password: str=Field(min_length=1,max_length=200)

@router.post('/auth/login')
def login(data: Login, request: Request):
    if not settings.is_dev or not settings.local_admin_password_hash or not settings.session_signing_key:
        raise HTTPException(503,'Login local não configurado. Em servidor, configure identidade verificada.')
    ip=request.client.host if request.client else 'unknown'
    current=time.monotonic()
    recent=[t for t in _attempts.get(ip,[]) if current-t<60]
    if len(recent)>=8:
        raise HTTPException(429,'Aguarde um minuto antes de tentar novamente.')
    recent.append(current); _attempts[ip]=recent
    if not verify_password(data.password, settings.local_admin_password_hash):
        raise HTTPException(401,'Senha incorreta')
    _attempts.pop(ip,None)
    now=datetime.now(timezone.utc)
    token=jwt.encode({'sub':'local-mafra','iss':'sim-labs-local','aud':'sim-labs','iat':now,'exp':now+timedelta(hours=12)},settings.session_signing_key,algorithm='HS256')
    return {'token':token,'expires_in':43200,'name':'Mafra','mode':'local-private'}
