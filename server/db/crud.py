import logging
from datetime import datetime, timedelta
from sqlalchemy import desc
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from db.models import EatHabits, Member, Food, Meal, MealFood, AnalysisStatus
from errors.business_exception import MemberNotFound, UserDataError, AnalysisInProgress, AnalysisNotCompleted, NoAnalysisRecord
from errors.server_exception import AnalysisSaveError, NoMemberFound, QueryError

# 로그 메시지
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


"""
식습관 분석 및 홈화면 분석 API : 실행되는 순서대로 정의

1. 서버(Background)상에서 실행
2. 요청에 따른 응답 제공
"""

"""
서버(Background)상에서 실행
"""

# member_id에 해당하는 사용자 정보 조회
def get_member_info(db: Session, member_id: int):
    member = db.query(Member).filter(Member.MEMBER_PK == member_id).first()

    # 존재하지 않은 회원
    if not member:
        logger.error(f"존재하지 않은 회원: {member_id}")
        raise MemberNotFound()
    
    return member


# TDEE 수식을 구하기 위한 사용자 신체정보 조회
def get_member_body_info(db: Session, member_id: int):

    member = get_member_info(db, member_id)
    
    # 신체활동지수(activity) 값 변환을 위한 데이터 사전 세팅
    activity_mapping = {
        'NOT_ACTIVE': 1.2,
        'LIGHTLY_ACTIVE': 1.3,
        'NORMAL_ACTIVE': 1.5,
        'VERY_ACTIVE': 1.7,
        'EXTREMELY_ACTIVE': 1.9
    }
    # 데이터베이스에 문자열로 되어있는 것을 매핑하여 수치화: 기본값은 1.2
    activity_value = activity_mapping.get(member.MEMBER_ACTIVITY, 1.2)  
    
    # 사용자 신체정보
    body_info = {
        'gender': member.MEMBER_GENDER,
        'age': member.MEMBER_AGE,
        'height': member.MEMBER_HEIGHT,
        'weight': member.MEMBER_WEIGHT,
        'physical_activity_index': activity_value
    }
    
    if not (member.MEMBER_GENDER and member.MEMBER_AGE and member.MEMBER_HEIGHT and member.MEMBER_WEIGHT):
        logger.error(f"회원의 신체 정보 조회 중 문제 발생")
        raise QueryError()

    return body_info

# 일주일간 MEAL_TYPE 조회
def get_last_weekend_meals(db: Session, member_id: int):
    
    now = datetime.now()
    # 지난 주 월요일 0시
    start_of_this_week = now - timedelta(days=now.weekday(), weeks=1)  
    # 이번 주 월요일 0시
    start_of_next_week = start_of_this_week + timedelta(weeks=1)  
    meals = db.query(Meal).filter(
        Meal.MEMBER_FK == member_id, 
        Meal.CREATED_DATE >= start_of_this_week,
        Meal.CREATED_DATE < start_of_next_week
        ).all()
    
    if not meals:
        logger.error(f"일주일 간의 식사 기록이 존재하지 않음: {member_id}")
        raise QueryError()
    
    return meals


# MEAL_FK에 해당하는 음식 조회
def get_meal_foods(db: Session, meal_id: int):
    meal_foods = db.query(MealFood).filter(MealFood.MEAL_FK == meal_id).all()

    if not meal_foods:
        logger.error("먹은 음식과 식사 매칭 실패")
        raise QueryError()
    
    return meal_foods
        

# FOOD_FK에 해당하는 음식 정보 조회
def get_food_info(db: Session, food_id: int):
    food = db.query(Food).filter(Food.FOOD_PK == food_id).first()
    
    if not food:
        logger.error("음식 정보가 존재하지 않음")
        raise QueryError()
    
    return food


# 최종적으로 얻고자하는 사용자에 따른 7일간의 영양성분의 평균값 얻기
def get_member_meals_avg(db: Session, member_id: int): 

    # 사용자가 일주일간 섭취한 음식
    meals = get_last_weekend_meals(db, member_id)

    # 영양성분 초기화
    total_nutrition = {
        "calorie": 0,
        "carbohydrate": 0,
        "fat": 0,
        "protein": 0,
        "serving_size": 0,
        "sugars": 0,
        "dietary_fiber": 0,
        "sodium": 0,
    }
    total_foods = 0

    # 식사 확인
    for meal in meals:
        meal_foods = get_meal_foods(db, meal.MEAL_PK)
        # 음식 확인
        for meal_food in meal_foods:
            food_info = get_food_info(db, meal_food.FOOD_FK)

            # 사용자가 먹은 양 설정(단위: multiple or g)
            if food_info:
                # 기본값 설정
                multiplier = 1
                # 인분(multiple) 단위 사용
                if meal_food.MEAL_FOOD_MULTIPLE is not None:
                    multiplier = meal_food.MEAL_FOOD_MULTIPLE
                # 그램(g) 단위 사용
                elif meal_food.MEAL_FOOD_G is not None:
                    multiplier = meal_food.MEAL_FOOD_G / food_info.FOOD_SERVING_SIZE

                # 최종 양 설정
                total_nutrition["calorie"] += food_info.FOOD_CALORIE * multiplier
                total_nutrition["carbohydrate"] += food_info.FOOD_CARBOHYDRATE * multiplier
                total_nutrition["fat"] += food_info.FOOD_FAT * multiplier
                total_nutrition["protein"] += food_info.FOOD_PROTEIN * multiplier
                total_nutrition["serving_size"] += food_info.FOOD_SERVING_SIZE * multiplier
                total_nutrition["sugars"] += food_info.FOOD_SUGARS * multiplier
                total_nutrition["dietary_fiber"] += food_info.FOOD_DIETARY_FIBER * multiplier
                total_nutrition["sodium"] += food_info.FOOD_SODIUM * multiplier

                # 일주일간 식사 등록 한 번 이상했는지 확인
                total_foods += 1

    # 일주일 간 식사 등록을 한 번 이상했을 경우
    if total_foods > 0:
        avg_nutrition = {key: value / total_foods for key, value in total_nutrition.items()}
    else:
        avg_nutrition = total_nutrition

    return avg_nutrition

