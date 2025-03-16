import pandas as pd
import re

# 식품코드: "D" 및 "-" 제거
def normalize_food_code(foodCd):

    # 문자열이 아닐 경우 그대로 반환
    if not isinstance(foodCd, str):
        return foodCd  
    
    cleaned_code = re.sub(r"[D-]", "", foodCd)

    return int(cleaned_code) if cleaned_code.isdigit() else cleaned_code

# 식품중량: ml / g 단위 제거
def convert_food_size(foodSize):

    # 식품중량 없을 경우 0 반환
    if not isinstance(foodSize, str):
        return 0  
    
    size = re.sub(r"[^\d]", "", foodSize)  

    return int(size) if size.isdigit() else 0

# 영양성분: 수치형(float) 변환
def convert_nutrition_values(df):
    
    numeric_cols = [col for col in df.columns if col not in ["foodNm", "foodCd", "foodSize"]]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)  # 변환 불가능한 값은 0.0으로 처리

    return df

# 영양성분: 식품중량 기준으로 변환
def adjust_nutrition_values(df):

    # 영양성분 컬럼 목록 (foodNm, foodCd, foodSize 제외)
    nutrition_cols = [col for col in df.columns if col not in ["foodNm", "foodCd", "foodSize", "foodLv3Cd"]]

    # 식품 중량 0이면 변환 x: 0으로 나누는 것 방지
    df["foodSize"] = df["foodSize"].replace(0, 100)  # 기본값 100으로 설정

    # 영양성분 값 변환
    for col in nutrition_cols:
        df[col] = df[col] * (df["foodSize"] / 100)

    return df

# 데이터 변환 
def transform_data(data):
    df = pd.DataFrame(data)

    # 식품코드 정리
    df["foodCd"] = df["foodCd"].apply(normalize_food_code)

    # 식품중량 정리
    df["foodSize"] = df["foodSize"].apply(convert_food_size)

    # 영양성분 값 변환
    df = convert_nutrition_values(df)

    # 영양성분 값 식품중량 기준으로 변환
    df = adjust_nutrition_values(df)

    # 리스트로 변환
    data = df.to_dict(orient="records")
    
    return data