# 메인 로직 작성
import os
import logging
import pandas as pd
from openai import OpenAI
from datetime import datetime
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from core.config import settings
from db.database import get_db
from db.models import AnalysisStatus
from db.crud import (create_eat_habits, get_user_data, get_all_member_id, 
                     get_analysis_status, get_last_weekend_meals)
from errors.server_exception import FileAccessError, ExternalAPIError

# 로그 메시지
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

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
        logger("식습관 조언 기능 (외부 호출) 실패")
        raise ExternalAPIError()

    return completion

# 식습관 분석 함수 (판단 프롬프트)
def analyze_diet(prompt_type, user_data):

    prompt_file = os.path.join(settings.PROMPT_PATH, f"{prompt_type}.txt")
    prompt = read_prompt(prompt_file)
    df = pd.read_csv(os.path.join(settings.DATA_PATH, "diet.csv"))
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
        df = df[df['weight_change'] < 0] # 데이터에서 체중이 감소한 경우
    else:
        df = df[df['weight_change'] > 0] # 데이터에서 체중이 증가한 경우
    
    # langchain의 create_pandas_dataframe_agent 사용
    agent = create_pandas_dataframe_agent(
    ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=settings.OPENAI_API_KEY),
    df=df,
    verbose=True,
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
    # 유저 데이터 활용
    user_data = get_user_data(db, member_id)

    # 체중 예측
    weight_result = weight_predict(user_data)
    user_data['weight_change'] = weight_result

    analysis_status = get_analysis_status(db, member_id)

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
        analysis_status_id=analysis_status.STATUS_PK
    )

# 스케줄링 설정
def scheduled_task():
    db: Session = next(get_db())
    try:
        # ANALYSIS_STATUS_TB에 존재하는 모든 사용자 분석 대기 상태(IS_PENDING = True)로 설정
        db.query(AnalysisStatus).update({"IS_PENDING": True})
        db.commit()

        # 각 회원의 식습관 분석 수행
        # 현재는 for문을 통한 순차적으로 분석을 업데이트하지만, 추후에 비동기적 처리 필요
        member_ids = get_all_member_id(db)

        for member_id in member_ids:
            try:
                # 지난 일주일 동안 식사 등록 유무 확인
                meals = get_last_weekend_meals(db, member_id)
                if meals:
                    # 분석 실행
                    full_analysis(db, member_id)
                    # 분석 상태 업데이트: 완료
                    db.query(AnalysisStatus).filter(AnalysisStatus.MEMBER_FK == member_id).update({
                        "IS_ANALYZED": True,
                        "IS_PENDING": False,
                        "ANALYSIS_DATE": datetime.now()
                    })
                else:
                    # 식사기록이 없는 경우 분석 대기 상태 해제
                    db.query(AnalysisStatus).filter(AnalysisStatus.MEMBER_FK == member_id).update({
                        "IS_PENDING": False
                    })
            except Exception as e:
                logger.error(f"식습관 분석 실패 member_id: {member_id} - {e}")
    finally:
        db.close()

# APScheduler 설정
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_task, 'cron', day_of_week='mon', hour=0, minute=0)
scheduler.start()