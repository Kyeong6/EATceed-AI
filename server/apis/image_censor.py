from google.cloud import vision
from logs.logger_config import get_logger
from errors.server_exception import ExternalAPIError

logger = get_logger()

# 이미지 검열을 위한 GCP API 이용
def detect_safe_search(member_id, image_base64):

    try:
        # 클라이언트 생성
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_base64)

        response = client.safe_search_detection(image=image)
        safe = response.safe_search_annotation

        # 검증 결과 확인
        categories = {
            "adult": safe.adult,
            "medical": safe.medical,
            "spoofed": safe.spoof,
            "violence": safe.violence,
            "racy": safe.racy,
        }

        # "LIKELY" 또는 "VERY_LIKELY" 판정
        for category, likelihood in categories.items():
            # LIKELY 이상의 경우
            if likelihood >= 4:  
                logger.info(f"유해한 이미지({category})를 업로드한 유저: {member_id}")
                return False
            
        return True
    except Exception as e:
        logger.error(f"GCP API 연결 오류 발생: {e}")
        raise ExternalAPIError()