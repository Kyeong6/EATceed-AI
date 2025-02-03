from errors.server_exception import FileAccessError
from logs.logger_config import get_logger

# 공용 로거 
logger = get_logger()

# prompt를 불러오기
def read_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        prompt = file.read().strip()

    if not prompt:
        logger.error("prompt 파일을 불러오기에 실패했습니다.")
        raise FileAccessError()
    
    return prompt