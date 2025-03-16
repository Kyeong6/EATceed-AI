import os
import base64
import time
import asyncio
from openai import AsyncOpenAI
from openai import RateLimitError, APIError, APIConnectionError, APITimeoutError
from pinecone.grpc import PineconeGRPC as Pinecone
from core.config import settings
from utils.file_handler import read_prompt
from fallback.fallback_food_image import food_image_analyze_fallback
from errors.business_exception import ImageAnalysisError, ImageProcessingError
from errors.server_exception import FileAccessError, ExternalAPIError
from logs.logger_config import get_logger

# 공용 로거
logger = get_logger()

# OpenAI API 사용
client = AsyncOpenAI(api_key = settings.OPENAI_API_KEY)

# Upsage API 사용
upstage = AsyncOpenAI(
    api_key = settings.UPSTAGE_API_KEY,
    base_url="https://api.upstage.ai/v1/solar"
)

# Pinecone 설정
pc = Pinecone(api_key=settings.PINECONE_API_KEY)
index = pc.Index(host=settings.INDEX_HOST)

# Multi-part 방식 이미지 처리 및 Base64 인코딩
async def process_image_to_base64(file):
    try:
        # 파일 읽기
        file_content = await file.read()

        # Base64 인코딩
        image_base64 = base64.b64encode(file_content).decode("utf-8")
        
        return image_base64
    except Exception as e:
        logger.error(f"이미지 파일 처리 및 Base64 인코딩 실패: {e}")
        raise ImageProcessingError()

# 음식 이미지 분석 API: prompt_type은 함수명과 동일
async def food_image_analyze(image_base64: str):

    # prompt 타입 설정
    prompt_file = os.path.join(settings.PROMPT_PATH, "image_detection.txt")
    prompt = await read_prompt(prompt_file, category="image", ttl=3600)

    # prompt 내용 없을 경우
    if not prompt:
        logger.error("image_detection.txt에 prompt 내용 미존재")
        raise FileAccessError()

    # 지수 백오프 전략: 최대 3번 재시도
    max_retries = 2
    for attemp in range(max_retries):
        try:
            # OpenAI API 호출
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    # 성능이 좋아지지만, token 소모 큼(tradeoff): 검증 필요
                                    # "detail": "high"
                                }
                            }
                        ]
                    },
                    {"role": "system", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=300
            )
            
            result = response.choices[0].message.content
            
            # 응답 반환
            if result:
                return result

        except (RateLimitError, APIError, APIConnectionError, APITimeoutError) as e:
                logger.error(f"Food Image Analysis: OpenAI 오류 발생(시도 {attemp+1}/{max_retries}): {e}")

                # 마지막 재시도 실패 시 Fallback 수행
                if attemp == max_retries - 1:
                    logger.error(f"Food Image Analysis: OpenAI 3회 재시도 후 실패 Fallback 실행")
                    result = await food_image_analyze_fallback(image_base64, prompt)

                    return result

                await asyncio.sleep(attemp ** 2)

    # 음식명(반환값)이 존재하지 않을 경우
    logger.error("OpenAI API / Claude API 음식명 얻기 실패")
    raise ImageAnalysisError()


# 제공받은 음식의 벡터 임베딩 값 변환 작업 수행(Upstage-Embedding 사용)
async def get_embedding(text, model="embedding-query"):
    try:
        text = text.replace("\n", " ")
        response = await upstage.embeddings.create(input=[text], model=model)
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"텍스트 임베딩 변환 실패: {e}")
        raise ExternalAPIError()


# 벡터 임베딩을 통한 유사도 분석 진행(Pinecone)
async def search_similar_food(query_name, top_k=3, score_threshold=0.7, candidate_multiplier=2):
    try:
        # 음식명 Embedding Vector 변환
        query_vector = await get_embedding(query_name)

        # Pinecone에서 유사도 검색
        results = index.query(
            vector=query_vector,
            top_k=top_k * candidate_multiplier,
            include_metadata=True
        )

        # 결과 처리 (점수 필터링 적용)
        candidates = [
            {
                'food_pk': match['id'],
                'food_name': match['metadata']['food_name'],
                'score': match['score']
            }
            for match in results['matches'] if match['score'] >= score_threshold
        ]

        # 유사도 점수를 기준으로 내림차순 정렬
        sorted_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)

        # 상위 top_k개 선택
        final_results = sorted_candidates[:top_k]

        # null로 채워서 항상 top_k 크기로 반환
        while len(final_results) < top_k:
            final_results.append({'food_name': None, 'food_pk': None})

        return final_results

    except Exception as e:
        logger.error(f"유사도 검색 실패: {e}")
        raise ExternalAPIError()
