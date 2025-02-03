# 메인 로직 작성
import os
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from operator import itemgetter
from langchain_core.runnables import RunnablePassthrough
from core.config import settings
from db.database import get_db
from db.models import AnalysisStatus
from db.crud import (create_eat_habits, get_user_data, get_all_member_id, get_last_weekend_meals, 
                     add_analysis_status, update_analysis_status, create_diet_analysis)
from utils.scheduler import scheduler_listener
from templates.prompt_template import (create_advice_chain, create_nutrition_analysis_chain, create_improvement_chain, 
                                       create_diet_recommendation_chain, create_summarize_chain, create_evaluation_chain)
from errors.server_exception import ExternalAPIError, FileAccessError, QueryError
from logs.logger_config import get_logger

# 스케줄러 테스트
from datetime import timedelta
from apscheduler.triggers.date import DateTrigger

# 공용 로거 
logger = get_logger()
 
# 정량적 평가 기준(임계값)
THRESHOLD_RELEVANCE= 3.0
THRESHOLD_FAITHFULNESS= 0.6

# csv 파일 조회 및 필터링 진행
def filter_calculate_averages(data_path, user_data):
    
    # csv 파일 조회
    csv_path = os.path.join(data_path, "diet_advice.csv")
    df = pd.read_csv(csv_path)

    # csv 파일 조회 없을 시 예외처리 
    if df.empty:
        logger.error("csv 파일(diet_advice.csv)을 불러오기에 실패했습니다.")
        raise FileAccessError()
    
    # 성별 변환 처리 (user_data['gender'] -> 숫자로 변환)
    gender_map = {"Male": 1, "Female": 2}
    user_gender = gender_map.get(user_data['gender'], None)

    if user_gender is None:
        return {"carbo_avg": "데이터 없음", "protein_avg": "데이터 없음", "fat_avg": "데이터 없음"}

    # 조건 필터링
    filtered_df = df[
        (df['gender'] == user_gender) &
        (abs(df['age'] - user_data['age']) <= 6) &
        (abs(df['height'] - user_data['height']) <= 6) &
        (abs(df['weight'] - user_data['weight']) <= 6) &
        (abs(df['physical_activity_index'] - user_data['physical_activity_index']) <= 1)
    ]

    # 각 열의 평균 계산
    if not filtered_df.empty:
        averages = {
            'carbo_avg': filtered_df['carbohydrate'].mean(),
            'protein_avg': filtered_df['protein'].mean(),
            'fat_avg': filtered_df['fat'].mean(),
        }
    else:
        # 조건에 맞는 데이터가 없으면 평균값 데이터없음 설정
        averages = {'carbo_avg': "데이터 없음",
                    'protein_avg': "데이터 없음",
                    'fat_avg': "데이터 없음"}
    
    return averages

# 체중 예측 함수
def weight_predict(user_data: dict) -> str:
    
    energy = user_data['user'][5]["calorie"]
    tdee = user_data['user'][13]["tdee"]

    if energy > tdee:
        return '증가'
    else:
        return '감소'

# Analysis Multi-Chain 연결
def create_multi_chain(input_data):
    try:
        # 체인 정의
        nutrient_chain = create_nutrition_analysis_chain()
        improvement_chain = create_improvement_chain()
        recommendation_chain = create_diet_recommendation_chain()
        summary_chain = create_summarize_chain()
        
        # 체인 실행 흐름 정의
        multi_chain = (
            {
                "nutrition_analysis": nutrient_chain,
                "carbohydrate": itemgetter("carbohydrate"),
                "carbo_avg": itemgetter("carbo_avg"),
                "protein": itemgetter("protein"),
                "protein_avg": itemgetter("protein_avg"),
                "fat": itemgetter("fat"),
                "fat_avg": itemgetter("fat_avg"),
                "weight": itemgetter("weight"),
                "target_weight": itemgetter("target_weight"),
                "calorie": itemgetter("calorie"),
                "tdee": itemgetter("tdee"),
                "etc": itemgetter("etc")
            }
            # Chain 연결을 위한 Runnable 객체 생성
            | RunnablePassthrough()
            | {
                "diet_improvement": improvement_chain,
                "nutrition_analysis": itemgetter("nutrition_analysis"),
                "target_weight": itemgetter("target_weight"),
                "etc": itemgetter("etc")
            }
            | RunnablePassthrough()
            | {
                "custom_recommendation": recommendation_chain,
                "diet_improvement": itemgetter("diet_improvement"),
                "nutrition_analysis": itemgetter("nutrition_analysis")
            }
            | RunnablePassthrough()
            | {
                "diet_summary": summary_chain,
                "custom_recommendation": itemgetter("custom_recommendation"),
                "diet_improvement": itemgetter("diet_improvement"),
                "nutrition_analysis": itemgetter("nutrition_analysis")
            }
            | RunnablePassthrough()
        )
        
        return multi_chain
    except Exception as e:
        logger.error(f"Multi-Chain 실행 실패: {e}")
        raise ExternalAPIError()

