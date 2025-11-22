import streamlit as st
import time
import random
import re
from openai import OpenAI

# =========================================================
# 기본 설정
# =========================================================
# 💡 [요구사항 ⑥] iframe에서 잘리는 문제 방지 CSS 추가
st.set_page_config(page_title="AI 쇼핑 에이전트 실험용", page_icon="🎧", layout="wide")

# -------------------------------
# 🔥 레이아웃 전체 스타일 커스텀 및 수정된 CSS 통합
# -------------------------------
st.markdown("""
<style>
/* 전체 앱 배경 */
body {
    background: #f8f9fa; /* 더 밝은 배경 */
}
/* Streamlit 메인 컨테이너 최대 폭 제한 및 중앙 정렬 (iframe 대응) */
.block-container {
    max-width: 1100px !important;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    margin: 0 auto;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* 공통 카드 스타일 */
.app-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); /* 부드러운 그림자 */
    border: 1px solid #e5e7eb;
}

.memory-card {
    background: #f9fafb;
    border-radius: 16px;
    padding: 1rem 1.1rem;
    border: 1px solid #e5e7eb;
}

/* 💡 [요구사항 ⑤] 로딩 스피너 제거 (chat_input 사용 시 Streamlit 기본 로딩 원형 UI) */
.stSpinner, [data-testid="stSpinner"] {
    display: none !important;
}

/* 단계 인디케이터 */
.stage-row {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.8rem;
    flex-wrap: wrap;
}
.stage-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.78rem;
    padding: 0.3rem 0.7rem;
    border-radius: 999px;
    border: 1px solid #e5e7eb;
    background: #ffffff;
    color: #4b5563;
    transition: all 0.3s;
}
.stage-pill.active {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
    box-shadow: 0 2px 4px rgba(37, 99, 235, 0.4);
}
.stage-dot {
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: #d1d5db;
}
.stage-pill.active .stage-dot {
    background: #ffffff;
}

/* 💡 [요구사항 ①] 채팅 컨테이너 높이 및 스크롤 설정 */
.chat-container {
    height: 520px;
    overflow-y: auto;
    padding-right: 0.3rem; /* 스크롤바 공간 확보 */
    padding-top: 0.25rem;
}

/* 💡 [요구사항 ②] 첫 메시지가 상단에서 시작되도록 강제 (Streamlit의 기본 마진 덮어쓰기) */
.chat-container .stChatMessage {
    margin-top: 0 !important;
}

/* 채팅 말풍선 레이아웃 */
.stChatMessage { /* Streamlit 기본 메시지 컨테이너 제거 */
    background-color: transparent !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin-bottom: 0.5rem !important; 
}
[data-testid="stChatMessage"] {
    padding: 0 !important;
    background-color: transparent !important;
    border: none !important;
}

.chat-row {
    display: flex;
    margin-bottom: 0.5rem;
}
.chat-row.user {
    justify-content: flex-end;
}
.chat-row.assistant {
    justify-content: flex-start;
}
.chat-bubble {
    padding: 0.7rem 1.1rem;
    border-radius: 18px;
    max-width: 85%;
    display: inline-block;
    font-size: 0.95rem;
    line-height: 1.5;
    word-wrap: break-word;
    white-space: pre-wrap;
    box-shadow: 0 1px 1px rgba(0,0,0,0.05);
}
.chat-bubble.user {
    background: #2563eb;
    color: #ffffff;
    border-bottom-right-radius: 4px;
}
.chat-bubble.assistant {
    background: #f3f4f6;
    color: #111827;
    border-bottom-left-radius: 4px;
}

/* 메모리 항목 */
.memory-label {
    font-size: 0.8rem;
    color: #6b7280;
    margin-top: 0.5rem;
    margin-bottom: 0.15rem;
}
.memory-divider {
    border-top: 1px dashed #e5e7eb;
    margin: 1rem 0;
}

/* 버튼 가독성 */
.stButton > button {
    border-radius: 999px;
    font-size: 0.9rem;
    padding: 0.4rem 1.0rem;
    transition: all 0.2s;
}

/* Info Alert box (알림창) */
[data-testid="stAlert"] {
    background-color: #e6f0ff !important;
    border-left: 5px solid #2563eb !important;
    color: #1e3a8a !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# GPT 설정 (기존 로직 유지)
# =========================================================
SYSTEM_PROMPT = """
너는 'AI 쇼핑 도우미'이며 사용자의 블루투스 헤드셋 기준을 파악해 추천을 돕는 역할을 한다.

[역할 규칙]
- 너는 챗봇이 아니라 '개인 컨시어지' 같은 자연스러운 톤으로 말한다.
- 사용자가 말한 기준은 아래의 [메모리]를 참고해 반영한다.
- **🚨 [최우선 규칙] 메모리에 이미 저장된 기준(특히 용도/상황/기능)은 절대 다시 물어보지 않고, 바로 다음 단계의 구체적인 질문으로 전환한다.**
- 새로운 기준이 등장하면, '메모리에 추가하면 좋겠다'라고 자연스럽게 제안한다.
- 단, 실제 메모리 추가/수정/삭제는 시스템(코드)이 처리하므로, 너는 "내가 메모리에 저장했다"라고 단정적으로 말하지 말고
  "이 기준을 기억해둘게요" 정도로 표현한다.
- 사용자가 모호하게 말하면 부드럽게 구체적으로 다시 물어본다.
- 사용자가 “잘 모르겠어 / 글쎄 / 아직 생각 안 했어”라고 말하면,
  “그렇다면 주로 어떤 상황에서 사용하실 때 중요할까요?”와 같이 사용 상황을 묻는다.
- 사용자는 블루투스 '헤드셋(오버이어/온이어)'을 구매하려고 한다. '이어폰' 또는 '인이어' 타입에 대한 질문은 피하라.

[대화 흐름 규칙]
- **🚨 1. 초기 대화는 [이전 구매 내역]을 바탕으로 사용자의 일반적인 취향을 파악하는 데 집중한다. (예: 디자인, 색상, 가격 중시 여부)**
- **🚨 2. 일반적인 취향이 파악된 후(메모리 1~2개 추가 후), 대화는 현재 구매 목표인 블루투스 헤드셋의 기준(용도/상황 → 기능/착용감/배터리/디자인/브랜드/색상 → 예산) 순으로 자연스럽게 넓혀 간다.**
- 메모리에 이미 용도/상황/기능 등의 기준이 파악되었다면, 다음 단계의 질문으로 넘어가라.
- 🚨 디자인/스타일 기준이 파악되면, 다음 질문은 선호하는 색
