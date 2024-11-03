# 메인 로직 작성
import os
import logging
import pandas as pd
import redis
from datetime import datetime, timedelta
from core.config import settings
from sqlalchemy.orm import Session
from db.database import get_db
from db.crud import create_eat_habits, get_user_data, update_flag, get_all_member_id
from apscheduler.schedulers.background import BackgroundScheduler
from errors.custom_exceptions import UserDataError, AnalysisError
from openai import OpenAI
from elasticsearch import Elasticsearch
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI

# 로그 메시지
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# 환경변수 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATA_PATH = os.getenv("DATA_PATH")
PROMPT_PATH = os.getenv("PROMPT_PATH")

# Elasticsearch 클라이언트 설정
es = Elasticsearch(
    settings.ELASTICSEARCH_LOCAL_HOST, 
    http_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD))


# Redis 클라이언트 설정
redis_client = redis.StrictRedis(
    host=settings.REDIS_LOCAL_HOST,  
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

# 요청 제한 설정
RATE_LIMIT = settings.RATE_LIMIT  # 하루 최대 요청 가능 횟수

# Chatgpt API 사용
client = OpenAI(api_key = OPENAI_API_KEY)

# prompt를 불러오기
def read_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        prompt = file.read().strip()
    return prompt

# 식습관 분석 진행을 위한 OpenAI API 연결
def get_completion(prompt, model="gpt-4o-mini"):
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0
    )
    # logger.debug(f"Prompt sent to OpenAI: {prompt}")
    # logger.debug(f"Response from OpenAI: {response.choices[0].message.content}")
    return response.choices[0].message.content


# 체중 예측 함수
def weight_predict(user_data: dict) -> str:
    try:
        logger.debug(f"user_data in weight_predict: {user_data}")
        energy = user_data['user'][5]["calorie"]
        tdee = user_data['user'][13]["tdee"]
        if energy > tdee:
            return '증가'
        else:
            return '감소'
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error in weight_predict function: {e}")
        raise UserDataError("유저 데이터 에러입니다")

# 식습관 조언 함수 (조언 프롬프트)
def analyze_advice(prompt_type, user_data):
    try:
        prompt_file = os.path.join(PROMPT_PATH, f"{prompt_type}.txt")
        prompt = read_prompt(prompt_file)
        
        # 프롬프트 변수 설정
        carbohydrate = user_data['user'][8]['carbohydrate)']
        protein = user_data['user'][6]['protein']
        fat = user_data['user'][7]['fat']
        sodium = user_data['user'][11]['sodium']
        dietary_fiber = user_data['user'][9]['dietary_fiber']
        sugar = user_data['user'][10]['sugars']
        
        prompt = prompt.format(carbohydrate=carbohydrate, protein=protein, fat=fat, 
                               sodium=sodium, dietary_fiber=dietary_fiber, sugars=sugar)

        # logger.debug(f"Generated prompt: {prompt}")
        # 식습관 분석 결과값 구성
        completion = get_completion(prompt)
        return completion
    except Exception as e:
        logger.error(f"Error in analyze_diet function: {e}")
        raise AnalysisError("식습관 분석을 실행할 수 없습니다")

# 식습관 분석 함수 (판단 프롬프트)
def analyze_diet(prompt_type, user_data):
    try:
        prompt_file = os.path.join(PROMPT_PATH, f"{prompt_type}.txt")
        prompt = read_prompt(prompt_file)
        df = pd.read_csv(os.path.join(DATA_PATH, "diet.csv"))
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
        ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY),
        df=df,
        verbose=True,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        allow_dangerous_code=True
        )
        
        completion = agent.invoke(prompt)
        return completion
        
    except Exception as e:
        logger.error(f"Error in analyze_diet function: {e}")
        raise AnalysisError("식습관 분석을 실행할 수 없습니다")

