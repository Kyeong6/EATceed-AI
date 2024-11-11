import os
import sys
import pytest
import redis
from fastapi.testclient import TestClient

# Root directory를 Project Root로 설정: server directory 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)
os.chdir(project_root)

from main import app  

# 환경에 따른 설정 파일 로드
if os.getenv("APP_ENV") == "prod":
    from core.config_prod import settings
else:
    from core.config import settings

# 클라이언트 설정
client = TestClient(app) 

# Redis 클라이언트 설정
redis_client = redis.StrictRedis(
    host=settings.REDIS_LOCAL_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

def reset_rate_limit(user_id: int):
    redis_key = f"rate_limit:{user_id}"
    redis_client.delete(redis_key)

def analyze_food_image(base64_data):
    headers = {
        "Authorization": f"Bearer {settings.TEST_TOKEN}"
    }
    
    response = client.post("/v1/ai/food_image_analysis/", headers=headers, json={"food_image": base64_data})
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 400 or response.status_code == 429:  # 429 상태 코드 추가
        raise ValueError("하루 요청 제한을 초과했습니다.")
    else:
        raise Exception(f"Failed with status code: {response.status_code}, Error: {response.text}")

@pytest.fixture
def load_base64_data():
    with open("./test/image/파스타_768_1364.txt", "r") as file:
        return file.read().strip()

@pytest.fixture(autouse=True)
def reset_rate_limit_before_tests():
    reset_rate_limit(user_id=4)  

def test_food_image_analysis(load_base64_data):
    response = analyze_food_image(load_base64_data)
    
    assert "success" in response, "응답에 'success' 필드가 없습니다."
    assert response["success"] is True, "요청이 실패했습니다."
    assert "response" in response, "응답에 'response' 필드가 없습니다."
    assert "error" in response, "응답에 'error' 필드가 없습니다."
    
    response_data = response["response"]
    assert "remaining_requests" in response_data, "'remaining_requests' 필드가 없습니다."
    assert isinstance(response_data["remaining_requests"], int), "'remaining_requests'는 정수형이어야 합니다."
    assert "food_info" in response_data, "'food_info' 필드가 없습니다."
    assert isinstance(response_data["food_info"], list), "'food_info' 필드는 리스트 형식이어야 합니다."

    for food_data in response_data["food_info"]:
        assert "detected_food" in food_data, "'detected_food' 필드가 응답에 없습니다."
        assert "similar_foods" in food_data, "'similar_foods' 필드가 응답에 없습니다."
        assert isinstance(food_data["similar_foods"], list), "'similar_foods' 필드는 리스트 형식이 아닙니다."
        
        for similar_food in food_data["similar_foods"]:
            if similar_food.get("food_name") is None and similar_food.get("food_pk") is None:
                print("유사한 음식이 없는 경우를 확인했습니다.")
            else:
                assert "food_name" in similar_food, "유사 음식에 'food_name' 필드가 없습니다."
                assert "food_pk" in similar_food, "유사 음식에 'food_pk' 필드가 없습니다."

def test_rate_limit_exceeded(load_base64_data):
    rate_limit = settings.RATE_LIMIT

    for _ in range(rate_limit):
        response = analyze_food_image(load_base64_data)
        assert response["success"], "Rate limit 내의 요청이 실패했습니다."
        remaining_requests = response["response"]["remaining_requests"]
        assert remaining_requests >= 0, "'remaining_requests'가 0 이상이어야 합니다."

    with pytest.raises(ValueError) as excinfo:
        analyze_food_image(load_base64_data)
    assert "하루 요청 제한을 초과했습니다." in str(excinfo.value), "Rate limit 초과 예외가 발생하지 않았습니다."
