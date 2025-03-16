from fastapi import APIRouter, Depends, File, UploadFile
from auth.decoded_token import get_current_member
from errors.business_exception import InvalidFileFormat
from logs.logger_config import get_logger
from swagger.response_config import cencoring_image_responses
from apis.food_image import process_image_to_base64
from apis.image_censor import detect_safe_search

# 공용 로거
logger = get_logger()


router = APIRouter(
    tags=["이미지 검열"]
)

# 이미지 검열 API
@router.post("/check", responses=cencoring_image_responses)
async def analyze_food_image(file: UploadFile = File(...), member_id: int = Depends(get_current_member)):

    # 지원하는 파일 형식
    ALLOWED_FILE_TYPES = ["image/jpeg", "image/png"]

    # 파일 형식 검증
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise InvalidFileFormat(allowed_types=ALLOWED_FILE_TYPES)
    
    # 이미지 처리 및 Base64 인코딩 진행
    image_base64 = await process_image_to_base64(file)

    # 이미지 검열 진행
    censor = detect_safe_search(member_id, image_base64)

    # 응답값 구성
    response = {
        "success": True,
        "response": censor,
        "error": None
    }

    return response