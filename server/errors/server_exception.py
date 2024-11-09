from fastapi import HTTPException, status

# 파일 접근 오류
class FileAccessError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SERVER_500_1",
                "reason": "파일 접근 중 오류가 발생했습니다.",
                "http_status": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        )

# 외부 API 호출 실패
class ExternalAPIError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SERVER_500_2",
                "reason": "외부 서비스 호출 중 문제가 발생했습니다.",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        )

# 외부 서버 연결 오류
class ServiceConnectionError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SERVER_500_3",
                "reason": "외부 서버 연결 중 오류가 발생했습니다.",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        )

# 분석 결과 저장 중 발생하는 오류
class AnalysisSaveError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SERVER_500_4",
                "reason": "분석 결과를 저장하는 중 오류가 발생했습니다.",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        )

# 분석 처리 중 발생하는 오류
class AnalysisProcessError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SERVER_500_5",
                "reason": "분석 처리 중 오류가 발생했습니다.",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        )

# 분석 상태 업데이트 중 발생하는 오류
class AnalysisStatusUpdateError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SERVER_500_6",
                "reason": "분석 상태 업데이트 중 오류가 발생했습니다.",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        )

# 유저가 아무도 존재하지 않을 경우 발생하는 오류
class NoMemberFound(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SERVER_500_7",
                "reason": "Member 테이블에 유저가 아무도 존재하지 않습니다.",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        )