# 최종 식습관 분석 기능 함수
def full_analysis(db: Session, member_id: int):
    try:
        user_data = get_user_data(db, member_id)

        # 체중 예측
        weight_result = weight_predict(user_data)
        user_data['weight_change'] = weight_result
        avg_calorie = user_data['user'][5]["에너지(kcal)"]

        # 각 프롬프트에 대해 분석 수행
        prompt_types = ['health_advice', 'weight_carbo', 'weight_fat', 'weight_protein']
        analysis_results = {}
        for prompt_type in prompt_types:
            if prompt_type == 'health_advice': # 조언 프롬프트는 analyze_advice 함수
                result = analyze_advice(prompt_type, user_data)
                analysis_results[prompt_type] = result
            else: # 판단 프롬프트는 analyze_diet 함수
                result = analyze_diet(prompt_type, user_data)
                analysis_results[prompt_type] = result['output']

        # DB에 결과값 저장
        create_eat_habits(
            db=db,
            member_id=member_id,
            weight_prediction=weight_result,
            advice_carbo=analysis_results['weight_carbo'],
            advice_protein=analysis_results['weight_protein'],
            advice_fat=analysis_results['weight_fat'],
            synthesis_advice=analysis_results['health_advice'],
            flag=True,
            avg_calorie=avg_calorie
        )

        logger.info(f"Insert success ")

    except ValueError as e:
        logger.error(f"Value error during analysis: {e}")
        raise UserDataError("유저 데이터 에러입니다")
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        raise AnalysisError("식습관 분석을 실행할 수 없습니다")


# scheduling 
def scheduled_task():
    db: Session = next(get_db())
    try:
        # 모든 기존 레코드의 FLAG를 0으로 업데이트
        update_flag(db)

        # 모든 유저 분석 작업 수행
        member_ids = get_all_member_id(db)
        for member_id in member_ids:
            full_analysis(db=db, member_id=member_id)

    except Exception as e:
        logger.error(f"Error during scheduled task: {e}")
    finally:
        db.close()

# APScheduler 설정
scheduler = BackgroundScheduler()

# test를 위한 시간 설정
# scheduler.add_job(scheduled_task, 'interval', minutes=5)

# 실제 기능 수행 시간 설정
scheduler.add_job(scheduled_task, 'cron', day_of_week='mon', hour=0, minute=0)
scheduler.start()


# 음식 이미지 분석 API: prompt_type은 함수명과 동일
def food_image_analyze(image_base64: str):

    try:
        # prompt 타입 설정
        prompt_file = os.path.join(PROMPT_PATH, "food_image_analyze.txt")
        prompt = read_prompt(prompt_file)

        # OpenAI API 호출
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                                # 검증 필요
                                # "detail": "high"
                            }
                        }
                    ]
                }
            ],
            temperature=0.0,
            max_tokens=300
        )
        
        result = response.choices[0].message.content

        return result
    except Exception as e:
        raise AnalysisError("OpenAI API 호출 중 오류 발생")


# 제공받은 음식의 벡터 임베딩 값 변환 작업 수행
def get_embedding(text, model="text-embedding-3-small"):
    text = text.replace("\n", " ")
    embedding = client.embeddings.create(input=[text], model=model).data[0].embedding
    return embedding


# 벡터 임베딩을 통한 유사도 분석 진행
def search_similar_food(query_name):
    try:
        index_name = "food_names"

        # OpenAI API를 사용하여 임베딩 생성
        query_vector = get_embedding(query_name)

        # Elasticsearch 벡터 유사도 검색
        response = es.search(
            index=index_name,
            body={
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            # 코사인 유사도 진행
                            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                            "params": {"query_vector": query_vector}
                        }
                    }
                },
                # 상위 3개의 유사한 결과 반환
                "size": 3  
            }
        )

        # 검색 결과: food_name, food_pk 추출
        hits = response.get('hits', {}).get('hits', [])
        
        # 검색 결과가 있을 경우 food_name과 food_pk 추출, 없을 경우 null로 설정: AOS와 논의 필요
        result = [{"food_name": hit["_source"]["food_name"], "food_pk": hit["_source"]["food_pk"]} for hit in hits] if hits else [{"food_name": None, "food_pk": None}]

        # 결과 확인
        print("Search result:", result)
        
        # 최대 3개의 결과 반환 또는 null
        return result  

    except Exception as e:
        raise AnalysisError(f"유사도 분석 중 오류 발생: {str(e)}")
    

# Redis 기반 요청 제한 함수
def rate_limit_user(user_id: int):
    redis_key = f"rate_limit:{user_id}"
    current_count = redis_client.get(redis_key)

    if current_count:
        if int(current_count) >= RATE_LIMIT:
            raise UserDataError("하루 요청 제한을 초과했습니다.")
        else:
            redis_client.incr(redis_key)
            remaning_requests = RATE_LIMIT - int(current_count) - 1
    else:
        redis_client.set(redis_key, 1)
        # 매일 자정 횟수 리셋
        next_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        redis_client.expireat(redis_key, int(next_time.timestamp()))
        remaning_requests = RATE_LIMIT - 1

    return remaning_requests