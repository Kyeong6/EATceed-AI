import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from core.config import settings
from alert.google_sheets import read_unchecked_data, update_processed_status
from database.session import get_db
from pipeline.load import insert_food_data, insert_food_data_embedding
from logs.get_logger import get_logger
from utils.form import format_food_result_table

logger = get_logger()

# Slack 클라이언트 설정
slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)

def lambda_handler(event, context):

    try:
        body = json.loads(event["body"])
        # Slack에서 보낸 데이터 파싱
        payload = json.loads(body["payload"])
        action = payload["actions"][0]
        action_value = action["value"]
        channel_id = payload["channel"]["id"]

        # Load 버튼 클릭 시 Google Sheets에서 적재되지 않은 데이터 가져오기
        if action_value == "load":
            data = read_unchecked_data()

            # 적재 상태 "1"만 존재 (이미 모든 데이터 적재됨)
            if not data:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    text=f"이미 모든 데이터가 데이터베이스에 적재 완료되었습니다."
                )
                return {"statusCode": 200, "body": json.dumps("모든 데이터 적재 완료")}

            # 데이터베이스 연결
            db = next(get_db())

            # 데이터베이스 적재
            new_food_pks = []
            try:
                for record in data:
                    food_pk = insert_food_data(db, record)
                    new_food_pks.append({"FOOD_NAME": record["식품명"], "FOOD_PK": food_pk})
                logger.info(f"데이터베이스 적재 완료")
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"데이터베이스 적재 중 오류 발생: {str(e)}")
                return {"statusCode": 500, "body": json.dumps("데이터베이스 적재 실패")}
            finally:
                db.close()

            # Pinecone에 새로운 데이터 적재
            insert_food_data_embedding([f["FOOD_PK"] for f in new_food_pks], settings.INDEX_NAME)

            # Google Sheets에서 "적재 상태"를 1로 업데이트
            update_processed_status()

            list_text = format_food_result_table(new_food_pks[:5])

            slack_client.chat_postMessage(
                channel=channel_id,
                text=f"Google Sheet에서 {len(new_food_pks)}건의 데이터가 성공적으로 FOOD_TB에 적재되었습니다.\n\n{list_text}"
            )

        logger.info("데이터 파이프라인 완료")
        return {"statusCode": 200, "body": json.dumps("데이터 파이프라인 완료")}
    
    except SlackApiError as e:
        logger.error(f"Slack Action 실패: {e.response['error']}")
        return {"statusCode": 500, "body": json.dumps(f"Slack Action 실패: {e.response['error']}")}
    
    except Exception as e:
        logger.error(f"API-Gateway 실행 오류: {str(e)}")
        return {"statusCode": 500, "body": json.dumps("API-Gateway 실행 오류")}