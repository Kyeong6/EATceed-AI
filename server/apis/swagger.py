import os
import secrets
from fastapi import Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from errors.business_exception import InvalidJWT

# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") == "prod":
    from core.config_prod import settings
else:
    from core.config import settings

# HTTP 기본 인증을 사용하는 Security 객체 생성
security = HTTPBasic()

# Swagger 인증
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_username = secrets.compare_digest(credentials.username, settings.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise InvalidJWT()
        
    return credentials.username