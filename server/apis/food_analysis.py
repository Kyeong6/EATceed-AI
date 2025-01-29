# 메인 로직 작성
import os
import pandas as pd
from openai import OpenAI
from datetime import datetime
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from db.database import get_db
from db.models import AnalysisStatus
from db.crud import create_eat_habits, get_user_data, get_all_member_id, get_last_weekend_meals, add_analysis_status, update_analysis_status
from errors.server_exception import FileAccessError, ExternalAPIError
from logs.logger_config import get_logger

# 스케줄러 테스트
from datetime import timedelta
from apscheduler.triggers.date import DateTrigger

# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") == "prod":
    from core.config_prod import settings
elif os.getenv("APP_ENV") == "dev":
    from core.config_dev import settings
else:
    from core.config_local import settings


# 공용 로거 
logger = get_logger()


# 스케줄러 이벤트 리스너 함수
def scheduler_listener(event):
    if event.exception:
        logger.error(f"스케줄러 작업 실패: {event.job_id} - {event.exception}")
    else:
        logger.info(f"스케줄러 작업 종료: {event.job_id}")


# Chatgpt API 사용
client = OpenAI(api_key = settings.OPENAI_API_KEY)

# prompt를 불러오기
def read_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        prompt = file.read().strip()

    if not prompt:
        logger.error("prompt 파일을 불러오기에 실패했습니다.")
        raise FileAccessError()
    
    return prompt

# 식습관 분석 진행을 위한 OpenAI API 연결
def get_completion(prompt, model="gpt-4o-mini"):
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0
    )
    return response.choices[0].message.content

# 체중 예측 함수: user_data 이용
def weight_predict(user_data: dict) -> str:
    
    energy = user_data['user'][5]["calorie"]
    tdee = user_data['user'][13]["tdee"]

    if energy > tdee:
        return '증가'
    else:
        return '감소'

# 식습관 조언 함수 (조언 프롬프트)
def analyze_advice(prompt_type, user_data):

    prompt_file = os.path.join(settings.PROMPT_PATH, f"{prompt_type}.txt")
    prompt = read_prompt(prompt_file)
    
    # 프롬프트 변수 설정
    carbohydrate = user_data['user'][8]['carbohydrate']
    protein = user_data['user'][6]['protein']
    fat = user_data['user'][7]['fat']
    sodium = user_data['user'][11]['sodium']
    dietary_fiber = user_data['user'][9]['dietary_fiber']
    sugar = user_data['user'][10]['sugars']
    
    prompt = prompt.format(carbohydrate=carbohydrate, protein=protein, fat=fat, 
                            sodium=sodium, dietary_fiber=dietary_fiber, sugars=sugar)

    # 식습관 분석 결과값 구성
    completion = get_completion(prompt)

    if not completion:
        logger.error("식습관 조언 기능 (외부 호출) 실패")
        raise ExternalAPIError()

    return completion

# 식습관 분석 함수 (판단 프롬프트)
def analyze_diet(prompt_type, user_data):

    prompt_file = os.path.join(settings.PROMPT_PATH, f"{prompt_type}.txt")
    prompt = read_prompt(prompt_file)
    df = pd.read_csv(os.path.join(settings.DATA_PATH, "analysis_diet.csv"))
    weight_change = weight_predict(user_data)
    
    # 프롬프트 변수 설정
    gender = user_data['user'][0]['gender']
    age = user_data['user'][1]['age']
    height = user_data['user'][2]['height']
    weight = user_data['user'][3]['weight']
    physical_activity_index = user_data['user'][12]['physical_activity_index']
    carbohydrate = user_data['user'][8]['carbohydrate']
    protein = user_data['user'][6]['protein']
    fat = user_data['user'][7]['fat']
    
    prompt = prompt.format(gender=gender, age=age, height=height, weight=weight, 
                            physical_activity_index=physical_activity_index,
                            carbohydrate=carbohydrate, protein=protein, fat=fat)
    
    # agent에 전달할 데이터 설정
    if weight_change == '증가':
        # 데이터에서 체중이 감소한 경우
        df = df[df['weight_change'] < 0] 
    else:
        # 데이터에서 체중이 증가한 경우
        df = df[df['weight_change'] > 0] 
    
    # langchain의 create_pandas_dataframe_agent 사용
    agent = create_pandas_dataframe_agent(
    ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=settings.OPENAI_API_KEY),
    df=df,
    # 상세 로그 출력 비활성화
    verbose=False,
    agent_type=AgentType.OPENAI_FUNCTIONS,
    allow_dangerous_code=True
    )
    
    completion = agent.invoke(prompt)

    if not completion:
        logger.error("식습관 분석 기능(외부 호출) 실패")
        raise ExternalAPIError()

    return completion

# 최종 식습관 분석 기능 함수
def full_analysis(db: Session, member_id: int):

    # 새로운 분석 상태 추가 및 진행 중 상태로 설정
    analysis_status = add_analysis_status(db, member_id)

    try:
        # 분석 시작 시간
        start_time = datetime.now()
        logger.info(f"분석 시작 member_id: {member_id} at {start_time}")

        # 식사 기록 확인
        meals = get_last_weekend_meals(db, member_id)
        if not meals:
            logger.info(f"member_id={member_id}: 최근 7일간 식사 기록 없음")

            # 식사 기록이 없으면 분석 실패 상태
            db.query(AnalysisStatus).filter(AnalysisStatus.STATUS_PK==analysis_status.STATUS_PK).update({
                "IS_PENDING": False,
                "IS_ANALYZED": False,
                "ANALYSIS_DATE": datetime.now()
            })
            db.commit()
            # 식사 기록 없으므로 분석 진행하지 않고 종료
            return 

        # 유저 데이터 활용
        user_data = get_user_data(db, member_id)

        # 체중 예측
        weight_result = weight_predict(user_data)
        user_data['weight_change'] = weight_result

        # 평균 칼로리 계산
        avg_calorie = user_data['user'][5]['calorie']

        # 각 프롬프트에 대해 분석 수행
        analysis_results = {}
        prompt_types = ['health_advice', 'weight_carbo', 'weight_fat', 'weight_protein']
        for prompt_type in prompt_types:
            if prompt_type == 'health_advice':  # 조언 프롬프트는 analyze_advice 함수
                result = analyze_advice(prompt_type, user_data)
                analysis_results[prompt_type] = result
            else:  # 판단 프롬프트는 analyze_diet 함수
                result = analyze_diet(prompt_type, user_data)
                analysis_results[prompt_type] = result['output']

        # DB에 결과값 저장
        create_eat_habits(
            db=db,
            weight_prediction=weight_result,
            advice_carbo=analysis_results['weight_carbo'],
            advice_protein=analysis_results['weight_protein'],
            advice_fat=analysis_results['weight_fat'],
            synthesis_advice=analysis_results['health_advice'],
            analysis_status_id=analysis_status.STATUS_PK,
            avg_calorie=avg_calorie
        )

        # 분석 성공적으로 완료 후 상태 업데이트(IS_ANALYZED = True)
        update_analysis_status(db, analysis_status.STATUS_PK)
        db.commit()

    except Exception as e:
        logger.error(f"분석 진행(full_analysis) 에러 member_id: {member_id} - {e}")

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
            # 각 유저마다 개별 세션 생성
            db: Session = next(get_db())
            try:
                # 식습관 분석 실행
                full_analysis(db, member_id)
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