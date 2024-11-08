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
