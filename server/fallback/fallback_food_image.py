import json
import anthropic
from core.config import settings
from logs.logger_config import get_logger
from errors.business_exception import ImageAnalysisError

# 로거 설정
logger = get_logger()

# Claude API 클라이언트 설정
claude_client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)

# OpenAI API 실패시 Claude API 이용
async def food_image_analyze_fallback(image_base64: str, prompt: str):
    try:
        response = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )
        result = response.content[0].text
        print(result)
        return result

    except Exception as e:
        logger.error(f"Food Image Analysis: Claude API 실패: {e}")
        raise ImageAnalysisError()