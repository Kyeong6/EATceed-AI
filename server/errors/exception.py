from fastapi import HTTPException, status

# 예외 응답 함수
def generate_error_response(code: str, reason: str, http_status: int):
    return {
        "success": False,
        "response": None,
        "error": {
            "code": code,
            "reason": reason,
            "status": str(http_status)
        }
    }

"""
인증
1. 잘못된 인증 토큰
2. 만료된 인증 토큰
"""
# 잘못된 인증 토큰
class InvalidJWT(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=generate_error_response(
                code="SECURITY_401_1", 
                reason="잘못된 인증 토큰 형식입니다.", 
                http_status=status.HTTP_401_UNAUTHORIZED),
            headers={"WWW-Authenticate": "Bearer"}
        )

# 만료된 인증 토큰 
class ExpiredJWT(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=generate_error_response(
            code="SECURITY_401_2", 
            reason="인증 토큰이 만료되었습니다.", 
            http_status=status.HTTP_401_UNAUTHORIZED),
            headers={"WWW-Authenticate": "Bearer"}
        )

# 존재하지 않은 유저 
class MemberNotFound(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=generate_error_response(
                code="MEMBER_400_9",
                reason="존재하지 않는 회원입니다.",
                http_status=status.HTTP_404_NOT_FOUND
            )
        )

"""
음식 이미지 분석
1. 기능 횟수 제한
2. 음식 이미지 분석 실패(OpenAI API)
"""

# 기능 횟수 제한
class RateLimitExceeded(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=generate_error_response(
                code="IMAGE_429_1",
                reason="하루 요청 제한을 초과했습니다.",
                http_status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        )


# 음식 이미지 분석 실패(OpenAI API)
class AnalysisError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=generate_error_response(
                code="IMAGE_400_1",
                reason="OpenAI API를 이용한 음식 이미지를 분석할 수 없습니다.",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        )