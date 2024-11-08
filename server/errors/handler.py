from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from exception import MemberNotFound, EmailNotMatch, InvalidJWT
import logging

logger = logging.getLogger(__name__)

# 비즈니스 로직 예외 처리
def business_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )

# 서버 에러 예외 처리
def server_exception_handler(request: Request, exc: Exception):
    # 로그에 자세한 에러 정보 기록
    logger.error(f"Server error: {exc}", exc_info=True)
    # 사용자에게는 일반적인 메시지 전달
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "response": None,
            "error": {
                "code": "500",
                "reason": "서버 오류가 발생했습니다.",
                "status": "500"
            }
        }
    )

# 예외 핸들러 등록
def register_exception_handlers(app):
    app.add_exception_handler(MemberNotFound, business_exception_handler)
    app.add_exception_handler(EmailNotMatch, business_exception_handler)
    app.add_exception_handler(InvalidJWT, business_exception_handler)
    # 기타 비즈니스 예외 등록...
    app.add_exception_handler(Exception, server_exception_handler)
