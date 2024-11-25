#!/bin/bash
set -e  # 에러 발생 시 스크립트 중단

# Elasticsearch 데이터 적재 스크립트 실행
echo "Starting init/load_food_espy"
python init/load_food_es.py

# DB 연결 상태 확인
echo "Checking DB connection"
python init/check_db_connection.py

# FastAPI 서버 실행
echo "Starting FastAPI server"
python main.py 