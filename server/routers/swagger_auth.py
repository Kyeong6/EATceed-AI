from fastapi import Depends, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from apis.swagger import get_current_username


router = APIRouter(
    prefix="/v1/ai/api",
    tags=["Swagger"]
)

@router.get("/docs", response_class=HTMLResponse)
async def get_docs(username: str = Depends(get_current_username)) -> HTMLResponse:
    return get_swagger_ui_html(openapi_url="/v1/ai/api/openapi.json", title="docs")


@router.get("/redocs", response_class=HTMLResponse)
async def get_redoc(username: str = Depends(get_current_username)) -> HTMLResponse:
    return get_redoc_html(openapi_url="/v1/ai/api/openapi.json", title="redoc")