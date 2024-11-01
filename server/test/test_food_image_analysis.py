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
        
        # 응답 데이터가 지정한 구조로 구성되어 있는지 확인
        assert "success" in response, "응답에 'success' 필드가 없습니다."
        assert response["success"] is True, "요청이 실패했습니다."
        assert "response" in response, "응답에 'response' 필드가 없습니다."
        assert "error" in response, "응답에 'error' 필드가 없습니다."
        
        # response 내 similar_food_results의 구조 검증
        for food_data in response["response"]:
            assert "detected_food" in food_data, "'detected_food' 필드가 응답에 없습니다."
            assert "similar_foods" in food_data, "'similar_foods' 필드가 응답에 없습니다."
            assert isinstance(food_data["similar_foods"], list), "'similar_foods' 필드가 리스트 형식이 아닙니다."

            for similar_food in food_data["similar_foods"]:
                # 유사도 검색 실패 시 null 값 설정 검증
                if similar_food.get("food_name") is None and similar_food.get("food_pk") is None:
                    print("유사한 음식이 없는 경우를 확인했습니다.")
                else:
                    assert "food_name" in similar_food, "유사 음식에 'food_name' 필드가 없습니다."
                    assert "food_pk" in similar_food, "유사 음식에 'food_pk' 필드가 없습니다."

        print("Test Response Data:", response)  # 최종 응답 디버그 출력

    except Exception as e:
        print("Response Error:", e)  # 디버그 출력
        pytest.fail(str(e))
