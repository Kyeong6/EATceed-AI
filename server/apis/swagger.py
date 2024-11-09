import secrets
from fastapi import Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from core.config import settings
from errors.business_exception import InvalidJWT


# HTTP 기본 인증을 사용하는 Security 객체 생성
security = HTTPBasic()

# Swagger 인증
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_username = secrets.compare_digest(credentials.username, settings.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise InvalidJWT()
        
    return credentials.username