import os
import sys
import time
import redis
import pandas as pd
from fastapi.testclient import TestClient

# Root directory를 Project Root로 설정: server directory 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)
os.chdir(project_root)

from main import app  

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

# 테스트 진행을 위한 Rate limit 초기화
def reset_rate_limit(user_id: int):
    redis_key = f"rate_limit:{user_id}"
    redis_client.delete(redis_key)

# 테스트 진행을 위한 API 요청
def analyze_food_image(image_path):
    headers = {
        "Authorization": f"Bearer {settings.TEST_TOKEN}"
    }

    # 파일을 multipart 형식으로 업로드
    with open(image_path, "rb") as img:
        files = {"file": (image_path, img, "image/jpeg")}

        response = client.post("/ai/v1/food_image_analysis/image", headers=headers, files=files)

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 400 or response.status_code == 429:
        raise ValueError("하루 요청 제한을 초과했습니다.")
    else:
        raise Exception(f"Failed with status code: {response.status_code}, Error: {response.text}")

# 테스트할 이미지 목록
image_dir = os.path.join(settings.TEST_PATH, '/test_image/')
image_files = sorted(
    [f for f in os.listdir(image_dir) if f.endswith(('.jpeg', '.jpg'))],
    key=lambda x: int(os.path.splitext(x)[0])
)

# CSV 파일 경로
output_csv = os.path.join(settings.TEST_PATH, '/test_image/test_result.csv')

# 테스트 결과 저장할 리스트
test_results = []

# Rate limit 초기화
reset_rate_limit(user_id=1)

# 음식 이미지 처리 및 API 테스트
for idx, image_file in enumerate(image_files, start=1):
    image_path = os.path.join(image_dir, image_file)
    order = f"{idx}-1"
    read_food = "None"

    start_total = time.time()
    try:
        response = analyze_food_image(image_path)
        end_total = time.time()

        total_time = round(end_total - start_total, 4)
        analyze_time = response.get("food_image_analyze_time", 0)
        search_time = response.get("search_similar_time", 0)

        if response.get("success") and "response" in response:
            food_info = response["response"].get("food_info", [])

            for j, food_item in enumerate(food_info):
                # 감지된 음식 존재하지 않으면 N/A 설정
                detected = food_item.get("detected_food", "N/A")

                # None 값 제거 후 유사 음식 리스트 구성
                similar_foods_list = [
                    food["food_name"] for food in food_item.get("similar_foods", []) 
                    if food["food_name"] is not None
                ]

                # 유사한 음식 존재하지 않으면 N/A 설정
                similar_foods = ",".join(similar_foods_list) if similar_foods_list else "N/A"

                test_results.append([
                    f"{idx}-{j + 1}", # 1-1, 1-2 형식
                    read_food,
                    total_time,
                    analyze_time,
                    search_time,
                    detected,
                    similar_foods
                ])
        else:
            print(f"API returned unexpected response: {response}")
            test_results.append([f"{idx}-1", read_food, 0, 0, 0, "ERROR", ""])

    except Exception as e:
        print(f"Error processing {image_file}: {e}")
        test_results.append([f"{idx}-1", read_food, 0, 0, 0, "ERROR", str(e)])

# Dataframe 생성 및 저장
columns = ["ORDER", "READ_FOOD", "ANALYZE_FOOD_IMAGE(sec)", "FOOD_IMAGE_ANALYZE(sec)", "SEARCH_SIMILAR(sec)", "DETECTED", "SIMILAR"]
df = pd.DataFrame(test_results, columns=columns)

# 최종적으로 csv로 저장
df.to_csv(output_csv, index=False)
print(f"테스트 및 결과 저장 완료")