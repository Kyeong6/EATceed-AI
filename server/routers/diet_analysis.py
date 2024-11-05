# 식습관 분석 router
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.crud import get_latest_eat_habits, get_analysis_status, calculate_avg_calorie
from auth.decoded_token import get_current_member
import logging
from errors.custom_exceptions import InvalidJWT, UserDataError

# 로그 메시지
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/ai/diet_analysis",
    tags=["식습관 분석"]
)

# 전체 식습관 분석 라우터
@router.get("/")
def get_user_analysis(db: Session = Depends(get_db), member_id: int = Depends(get_current_member)):
    
    # 인증 확인
    if not member_id:
            raise InvalidJWT()

    latest_eat_habits = get_latest_eat_habits(db, member_id)
    if not latest_eat_habits:
         raise UserDataError("유저 데이터 에러입니다")
    
    # 평균 칼로리 계산
    avg_calorie = calculate_avg_calorie(db, member_id)

    response = {
        "success": True,
        "response": {
            "avg_calorie" : avg_calorie,
            "weight_prediction": latest_eat_habits.WEIGHT_PREDICTION,
            "advice_carbo": latest_eat_habits.ADVICE_CARBO,
            "advice_protein": latest_eat_habits.ADVICE_PROTEIN,
            "advice_fat": latest_eat_habits.ADVICE_FAT,
            "synthesis_advice": latest_eat_habits.SYNTHESIS_ADVICE
        },
        "error": None
        }
    return response


# 식습관 분석 상태 알림 라우터
@router.get("/status")
def get_status_alert(db: Session = Depends(get_db), member_id: int = Depends(get_current_member)):
    
    # 인증 확인
    if not member_id:
            raise InvalidJWT()
    
    # 분석 상태 조회
    analysis_status = get_analysis_status(db, member_id)
    
    if not analysis_status:
        raise UserDataError("식습관 분석 상태를 찾을 수 없습니다.")

    # 분석 완료 상태 응답
    response = {
        "success": True,
        "response": {
            "status": analysis_status.IS_ANALYZED,
            "analysis_date": analysis_status.ANALYSIS_DATE
        },
        "error": None
    }
    
    return response