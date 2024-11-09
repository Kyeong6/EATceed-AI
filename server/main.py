from fastapi import FastAPI, status
from fastapi.responses import UJSONResponse
from routers import diet_analysis, food_image_analysis, swagger_auth
from errors.handler import register_exception_handlers


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
