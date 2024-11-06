import os
import sys
import pandas as pd
from openai import OpenAI

# Root directory를 Project Root로 설정: server directory 
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(project_root)
os.chdir(project_root)

from core.config import settings


# Chatgpt API 사용
client = OpenAI(api_key = settings.OPENAI_API_KEY)

# 데이터셋 불러오기
df = pd.read_csv(os.path.join(settings.DATA_PATH, "food_before_embedding.csv"))

# 벡터 임베딩 수행
def get_embedding(text, model="text-embedding-3-small"):
   text = text.replace("\n", " ")
   response = client.embeddings.create(input = [text], model=model).data[0].embedding
   return response

df['EMBEDDING'] = df["FOOD_NAME"].apply(lambda x: get_embedding(x, model='text-embedding-3-small'))

df.to_csv(os.path.join(settings.DATA_PATH, "food.csv"), index=False)
print("임베딩 포함 파일 저장 완료")