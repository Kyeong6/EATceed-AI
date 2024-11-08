# 식습관 분석 router
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.crud import get_latest_eat_habits, get_analysis_status, calculate_avg_calorie
from auth.decoded_token import get_current_member
from errors.exception import InvalidJWT

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
    
    # 분석 상태 확인
    analysis_status = get_analysis_status(db, member_id)
    if not analysis_status:
        raise UserDataError("해당 유저에 대한 분석 데이터가 존재하지 않습니다.")

    # 분석 진행 중 여부 확인
    if analysis_status.IS_PENDING:
        raise UserDataError("해당 유저에 대한 분석이 진행 중입니다.")
    
    # 분석 완료 상태 확인
    if not analysis_status.IS_ANALYZED:
        raise UserDataError("분석이 아직 완료되지 않았습니다.")
    
    # 최신 분석 기록 조회
    latest_eat_habits = get_latest_eat_habits(db, analysis_status.STATUS_PK)
    if not latest_eat_habits:
        raise UserDataError("분석 결과를 찾을 수 없습니다.")

    # 분석 날짜
    analysis_date = analysis_status.ANALYSIS_DATE.strftime("%Y-%m-%d")
    
    # 평균 칼로리 계산
    avg_calorie = calculate_avg_calorie(db, member_id)

    response = {
        "success": True,
        "response": {
            "analysis_date": analysis_date,
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
        raise UserDataError("분석 상태 정보를 찾을 수 없습니다.")
    
    # 분석 진행 중 여부 확인
    if analysis_status.IS_PENDING:
         raise UserDataError("해당 유저에 대한 분석이 진행 중입니다.")
    
    # 분석 완료 상태 확인
    if not analysis_status.IS_ANALYZED:
        raise UserDataError("분석이 아직 완료되지 않았습니다.")

    analysis_date = analysis_status.ANALYSIS_DATE.strftime("%Y-%m-%d")

    # 분석 완료 응답
    response = {
        "success": True,
        "response": {
            "analysis_date": analysis_date
        },
        "error": None
    }
    
    return response