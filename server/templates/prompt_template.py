import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from utils.file_handler import read_prompt
from core.config import settings
from logs.logger_config import get_logger

# 공용 로거 
logger = get_logger()

# Langchain 모델 설정: analysis / other
llm = ChatOpenAI(model='gpt-4o-mini', temperature=0, max_completion_tokens=250)
analysis_llm = ChatOpenAI(model='gpt-4o', temperature=0, max_completion_tokens=250)
vision_llm = ChatOpenAI(model='gpt-4o', temperature=0)

# Prompt 템플릿 정의
def create_prompt_template(file_path, input_variables):
    prompt_content = read_prompt(file_path)

    return PromptTemplate(template=prompt_content, input_variables=input_variables)

# Chain 정의: 식습관 조언
def create_advice_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "diet_advice.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "gender", "age", "height", "weight", "physical_activity_index",
            "carbohydrate", "protein", "fat", "carbo_avg", "protein_avg", "fat_avg"
        ]
    )
    return prompt_template | llm | JsonOutputParser()

# Chain 정의: 전체적인 영양소 분석
def create_nutrition_analysis_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "nutrition_analysis.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "gender", "age", "height", "weight",
            "physical_activity_index", "carbohydrate", "protein", "fat",
            "calorie", "sodium", "dietary_fiber", "sugars",
            "carbo_avg", "protein_avg", "fat_avg", "tdee"
        ]
    )
    return prompt_template | analysis_llm | StrOutputParser()

# Chain 정의: 개선점
def create_improvement_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "diet_improvement.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "carbohydrate", "carbo_avg", "protein", "protein_avg",
            "fat", "fat_avg", "calorie", "tdee", "nutrition_analysis", "target_weight"
        ]
    )
    return prompt_template | analysis_llm | StrOutputParser()

# Chain 정의: 맞춤형 식단 제공
def create_diet_recommendation_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "custom_recommendation.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "diet_improvement", "etc", "target_weight"
        ]
    )
    return prompt_template | analysis_llm | StrOutputParser()

# Chain 정의: 식습관 분석 요약
def create_summarize_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "diet_summary.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "nutrition_analysis", "diet_improvement", "custom_recommendation"
        ]
    )
    return prompt_template | llm | StrOutputParser()

# Chain 정의: 평가 체인
def create_evaluation_chain():
    prompt_path = os.path.join(settings.PROMPT_PATH, "diet_eval.txt")
    prompt_template = create_prompt_template(
        prompt_path,
        input_variables=[
            "gender", "age", "height", "weight",
            "physical_activity_index", "etc", "target_weight",
            "carbohydrate", "protein", "fat",
            "calorie", "sodium", "dietary_fiber", "sugars", "tdee",
            "nutrition_analysis", "diet_improvement", "custom_recommendation", "diet_summary"
        ]
    )
    return prompt_template | llm | JsonOutputParser()