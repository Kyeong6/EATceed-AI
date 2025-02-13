from openai import OpenAI
from core.config import settings

# Upstage 클라이언트
upstage = OpenAI(
    api_key=settings.UPSTAGE_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

# 운영 환경 사용
# 제공받은 음식의 벡터 임베딩 값 변환 작업 수행(Upstage-Embedding 사용)
def get_embedding(text, model="embedding-query"):
      
      text = text.replace("\n", " ")
      response = upstage.embeddings.create(input=[text], model=model)
      return response.data[0].embedding
    