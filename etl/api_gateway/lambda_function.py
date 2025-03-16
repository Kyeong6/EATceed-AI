import json
import urllib.parse
import requests
from slack_sdk import WebClient
from core.config import settings
from alert.google_sheets import read_unchecked_data, update_processed_status
from database.session import get_db
from pipeline.load import insert_food_data, insert_food_data_embedding
from utils.form import format_food_result_table

def lambda_handler(event, context):
    # Slack에서 온 이벤트 로깅
    print("Received event:", json.dumps(event, indent=2))

    # API Gateway의 body에서 payload 추출
    body_str = event.get("body", "{}")
    decoded_body = urllib.parse.parse_qs(body_str).get("payload", ["{}"])[0]
    payload = json.loads(decoded_body)

    # Slack에서 온 데이터 확인
    action = payload["actions"][0]
    action_value = action["value"]
    channel_id = payload["channel"]["id"]
    response_url = payload.get("response_url", "")

    # Slack에 즉시 응답 진행
    if response_url:
        requests.post(response_url, json={"text": "🚀 데이터 적재 시작"})

    # Load 버튼 클릭 시 Google Sheets에서 적재되지 않은 데이터 가져오기
    if action_value == "load":
        data = read_unchecked_data()

        # 적재할 데이터가 없으면 Slack에 메시지 전송 후 종료
        if not data:
            WebClient(token=settings.SLACK_BOT_TOKEN).chat_postMessage(
                channel=channel_id,
                text="❗️ 이미 모든 데이터가 데이터베이스에 적재 완료되었습니다."
            )
            return {"statusCode": 200, "body": json.dumps("모든 데이터 적재 완료")}

        # 데이터베이스 연결 및 적재
        db = next(get_db())
        new_food_pks = []
        try:
            for record in data:
                food_pk = insert_food_data(db, record)
                new_food_pks.append({"FOOD_NAME": record["식품명"], "FOOD_PK": food_pk})
            db.commit()
        except Exception as e:
            db.rollback()
            WebClient(token=settings.SLACK_BOT_TOKEN).chat_postMessage(
                channel=channel_id, text="❌ 데이터 적재 실패"
            )
            return {"statusCode": 500, "body": json.dumps("데이터베이스 적재 실패")}
        finally:
            db.close()

        # Pinecone에 데이터 적재
        insert_food_data_embedding([f["FOOD_PK"] for f in new_food_pks], settings.INDEX_NAME)

        # Google Sheets 업데이트
        update_processed_status()

        # Slack 메시지 전송
        WebClient(token=settings.SLACK_BOT_TOKEN).chat_postMessage(
            channel=channel_id,
            text=f"✅ Google Sheet에서 {len(new_food_pks)}건의 데이터가 성공적으로 적재되었습니다.\n\n{format_food_result_table(new_food_pks[:5])}"
        )

    return {"statusCode": 200, "body": json.dumps("데이터 파이프라인 완료")}