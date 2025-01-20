# 식습관 분석 router
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.crud import get_latest_eat_habits, get_analysis_status, get_analysis_detail
from auth.decoded_token import get_current_member
from swagger.response_config import get_user_analysis_responses, get_status_alert_responses, get_detail_responses

router = APIRouter(
    tags=["식습관 분석"]
)

# 전체 식습관 분석 라우터
@router.get("/diet", responses=get_user_analysis_responses)
def get_user_analysis(db: Session = Depends(get_db), member_id: int = Depends(get_current_member)):
    
    # 최신 분석 상태 확인
    analysis_status = get_analysis_status(db, member_id)
    
    # 최신 분석 기록 조회
    latest_eat_habits = get_latest_eat_habits(db, analysis_status.STATUS_PK)
    
    # 분석 날짜
    analysis_date = analysis_status.ANALYSIS_DATE.strftime("%Y-%m-%d")
    
    # 식습관 분석 응답
    response = {
        "success": True,
        "response": {
            "analysis_date": analysis_date,
            "avg_calorie" : latest_eat_habits.AVG_CALORIE,
            "weight_prediction": latest_eat_habits.WEIGHT_PREDICTION,
            "advice_carbo": latest_eat_habits.ADVICE_CARBO,
            "advice_protein": latest_eat_habits.ADVICE_PROTEIN,
            "advice_fat": latest_eat_habits.ADVICE_FAT,
            "summarized_advice": latest_eat_habits.SUMMARIZED_ADVICE
        },
        "error": None
        }
    return response


# 식습관 분석 상태 알림 라우터
@router.get("/status", responses=get_status_alert_responses)
def get_status_alert(db: Session = Depends(get_db), member_id: int = Depends(get_current_member)):

    # 분석 유무 확인
    analysis_status = get_analysis_status(db, member_id)

    # 분석 날짜
    analysis_date = analysis_status.ANALYSIS_DATE.strftime("%Y-%m-%d")

    # 알림 응답
    response = {
        "success": True,
        "response": {
            "analysis_date": analysis_date
        },
        "error": None
    }
    
    return response

# 식습관 분석 결과 상세보기
@router.get("/detail", responses=get_detail_responses)
def get_detail(db: Session = Depends(get_db), member_id: int = Depends(get_current_member)):
    
    # 식습관 분석 상세보기 조회
    analysis_detail = get_analysis_detail(db, member_id)

    # 식습관 분석 상세보기 응답
    response = {
        "success": True,
        "response": {
            "nutrient_analysis": analysis_detail.NUTRIENT_ANALYSIS,
            "diet_improvement": analysis_detail.DIET_IMPROVE,
            "custom_recommendation": analysis_detail.CUSTOM_RECOMMEND
        },
        "error": None
    }

    return response
