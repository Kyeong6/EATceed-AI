# 메인 로직 작성
import os
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from operator import itemgetter
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser
from core.config import settings
from db.database import get_db
from db.models import AnalysisStatus
from db.crud import (create_eat_habits, get_user_data, get_all_member_id, get_last_weekend_meals, 
                     add_analysis_status, update_analysis_status, create_diet_analysis)
from models.food_analysis_model import (DietAdvice, DietNurientAnalysis, DietImprovement,
                                        CustomRecommendation, DietSummary)
from utils.file_handler import read_prompt
from utils.scheduler import scheduler_listener
from errors.server_exception import ExternalAPIError, FileAccessError, QueryError
from logs.logger_config import get_logger

# 스케줄러 테스트
from datetime import timedelta
from apscheduler.triggers.date import DateTrigger

# 공용 로거 
logger = get_logger()

# JSON 파서 생성
advice_parser = JsonOutputParser(pydantic_object=DietAdvice)
nutrient_parser = JsonOutputParser(pydantic_object=DietNurientAnalysis)
improvement_parser = JsonOutputParser(pydantic_object=DietImprovement)
custom_parser = JsonOutputParser(pydantic_object=CustomRecommendation)
summary_parser = JsonOutputParser(pydantic_object=DietSummary)

# Langchain 모델 설정: analysis / other
llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
analysis_llm = ChatOpenAI(model='gpt-4o', temperature=0)

# csv 파일 조회 및 필터링 진행
def filter_calculate_averages(data_path, user_data):
    
    # csv 파일 조회
    csv_path = os.path.join(data_path, "diet_advice.csv")
    df = pd.read_csv(csv_path)

    # csv 파일 조회 없을 시 예외처리 
    if df.empty:
        logger.error("csv 파일(diet_advice.csv)을 불러오기에 실패했습니다.")
        raise FileAccessError()

    # 조건 필터링
    filtered_df = df[
        (df['gender'] == user_data['gender']) &
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
    
# # 유저 데이터 형식 변환
# def extract_user_data(user_data: dict) -> dict:
#     return {
#         'gender': user_data['user'][0]['gender'],
#         'age': user_data['user'][1]['age'],
#         'height': user_data['user'][2]['height'],
#         'weight': user_data['user'][3]['weight'],
#         'physical_activity_index': user_data['user'][12]['physical_activity_index'],
#         'carbohydrate': user_data['user'][8]['carbohydrate'],
#         'protein': user_data['user'][6]['protein'],
#         'fat': user_data['user'][7]['fat'],
#         'calorie': user_data['user'][5]['calorie'],
#         'dietary_fiber': user_data['user'][9]['dietary_fiber'],
#         'sugars': user_data['user'][10]['sugars'],
#         'sodium': user_data['user'][11]['sodium'],
#         'tdee': user_data['user'][13]['tdee'],
#         'etc': user_data['user'][14]['etc'],
#         'target_weight': user_data['user'][15]['target_weight']
#     }

# # 사용자 정보 기반으로 평균 영양소 값 계산
# def calculate_nutrient_averages(user_dict: dict) -> dict:
#     averages = filter_calculate_averages(settings.DATA_PATH, user_dict)
#     return {key: averages.get(key, "데이터 없음") for key in ["carbo_avg", "protein_avg", "fat_avg"]}

# Prompt 템플릿 정의
def create_prompt_template(file_path, input_variables, parser=None):
    prompt_content = read_prompt(file_path)
    template_kwargs = {"template": prompt_content, "input_variables": input_variables}
    if parser:
        template_kwargs["partial_variables"] = {"format_instructions": parser.get_format_instructions()}
    return PromptTemplate(**template_kwargs)

# Chain 정의: 식습관 조언
def create_advice_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "diet_advice.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "gender", "age", "height", "weight", "physical_activity_index",
            "carbohydrate", "protein", "fat", "carbo_avg", "protein_avg", "fat_avg"
        ],
        parser=None
    )
    return prompt_template | llm | advice_parser