# A/B 테스트 함수
def compare_results(result_A, result_B, eval_A, eval_B):
    # 가중치 설정
    w1, w2 = 0.7, 0.3

    # 평가 점수 계산(relevance + faithfulness)
    score_A = (w1 * eval_A["relevance"]) + (w2 * eval_A["faithfulness"])
    score_B = (w1 * eval_B["relevance"]) + (w2 * eval_B["faithfulness"])

    # 각 실행 점수 로그
    logger.info(f"A/B 테스트 비교 점수")
    logger.info(f"실행 A → Score: {score_A:.2f} (Relevance: {eval_A['relevance']:.2f}, Faithfulness: {eval_A['faithfulness']:.2f})")
    logger.info(f"실행 B → Score: {score_B:.2f} (Relevance: {eval_B['relevance']:.2f}, Faithfulness: {eval_B['faithfulness']:.2f})")

    # A와 B 중 더 높은 점수 가진 결과 선택
    if score_A >= score_B:
        logger.info(f"A/B 테스트 결과 → 첫 번째 실행 결과(A) 선택")
        return result_A
    else:
        logger.info(f"A/B 테스트 결과 → 두 번째 실행 결과(B) 선택")
        return result_B

# 평가 후 재실행 함수: A/B 테스트 적용
def run_multi_chain(user_data):
    evaluation_chain = create_evaluation_chain()

    # 첫 번째 실행(A)
    result_A = create_multi_chain(user_data).invoke(user_data)
    evaluation_A = evaluation_chain.invoke({
        **user_data,
        **result_A
    })

    # 첫 번째 실행 평가 결과 추가(A)
    result_A_with_eval = {**result_A, "evaluation": evaluation_A}
    relevance_A = evaluation_A["relevance"]
    faithfulness_A = evaluation_A["faithfulness"]

    # 첫 번째 실행 평가 점수 로그
    logger.info(f"첫 번째 실행(A) 평가 점수 → Relevance: {relevance_A:.2f}, Faithfulness: {faithfulness_A:.2f}")

    # 첫 번째 실행 결과가 임계값을 넘을 경우 해당 결과값 적재
    if relevance_A >= THRESHOLD_RELEVANCE and faithfulness_A >= THRESHOLD_FAITHFULNESS:
        logger.info("첫 번째 Multi-Chain(A) 실행 성공하여 결과 저장")
        return result_A_with_eval
    
    # 두 번째 실행(B)
    result_B = create_multi_chain(user_data).invoke(user_data)
    evaluation_B = evaluation_chain.invoke({
        **user_data,
        **result_B
    })

    # 두 번째 실행 평가 결과 추가(B)
    result_B_with_eval = {**result_B, "evaluation": evaluation_B}
    relevance_B = evaluation_B["relevance"]
    faithfulness_B = evaluation_B["faithfulness"]

    # 두 번째 실행 평가 점수 로그
    logger.info(f"두 번째 실행(B) 평가 점수 → Relevance: {relevance_B:.2f}, Faithfulness: {faithfulness_B:.2f}")

    # 두 번째 실행 결과가 임계값을 넘을 경우 해당 결과값 적재
    if relevance_B >= THRESHOLD_RELEVANCE and faithfulness_B >= THRESHOLD_FAITHFULNESS:
        logger.info("첫 번째 Multi-Chain(A) 실행 성공하여 결과 저장")
        return result_B_with_eval

    # 두 실행 모두 임계값 미달하여 A/B 테스트 후 최적의 결과값 적재
    logger.info("두 실행(A, B) 모두 임계값 미달")
    final_result = compare_results(result_A_with_eval, result_B_with_eval, evaluation_A, evaluation_B)
    
    return final_result

