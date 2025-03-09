# Event-Trigger
def format_food_table(data):
    # 상위 5개
    paginated_data = data[:5]

    list_text = "*수집된 데이터 리스트(상위 5개 표시)*\n"
    
    for idx, item in enumerate(paginated_data, start=1):
        list_text += f"{idx}. {item['foodNm']} (CATEGORY: {item['foodLv3Cd']})\n"

    buttons = [
        {
            "name": "load_data",
            "text": "Load",
            "type": "button",
            "style": "primary",
            "value": "load"
        }
    ]

    return list_text, buttons


# API-Gateway
def format_food_result_table(data):
    # 상위 5개
    paginated_data = data[:5]

    list_text = "*데이터베이스 적재 결과(상위 5개 표시)*\n"
    
    for idx, item in enumerate(paginated_data, start=1):
        list_text += f"{idx}. {item['FOOD_NAME']} (FOOD_PK: {item['FOOD_PK']})\n"

    return list_text