import uvicorn
import logging
from fastapi import FastAPI, status
from fastapi.responses import UJSONResponse
from routers import diet_analysis, food_image_analysis, swagger_auth
from errors.handler import register_exception_handlers
from apis.food_analysis import test_start_scheduler

# 커스텀 로거 설정
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)


app = FastAPI(
    title="EATceed",
    description="API that use food classification and eating habits analysis",
    docs_url="/v1/ai/api/docs",
    redoc_url="/v1/ai/api/redocs",
    openapi_url="/v1/ai/api/openapi.json",
    default_response_class=UJSONResponse,
)

# handler
register_exception_handlers(app)

# router
app.include_router(diet_analysis.router)
app.include_router(food_image_analysis.router)
app.include_router(swagger_auth.router)

# API Server Test
@app.get("/", status_code=status.HTTP_200_OK)
async def read_root():
    return {"Hello" : "World"}


# 서버 실행
if __name__ == "__main__":
    
    # 테스트 스케줄러 
    test_start_scheduler()
    # # 스케줄러 시작
    # start_scheduler()
  
    uvicorn.run("main:app", host="127.0.0.1", port=8000)