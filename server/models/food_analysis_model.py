from langchain_core.pydantic_v1 import BaseModel, Field

# 식습관 조언 구분
class DietAdvice(BaseModel):
    carbo_advice: str = Field(description="Advice for carbohydrate consumption.")
    protein_advice: str = Field(description="Advice for protein consumption.")
    fat_advice: str = Field(description="Advice for fat consumption.")

# 식습관 분석: 영양소 분석
class DietNurientAnalysis(BaseModel):
    nutrient_analysis: str = Field(description="Analysis for User's nutrient consumption improvement")

# 식습관 분석: 개선점
class DietImprovement(BaseModel):
    diet_improvement: str = Field(description="Improvements for user's eating habits")

# 식습관 분석: 맞춤형 식단 제공
class CustomRecommendation(BaseModel):
    custom_recommendation: str = Field(description="Offer personalized diets")

# 식습관 분석 요약
class DietSummary(BaseModel):
    diet_summary: str = Field(description="Eating habits analysis summary")
