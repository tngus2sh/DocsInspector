import os
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
from streamlit_chat import message  # streamlit-chat 라이브러리 사용
from sklearn.metrics.pairwise import cosine_similarity
from PyPDF2 import PdfReader
import docx
from urllib.parse import quote

from azure.storage.blob import BlobServiceClient

# openai 가져오기 (Azure OpenAI 사용하므로 해당 라이브러리 호출)
from openai import AzureOpenAI

# azure search ai
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

import pandas as pd
import uuid
from azure.storage.blob import BlobServiceClient

import streamlit.components.v1 as components
import time

# 환경변수 로딩
load_dotenv()

BLOB_CONN_STR = os.getenv("BLOB_CONN_STR", "")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME", "")
BLOB_CSV_CONTAINER_NAME = os.getenv("BLOB_CSV_CONTAINER_NAME", "")
FORM_ENDPOINT = os.getenv("FORM_ENDPOINT", "")
FORM_KEY = os.getenv("FORM_KEY", "")

# OpenAI API 설정
openai_api_key = os.getenv("AZURE_OPENAI_KEY")
opeanai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
openai_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# 문서 Azure OpenAI 클라이언트 설정
docs_client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=opeanai_endpoint,
    api_key=openai_api_key,
)

# text embedding Azure OpenAI 클라이언트 설정
embedding_name = os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME")

embedding_client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=opeanai_endpoint,
    api_key=openai_api_key,
)

# Azure Search AI 클라이언트 설정
search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
search_key = os.getenv("AZURE_SEARCH_KEY")

search_client = SearchClient(
    endpoint=search_endpoint,
    index_name=search_index_name,
    credential=AzureKeyCredential(search_key),
    api_version="2024-03-01-Preview",
)

# 페이지 설정
st.set_page_config(page_title="DocuLens: AI 기반 문서 분석 및 유사 문서 검색 시스템", layout="wide")

# 전체 스타일 삽입
st.markdown(
    """
<style>
    body {
        font-family: 'Segoe UI', sans-serif;
    }
    h1, h2, h3, h4 {
        color: #1f3b57;
    }
    .block-container {
        padding-top: 2rem;
    }
    .stButton button {
        border-radius: 8px;
        font-size: 16px;
    }
    .checklist-item {
        margin-bottom: 10px;
        padding: 8px 10px;
        background-color: #f9f9f9;
        border-left: 4px solid #ccc;
        border-radius: 6px;
    }
</style>
""",
    unsafe_allow_html=True,
)


