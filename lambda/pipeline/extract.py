import requests
import urllib.parse 
from datetime import datetime
from core.config import settings
from logs.get_logger import get_logger

logger = get_logger()

request_params = [
    "foodCd", "foodNm", "foodLv3Cd", "foodSize", "enerc", 
    "chocdf", "prot", "fatce", "sugar", "fibtg", "nat"
]

# Extract 
def request_data():
    
    # 현재 날짜
    today = datetime.now().strftime("%Y-%m-%d")
    all_data = []
    page = 1
    num_of_rows = 10

    decoded_api_key = urllib.parse.unquote(settings.API_KEY)

    while True:
        params = {
            'serviceKey': decoded_api_key,
            'pageNo': str(page),
            'numOfRows': str(num_of_rows),
            'type': 'json',
            # 'foodCd': 'D304-179000000-0001'
            'crtYmd': today,
            'crtrYmd': today
        }
        response = requests.get(settings.API_URL, params=params)


        if response.status_code != 200:
            logger.error(f"API 요청 실패(HTTP {response.status_code})")
            return []
        
        data = response.json()
        items = data.get("response", {}).get("body", {}).get("items", [])

        if not items:
            return []
        
        all_data.extend(items)

        # 다음 페이지
        page += 1

        if len(items) < num_of_rows:
            break
        
    return all_data

# Null 처리
def clean_value(value):
    return value if value else "0"

# 데이터 추출
def extract_data(data):
    if not data:
        return []
    
    result = [{key: clean_value(item.get(key, "")) for key in request_params} for item in data]

    return result
