from fastapi import HTTPException, status


"""
인증
1. 잘못된 인증 토큰
2. 만료된 인증 토큰
3. 존재하지 않은 유저
"""
# 잘못된 인증 토큰
class InvalidJWT(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "SECURITY_401_1", 
                "reason": "잘못된 인증 토큰 형식입니다.", 
                "http_status": status.HTTP_401_UNAUTHORIZED
            }
        )

# 만료된 인증 토큰 
class ExpiredJWT(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "SECURITY_401_2", 
                "reason": "인증 토큰이 만료되었습니다.", 
                "http_status": status.HTTP_401_UNAUTHORIZED
            }
        )   

# 존재하지 않은 유저 
class MemberNotFound(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "MEMBER_400_9",
                "reason": "존재하지 않는 회원입니다.",
                "http_status": status.HTTP_404_NOT_FOUND
            }
        )

"""
음식 이미지 분석
1. 이미지 형식 에러(수신)
2. 기능 횟수 제한
3. 이미지 처리 실패
4. 음식 이미지 분석 실패(OpenAI API)
5. 음식이 아닌 다른 이미지 업로드
"""
# 이미지 파일 형식 에러(수신)
class InvalidFileFormat(HTTPException):
    def __init__(self, allowed_types: list):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "IMAGE_400_3",
                "reason": f"지원되지 않는 파일 형식: {', '.join(allowed_types)}",
                "http_status": status.HTTP_400_BAD_REQUEST
            }
        )


# 기능 횟수 제한
class RateLimitExceeded(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "IMAGE_429_1",
                "reason": "하루 요청 제한을 초과했습니다.",
                "http_status": status.HTTP_429_TOO_MANY_REQUESTS
            }
        )

# 이미지 처리 실패
class ImageProcessingError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "IMAGE_422_1",
                "reason": "이미지 처리 및 Base64 인코딩 중 오류가 발생했습니다.",
                "http_status": status.HTTP_422_UNPROCESSABLE_ENTITY
            }
        )


# 음식 이미지 분석 실패(OpenAI API)
class ImageAnalysisError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "IMAGE_400_1",
                "reason": "OpenAI API를 이용한 음식 이미지를 분석할 수 없습니다.",
                "http_status": status.HTTP_400_BAD_REQUEST
            }
        )

# 음식이 아닌 다른 이미지 업로드
class InvalidFoodImageError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "IMAGE_400_2",
                "reason": "음식이 아닌 이미지를 업로드하셨습니다.",
                "status": status.HTTP_400_BAD_REQUEST
            }
        )

"""
식습관 분석
1. 유저의 분석 데이터가 없는 경우
2. 분석 진행 중인 경우
3. 분석 미완료 상태
4. 분석 기록이 없는 경우
"""

# 유저의 분석 데이터가 없는 경우
class UserDataError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DIET_404_1",
                "reason": "해당 유저의 분석에 필요한 데이터가 존재하지 않습니다.",
                "http_status": status.HTTP_404_NOT_FOUND
            }
        )

# 분석 진행 대기 중인 경우
class AnalysisInProgress(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DIET_409_1",
                "reason": "해당 유저에 대한 분석 진행 대기 중입니다.",
                "http_status": status.HTTP_409_CONFLICT
            }
        )

# 분석 미완료 상태
class AnalysisNotCompleted(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DIET_404_2",
                "reason": "해당 유저에 대한 분석이 아직 완료되지 않았습니다.",
                "http_status": status.HTTP_404_NOT_FOUND
            }
        )

# 분석 기록이 없는 경우
class NoAnalysisRecord(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DIET_404_3",
                "reason": "해당 유저에 대한 분석 기록이 존재하지 않습니다.",
                "http_status": status.HTTP_404_NOT_FOUND
            }
        )