# BMR 구하기
def get_bmr(gender: int, weight: float, height: float, age: int) -> float:
   # 남자
    if gender == 0: 
      # 남자일 경우의 bmr 수식
      bmr = 66 + (13.7 * weight) + (5 * height) - (6.8 * age)
    # 여자
    else:
       # 여자일 경우의 bmr 수식
       bmr = 655 + (9.6 * weight) + (1.7 * height) - (4.7 * age)
    return bmr

# TDEE 구하기
def get_tdee(bmr: float, activity: float) -> float:
   # tdee 수식
   tdee = bmr * activity
   return tdee

# 식습관 분석에 사용되는 사용자 데이터 조회
def get_user_data(db: Session, member_id: int):
    
    # 사용자 신체 정보 조회
    member_info = get_member_body_info(db, member_id)
    
    # 평균 영양 성분 조회
    avg_nutrition = get_member_meals_avg(db, member_id)
    
    # BMR 및 TDEE 계산
    bmr = get_bmr(
        gender=member_info['gender'],
        weight=member_info['weight'],
        height=member_info['height'],
        age=member_info['age']
    )
    tdee = get_tdee(bmr, member_info['physical_activity_index'])

    # 사용자 분석 데이터 구성
    user_data = {
        "user": [
            {"gender": 'Male' if member_info['gender'] == 0 else 'Female'},
            {"age": member_info['age']},
            {"height": member_info['height']},
            {"weight": member_info['weight']},
            {"serving_size": avg_nutrition["serving_size"]},
            {"calorie": avg_nutrition["calorie"]},
            {"protein": avg_nutrition["protein"]},
            {"fat": avg_nutrition["fat"]},
            {"carbohydrate": avg_nutrition["carbohydrate"]},
            {"dietary_fiber": avg_nutrition["dietary_fiber"]},
            {"sugars": avg_nutrition["sugars"]},
            {"sodium": avg_nutrition["sodium"]},
            {"physical_activity_index": member_info['physical_activity_index']},
            {"tdee": tdee}
        ]
    }

    # 식사 등록을 하지 않은 경우(영양 성분 값: 0)
    if all(value == 0 for value in avg_nutrition.values()):
        logger.error(f"식사 기록이 없어 평균 영양소 데이터 미존재: {member_id}")
        raise UserDataError()

    return user_data

# 식습관 분석 결과값 db에 저장
def create_eat_habits(db: Session, weight_prediction: str, advice_carbo: str,
                      advice_protein: str, advice_fat: str, synthesis_advice: str, analysis_status_id: int):
    try:
        eat_habits = EatHabits(
            ANALYSIS_STATUS_FK=analysis_status_id,
            WEIGHT_PREDICTION=weight_prediction,
            ADVICE_CARBO=advice_carbo,
            ADVICE_PROTEIN=advice_protein,
            ADVICE_FAT=advice_fat,
            SYNTHESIS_ADVICE=synthesis_advice,
        )
        
        db.add(eat_habits)
        db.commit()
        db.refresh(eat_habits)
        
        return eat_habits
    except Exception as e:
        logger.error(f"식습관 분석 결과 저장 중 오류 발생: {analysis_status_id} - {e}")
        db.rollback()
        raise AnalysisSaveError()
        
# 모든 사용자 조회: 전체 사용자에 대한 분석 결과 도출
def get_all_member_id(db: Session):
        
    result = [member.MEMBER_PK for member in db.query(Member).all()]

    if not result:
        logger.error("Member 테이블에 유저가 존재하지 않습니다.")
        raise NoMemberFound()

    return result

# 식습관 분석 알림: 분석 상태 추가
def add_analysis_status(db: Session, member_id: int):
    # 새 분석 상태 추가
    new_status = AnalysisStatus(
        MEMBER_FK=member_id,
        IS_ANALYZED=False,
        IS_PENDING=True,
        ANALYSIS_DATE=datetime.now()
    )
    db.add(new_status)
    db.commit()
    db.refresh(new_status)
    return new_status


