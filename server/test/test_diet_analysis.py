import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Root directory를 Project Root로 설정: server directory 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)
os.chdir(project_root)

from main import app
from core.config import settings

client = TestClient(app)

# 기본 테스트 인증 헤더 설정
auth_headers = {"Authorization": f"Bearer {settings.TEST_TOKEN}"}

# 가짜 데이터베이스 생성
fake_members = [
    {"MEMBER_PK": 3, "MEMBER_NAME": "User3", "MEMBER_ACTIVITY": "NORMAL_ACTIVE", "MEMBER_GENDER": 0, 
     "MEMBER_AGE": 30, "MEMBER_HEIGHT": 170, "MEMBER_WEIGHT": 70},
    {"MEMBER_PK": 4, "MEMBER_NAME": "User4", "MEMBER_ACTIVITY": "LIGHTLY_ACTIVE", "MEMBER_GENDER": 1, 
     "MEMBER_AGE": 25, "MEMBER_HEIGHT": 160, "MEMBER_WEIGHT": 55}
]

fake_analysis_status = [
    {"STATUS_PK": 1, "MEMBER_FK": 3, "IS_ANALYZED": False, "IS_PENDING": True, "ANALYSIS_DATE": "2024-11-10"},
    {"STATUS_PK": 2, "MEMBER_FK": 4, "IS_ANALYZED": False, "IS_PENDING": False, "ANALYSIS_DATE": "2024-11-03"}
]

fake_eat_habits = [
    {"ANALYSIS_STATUS_FK": 1, "WEIGHT_PREDICTION": "증가", "ADVICE_CARBO": "탄수화물 줄이기", 
     "ADVICE_PROTEIN": "단백질 늘리기", "ADVICE_FAT": "지방 줄이기", "SYNTHESIS_ADVICE": "균형 잡힌 식단 필요"},
]

# 가짜 함수 정의
def fake_get_latest_analysis_date(db, member_id):
    status = next((status for status in fake_analysis_status if status["MEMBER_FK"] == member_id and status["IS_ANALYZED"]), None)
    return status

def fake_is_analysis_in_progress_for_member(member_id, db):
    in_progress = any(status for status in fake_analysis_status if status["MEMBER_FK"] != member_id and status["IS_PENDING"])
    return in_progress

def fake_get_latest_eat_habits(db, analysis_status_id):
    return next((habit for habit in fake_eat_habits if habit["ANALYSIS_STATUS_FK"] == analysis_status_id), None)

def fake_calculate_avg_calorie(db, member_id):
    return 2000  # 임의의 평균 칼로리 값

# 테스트: 분석 진행 중 상태
def test_analysis_in_progress():
    with patch('db.crud.is_analysis_in_progress_for_member', new=fake_is_analysis_in_progress_for_member):
        response = client.get("/v1/ai/diet_analysis/?member_id=4")
        assert response.status_code == 409
        assert response.json() == {
            "success": False,
            "response": None,
            "error": {
                "code": "DIET_409_1",
                "reason": "해당 유저에 대한 분석 진행 대기 중입니다.",
                "http_status": 409
            }
        }

# 테스트: 분석 미완료 상태
def test_analysis_not_completed():
    with patch('db.crud.is_analysis_in_progress_for_member', new=fake_is_analysis_in_progress_for_member), \
         patch('db.crud.get_latest_analysis_date', new=fake_get_latest_analysis_date):
        response = client.get("/v1/ai/diet_analysis/?member_id=3", headers=auth_headers)
        assert response.status_code == 404
        assert response.json() == {
            "success": False,
            "response": None,
            "error": {
                "code": "DIET_404_2",
                "reason": "해당 유저에 대한 분석이 아직 완료되지 않았습니다.",
                "http_status": 404
            }
        }

# 테스트: 최근 분석 기록이 존재하는 경우
def test_recent_analysis_record():
    with patch('db.crud.get_latest_analysis_date', new=fake_get_latest_analysis_date), \
         patch('db.crud.get_latest_eat_habits', new=fake_get_latest_eat_habits), \
         patch('db.crud.calculate_avg_calorie', new=fake_calculate_avg_calorie):
        
        response = client.get("/v1/ai/diet_analysis/?member_id=5", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "response" in response.json()
        assert response.json()["response"]["analysis_date"] == "2023-12-01"  # 예상 날짜로 수정
        assert response.json()["response"]["avg_calorie"] == 2000

# 테스트: 분석 기록이 없는 경우
def test_no_analysis_record():
    with patch('db.crud.get_latest_analysis_date', new=fake_get_latest_analysis_date):
        response = client.get("/v1/ai/diet_analysis/?member_id=6", headers=auth_headers)
        assert response.status_code == 404
        assert response.json() == {
            "success": False,
            "response": None,
            "error": {
                "code": "DIET_404_3",
                "reason": "해당 유저에 대한 분석 기록이 존재하지 않습니다.",
                "http_status": 404
            }
        }

