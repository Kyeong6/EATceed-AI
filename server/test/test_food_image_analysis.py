import os
import sys
import requests
import pytest
import redis

# Root directory를 Project Root로 설정: server directory 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)
os.chdir(project_root)

from core.config import settings


# Redis 클라이언트 설정
redis_client = redis.StrictRedis(
    host=settings.REDIS_LOCAL_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

def reset_rate_limit(user_id: int):
    """
    Redis에서 주어진 user_id의 rate limit 카운트를 초기화하는 함수.
    """
    redis_key = f"rate_limit:{user_id}"
    redis_client.delete(redis_key)


def analyze_food_image(base64_data):
    """
    로컬 FastAPI 서버로 이미지 분석 요청을 보내는 함수.
    
    Args:
        base64_data (str): Base64로 인코딩된 이미지 데이터
    
    Returns:
        dict: API의 응답 JSON 데이터
    """
    # 서버 주소 설정
    url = "http://localhost:8000/v1/ai/food_image_analysis/"

    # 테스트 진행을 위한 JWT 토큰 설정 
    headers = {
        "Authorization": f"Bearer {settings.TEST_TOKEN}"  
    }

    # txt 파일에 존재하는 base64 인코딩 사용
    payload = {
        "image_base64": base64_data
    }

    # 요청에 대한 응답값
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 400:
        raise ValueError("하루 요청 제한을 초과했습니다.")
    else:
        raise Exception(f"Failed with status code: {response.status_code}, Error: {response.text}")


"""
Base64 인코딩된 이미지 데이터 불러오는 fixture
명령어 : pytest test_food_image_analysis.py
"""
@pytest.fixture
def load_base64_data():
    # 테스트 진행을 위한 base64 인코딩이 존재하는 파일 설정
    with open("./test/image/파스타_768_1364.txt", "r") as file:
        return file.read().strip()

@pytest.fixture(autouse=True)
def reset_rate_limit_before_tests():
    """
    각 테스트 실행 전에 Redis에 저장된 Rate Limit 카운트를 초기화합니다.
    """
    # 테스트할 user_id 값으로 설정: test 진행 시에는 수동
    reset_rate_limit(user_id=4)  


def test_food_image_analysis(load_base64_data):
    """
    API 데이터 반환 형식 검증
    """
    response = analyze_food_image(load_base64_data)
    
    # 응답 데이터가 지정한 구조로 구성되어 있는지 확인
    assert "success" in response, "응답에 'success' 필드가 없습니다."
    assert response["success"] is True, "요청이 실패했습니다."
    assert "response" in response, "응답에 'response' 필드가 없습니다."
    assert "error" in response, "응답에 'error' 필드가 없습니다."
    
    # response가 지정한 구조로 구성되어 있는지 확인
    response_data = response["response"]
    assert "remaining_requests" in response_data, "'remaining_requests' 필드가 없습니다."
    assert isinstance(response_data["remaining_requests"], int), "'remaining_requests'는 정수형이어야 합니다."
    assert "food_info" in response_data, "'food_info' 필드가 없습니다."
    assert isinstance(response_data["food_info"], list), "'food_info' 필드는 리스트 형식이어야 합니다."

    # food_info 내 각 음식 데이터 검증
    for food_data in response_data["food_info"]:
        assert "detected_food" in food_data, "'detected_food' 필드가 응답에 없습니다."
        assert "similar_foods" in food_data, "'similar_foods' 필드가 응답에 없습니다."
        assert isinstance(food_data["similar_foods"], list), "'similar_foods' 필드는 리스트 형식이 아닙니다."
        
        # similar_foods 내 각 유사 음식 검증
        for similar_food in food_data["similar_foods"]:
            if similar_food.get("food_name") is None and similar_food.get("food_pk") is None:
                print("유사한 음식이 없는 경우를 확인했습니다.")
            else:
                assert "food_name" in similar_food, "유사 음식에 'food_name' 필드가 없습니다."
                assert "food_pk" in similar_food, "유사 음식에 'food_pk' 필드가 없습니다."


def test_rate_limit_exceeded(load_base64_data):
    """
    Rate limit 초과 시도 및 예외 발생 여부 검증
    """
    rate_limit = settings.RATE_LIMIT

    # Rate limit을 초과하는 요청을 시도
    for _ in range(rate_limit):
        response = analyze_food_image(load_base64_data)
        assert response["success"], "Rate limit 내의 요청이 실패했습니다."
        assert "remaining_requests" in response["response"], "'remaining_requests' 필드가 없습니다."
        remaining_requests = response["response"]["remaining_requests"]
        print(f"남은 요청 횟수: {remaining_requests}")
        assert remaining_requests >= 0, "'remaining_requests'가 0 이상이어야 합니다."

    # Rate limit을 초과한 후 요청이 차단되는지 확인
    with pytest.raises(ValueError) as excinfo:
        analyze_food_image(load_base64_data)
    assert "하루 요청 제한을 초과했습니다." in str(excinfo.value), "Rate limit 초과 예외가 발생하지 않았습니다."