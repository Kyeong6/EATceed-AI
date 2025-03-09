import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from core.config import settings
from pipeline.extract import extract_data, request_data
from pipeline.transform import transform_data
from alert.google_sheets import insert_sheet_data
from logs.get_logger import get_logger
from utils.form import format_food_table

logger = get_logger()

# Slack 클라이언트 설정
slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)

def lambda_handler(event, context):
    
    logger.info("데이터 파이프라인 실행")

    # 1. 데이터 추출
    raw_data = request_data()

    if not raw_data:
        logger.info("OpenAPI 데이터 미존재: 파이프라인 종료")
        return {"statusCode": 204, "body": json.dumps("OPENAPI 데이터 없음, 종료")}
    
    extracted_data = extract_data(raw_data)

    # 2. 데이터 변환
    transformed_data = transform_data(extracted_data)

    if not transformed_data:
        logger.info("변환된 데이터 미존재: 파이프라인 종료")
        return {"statusCode": 204, "body": json.dumps("변환된 데이터 없음, 종료")}
    
    # 3. 구글 시트 적재
    data_count = insert_sheet_data(transformed_data)

    # 4. Slack 메시지 전송
    try:
        list_text, buttons = format_food_table(transformed_data[:5])

        slack_client.chat_postMessage(
            channel=settings.CHANNEL_ID,
            text=f"Google Sheet에 {data_count}개의 데이터가 적재 완료되었습니다.\n\n{list_text}",
            attachments=[
                {
                    "fallback": "Actions",
                    "color": "#2eb886",
                    "callback_id": "data_validation",
                    "actions": buttons
                }
            ]
        )
        logger.info(f"Slack 메시지 전송 완료")

    except SlackApiError as e:
        logger.error(f"Slack 메시지 전송 실패: {e.response['error']}")
        return {"statusCode": 500, "body": json.dumps(f"Slack 메시지 전송 실패: {e.response['error']}")}
    
    return {"statusCode": 200, "body": json.dumps("Event Trigger 실행 완료")}