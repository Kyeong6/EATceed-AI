from fastapi import Request, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from errors.business_exception import (
    InvalidJWT, ExpiredJWT, MemberNotFound, InvalidFileFormat, RateLimitExceeded, ImageProcessingError, ImageAnalysisError, InvalidFoodImageError,
    UserDataError, AnalysisInProgress, AnalysisNotCompleted, NoAnalysisRecord
)
from errors.server_exception import (
    FileAccessError, ExternalAPIError, ServiceConnectionError, AnalysisSaveError,
    AnalysisProcessError, AnalysisStatusUpdateError, NoMemberFound, QueryError, DecryptError
)

# 서버 예외 핸들러
async def server_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "response": None,
            "error": exc.detail
        }
    )

# 비즈니스 예외 핸들러
async def business_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "response": None,
            "error": exc.detail
        }
    )

def register_exception_handlers(app: FastAPI):
    # 서버 예외 핸들러 등록
    app.add_exception_handler(FileAccessError, server_exception_handler)
    app.add_exception_handler(ExternalAPIError, server_exception_handler)
    app.add_exception_handler(ServiceConnectionError, server_exception_handler)
    app.add_exception_handler(AnalysisSaveError, server_exception_handler)
    app.add_exception_handler(AnalysisProcessError, server_exception_handler)
    app.add_exception_handler(AnalysisStatusUpdateError, server_exception_handler)
    app.add_exception_handler(NoMemberFound, server_exception_handler)
    app.add_exception_handler(QueryError, server_exception_handler)
    app.add_exception_handler(DecryptError, server_exception_handler)

    # 비즈니스 예외 핸들러 등록
    app.add_exception_handler(InvalidJWT, business_exception_handler)
    app.add_exception_handler(ExpiredJWT, business_exception_handler)
    app.add_exception_handler(MemberNotFound, business_exception_handler)
    app.add_exception_handler(InvalidFileFormat, business_exception_handler)
    app.add_exception_handler(RateLimitExceeded, business_exception_handler)
    app.add_exception_handler(ImageProcessingError, business_exception_handler)
    app.add_exception_handler(ImageAnalysisError, business_exception_handler)
    app.add_exception_handler(InvalidFoodImageError, server_exception_handler)
    app.add_exception_handler(UserDataError, business_exception_handler)
    app.add_exception_handler(AnalysisInProgress, business_exception_handler)
    app.add_exception_handler(AnalysisNotCompleted, business_exception_handler)
    app.add_exception_handler(NoAnalysisRecord, business_exception_handler)
