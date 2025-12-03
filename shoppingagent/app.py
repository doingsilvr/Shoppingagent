import re
import streamlit as st
import time
import html
import json
from openai import OpenAI

# OpenAI 클라이언트
client = OpenAI()

# =========================================================
# 1. 초기 세션 설정
# =========================================================
def ss_init():
    ss = st.session_state
    ss.setdefault("page", "context_setting")
    ss.setdefault("nickname", "")
    ss.setdefault("phone_number", "")
    ss.setdefault("messages", [])
    ss.setdefault("memory", [])
    ss.setdefault("memory_changed", False)
    ss.setdefault("notification_message", "")
    ss.setdefault("stage", "explore")
    ss.setdefault("waiting_for_priority", False)
    ss.setdefault("current_recommendation", [])
    ss.setdefault("selected_product", None)
    ss.setdefault("comparison_hint_shown", False)

ss_init()

st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

# =========================================================
# 2. CSS 스타일
# =========================================================
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 2rem; max-width: 1200px !important;}

    div.stButton > button {
        background-color: #2563EB !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    div.stButton > button:hover { background-color: #1D4ED8 !important; }

    div[data-testid="stBlinkContainer"] button {
        background-color: #ffffff !important;
        color: #2563EB !important;
        border: 1px solid #E5E7EB !important;
        padding: 2px 8px !important;
        height: auto !important;
    }

    /* 시나리오 박스 */
    .scenario-box {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
        color: #0369A1;
        font-size: 15px;
    }

    /* 채팅창 */
    .chat-display-area {
        height: 450px;
        overflow-y: auto;
        padding: 20px;
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        margin-bottom: 20px;
        display: flex;
        flex-direction: column;
    }
    .chat-bubble {
        padding: 12px 16px;
        border-radius: 16px;
        margin-bottom: 10px;
        max-width: 85%;
        line-height: 1.5;
    }
    .chat-bubble-user {
        background: #E0E7FF;
        align-self: flex-end;
        color: #111;
        border-top-right-radius: 2px;
    }
    .chat-bubble-ai {
        background: #F3F4F6;
        align-self: flex-start;
        color: #111;
        border-top-left-radius: 2px;
    }

    .memory-section-header {
        font-size: 20px;
        font-weight: 800;
        margin-bottom: 10px;
    }
    .memory-guide-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
        font-size: 13px;
        color: #64748B;
        margin-bottom: 15px;
    }
    .memory-block {
        background: #F3F4F6;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 14px;
        color: #374151;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 헬퍼 함수
# =========================================================
def naturalize_memory(text):
    return text.strip().replace("(가장 중요)", "").strip()

def ai_say(msg):
    st.session_state.messages.append({"role": "assistant", "content": msg})

def extract_memory_with_gpt(user_input, memory_list):
    if any(x in user_input for x in ["?", "뭐야", "어때", "알려줘", "추천"]):
        return []
    return []

# =========================================================
# ★ 수정된 헤더 — 설명이 박스 안에서 정상적으로 표시되는 버전 ★
# =========================================================
def render_step_header():
    stage = st.session_state.stage

    if stage in ["explore", "summary"]:
        step_num = 1
        title = "선호 조건 탐색"
        desc = "최근 구매 제품과 평소 쇼핑 취향을 기반으로 원하는 조건을 알려주세요."
    elif stage in ["comparison", "product_detail"]:
        step_num = 2
        title = "후보 비교"
        desc = "AI가 정리한 기준을 바탕으로 추천 후보를 비교합니다."
    else:
        step_num = 3
        title = "최종 결정"
        desc = "관심 제품의 상세 정보를 확인하고 최종 결정을 진행합니다."

    html = f"""
    <div style="
        background:#2563EB;
        padding:22px 28px;
        border-radius:14px;
        color:white;
        margin-bottom:25px;
    ">
        <div style="opacity:0.9; font-size:14px;">단계 {step_num}/3</div>

        <div style="font-size:24px; font-weight:700; margin-top:6px;">
            {title}
        </div>

        <div style="
            font-size:15px;
            opacity:0.88;
            line-height:1.6;
            margin-top:12px;
        ">
            {desc}
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)

# =========================================================
# 메모리 패널
# =========================================================
def render_memory_sidebar():
    st.markdown('<div class="memory-section-header">🛠 메모리 제어창</div>', unsafe_allow_html=True)
    st.markdown('<div class="memory-guide-box">메모리 추가, 삭제 모두 가능합니다.</div>', unsafe_allow_html=True)

    if not st.session_state.memory:
        st.caption("대화를 통해 기준이 수집됩니다.")
    else:
        for i, mem in enumerate(st.session_state.memory):
            c1, c2 = st.columns([85, 15])
            with c1:
                st.markdown(f'<div class="memory-block">{naturalize_memory(mem)}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("✕", key=f"delete_{i}"):
                    del st.session_state.memory[i]
                    st.session_state.memory_changed = True
                    st.rerun()

    new_mem = st.text_input("기준 직접 추가", placeholder="예: 디자인 중요", label_visibility="collapsed")
    if st.button("➕ 기준 추가하기", use_container_width=True):
        if new_mem:
            st.session_state.memory.append(new_mem)
            st.rerun()

# =========================================================
# 추천 UI
# =========================================================
def recommend_products_ui():
    st.markdown("### 🏆 추천 제품 TOP 3")
    st.info("→ 실제 추천 로직은 테스트용으로 간단히 구성되어 있습니다.")

# =========================================================
# 채팅 입력 처리
# =========================================================
def handle_input():
    msg = st.session_state.user_input_text
    if not msg.strip(): return
    st.session_state.messages.append({"role": "user", "content": msg})

    if st.session_state.stage == "explore" and "추천" in msg:
        st.session_state.stage = "comparison"
        ai_say("기준에 맞춰 제품을 추천해드릴게요!")
        return

    ai_say("알겠습니다!")

# =========================================================
# 메인 채팅 인터페이스
# =========================================================
def main_chat_interface():
    render_step_header()

    col1, col2 = st.columns([3, 7], gap="large")

    with col1:
        render_memory_sidebar()

    with col2:
        chat_html = '<div class="chat-display-area">'
        for msg in st.session_state.messages:
            cls = "chat-bubble-ai" if msg["role"] == "assistant" else "chat-bubble-user"
            chat_html += f'<div class="chat-bubble {cls}">{msg["content"]}</div>'
        chat_html += "</div>"

        st.markdown(chat_html, unsafe_allow_html=True)

        if st.session_state.stage in ["comparison", "product_detail"]:
            st.markdown("---")
            recommend_products_ui()

        with st.form(key="chat_form", clear_on_submit=True):
            c1, c2 = st.columns([85, 15])
            with c1:
                st.text_input("msg", key="user_input_text", placeholder="메시지를 입력하세요...")
            with c2:
                if st.form_submit_button("전송"):
                    handle_input()
                    st.rerun()

# =========================================================
# 첫 화면 (사전 설정)
# =========================================================
if st.session_state.page == "context_setting":
    st.title("🛒 쇼핑 에이전트 실험 준비")

    name = st.text_input("이름 (닉네임)", placeholder="홍길동")
    fav_color = st.text_input("Q. 평소 선호하는 색상은?", placeholder="예: 화이트, 블랙")

    if st.button("쇼핑 시작하기 (정보 저장)", type="primary"):
        if name and fav_color:
            st.session_state.nickname = name
            st.session_state.memory.append(f"선호 색상: {fav_color}")
            st.session_state.page = "chat"
            st.session_state.messages.append({"role": "assistant",
                                              "content": f"안녕하세요 {name}님! 사용 용도를 알려주세요 :)"})
            st.rerun()
else:
    main_chat_interface()
