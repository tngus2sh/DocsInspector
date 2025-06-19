# 📄 분석서 인스펙터 (Document Inspector)

**문서를 업로드하면 AI가 자동으로 주제, 요약, 키워드, 유사 문서, 체크리스트까지 생성해주는 Streamlit 기반 문서 분석 어시스턴트입니다.**

Azure OpenAI와 Azure AI Search를 통합하여 RAG 기반 검색 및 분석을 수행합니다.

---

## 🚀 주요 기능

* ✅ 문서 업로드 (PDF, DOCX, TXT 지원)
* 🔎 주제 추출, 요약, 키워드 분석
* 📎 키워드를 기반으로 유사 문서 추천 (벡터 검색)
* 📋 자동 체크리스트 생성 및 리뷰 진행률 시각화
* 💬 팀 피드백 및 항목 반영
* 🧠 GPT 기반 문서 검색 채팅 (RAG 기반)

---

## 📁 프로젝트 구조

```bash
.
├── docInspector.py        # Streamlit 실행 메인 앱
├── .env                   # 환경변수 파일 (민감 정보 포함, 공개 X)
├── requirements.txt       # Python 패키지 목록
└── README.md              # 설명 문서
```

---

## ⚙️ 환경 변수 설정 (.env)

```env
# Azure Blob Storage
BLOB_CONN_STR=DefaultEndpointsProtocol=...        # Blob Storage 연결 문자열
BLOB_CONTAINER_NAME=originals                     # 원본 문서 컨테이너 이름
BLOB_CSV_CONTAINER_NAME=metadata                  # 분석 결과 저장용 CSV 컨테이너

# Azure OpenAI
AZURE_OPENAI_KEY=your_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4               # GPT deployment 이름
AZURE_EMBEDDING_DEPLOYMENT_NAME=text-embedding   # 임베딩 모델 deployment 이름

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=your-index-name
```

---

## 🧪 설치 방법

1. Python 3.9 이상 설치 필요
2. 가상환경 생성 및 패키지 설치

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> `requirements.txt` 파일이 없다면 아래 명령어로 주요 패키지를 설치하세요:

```bash
pip install streamlit python-dotenv openai azure-search-documents azure-storage-blob PyPDF2 python-docx scikit-learn matplotlib streamlit-chat
```

---

## ▶ 실행 방법

```bash
streamlit run app.py
```

> 실행 후 브라우저에서 `http://localhost:8501` 로 접속하세요.

---

## 📷 기능 미리보기

| 기능       | 설명                              |
| -------- | ------------------------------- |
| 문서 업로드   | PDF, DOCX, TXT 파일을 업로드하여 분석 시작  |
| 요약/주제 추출 | Azure OpenAI로 문서 내용을 정리해 표시     |
| 키워드 추출   | 핵심 키워드를 해시태그로 시각화               |
| 유사 문서 추천 | 벡터 기반 Azure Search를 통한 관련 문서 찾기 |
| 체크리스트 생성 | 문서 기반 검토 항목 자동 생성 및 완료율 시각화     |
| 문서 검색 채팅 | 사용자 질문을 기반으로 GPT가 관련 문서 추천      |

---

## 💬 예시 질문 (문서 검색)

* “AI 관련 프로젝트 문서 찾아줘”
* “재무 관련 자료 있는 문서 있어?”
* “RAG 기술 설명하는 문서 있니?”

---

## 🛠️ 향후 개선 아이디어

* 🖼️ 멀티 모달 문서 검색
* 🏷️ 문서 메타데이터 자동 태깅
* 🔗 API화 및 외부 시스템 연동
* 🧾 CSV 메타데이터 다운로드 버튼

---
