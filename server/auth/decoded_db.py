import os
import base64
from Crypto.Cipher import AES
from hashlib import sha256
from logs.logger_config import get_logger
from errors.server_exception import DecryptError


# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") == "prod":
    from core.config_prod import settings
elif os.getenv("APP_ENV") == "dev":
    from server.core.config_dev import settings
else:
    from server.core.config_local import settings

# 공용 로거 
logger = get_logger()

# SHA-256 해싱을 통해 AES 키 생성 함수
def generate_key(secret: str) -> bytes:
    hash_digest = sha256(secret.encode("utf-8")).digest()
    return hash_digest[:16]

# 데이터 복호화 진행 함수
def decrypt_db(encrypted_data: str) -> str:

    try:
        # AES 키 생성
        key = generate_key(settings.ENCRYPTION_SECRET)

        # Base64 URL-safe 디코딩
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data)

        # AES 복호화(ECB 모드)
        cipher = AES.new(key, AES.MODE_ECB)
        decrypted_bytes = cipher.decrypt(encrypted_bytes)

        # PKCS5Padding 제거
        padding_length = decrypted_bytes[-1]
        if padding_length > AES.block_size:
            logger.error(f"PKCS5Padding 제거 과정 중 에러 발생")
            raise DecryptError()
        
        decrypted_data = decrypted_bytes[:-padding_length].decode("utf-8")

        return decrypted_data
    except Exception as e:
        logger.error(f"데이터 복호화 실패: {e}")
        raise DecryptError()