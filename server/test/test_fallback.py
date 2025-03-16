import os
import sys
import time
import asyncio
import httpx
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from openai import RateLimitError


# Root directory를 Project Root로 설정: server directory 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)
os.chdir(project_root)

from main import app  

from core.config import settings
from core.config_redis import redis_client

# 클라이언트 설정
client = TestClient(app) 

def reset_rate_limit(user_id: int):
    redis_key = f"rate_limit:{user_id}"
    redis_client.delete(redis_key)

# Fallback 수행 테스트
async def analyze_food_image_with_fallback(image_path):
    headers = {"Authorization": f"Bearer {settings.TEST_TOKEN}"}

    with open(image_path, "rb") as img:
        files = {"file": (os.path.basename(image_path), img, "image/jpeg")}

        # OpenAI API 호출 강제 실패
        request = httpx.Request(method="POST", url="https://api.openai.com/v1/chat/completions")
        fake_response = httpx.Response(status_code=429, request=request)  

        with patch("apis.food_image.client.chat.completions.create", new=AsyncMock(
            side_effect=RateLimitError(
                message="Forced Rate Limit Error for testing fallback",
                response=fake_response,
                body=None
            )
        )):
            # 기존 API 호출 (Fallback 수행 확인)
            response = client.post("/ai/v1/food_image_analysis/image", headers=headers, files=files)

    return response


async def main():
    image_dir = os.path.join(settings.TEST_PATH, "test_image")
    image_files = sorted(
        [f for f in os.listdir(image_dir) if f.endswith((".jpeg", ".jpg"))],
        key=lambda x: int(os.path.splitext(x)[0])
    )

    # 테스트 전에 Rate Limit 초기화
    reset_rate_limit(user_id=26)

    # 테스트 실행
    print("\n========== 음식 이미지 분석 API Fallback 테스트 ==========")
    
    for idx, image_file in enumerate(image_files, start=1):
        image_path = os.path.join(image_dir, image_file)
        print(f"\n[{idx}] 테스트 이미지: {image_file}")

        start_total = time.time()
        try:
            response = await analyze_food_image_with_fallback(image_path)
            end_total = time.time()
            total_time = round(end_total - start_total, 4)

            # 응답 확인
            print(f"응답 (총 처리 시간: {total_time}초):")
            print(response.json())

        except Exception as e:
            print(f"에러 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())