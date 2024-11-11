# python image
FROM python:3.9-slim

# 환경 변수 
ENV PYTHONUNBUFFERED 1
ENV APP_ENV=prod

# 작업 디렉토리 
WORKDIR /app

# 종속성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 및 실행 순서 파일(entrypoint.sh)
COPY . .
COPY entrypoint.sh /app/entrypoint.sh

# 실행 권한 부여
RUN chmod +x /app/entrypoint.sh

# 포트 
EXPOSE 8000

# PYTHON 경로 설정
ENV PYTHONPATH="${PYTHONPATH}:/app"

# 실행 명령어 수행
ENTRYPOINT ["/app/entrypoint.sh"]
