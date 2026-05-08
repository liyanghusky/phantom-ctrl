import hmac
from fastapi import Header, HTTPException, status
from config import settings


def verify_token(token: str) -> bool:
    return hmac.compare_digest(token, settings.SECRET_TOKEN)


async def require_auth(x_token: str = Header(..., alias="X-Token")):
    if not verify_token(x_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
