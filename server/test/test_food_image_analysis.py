import os
import sys
import requests
import pytest

# Root directory를 Project Root로 설정: server directory 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)
os.chdir(project_root)

from core.config import settings

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
        result = response.json()
        print("Analyze result:", result)  # 디버그 출력
        return result
    else:
        raise Exception(f"Failed with status code: {response.status_code}, Error: {response.text}")


"""
Base64 인코딩된 이미지 데이터 불러오는 fixture
명령어 : pytest test_food_image_analysis.py
"""
@pytest.fixture
def load_base64_data():
    # 테스트 진행을 위한 base64 인코딩이 존재하는 파일 설정
    with open("./test/image/식판_768_1364.txt", "r") as file:
        return file.read().strip()

def test_food_image_analysis(load_base64_data):
    try:
        response = analyze_food_image(load_base64_data)
        
        # 응답 데이터 형식 확인
        print("Test Response Data:", response)  # 디버그 출력
        
        assert "response" in response, "응답에 'response' 필드가 없습니다."
        assert response["success"] is True, "요청이 실패했습니다."

        # 응답 데이터 검증
        for food in response["response"]:
            assert "detected_food" in food, "'detected_food' 필드가 응답에 없습니다."
            assert "similar_foods" in food, "'similar_foods' 필드가 응답에 없습니다."
            assert len(food["similar_foods"]) > 0, "유사한 음식 결과가 없습니다."
            
            for similar_food in food["similar_foods"]:
                assert "food_name" in similar_food, "유사 음식에 'food_name' 필드가 없습니다."
                assert "food_pk" in similar_food, "유사 음식에 'food_pk' 필드가 없습니다."

    except Exception as e:
        print("Response Error:", e)  # 디버그 출력
        pytest.fail(str(e))
