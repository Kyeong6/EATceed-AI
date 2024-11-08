from fastapi import HTTPException, status

# 공통 예외 응답 생성 함수
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

# 비즈니스 로직 예외 클래스 예시
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

class EmailNotMatch(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=generate_error_response(
                code="1001",
                reason="이메일이 일치하지 않습니다.",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        )

class InvalidJWT(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=generate_error_response(
                code="1002",
                reason="잘못된 토큰입니다.",
                http_status=status.HTTP_401_UNAUTHORIZED
            )
        )

# 필요한 비즈니스 예외 클래스들 추가...
