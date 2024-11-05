import os
import sys
import pytest
from fastapi.testclient import TestClient

# Root directory를 Project Root로 설정: server directory 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)
os.chdir(project_root)

from main import app
from core.config import settings

client = TestClient(app)

# header를 사용하여 테스트 클라이언트를 설정하는 fixture
@pytest.fixture
def auth_headers():
    return {
        "Authorization": f"Bearer {settings.TEST_TOKEN}"  
    }

# 식습관 분석 API 테스트
def test_diet_analysis(auth_headers):
    response = client.get("/v1/ai/diet_analysis/", headers=auth_headers)
    assert response.status_code == 200, f"응답 상태 코드가 200이 아닙니다: {response.status_code}"
    
    response_json = response.json()
    assert response_json.get("success") is True, "API 요청이 성공하지 않았습니다."
    assert "response" in response_json, "응답에 'response' 필드가 없습니다."
    assert "error" in response_json, "응답에 'error' 필드가 없습니다."
    
    response_data = response_json["response"]
    assert "avg_calorie" in response_data, "'avg_calorie' 필드가 응답에 없습니다."
    assert "weight_prediction" in response_data, "'weight_prediction' 필드가 응답에 없습니다."
    assert "advice_carbo" in response_data, "'advice_carbo' 필드가 응답에 없습니다."
    assert "advice_protein" in response_data, "'advice_protein' 필드가 응답에 없습니다."
    assert "advice_fat" in response_data, "'advice_fat' 필드가 응답에 없습니다."
    assert "synthesis_advice" in response_data, "'synthesis_advice' 필드가 응답에 없습니다."

# 식습관 분석 알림 API 테스트
def test_status_alert(auth_headers):
    response = client.get("/v1/ai/diet_analysis/status", headers=auth_headers)
    assert response.status_code == 200, f"응답 상태 코드가 200이 아닙니다: {response.status_code}"
    
    response_json = response.json()
    assert response_json.get("success") is True, "API 요청이 성공하지 않았습니다."
    assert "response" in response_json, "응답에 'response' 필드가 없습니다."
    assert "error" in response_json, "응답에 'error' 필드가 없습니다."
    
    response_data = response_json["response"]
    assert "status" in response_data, "'status' 필드가 응답에 없습니다."
    assert "analysis_date" in response_data, "'analysis_date' 필드가 응답에 없습니다."
