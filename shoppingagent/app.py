import re
import streamlit as st
import time
import html
from openai import OpenAI

client = OpenAI()

# =========================================================
# 기본 설정
# =========================================================
st.set_page_config(
    page_title="AI 쇼핑 에이전트 실험용",
    page_icon="🎧",
    layout="wide"
)

# =========================================================
# 전역 CSS (하나의 <style>만 존재)
# =========================================================
st.markdown(
    """
    <style>

    /* -------------------------
       기본 UI 숨기기
    -------------------------- */
    #MainMenu, footer, header {
        visibility: hidden;
        display: none !important;
    }

    /* -------------------------
       메인 컨테이너
    -------------------------- */
    .block-container {
        max-width: 1050px !important;
        padding: 1rem 1.2rem 2rem 1.2rem;
        margin: auto;
    }

    /* Title 카드 */
    .title-card {
        background: white;
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        border: 1px solid #e8e8e8;
        margin-bottom: 1.2rem;
    }

    /* 파란 버튼 통일 */
    .stButton>button {
        background-color: #2f80ed !important;
        color: white !important;
        border-radius: 8px !important;
        height: 42px;
        padding: 0 22px;
        font-size: 15px;
        border: none;
    }

    /* 말풍선 영역 */
    .chat-display-area {
        background: #ffffff;
        padding: 14px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        height: 550px;
        overflow-y: auto;
        margin-bottom: 10px;
    }

    .chat-bubble-user {
        background: #e8f0fe;
        color: #000;
        padding: 10px 14px;
        border-radius: 12px;
        margin: 10px 0;
        width: fit-content;
        max-width: 80%;
        margin-left: auto;
    }

    .chat-bubble-ai {
        background: #f9f9f9;
        border: 1px solid #ddd;
        color: #000;
        padding: 10px 14px;
        border-radius: 12px;
        margin: 10px 0;
        width: fit-content;
        max-width: 80%;
        margin-right: auto;
    }

    /* 메모리 박스 */
    .memory-box {
        background: #fffaf2;
        border-left: 4px solid #ffb74d;
        padding: 12px 14px;
        border-radius: 8px;
        margin-bottom: 8px;
        font-size: 14px;
    }

    /* 단계 진행 원형 */
    .stage-indicator {
        display: flex;
        gap: 10px;
        margin: 16px 0 20px 0;
    }
    .stage-dot {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #d3d3d3;
    }
    .stage-dot.active {
        background: #2f80ed;
    }

    /* 요약 버튼 */
    .summary-btn {
        background: #2f80ed;
        color: white;
        border-radius: 6px;
        padding: 8px 14px;
        border: none;
        cursor: pointer;
        margin-top: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# 세션 상태 초기값 설정 함수
# =========================================================
def ss_init():
    ss = st.session_state

    ss.setdefault("page", "context_setting")

    # 사용자 정보
    ss.setdefault("nickname", "")
    ss.setdefault("budget", None)

    # 대화 메시지
    ss.setdefault("messages", [])

    # 메모리
    ss.setdefault("memory", [])
    ss.setdefault("just_updated_memory", False)

    # 단계(stage)
    ss.setdefault("stage", "explore")
    ss.setdefault("summary_text", "")

    # 추천/상세 정보 컨트롤
    ss.setdefault("current_recommendation", [])
    ss.setdefault("selected_product", None)

    # 로그용
    ss.setdefault("turn_count", 0)
    ss.setdefault("final_choice", None)
    ss.setdefault("decision_turn_count", 0)


ss_init()

# =========================================================
# 페이지 라우팅
# =========================================================
if st.session_state.page == "context_setting":
    def context_setting_page():

        st.markdown("<div class='title-card'><h2>🎧 헤드폰 쇼핑 시작하기</h2></div>", unsafe_allow_html=True)

        nickname = st.text_input("닉네임을 입력해주세요", key="nickname_input")
        budget = st.number_input("예산(원)을 입력해주세요", min_value=0, key="budget_input")

        if st.button("쇼핑 시작하기 🚀"):
            st.session_state.nickname = nickname
            st.session_state.budget = budget
            st.session_state.page = "chat"
            st.experimental_rerun()

    context_setting_page()
    st.stop()

# =========================================================
# 유틸: 대화 추가
# =========================================================
def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})

# =========================================================
# OpenAI 호출 함수
# =========================================================
def call_gpt(messages):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return resp.choices[0].message.content

# =========================================================
# 메모리 탐지 (단순 규칙 기반)
# =========================================================
def detect_memory_from_user(u):
    res = []

    if "편한" in u or "착용감" in u:
        res.append("편안한 착용감을 선호")
    if "음질" in u:
        res.append("음질을 중요시")
    if "가볍" in u:
        res.append("가벼운 무게 선호")
    if "블랙" in u or "검정" in u:
        res.append("블랙 색상 선호")
    if "화이트" in u or "하양" in u:
        res.append("화이트 색상 선호")

    return res


# =========================================================
# 추천 로직 (샘플)
# =========================================================
def generate_recommendation(mem_list):
    # 가장 최근 메모리를 기반으로 매우 단순 추천
    text = "지금까지 말씀하신 선호도를 기준으로 제품을 골라드릴게요!\n\n"

    if "음질을 중요시" in mem_list:
        text += "- 프리미엄 음질 모델 중심으로 선택했어요.\n"
    if "편안한 착용감을 선호" in mem_list:
        text += "- 장시간 착용해도 편한 헤드밴드 제품을 포함했어요.\n"
    if "가벼운 무게 선호" in mem_list:
        text += "- 경량 모델을 우선 포함했어요.\n"
    if "블랙 색상 선호" in mem_list:
        text += "- 블랙 색상 모델을 우선 반영했어요.\n"

    # 임시 추천 3개
    st.session_state.current_recommendation = [
        {"name": "Sony WH-1000XM5", "price": 419000},
        {"name": "Bose QC45", "price": 369000},
        {"name": "AKG K371", "price": 189000},
    ]

    return text


# =========================================================
# 채팅 인터페이스
# =========================================================
def chat_interface():

    st.markdown("<div class='title-card'><h3>AI 쇼핑 에이전트</h3></div>", unsafe_allow_html=True)

    # 단계 표시
    stage_order = ["explore", "summary", "comparison", "final"]
    current_stage = st.session_state.stage

    st.markdown("<div class='stage-indicator'>", unsafe_allow_html=True)
    for s in stage_order:
        if s == current_stage:
            st.markdown(f"<div class='stage-dot active'></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='stage-dot'></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1.4, 1])

    # -------------------------
    # 왼쪽: 대화 UI
    # -------------------------
    with col_left:

        chat_html = '<div class="chat-display-area">'

        # 기존 메시지 렌더링
        for msg in st.session_state.messages:
            safe = html.escape(msg["content"])
            role = msg["role"]
            if role == "assistant":
                chat_html += f'<div class="chat-bubble-chat chat-bubble-ai">{safe}</div>'
            else:
                chat_html += f'<div class="chat-bubble-user">{safe}</div>'

        # 요약 스테이지 → 요약 말풍선
        if st.session_state.stage == "summary":
            safe_sum = html.escape(st.session_state.summary_text)
            chat_html += f'<div class="chat-bubble-ai">{safe_sum}</div>'
            chat_html += '<button class="summary-btn" id="go_reco_btn">추천 보기</button>'

        chat_html += "</div>"

        st.markdown(chat_html, unsafe_allow_html=True)

        # JS → go_reco 버튼 클릭 시 URL 파라미터 전달
        st.markdown("""
            <script>
            const btn = window.parent.document.getElementById("go_reco_btn");
            if (btn) {
                btn.onclick = () => {
                    const url = new URL(window.location);
                    url.searchParams.set("go_reco", "1");
                    window.location = url;
                };
            }
            </script>
        """, unsafe_allow_html=True)

        # 사용자 입력
        user_input = st.text_input("메시지 입력", key="user_input")

        if st.button("전송"):
            if user_input.strip():
                add_message("user", user_input)
                st.session_state.turn_count += 1

                # 메모리 감지
                new_mems = detect_memory_from_user(user_input)
                if new_mems:
                    st.session_state.memory.extend(new_mems)
                    st.session_state.just_updated_memory = True

                # GPT 응답
                gpt_msg = call_gpt(st.session_state.messages)
                add_message("assistant", gpt_msg)

                # 일정 턴 이후 → summary 단계로
                if st.session_state.turn_count >= 3 and st.session_state.stage == "explore":
                    st.session_state.summary_text = "지금까지의 선호도를 요약해 드릴게요!"
                    st.session_state.stage = "summary"

                st.experimental_rerun()

        # URL 파라미터 체크 → summary 버튼 클릭
        if st.experimental_get_query_params().get("go_reco", ["0"])[0] == "1":
            st.session_state.stage = "comparison"
            st.experimental_rerun()

    # -------------------------
    # 오른쪽: 메모리·컨텍스트
    # -------------------------
    with col_right:
        st.subheader("🧠 현재까지 파악된 선호도")

        if not st.session_state.memory:
            st.write("아직 파악된 선호 정보가 없습니다.")
        else:
            for m in st.session_state.memory:
                st.markdown(f"<div class='memory-box'>{m}</div>", unsafe_allow_html=True)

        # 추천 보기 단계일 때
        if st.session_state.stage == "comparison":
            st.subheader("🎧 추천 제품 목록")

            rec_text = generate_recommendation(st.session_state.memory)
            st.write(rec_text)

            for item in st.session_state.current_recommendation:
                st.markdown(
                    f"""
                    <div style="
                        background:#f5f7ff;
                        padding:12px;
                        border-radius:10px;
                        margin-top:10px;
                        border:1px solid #dbe3ff;
                    ">
                    <b>{item['name']}</b><br>
                    가격: {item['price']}원
                    </div>
                    """,
                    unsafe_allow_html=True
                )


# =========================================================
# 메인 시작
# =========================================================
chat_interface()