# 식습관 분석 실행 함수
def run_analysis(db: Session, member_id: int):
    # 분석 상태 업데이트
    analysis_status = add_analysis_status(db, member_id)

    try:
        # 분석 시작 시간
        start_time = datetime.now()
        logger.info(f"분석 시작 member_id: {member_id} at {start_time}")

        # 식사 기록 확인
        meals = get_last_weekend_meals(db, member_id)
        if not meals:
            logger.info(f"member_id={member_id}: 최근 7일간 식사 기록 없음")

            # 식사 기록이 없으면 분석 상태 실패
            db.query(AnalysisStatus).filter(AnalysisStatus.STATUS_PK==analysis_status.STATUS_PK).update({
                "IS_PENDING": False,
                "IS_ANALYZED": False,
                "ANALYSIS_DATE": datetime.now()
            })
            db.commit()
            # 식사 기록 없으므로 분석 진행하지 않고 종료
            return 

        # 유저 데이터 조회
        user_data = get_user_data(db, member_id)

        # 유저 데이터 조회 실패 예외처리 
        if not user_data:
            logger.error("run_analysis: user_data 조회 에러 발생")
            QueryError()

         # 리스트를 딕셔너리로 변환
        user_dict = {key: value for d in user_data["user"] for key, value in d.items()}

        # 영양소 평균값 계산
        averages = filter_calculate_averages(settings.DATA_PATH, user_dict)
        for key in ["carbo_avg", "protein_avg", "fat_avg"]:
            averages[key] = averages.get(key, "데이터 없음")
        
        # 체중 예측
        weight_result = weight_predict(user_data)
        user_data['weight_change'] = weight_result

        # 식습관 조언 독립 실행
        advice_chain = create_advice_chain()
        result_advice = advice_chain.invoke({
            "gender": user_dict['gender'],
            "age": user_dict['age'],
            "height": user_dict['height'],
            "weight": user_dict['weight'],
            "physical_activity_index": user_dict['physical_activity_index'],
            "carbohydrate": user_data['user'][8]['carbohydrate'],
            "protein": user_data['user'][6]['protein'],
            "fat": user_data['user'][7]['fat'],
            "carbo_avg": averages["carbo_avg"],
            "protein_avg": averages["protein_avg"],
            "fat_avg": averages["fat_avg"]
        })
        logger.info(f"Advice chain result: {result_advice}")

        updated_user_data = {
            **user_dict,  # 🔥 user_dict의 모든 값을 포함
            "carbo_avg": averages["carbo_avg"],
            "protein_avg": averages["protein_avg"],
            "fat_avg": averages["fat_avg"]
        }

        # Multi-Chain 실행
        final_results = run_multi_chain(updated_user_data)

        # 식습관 조언 데이터 저장
        eat_habits = create_eat_habits(
            db=db,
            weight_prediction=weight_result,
            advice_carbo=result_advice["carbo_advice"],
            advice_protein=result_advice["protein_advice"],
            advice_fat=result_advice["fat_advice"],
            summarized_advice=final_results["diet_summary"],
            analysis_status_id=analysis_status.STATUS_PK,
            avg_calorie=user_data['user'][5]['calorie']
        )

        # 식습관 분석 데이터 저장
        create_diet_analysis(
            db=db,
            eat_habits_id=eat_habits.EAT_HABITS_PK,
            nutrient_analysis=final_results["nutrition_analysis"],
            diet_improve=final_results["diet_improvement"],
            custom_recommend=final_results["custom_recommendation"]
        )

        # 분석 상태 완료 처리
        update_analysis_status(db, analysis_status.STATUS_PK)
        db.commit()

    except Exception as e:
        logger.error(f"분석 진행(run_analysis) 에러 member_id: {member_id}, user_data: {user_data} - {e}")

        # 분석 실패: IS_PENDING=False, IS_ANALYZED=False
        db.query(AnalysisStatus).filter(AnalysisStatus.STATUS_PK == analysis_status.STATUS_PK).update({
            "IS_PENDING": False,
            "IS_ANALYZED": False
        })
        db.commit()
    
    finally:
        # 분석 종료 시간
        end_time = datetime.now()
        logger.info(f"분석 완료 member_id: {member_id} at {end_time} (Elapsed time: {end_time - start_time})")

# 스케줄링 설정
def scheduled_task():
    try:
        # Session Pool에서 get_all_member_id 실행을 위한 임시 세션
        db_temp = next(get_db())
        # 유저 테이블에 존재하는 모든 member_id 조회
        member_ids = get_all_member_id(db_temp)
        db_temp.close()

        # 각 회원의 식습관 분석 수행
        # 현재는 for문을 통한 순차적으로 분석을 업데이트하지만, 추후에 비동기적 처리 필요
        for member_id in member_ids:
            db: Session = next(get_db())
            try:
                run_analysis(db, member_id)
            except Exception as e:
                db.rollback()
                logger.error(f"식습관 분석 실패 member_id: {member_id} - {e}")
            finally:
                db.close()
    except Exception as e:
        logger.error(f"스케줄링 전체 작업 중 오류 발생: {e}")

# APScheduler 설정 및 시작
def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    
    # # 테스트 진행 스케줄러
    # start_time = datetime.now() + timedelta(seconds=3)
    # trigger = DateTrigger(run_date=start_time)
    # scheduler.add_job(scheduled_task, trigger=trigger)

    # 운영용 스케줄러
    scheduler.add_job(scheduled_task, 'cron', day_of_week='mon', hour=0, minute=0)

    scheduler.add_listener(scheduler_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    scheduler.start()
    logger.info("스케줄러 시작")