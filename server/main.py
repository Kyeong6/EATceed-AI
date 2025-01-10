import os
import uvicorn
import logging
from fastapi import FastAPI, status
from fastapi.responses import UJSONResponse
from routers import diet_analysis, food_image_analysis, swagger_auth, image_censorship
from errors.handler import register_exception_handlers
from apis.food_analysis import start_scheduler
from logs.logger_config import get_logger, configure_uvicorn_logger

# 공용 로거
logger = get_logger()

# 특정 라이브러리 로거 설정
logging.getLogger("openai").setLevel(logging.ERROR)  
logging.getLogger("httpx").setLevel(logging.ERROR)

# 환경에 따른 root_path 설정
env = os.getenv("APP_ENV")
root_path = f"/{env}" if env in ["prod", "dev"] else ""

# 운영 환경 Swagger 비활성화
docs_url = f"{root_path}/ai/v1/api/docs" if env != "prod" else None
redocs_url = f"{root_path}/ai/v1/api/redocs" if env != "prod" else None
openapi_url = f"{root_path}/ai/v1/api/openapi.json" if env != "prod" else None

# FastAPI APP 설정
app = FastAPI(
    title="EATceed",
    description="EATceed 프로젝트 AI 서버",
    docs_url=docs_url,
    redoc_url=redocs_url,
    openapi_url=openapi_url,
    default_response_class=UJSONResponse,
    root_path=root_path
)

# API Server Test
@app.get("/ai", status_code=status.HTTP_200_OK)
async def read_root():
    return {"Hello" : "World"}

# handler
register_exception_handlers(app)

# router
app.include_router(diet_analysis.router)
app.include_router(food_image_analysis.router)
app.include_router(image_censorship.router)
app.include_router(swagger_auth.router)


# 서버 실행
if __name__ == "__main__":

    # Uvicorn 로거 설정
    configure_uvicorn_logger()
    
    # 스케줄러 시작
    start_scheduler()

    # 외부 접근 가능 포트로 설정
    uvicorn.run("main:app", host="0.0.0.0", port=8000)