import os

# 환경 설정 로드 함수
def load_settings():
    
    # 기본값을 'local'로 설정
    env = os.getenv("APP_ENV", "local").lower()

    if env == "prod":
        from core.config_prod import settings
    elif env == "dev":
        from core.config_dev import settings
    else:
        from core.config_local import settings

    return settings

settings = load_settings()