# 식습관 분석 알림: 분석 상태 업데이트
def update_analysis_status(db: Session, status_id: int):
    try:
        # logger.info(f"업데이트 for status_id: {status_id} to IS_ANALYZED=True")
        
        # 분석 상태 업데이트
        analysis_status = db.query(AnalysisStatus).filter(
            AnalysisStatus.STATUS_PK == status_id
        ).first()

        # 존재 여부 확인
        if analysis_status:
            analysis_status.IS_ANALYZED = True
            analysis_status.IS_PENDING = False
            analysis_status.ANALYSIS_DATE = datetime.now()
            db.commit()
            # logger.info(f"분석 상태 업데이트 성공 status_id: {status_id}")

            # # 업데이트 확인용 추가 로그
            # updated_status = db.query(AnalysisStatus).filter(
            #     AnalysisStatus.STATUS_PK == status_id
            # ).first()
            # logger.info(f"확인된 업데이트 상태 status_id: {status_id} - IS_ANALYZED: {updated_status.IS_ANALYZED}, IS_PENDING: {updated_status.IS_PENDING}")
        
        # 기록이 존재하지 않을 경우 새로 추가
        else:
            logger.error(f"분석 상태 업데이트 실패: {status_id}가 존재하지 않습니다")
            raise AnalysisSaveError()
        
    except Exception as e:
        db.rollback()
        logger.error(f"분석 상태 업데이트 중 오류 발생: {e}")
        raise AnalysisSaveError()

"""
요청에 따른 응답 제공
"""

# 최신 분석 결과 조회: 서버(Background)상에서 이미 분석 결과 존재해야 데이터 응답 가능 
def get_latest_eat_habits(db: Session, analysis_status_id: int):

    result = db.query(EatHabits).filter(EatHabits.ANALYSIS_STATUS_FK == analysis_status_id).first()
    if not result:
        logger.error("최신 분석 기록이 존재하지 않습니다.")
        raise UserDataError()
    
    return result

# 사용자의 평균 칼로리 얻기: API 반환값 사용
def calculate_avg_calorie(db: Session, member_id: int):
    
    avg_nutrition = get_member_meals_avg(db, member_id)
    
    return avg_nutrition["calorie"]


# 최신 완료된 분석 날짜 조회 함수
def get_latest_analysis_date(db: Session, member_id: int):
    latest_completed = db.query(AnalysisStatus).filter(
        AnalysisStatus.MEMBER_FK == member_id,
        # 성공한 분석 날짜만 조회: AOS 캐싱
        AnalysisStatus.IS_ANALYZED == True
        ).order_by(desc(AnalysisStatus.ANALYSIS_DATE)).first()

    return latest_completed

# 다른 유저가 현재 분석 중인지를 확인
def is_analysis_in_progress_for_member(member_id: int, db: Session) -> bool:
    """
    다른 유저가 현재 분석 중인지 확인하는 함수
    """
    in_progress = db.query(AnalysisStatus).filter(
        AnalysisStatus.MEMBER_FK != member_id,
        AnalysisStatus.IS_PENDING == True
    ).first()
    
    return in_progress is not None


# 식습관 분석 알림: 분석 상태 조회
def get_analysis_status(db: Session, member_id: int):
    
    # 가장 최신의 분석 상태 조회(성공 여부 상관없음)
    analysis_status = db.query(AnalysisStatus).filter(
        AnalysisStatus.MEMBER_FK == member_id
    ).first()

    # 분석 상태 확인
    if not analysis_status:
        logger.info(f"해당 유저는 분석 상태 미존재입니다.: {member_id}")
        raise UserDataError()
    
    # 분석 진행 중 여부 확인
    """
    IS_ANALYZEd : False
    IS_PENDING : True
    """
    if not analysis_status.IS_ANALYZED and analysis_status.IS_PENDING:
        
        # 다른 유저의 분석으로 대기 중인 상태
        if not is_analysis_in_progress_for_member(member_id, db):
            logger.info(f"해당 유저는 분석 대기 중입니다.: {member_id}")
            raise AnalysisInProgress()
        
        # 분석이 진행 중인 경우(현재 유저)
        logger.info(f"해당 유저는 아직 분석이 완료되지 않았습니다.: {member_id}")
        raise AnalysisNotCompleted()

    # 분석이 완료되지 않은 경우
    """
    IS_ANALYZEd : False
    IS_PENDING : False
    """
    if not analysis_status.IS_ANALYZED and not analysis_status.IS_PENDING:
        
        # 최신 성공 분석 조회
        latest_completed = get_latest_analysis_date(db, member_id)

        # 최근 성공한 분석이 존재한다면 해당 기록 반환
        if latest_completed:
            logger.info(f"해당 유저는 최근 성공한 분석 기록 존재합니다.: {member_id}")
            return latest_completed
        else:
            # 완료된 기록이 전혀 없는 경우
            logger.info(f"해당 유저는 완료된 분석 기록이 없습니다.: {member_id}")
            raise NoAnalysisRecord()
                
    return analysis_status
