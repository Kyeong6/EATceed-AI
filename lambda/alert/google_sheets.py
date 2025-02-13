import json
import gspread
from core.config import settings
from logs.get_logger import get_logger

logger = get_logger()

# Sheet 연결
gc = gspread.service_account(filename=settings.API_FILE)
sh = gc.open("food_dataset")

# Google Sheet 데이터 적재: 초기 적재상태(0)
def insert_sheet_data(data):
    try:
        # 첫번째 시트 사용
        worksheet = sh.sheet1

        # 리스트로 변환(각 데이터 한 줄씩 입력)
        rows = []
        for item in data:
            if isinstance(item, dict):
                row = [
                    str(item.get("foodCd", "")),
                    item.get("foodNm", ""),
                    str(item.get("foodLv3Cd", "")),
                    str(item.get("foodSize", "")),
                    str(item.get("enerc", "")),
                    str(item.get("chocdf", "")),
                    str(item.get("prot", "")),
                    str(item.get("fatce", "")),
                    str(item.get("sugar", "")),
                    str(item.get("fibtg", "")),
                    str(item.get("nat", "")),
                    # 초기 적재상태: 0
                    "0"  
                ]
                rows.append(row)
            else:
                logger.error(f"잘못된 데이터 형식 감지: {item}")
                return {"statusCode": 500, "body": json.dumps("Google Sheets 적재 실패")}

        # 데이터 적재
        worksheet.append_rows(rows, value_input_option="RAW")
        logger.info(f"Google Sheets {len(rows)}개의 데이터 추가")
        return len(rows)
    
    except Exception as e:
        logger.error(f"Google Sheets 데이터 적재 실패: {e}")
        return {"statusCode": 500, "body": json.dumps("Google Sheets 적재 실패")}

# Google Sheets 데이터 조회: 초기 적재상태
def read_unchecked_data():
    try:
        worksheet = sh.sheet1
        data = worksheet.get_all_values()
        headers = data[0]
        records = [dict(zip(headers, row)) for row in data[1:]]

        # "적재 상태"가 0인 데이터만 조회
        unprocessed_data = [
            {
                "식품코드": int(row["식품코드"]) if row["식품코드"].isdigit() else row["식품코드"],
                "식품명": row["식품명"],
                "식품대분류코드": int(row["식품대분류코드"]) if row["식품대분류코드"].isdigit() else row["식품대분류코드"],
                "식품중량": float(row["식품중량"]),
                "에너지(kcal)": float(row["에너지(kcal)"]),
                "탄수화물(g)": float(row["탄수화물(g)"]),
                "단백질(g)": float(row["단백질(g)"]),
                "지방(g)": float(row["지방(g)"]),
                "당류(g)": float(row["당류(g)"]),
                "식이섬유(g)": float(row["식이섬유(g)"]),
                "나트륨(mg)": float(row["나트륨(mg)"]),
                "적재상태": row["적재상태"]
            }
            for row in records if row.get("적재 상태", "0").strip() == "0"
        ]

        return unprocessed_data

    except Exception as e:
        logger.error(f"Google Sheets 데이터 읽기(초기 적재상태) 실패: {e}")
        return []
    
# Google Sheets 데이터 변경: 적재상태 "1"로 변경
def update_processed_status():
    try:
        worksheet = sh.sheet1
        data = worksheet.get_all_values()
        headers = data[0]

        # 적재 상태가 0인 데이터 1로 변경
        for i, row in enumerate(data[1:], start=2):
            if row[-1] == "0":
                worksheet.update_cell(i, len(headers), "1")
        logger.info("Google Sheets 적재 상태 업데이트 완료")

    except Exception as e:
        logger.error(f"Google Sheets 적재 상태 업데이트 실패: {e}")