# Chain 정의: 전체적인 영양소 분석
def create_nutrition_analysis_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "nutrition_analysis.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "gender", "age", "height", "weight",
            "physical_activity_index", "carbohydrate", "protein", "fat",
            "calorie", "sodium", "dietary_fiber", "sugars",
            "carbo_avg", "protein_avg", "fat_avg", "tdee"
        ],
        parser=nutrient_parser
    )
    return prompt_template | analysis_llm | nutrient_parser

# Chain 정의: 개선점
def create_improvement_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "diet_improvement.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "carbohydrate", "carbo_avg", "protein", "protein_avg",
            "fat", "fat_avg", "calorie", "tdee", "nutrition_analysis", "target_weight"
        ],
        parser=improvement_parser
    )
    return prompt_template | analysis_llm | improvement_parser

# Chain 정의: 맞춤형 식단 제공
def create_diet_recommendation_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "custom_recommendation.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "diet_improvement", "etc", "target_weight"
        ],
        parser=custom_parser
    )
    return prompt_template | analysis_llm | custom_parser

# Chain 정의: 식습관 분석 요약
def create_summarize_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "diet_summary.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "nutrition_analysis", "diet_improvement", "custom_recommendation"
        ],
        parser=summary_parser
    )
    return prompt_template | llm | summary_parser

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
                "carbohydrate": RunnablePassthrough(),
                "carbo_avg": RunnablePassthrough(),
                "protein": RunnablePassthrough(),
                "protein_avg": RunnablePassthrough(),
                "fat": RunnablePassthrough(),
                "fat_avg": RunnablePassthrough(),
                "weight": RunnablePassthrough(),
                "target_weight": RunnablePassthrough(),
                "calorie": RunnablePassthrough(),
                "tdee": RunnablePassthrough(),
                "etc": RunnablePassthrough()
            }
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

# # 식습관 조언 체인 실행
# def execute_advice_chain(user_dict: dict, user_data: dict, averages: dict) -> dict:
#     advice_chain = create_advice_chain()
#     input_data = {**user_data, **averages}
#     return advice_chain.invoke(input_data)

# # 식습관 분석(Multi-Chain) 체인 실행
# def execute_multi_chain(user_data: dict, averages: dict) -> dict:
#     input_data = {**user_data, **averages}
#     multi_chain = create_multi_chain(input_data)
#     return multi_chain.invoke(input_data)

# # 분석 결과 데이터베이스 저장(EAT_HABITS_TB / DIET_ANALYSIS_TB)
# def save_analysis_results(db, status_pk, advice_result, analysis_results, weight_result, user_data):
#     eat_habits = create_eat_habits(
#         db=db,
#         weight_prediction=weight_result,
#         advice_carbo=advice_result["carbo_advice"],
#         advice_protein=advice_result["protein_advice"],
#         advice_fat=advice_result["fat_advice"],
#         summarized_advice=analysis_results["diet_summary"]["diet_summary"],
#         analysis_status_id=status_pk,
#         avg_calorie=user_data['calorie']
#     )    
#     create_diet_analysis(
#         db=db,
#         eat_habits_id=eat_habits.EAT_HABITS_PK,
#         nutrient_analysis=analysis_results["nutrition_analysis"]["nutrient_analysis"],
#         diet_improve=analysis_results["diet_improvement"]["diet_improvement"],
#         custom_recommend=analysis_results["custom_recommendation"]["custom_recommendation"]
#     )

