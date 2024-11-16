import uvicorn
import logging
from fastapi import FastAPI, status
from fastapi.responses import UJSONResponse
from routers import diet_analysis, food_image_analysis, swagger_auth
from errors.handler import register_exception_handlers
from apis.food_analysis import start_scheduler

# 커스텀 로거 설정
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)



app = FastAPI(
    title="EATceed",
    description="EATceed 프로젝트 AI 서버",
    docs_url=None,
    redoc_url=None,
    openapi_url="/ai/v1/api/openapi.json",
    default_response_class=UJSONResponse,
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
app.include_router(swagger_auth.router)


# 서버 실행
if __name__ == "__main__":
    
    # 스케줄러 시작
    start_scheduler()
  
    # 외부 접근 가능 포트로 설정
    uvicorn.run("main:app", host="0.0.0.0", port=8000)