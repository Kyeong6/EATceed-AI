# EATceed

---

<img src="https://github.com/user-attachments/assets/276b3db0-582b-4b20-a347-8f76e9ac05d3" width="1000">

<br/>

## 서비스 소개
 
**EATceed**는 건강한 체중 증가를 원하는 사용자를 위한 **체중 증량 도우미 서비스**입니다.  

사용자가 섭취한 음식을 기반으로 **칼로리 및 영양 성분을 자동 계산**하고,  
**캘린더 시각화**를 통해 일일 권장 섭취 칼로리 달성률을 직관적으로 확인할 수 있습니다.

또한, **알림 기능**을 통해 사용자가 설정한 시간에 음식 섭취를 유도하고,
**AI 기반 식습관 분석**을 통해 맞춤형 조언을 제공함으로써 건강한 체중 증가를 지원합니다.

> 본 레포지토리는 EATceed 프로젝트 중 AI 기능(푸드렌즈, AI 영양사)을 개발·구현한 내용을 다룹니다.


### 화면 구성

<div align="center">
  <div style="display:inline-block; margin: 0 10px;">
    <strong>홈 화면</strong><br/>
    <img src="https://github.com/user-attachments/assets/875bbf63-9b86-4b0c-a77c-736a0f35a494" width="180" height="320"/>
  </div>
  <div style="display:inline-block; margin: 0 10px;">
    <strong>캘린더</strong><br/>
    <img src="https://github.com/user-attachments/assets/b2118fef-4fca-4abd-aa2e-89333202a1a1" width="180" height="320"/>
  </div>
  <div style="display:inline-block; margin: 0 10px;">
    <strong>식사 알림</strong><br/>
    <img src="https://github.com/user-attachments/assets/c39edb1c-8544-4a34-9048-19f9cfba93fe" width="180" height="320"/>
  </div>
</div>

<br/>

<div align="center">
  <div style="display:inline-block; margin: 0 10px;">
    <strong>푸드렌즈</strong><br/>
    <img src="https://github.com/user-attachments/assets/60e4e278-b3ad-435c-9a8d-fd8ee9d55725" width="180" height="320"/>
  </div>
  <div style="display:inline-block; margin: 0 10px;">
    <strong>AI 영양사</strong><br/>
    <img src="https://github.com/user-attachments/assets/b41ce362-2898-4b3e-90d1-25f6df07b89d" width="180" height="320"/>
  </div>
</div>


### AI 기능

**푸드렌즈 (Food Lens)**

<br/>

<p align="center">
  <img src="https://github.com/user-attachments/assets/d2852543-d8f1-4fca-b543-22a9ed4ab73b" width="700" alt="<Food Lens Flow>"/>
</p>

<br/>

- 사용자가 업로드한 음식 이미지를 GPT-4o를 통해 인식하고 음식명 자동 추출
- Pinecone을 활용해 유사 음식명을 검색하고 상위 3개의 후보 반환
- 데이터베이스에 등록된 영양 성분 정보를 기반으로 사용자는 추천 음식 중 선택만으로 간편하게 식단을 등록할 수 있음

**AI 영양사 (AI Nutritionist)**

<br/>

<p align="center">
  <img src="https://github.com/user-attachments/assets/c8bab371-92f3-4b9b-a69b-dba61b81bb9f" width="700" alt="<AI Nutritionist Flow>"/>
</p>

<br/>

- 사용자의 신체 정보, 활동량, 최근 일주일 식단 기록을 기반으로 LangChain의 RAG 및 멀티 체인 구조를 활용해 리포트 생성
- 리포트는 식습관 조언, 영양소 분석, 식사 개선점, 개인 맞춤 식단 추천으로 구성


## 기술 스택
### AI
<p>
  <img src="https://github.com/user-attachments/assets/8ee4ea88-e6bd-4495-8847-486bbc1ad34d" width="70" style="margin:10px;" title="LangChain"/>
  <img src="https://github.com/user-attachments/assets/57db6ed5-fea6-4453-b3cf-8af5b6f76609" width="70" style="margin:10px;" title="OpenAI"/>
  <img src="https://github.com/user-attachments/assets/86966805-7017-43a1-805c-281456bc8aaa" width="70" style="margin:10px;" title="Claude"/>
</p>

### Back-End
<p>
  <img src="https://github.com/user-attachments/assets/b71a06ec-cd90-492e-a395-138a05fd91d1" width="70" style="margin:10px;" title="FastAPI"/>
  <img src="https://github.com/user-attachments/assets/a650a979-1abd-4988-9b4b-3a852c63e35c" width="70" style="margin:10px;" title="MariaDB"/>
  <img src="https://github.com/user-attachments/assets/5ce5a579-c4cb-47b5-9c57-095a29b390e3" width="70" style="margin:10px;" title="Pinecone"/>
</p>

### Infra
<p>
  <img src="https://github.com/user-attachments/assets/75c80791-5b16-457c-a13b-294edd500554" width="70" style="margin:10px;" title="AWS EC2"/>
  <img src="https://github.com/user-attachments/assets/2fff9786-3818-4ace-aba3-4b5283030d33" width="70" style="margin:10px;" title="AWS Lambda"/>
  <img src="https://github.com/user-attachments/assets/cb3cf99f-1c87-407a-9945-7c75ff463bb5" width="70" style="margin:10px;" title="Docker"/>
  <img src="https://github.com/user-attachments/assets/cb6cc17c-b65a-48f0-b2ab-a470593ae3b0" width="70" style="margin:10px;" title="GitHub Actions"/>
</p>

### Communication
<p>
  <img src="https://github.com/user-attachments/assets/25a7561b-8de1-4293-b467-98b00077b9c6" width="70" style="margin:10px;" title="GitHub"/>
  <img src="https://github.com/user-attachments/assets/43f92cb2-685b-4bc6-b878-1da14f3d3489" width="70" style="margin:10px;" title="Slack"/>
  <img src="https://github.com/user-attachments/assets/603e0c49-4591-4b8c-983a-1328c454da93" width="70" style="margin:10px;" title="Notion"/>
</p>

## 시스템 아키텍처

### 전체 아키텍처
<img width="1000" alt="Image" src="https://github.com/user-attachments/assets/d013fc64-3b3a-4354-83a9-50a4117ae629">


### 데이터 파이프라인 아키텍처
<img width="1000" alt="Image" src="https://github.com/user-attachments/assets/6230406e-94cd-414e-9492-428f2c0a46c8">


## 기술적 이슈와 해결 과정

| 이슈 | 해결 과정 |
|-------------|------------------------|
| 성능 최적화 | [실서비스를 고려한 성능 최적화](https://wwns1411.tistory.com/35) |
| LLM 응답 품질 보장 및 안정성 보장 | [LLM 응답의 품질 검증과 안정적인 운영을 위한 Fallback 패턴](https://wwns1411.tistory.com/36) |
| 데이터 파이프라인 자동화 | [AWS Lambda와 Slack을 활용한 데이터 파이프라인 구축기](https://wwns1411.tistory.com/37) |