# 식습관 분석 실행 함수
def run_analysis(db: Session, member_id: int):
    # 분석 상태 업데이트
    analysis_status = add_analysis_status(db, member_id)

    try:
        # 분석 시작 시간
        start_time = datetime.now()
        logger.info(f"분석 시작 member_id: {member_id} at {start_time}")

        # 유저 데이터 조회
        user_data = get_user_data(db, member_id)

        # 유저 데이터 조회 실패 예외처리 
        if not user_data:
            logger.error("run_analysis: user_data 조회 에러 발생")
            QueryError()

        user_dict = {
            'gender': user_data['user'][0]['gender'],
            'age': user_data['user'][1]['age'],
            'height': user_data['user'][2]['height'],
            'weight': user_data['user'][3]['weight'],
            'physical_activity_index': user_data['user'][12]['physical_activity_index']
        }

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

        input_data = {
            "gender": user_data['user'][0]['gender'],
            "age": user_data['user'][1]['age'],
            "height": user_data['user'][2]['height'],
            "weight": user_data['user'][3]['weight'],
            "physical_activity_index": user_data['user'][12]['physical_activity_index'],
            "carbohydrate": user_data['user'][8]['carbohydrate'],
            "protein": user_data['user'][6]['protein'],
            "fat": user_data['user'][7]['fat'],
            "calorie": user_data['user'][5]['calorie'],
            "dietary_fiber": user_data['user'][9]['dietary_fiber'],
            "sugars": user_data['user'][10]['sugars'],
            "sodium": user_data['user'][11]['sodium'],
            "tdee": user_data['user'][13]['tdee'],
            "etc": user_data['user'][14]['etc'],
            "target_weight": user_data['user'][15]['target_weight'],
            "carbo_avg": averages["carbo_avg"],
            "protein_avg": averages["protein_avg"],
            "fat_avg": averages["fat_avg"]
        }

        # Multi-Chain 실행
        multi_chain = create_multi_chain(input_data)
        result = multi_chain.invoke(input_data)

        # 결과값 JSON 변환 및 저장
        nutrient_analysis_str = result["nutrition_analysis"]["nutrient_analysis"]
        diet_improvement_str = result["diet_improvement"]["diet_improvement"]
        custom_recommendation_str = result["custom_recommendation"]["custom_recommendation"]
        diet_summary_str = result["diet_summary"]["diet_summary"]

        # 식습관 조언 데이터 저장
        eat_habits = create_eat_habits(
            db=db,
            weight_prediction=weight_result,
            advice_carbo=result_advice["carbo_advice"],
            advice_protein=result_advice["protein_advice"],
            advice_fat=result_advice["fat_advice"],
            summarized_advice=diet_summary_str,
            analysis_status_id=analysis_status.STATUS_PK,
            avg_calorie=user_data['user'][5]['calorie']
        )

        # 식습관 분석 데이터 저장
        create_diet_analysis(
            db=db,
            eat_habits_id=eat_habits.EAT_HABITS_PK,
            nutrient_analysis=nutrient_analysis_str,
            diet_improve=diet_improvement_str,
            custom_recommend=custom_recommendation_str
        )

        # 분석 상태 완료 처리
        update_analysis_status(db, analysis_status.STATUS_PK)

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
    db: Session = next(get_db())
    try:
        # 유저 테이블에 존재하는 모든 member_id 조회
        member_ids = get_all_member_id(db)

        # 각 회원의 식습관 분석 수행
        # 현재는 for문을 통한 순차적으로 분석을 업데이트하지만, 추후에 비동기적 처리 필요
        for member_id in member_ids:
            try:
                # 지난 일주일 동안 식사 등록 유무 확인
                meals = get_last_weekend_meals(db, member_id)
                if meals:
                    # 분석 실행
                    run_analysis(db, member_id)
                else:
                    # 식사기록이 없는 경우 분석 대기 상태 해제
                    db.query(AnalysisStatus).filter(AnalysisStatus.MEMBER_FK == member_id).update({
                        "ANALYSIS_DATE": datetime.now(),
                        "IS_PENDING": False
                    })
            except Exception as e:
                db.query(AnalysisStatus).filter(AnalysisStatus.MEMBER_FK == member_id).update({
                    "ANALYSIS_DATE": datetime.now(),
                    "IS_PENDING": False
                })
                db.commit()
                logger.error(f"식습관 분석 실패 member_id: {member_id} - {e}")
    finally:
        db.close()

# APScheduler 설정 및 시작
def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    
    # 테스트 진행 스케줄러
    start_time = datetime.now() + timedelta(seconds=3)
    trigger = DateTrigger(run_date=start_time)
    scheduler.add_job(scheduled_task, trigger=trigger)

    # # 운영용 스케줄러
    # scheduler.add_job(scheduled_task, 'cron', day_of_week='mon', hour=0, minute=0)

    scheduler.add_listener(scheduler_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    scheduler.start()
    logger.info("스케줄러 시작")