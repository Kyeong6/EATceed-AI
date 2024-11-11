#!/bin/bash
set -e  # 에러 발생 시 스크립트 중단

# Elasticsearch 데이터 적재 스크립트 실행
echo "Starting init/load_food_espy"
python init/load_food_es.py

# FastAPI 서버 실행 (백그라운드 실행)
echo "Starting FastAPI server"
python main.py &  # &를 사용하여 백그라운드 실행

# 백그라운드 프로세스가 종료되지 않도록 대기
wait -n