# 카드 스타일 함수
def card(title, content, color="#f8f9fa"):
    st.markdown(
        f"""
    <div style="background-color:{color}; padding:20px; border-radius:12px; margin-bottom:15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        <h4 style="margin-top:0;">{title}</h4>
        <div style="font-size:15px;">{content}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_feedback_msg(name, timestamp, text):
    st.markdown(
        f"""
        <div style="margin-bottom:10px; padding:10px; border-left:4px solid #1f77b4; background-color:#f9f9f9; border-radius:6px;">
            <strong>👤 {name}</strong> <span style="font-size:13px; color:gray;">{timestamp}</span><br>
            <span style="font-size:15px;">{text}</span>
        </div>
    """,
        unsafe_allow_html=True,
    )


# 문서 분석 결과 카드 스타일 함수
def result_card(title, content, color="#ffffff"):
    st.markdown(
        f"""
    <div style="background-color:{color}; padding:18px 24px; border-radius:12px; margin-bottom:24px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
        <h4 style="margin-top:0; margin-bottom:12px;">{title}</h4>
        <div style="font-size:15px; line-height:1.6;">{content}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# 상태값 초기화
if "feedback_list" not in st.session_state:
    st.session_state.feedback_list = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []  # 기존 문서 목록 저장용
if "generated_checklist" not in st.session_state:
    st.session_state.generated_checklist = []

# 사이드바 메뉴
menu = ["문서 업로드", "통합 리뷰", "문서 검색"]
choice = st.sidebar.radio("메뉴", menu)


# 파일 업로드 처리
def upload_file_to_blob(uploaded_file, blob_name):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
        container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

        container_client.upload_blob(name=blob_name, data=uploaded_file, overwrite=True)

        msg = st.empty()
        msg.success(f"'{original_filename}' 파일이 성공적으로 업로드되었습니다.")
        time.sleep(3)
        msg.empty()

    except Exception as e:
        st.error(f"파일 업로드 실패: {e}")


# CSV 파일 업로드 함수
def upload_file_to_csv(uploaded_file, blob_name):
    try:
        # CSV 생성 및 업로드
        df = pd.DataFrame([row])
        csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

        blob_service = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
        container = blob_service.get_container_client(BLOB_CSV_CONTAINER_NAME)
        container.upload_blob(name=f"{document_id}.csv", data=csv_bytes, overwrite=True)
    except Exception as e:
        st.error(f"csv 파일 업로드 실패: {e}")


# 문서 추출 함수 (PDF, DOCX, TXT 처리)
def extract_pdf_content(uploaded_file):
    reader = PdfReader(uploaded_file)
    content = ""
    for page in reader.pages:
        content += page.extract_text()
    return content


def extract_docx_content(uploaded_file):
    doc = docx.Document(uploaded_file)
    content = ""
    for para in doc.paragraphs:
        content += para.text + "\n"
    return content


# 문서 요약 함수
def gpt_summarize_document(content):
    response = docs_client.chat.completions.create(
        model=openai_name,
        messages=[
            {
                "role": "system",
                "content": "다음 문서를 400자 이내로 간결히 가독성 있게 요약해줘. 한국어로 요약해줘.",
            },
            {"role": "user", "content": content},
        ],
        temperature=0.5,
        max_tokens=300,
    )
    summary = response.choices[0].message.content
    return summary


# 문서 주제 추출 함수
def extract_topic(content):
    response = docs_client.chat.completions.create(
        model=openai_name,
        messages=[
            {
                "role": "system",
                "content": "이 문서의 주제를 한 단어나 짧은 문장으로 간결하게 알려줘. 한국어로 답변해줘.",
            },
            {"role": "user", "content": content},
        ],
        temperature=0.3,
        max_tokens=100,
    )
    return response.choices[0].message.content.strip()


# 키워드 추출 함수
def extract_keywords_openai(content, num_keywords=5):
    response = docs_client.chat.completions.create(
        model=openai_name,
        messages=[
            {
                "role": "system",
                "content": f"다음 문서에서 가장 중요한 핵심 키워드 {num_keywords}개만 뽑아줘. 한 단어 또는 짧은 명사구 형태로 추출하고, 조사나 불필요한 단어는 제거해줘. 키워드는 쉼표로 구분해서 출력해줘.",
            },
            {"role": "user", "content": content},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    keywords = response.choices[0].message.content
    return keywords


# 키워드 파싱 함수
def parse_keywords(gpt_output):
    candidates = [kw.strip() for kw in gpt_output.split(",")]
    words = []
    for phrase in candidates:
        words.extend(phrase.split(" "))
    clean_words = list(set(w.lower() for w in words if w and len(w) > 1))

    return clean_words  # 해시태그 붙이지 않음


# 유사 문서 검색 함수
# Azure Search AI를 사용하여 유사 문서 검색
def find_similar_documents(messages):

    # 검색을 위해 쿼리 작성
    rag_params = {
        "data_sources": [
            {
                "type": "azure_search",
                "parameters": {
                    "endpoint": search_endpoint,
                    "index_name": search_index_name,
                    "authentication": {
                        "type": "api_key",
                        "key": search_key,
                    },
                    "query_type": "vector",
                    "embedding_dependency": {
                        "type": "deployment_name",
                        "deployment_name": embedding_name,
                    },
                },
            }
        ]
    }

    # Submit the chat request with RAG parameters
    response = docs_client.chat.completions.create(
        model=openai_name, messages=messages, extra_body=rag_params
    )

    completion = response.choices[0].message.content
    return completion


# 체크리스트 생성 함수
def gpt_generate_checklist(text, num_items=5):
    prompt = f"""
    다음 문서를 기반으로 검토자가 점검해야 할 체크리스트를 작성해줘.
    총 {num_items}개 항목을 작성하고, 각 항목은 '을 해야 함'과 같이 검토형 문장으로 작성해줘. 
    1. 체크리스트의 항목만 출력되도록 하고, 번호는 붙이지 말고, 각 항목은 새 줄로 구분해줘.
    2. 각 항목은 명확하고 구체적이어야 하며, 검토자가 쉽게 이해할 수 있어야 해.
    3. 각 항목은 문서의 주요 내용과 관련이 있어야 하며, 문서의 목적을 달성하는 데 도움이 되어야 해.
    문서: \"\"\"{text}\"\"\"
    """

    response = docs_client.chat.completions.create(
        model=openai_name,
        messages=[
            {
                "role": "system",
                "content": "문서 분석 전문가처럼 체크리스트를 작성해줘.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=500,
        temperature=0.3,
    )

    checklist_raw = response.choices[0].message.content.strip()
    checklist_items = [
        item.strip("- ").strip() for item in checklist_raw.split("\n") if item.strip()
    ]

    return checklist_items


def gpt_suggest_checklist_items(feedback, existing_checklist):
    prompt = f"""
    현재 체크리스트 항목은 다음과 같습니다:
    {', '.join(existing_checklist)}
    
    아래 내용을 '을 해야 함'과 같이 검토형 문장으로 체크리스트 항목 하나를 추가로 작성해줘.
    만약 기존의 체크리스트 항목과 중복되는 내용이 있다면, '없음'이라고 답변해줘.
    
    피드백: {feedback.strip()}
    """

    response = docs_client.chat.completions.create(
        model=openai_name,
        messages=[
            {"role": "system", "content": "문서 리뷰 보조 시스템"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=200,
        temperature=0.2,
    )

    suggestion = response.choices[0].message.content.strip()
    return suggestion


def circular_progress(pct: int):
    # 색상 지정
    if pct >= 100:
        color = "#1f77b4"
    elif pct >= 60:
        color = "#2ca02c"
    elif pct >= 30:
        color = "#ff7f0e"
    else:
        color = "#d62728"

    # 도넛 스타일로 큰 원형 표시
    components.html(
        f"""
    <div style="display: flex; justify-content: center; align-items: center; height: 350px;">
        <div style="
            width: 280px;
            height: 280px;
            border-radius: 50%;
            background: conic-gradient({color} {pct}%, #e0e0e0 {pct}%);
            display: flex;
            justify-content: center;
            align-items: center;
            transition: background 1s ease;
        ">
            <div style="
                width: 190px;
                height: 190px;
                border-radius: 50%;
                background-color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                box-shadow: inset 0 0 10px rgba(0,0,0,0.05);
            ">
                <div style="font-size: 36px; font-weight: bold;">{pct}%</div>
            </div>
        </div>
    </div>
    """,
        height=380,
    )


# 1. 문서 업로드 화면
if choice == "문서 업로드":
    st.header("🗂️ 문서 업로드 & 분석")

    # 2단 레이아웃 구성
    col_left, col_right = st.columns([1.3, 1])

    # 좌측: 분석 안내
    with col_left:
        st.markdown(
            """
        <div style="background-color:#e3f2fd; padding:20px 26px; border-left:6px solid #1976d2;
                    border-radius:12px; margin-top:10px; margin-bottom:30px; box-shadow:0 2px 6px rgba(0,0,0,0.05);">
            <h4 style="margin:0 0 10px 0; color:#0d47a1;">📢 분석 안내</h4>
            <p style="margin:0; font-size:15px; line-height:1.6; color:#333;">
                문서를 업로드하면 아래 항목이 자동으로 생성됩니다:
            </p>
            <ul style="font-size:15px; line-height:1.7; padding-left:20px; margin-top:8px; color:#333;">
                <li><strong>문서 주제</strong> 자동 추출</li>
                <li><strong>내용 요약</strong> 생성</li>
                <li><strong>핵심 키워드</strong> 도출 및 해시태그 변환</li>
                <li><strong>유사 문서 추천</strong> 제공</li>
            </ul>
            <p style="margin:8px 0 0; font-size:13.5px; color:#444;">
                📎 분석 결과는 아래에서 실시간으로 확인할 수 있습니다.
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # 우측: 문서 업로드 박스
    with col_right:
        st.markdown(
            """
        <div style="background-color:#f9fbfd; padding:24px 28px; border-left:6px solid #42a5f5; border-radius:14px; border:1px solid #d0e3f5; box-shadow:0 2px 6px rgba(0,0,0,0.03); margin-bottom:24px;">
            <h4 style="margin:0 0 12px 0; color:#1565c0;">📄 문서 업로드</h4>
            <p style="font-size:15px; color:#444; margin-bottom:18px;">
                분석할 문서를 선택하거나, 아래에 파일을 드래그해 주세요.
            </p>
        """,
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "📎 파일 선택", type=["pdf", "docx", "txt"], label_visibility="collapsed"
        )

    if uploaded_file:

        original_filename = uploaded_file.name

        print("========= 파일 컨테이너 정보 =========")
        print(f"Blob Connection String: {BLOB_CONN_STR}")
        print(f"Blob Container Name: {BLOB_CONTAINER_NAME}")
        print(f"Blob Csv Container Name: {BLOB_CSV_CONTAINER_NAME}")

        # Azure Blob Storage 업로드
        with st.spinner("파일 업로드 중..."):
            upload_file_to_blob(uploaded_file, original_filename)

        # 파일 내용 처리 (PDF, DOCX, TXT 등)
        if uploaded_file.type == "application/pdf":
            content = extract_pdf_content(uploaded_file)
        elif (
            uploaded_file.type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            content = extract_docx_content(uploaded_file)
        elif uploaded_file.type == "text/plain":
            content = uploaded_file.read().decode("utf-8")

        if content:

            # 체크리스트를 session state에 보관
            st.session_state.generated_checklist = []

            # GPT 분석 수행
            with st.spinner("문서 분석 중..."):
                topic = extract_topic(content)
                summary = gpt_summarize_document(content)
                keywords_raw = extract_keywords_openai(content)
                keywords = parse_keywords(keywords_raw)

                if not st.session_state.generated_checklist:
                    checklist_items = gpt_generate_checklist(content)
                    st.session_state.generated_checklist = checklist_items

            # 결과 출력
            st.subheader("📊 문서 분석 결과")
            st.markdown("<hr style='margin-bottom: 2rem;'>", unsafe_allow_html=True)

            # 문서 키워드
            tags_html = "<div style='display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;'>"
            for tag in keywords:
                tags_html += f"<span style='background-color:#e3f2fd; color: #1565c0; padding:6px 12px; border-radius:12px;'>#{tag}</span>"
            tags_html += "</div>"
            result_card("📌 키워드 (해시태그)", tags_html)

            # 문서 주제
            result_card("📌 문서 주제", topic)

            # 문서 요약
            result_card("📌 문서 요약", summary)

            # 유사 문서 섹션 간격 추가
            st.markdown("<div style='margin-top:30px;'></div>", unsafe_allow_html=True)

            # 주제, 요약 키워드를 CSV로 저장
            document_id = str(uuid.uuid4())
            row = {
                "id": document_id,
                "filename": uploaded_file.name,
                "topic": topic,
                "summary": summary,
                "keywords": ", ".join(keywords),  # 문자열로 저장
                "blob_url": f"https://{BLOB_CONTAINER_NAME}.blob.core.windows.net/originals/{document_id}.pdf",
            }

            # CSV 파일 업로드
            upload_file_to_csv(uploaded_file, document_id)

            # 유사 문서 검색
            query_text = f"""
                            아래 내용을 바탕으로 유사한 문서를 추천해줘. 한국어로 답변해줘.

                            주제: {topic}
                            요약: {summary}
                            키워드: {", ".join(keywords)}

                            출력할 때 내용은 아래 형식에 따라 구성하고, 각 문서는 새 줄로 제목 앞에 '①'과 같이 숫자를 붙여서 구분해줘.

                            제목: [문서 제목]
                            내용: [문서 내용 요약]
                            링크: [문서 링크]
                            """

            similar_messages = []
            similar_messages.append(
                {
                    "role": "user",
                    "content": query_text.strip(),
                }
            )

            with st.spinner("유사 문서 검색 중..."):
                response = find_similar_documents(similar_messages)

            similar_messages.append({"role": "assistant", "content": response})
            st.markdown(
                f"""
            <div style="background-color:#eef6fb; padding:22px 26px; border-left:6px solid #1f77b4; border-radius:10px; margin-bottom:30px; box-shadow:0 2px 6px rgba(0,0,0,0.06);">
                <h4 style="margin-top:0; margin-bottom:12px;">📑 유사 문서</h4>
                <div style="font-size:15px; line-height:1.7; white-space:pre-wrap;">{response}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )


elif choice == "통합 리뷰":
    st.header("📋 통합 리뷰 대시보드")

    # 안내 박스 추가
    st.markdown(
        """
    <div style="background-color:#e3f2fd; padding:20px 26px; border-left:6px solid #1976d2;
                border-radius:12px; margin-top:10px; margin-bottom:30px; box-shadow:0 2px 6px rgba(0,0,0,0.05);">
        <h4 style="margin:0 0 10px 0; color:#0d47a1;">ℹ️ 통합 리뷰 안내</h4>
        <p style="margin:0; font-size:15px; line-height:1.6; color:#333;">
            이 화면에서는 업로드한 문서를 기반으로 자동 생성된 <strong>체크리스트</strong>를 확인하고<br>
            현재 <strong>업무 진행률</strong>을 모니터링하며, 팀원들과 <strong>피드백을 주고받을 수</strong> 있습니다.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    # col1 내부에서 체크박스 그리기
    with col1:

        checked = []
        st.subheader("✅ 자동 생성된 체크리스트")

        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

        for i, item in enumerate(st.session_state.generated_checklist):
            checked.append(st.checkbox(item, key=f"auto_task_{i}"))

    # 진행률
    with col2:
        st.subheader("📊 진행률")
        total = len(st.session_state.generated_checklist)
        comp = sum(checked)
        pct = int((comp / total) * 100) if total > 0 else 0

        circular_progress(pct)
        st.markdown(
            f"<div style='text-align:center; font-size:18px;'>{comp} / {total} 완료</div>",
            unsafe_allow_html=True,
        )
        st.session_state.prev_pct = pct

    # 피드백 채팅
    with col3:
        st.subheader("💬 피드백 채팅")
        for msg in st.session_state.feedback_list:
            render_feedback_msg(msg["name"], msg["timestamp"], msg["text"])
        st.markdown("---")
        with st.form("fb_form", clear_on_submit=True):
            nm = st.text_input("👤 사용자명", key="fn")
            fb = st.text_area("✏️ 피드백 입력", key="ft")
            if st.form_submit_button("전송"):
                if nm and fb:
                    st.session_state.feedback_list.append(
                        {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "name": nm,
                            "text": fb,
                        }
                    )
                    suggestion = gpt_suggest_checklist_items(
                        fb, st.session_state.generated_checklist
                    )
                    if (
                        suggestion.lower() != "없음"
                        and suggestion not in st.session_state.generated_checklist
                    ):
                        st.session_state.generated_checklist.append(suggestion)
                    st.rerun()
                else:
                    st.warning("모두 입력하세요.")

### 3. 문서 검색 (GPT 목업 채팅 화면)

elif choice == "문서 검색":
    st.header("🔍 GPT와 채팅하며 문서 검색하기")

    st.markdown(
        """
    <div style="background-color:#e3f2fd; padding:20px 26px; border-left:6px solid #1976d2;
                border-radius:12px; margin-top:10px; margin-bottom:30px; box-shadow:0 2px 6px rgba(0,0,0,0.05);">
        <h4 style="margin:0 0 10px 0; color:#0d47a1;">💡 문서 검색 안내</h4>
        <p style="margin:0; font-size:15px; line-height:1.6; color:#333;">
            이 화면에서는 <strong>RAG(Retrieval-Augmented Generation)</strong> 모델을 기반으로<br>
            GPT와 대화하듯 질문을 입력하면 관련 문서를 자동으로 찾아드립니다.<br><br>
            아래 채팅창에 <strong>검색하고 싶은 내용을</strong> 입력해 보세요!<br>
            ex) "AI 관련 프로젝트 문서 찾아줘!"<br>
            ps. 문서 이외에 궁금한 것이 있다면 언제든 질문해주세요!
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "system",
                "content": "당신은 문서 검색을 도와주는 AI 어시스턴트입니다. 사용자가 질문을 입력하면 관련 문서를 찾아 답변해 주세요. 만약 관련 문서가 없다면, '관련 문서를 찾을 수 없습니다.'라고 답변하세요. 문서가 있다면, 꼭 문서 링크를 포함해서 답변해 주세요.",
            },
        ]

    for message in st.session_state.messages:
        st.chat_message(message["role"]).write(message["content"])

    if user_input := st.chat_input("문서 검색을 위한 질문을 입력하세요."):
        # 메시지 상태 초기화
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        with st.spinner("응답을 기다리는 중..."):
            response = find_similar_documents(st.session_state.messages)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)
