import re
import streamlit as st
import time
import html
import json
from openai import OpenAI

# OpenAI 클라이언트 설정
client = OpenAI()

# =========================================================
# 1. 세션 및 초기 설정
# =========================================================
def ss_init():
    ss = st.session_state
    
    # 기본 데이터
    ss.setdefault("page", "context_setting")
    ss.setdefault("nickname", "")
    ss.setdefault("messages", [])
    
    # 메모리
    ss.setdefault("memory", [])
    ss.setdefault("memory_changed", False)
    ss.setdefault("notification_message", "")
    
    # 상태 제어
    ss.setdefault("stage", "explore") 
    ss.setdefault("waiting_for_priority", False)
    
    # 추천/제품 데이터
    ss.setdefault("summary_text", "")
    ss.setdefault("current_recommendation", [])
    ss.setdefault("selected_product", None)

ss_init()

st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

# =========================================================
# 2. CSS 스타일 (높이 조절 및 UI 복구)
# =========================================================
st.markdown("""
<style>
    /* 기본 헤더 숨기기 */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem; max-width: 1100px !important;}

    /* 🟢 시나리오 박스 */
    .scenario-box {
        background: #F0F6FF;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #BFDBFE;
    }

    /* 🟢 진행바 스타일 */
    .step-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
        background: #f8fafc;
        padding: 10px 20px;
        border-radius: 50px;
        border: 1px solid #e2e8f0;
    }
    .step-item {
        font-size: 14px;
        font-weight: 600;
        color: #94a3b8;
        display: flex;
        align-items: center;
    }
    .step-active {
        color: #2563eb;
        font-weight: 800;
    }
    .step-circle {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: #e2e8f0;
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 8px;
        font-size: 12px;
    }
    .step-active .step-circle {
        background: #2563eb;
    }

    /* 🟢 채팅창 높이 축소 (400px) */
    .chat-display-area {
        height: 400px;  /* 높이 수정됨 */
        overflow-y: auto;
        padding: 1rem;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
    }

    /* 말풍선 */
    .chat-bubble {
        padding: 10px 14px;
        border-radius: 12px;
        margin-bottom: 8px;
        max-width: 80%;
        font-size: 15px;
        line-height: 1.5;
        word-break: break-word;
    }
    .chat-bubble-user {
        background: #DCF8C6; /* 카톡 느낌 연두색 */
        align-self: flex-end;
        margin-left: auto;
        color: #111;
        border-top-right-radius: 2px;
    }
    .chat-bubble-ai {
        background: #F3F4F6;
        align-self: flex-start;
        margin-right: auto;
        color: #111;
        border-top-left-radius: 2px;
    }

    /* 메모리 패널 */
    .memory-item {
        background: white;
        border: 1px solid #e5e7eb;
        padding: 8px;
        border-radius: 8px;
        margin-bottom: 6px;
        font-size: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .memory-btn {
        color: #ef4444;
        cursor: pointer;
        font-weight: bold;
        margin-left: 8px;
        border: none;
        background: none;
    }
    
    /* 상품 카드 */
    .product-card {
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        transition: 0.2s;
    }
    .product-card:hover { transform: translateY(-3px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .product-img { width: 100%; height: 140px; object-fit: contain; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. 로직 함수 (메모리, GPT)
# =========================================================
def naturalize_memory(text: str) -> str:
    t = text.strip().replace("(가장 중요)", "").strip()
    return t

def extract_budget(mems):
    for m in mems:
        if re.search(r"\d+만\s*원|\d{3,}원", m): return True
    return False

# 🔥 메모리 추출 (질문 제외)
def extract_memory_with_gpt(user_input, memory_list):
    if any(x in user_input for x in ["?", "뭐야", "어때", "알려줘", "추천"]): return []
    
    current = "\n".join(memory_list) if memory_list else "(없음)"
    prompt = f"""
    [기존 메모리]
    {current}
    [사용자 발화]
    "{user_input}"
    
    사용자 발화에서 쇼핑 기준(가격, 색상, 기능, 용도 등)을 추출해 JSON으로 반환.
    기존 메모리와 중복되면 반환하지 말 것.
    형식: {{ "memories": ["~를 선호해요"] }}
    """
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}],
            temperature=0.0, response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content).get("memories", [])
    except: return []

def add_memory(text, announce=True):
    # 중복 제거 및 추가
    clean = text.replace("(가장 중요)", "").strip()
    st.session_state.memory = [m for m in st.session_state.memory if clean not in m]
    st.session_state.memory.append(text)
    st.session_state.memory_changed = True
    if announce: st.session_state.notification_message = "📝 메모리에 기준이 추가되었어요!"

def delete_memory(idx):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.memory_changed = True
        st.session_state.notification_message = "🗑️ 기준이 삭제되었습니다."

# 🔥 GPT 응답 생성 (상세 단계 분기 처리 완벽 적용)
def gpt_reply(user_input):
    stage = st.session_state.stage
    memories = "\n".join(st.session_state.memory)
    
    # [A] 상세 페이지 (제품 질문)
    if stage == "product_detail":
        p = st.session_state.selected_product
        system_prompt = f"""
        당신은 지금 '{p['name']}' 제품 전문 상담원입니다.
        
        [제품 정보]
        - 가격: {p['price']:,}원
        - 특징: {', '.join(p['tags'])}
        - 리뷰요약: {p['review_one']}
        
        [절대 규칙]
        1. 오직 이 제품에 대해서만 답변하세요.
        2. "지난번에 ~를 좋아하셨는데" 같은 과거 회상 멘트는 절대 하지 마세요.
        3. 사용자가 리뷰, 단점, 배터리 등을 물어보면 지어내서라도 자연스럽게 답변하세요.
        """
    
    # [B] 탐색/비교 단계 (쇼핑 가이드)
    else:
        system_prompt = f"""
        당신은 사용자의 과거 취향을 기억하는 쇼핑 에이전트입니다.
        [기억된 기준]
        {memories}
        
        [규칙]
        1. 메모리에 있는 내용은 다시 묻지 마세요.
        2. 아직 예산 정보가 없다면 예산을 자연스럽게 물어보세요.
        """

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.5
        )
        return res.choices[0].message.content
    except:
        return "죄송합니다. 잠시 생각할 시간이 필요해요."

# =========================================================
# 4. 데이터 및 추천 로직
# =========================================================
CATALOG = [
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 450000, "rating": 4.8, "tags": ["노이즈캔슬링", "음질", "통화품질"], "img": "https://via.placeholder.com/150", "review_one": "노캔 성능이 압도적이나 힌지가 약하다는 평이 있음."},
    {"name": "Bose QC45", "brand": "Bose", "price": 389000, "rating": 4.7, "tags": ["착용감", "물리버튼", "밸런스"], "img": "https://via.placeholder.com/150", "review_one": "착용감은 최고지만, 통화 품질은 소니보다 아쉽다는 평."},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 769000, "rating": 4.6, "tags": ["디자인", "애플연동", "무거움"], "img": "https://via.placeholder.com/150", "review_one": "디자인과 마감은 완벽하나 무겁고 비싸다는 의견 다수."},
]

def get_recommendation():
    # 간단 필터링 (실제론 점수 로직)
    return CATALOG

# =========================================================
# 5. UI 컴포넌트 렌더링 함수
# =========================================================
def render_scenario():
    st.markdown("""
    <div class="scenario-box">
        <b>🛒 시나리오 가이드</b><br>
        당신은 출퇴근용으로 사용할 <b>헤드셋</b>을 찾고 있습니다. 
        AI에게 원하는 조건(가격, 디자인, 기능 등)을 말하고, 메모리가 어떻게 쌓이는지 확인해보세요.
    </div>
    """, unsafe_allow_html=True)

def render_progress():
    steps = ["탐색", "요약", "비교", "상세"]
    current_idx = 0
    if st.session_state.stage == "explore": current_idx = 0
    elif st.session_state.stage == "summary": current_idx = 1
    elif st.session_state.stage == "comparison": current_idx = 2
    elif st.session_state.stage == "product_detail": current_idx = 3
    
    html_str = '<div class="step-container">'
    for i, step in enumerate(steps):
        active_cls = "step-active" if i == current_idx else ""
        html_str += f'<div class="step-item {active_cls}"><div class="step-circle">{i+1}</div>{step}</div>'
    html_str += "</div>"
    st.markdown(html_str, unsafe_allow_html=True)

def render_notification():
    if st.session_state.notification_message:
        # st.toast를 사용하여 우측 상단에 깔끔하게 표시
        st.toast(st.session_state.notification_message, icon="✅")
        st.session_state.notification_message = ""

# =========================================================
# 6. 메인 핸들러 (입력 처리)
# =========================================================
def handle_input():
    # 폼에서 입력된 값 가져오기
    user_text = st.session_state.user_input_text
    
    if not user_text.strip(): return

    # 1. 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": user_text})

    # 2. 메모리 추출 (탐색 단계일 때만)
    if st.session_state.stage == "explore":
        mems = extract_memory_with_gpt(user_text, st.session_state.memory)
        for m in mems: add_memory(m)

        # 탐색 종료 조건 체크 (예: 추천해줘)
        if "추천" in user_text:
            st.session_state.stage = "summary"
            st.session_state.summary_text = f"지금까지 모은 기준: {', '.join(st.session_state.memory)}\n이대로 추천할까요?"
            st.session_state.messages.append({"role": "assistant", "content": st.session_state.summary_text})
            # 입력창 비우기 (Rerun 전)
            st.session_state.user_input_text = "" 
            return

    # 3. AI 답변 생성
    response = gpt_reply(user_text)
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # 4. 입력창 초기화 (키값 충돌 방지 위해 값 비움)
    st.session_state.user_input_text = ""

# =========================================================
# 7. 화면 구성
# =========================================================
def main_chat_interface():
    # 알림 표시
    render_notification()
    
    # 1. 시나리오 & 진행바
    render_scenario()
    render_progress()

    col1, col2 = st.columns([3, 7], gap="medium")

    # [좌측] 메모리 패널
    with col1:
        st.subheader("🧠 메모리")
        if not st.session_state.memory:
            st.info("아직 수집된 기준이 없습니다.")
        else:
            for i, mem in enumerate(st.session_state.memory):
                c1, c2 = st.columns([8, 2])
                with c1: st.markdown(f"**·** {naturalize_memory(mem)}")
                with c2: 
                    if st.button("x", key=f"del_{i}"): delete_memory(i); st.rerun()
        
        st.divider()
        st.caption("새로운 기준을 직접 추가할 수 있습니다.")
        new_mem = st.text_input("기준 추가", placeholder="예: 디자인 중요", label_visibility="collapsed")
        if st.button("추가하기"):
            if new_mem: add_memory(new_mem); st.rerun()

    # [우측] 채팅창
    with col2:
        # (A) 상세 페이지일 경우 뒤로가기 버튼
        if st.session_state.stage == "product_detail":
            if st.button("⬅️ 목록으로 돌아가기"):
                st.session_state.stage = "comparison"
                st.session_state.selected_product = None
                st.rerun()

        # (B) 대화 내용 표시
        chat_container = st.container()
        with chat_container:
            # HTML로 말풍선 렌더링 (스크롤 적용됨)
            html_content = '<div class="chat-display-area">'
            for msg in st.session_state.messages:
                cls = "chat-bubble-ai" if msg['role'] == "assistant" else "chat-bubble-user"
                html_content += f'<div class="chat-bubble {cls}">{msg["content"]}</div>'
            html_content += '</div>'
            st.markdown(html_content, unsafe_allow_html=True)

        # (C) 중간 컴포넌트 (추천 리스트 등)
        if st.session_state.stage == "summary":
            if st.button("🔍 추천 결과 보기", use_container_width=True):
                st.session_state.stage = "comparison"
                st.rerun()

        if st.session_state.stage == "comparison":
            st.write("### 🏆 추천 제품 TOP 3")
            recos = get_recommendation()
            c_cols = st.columns(3)
            for idx, p in enumerate(recos):
                with c_cols[idx]:
                    st.markdown(f"""
                    <div class="product-card">
                        <h4>{p['name']}</h4>
                        <p>{p['price']:,}원</p>
                        <span style="font-size:12px; color:gray;">{p['brand']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"상세보기", key=f"btn_{idx}", use_container_width=True):
                        st.session_state.selected_product = p
                        st.session_state.stage = "product_detail"
                        st.session_state.messages.append({"role": "assistant", "content": f"**{p['name']}** 제품을 선택하셨군요. 궁금한 점을 물어보세요!"})
                        st.rerun()

        # (D) 입력창 (st.form 사용 - 엔터키 작동 보장)
        with st.form(key="chat_form", clear_on_submit=True):
            # 입력창과 전송 버튼 레이아웃
            input_cols = st.columns([8, 1])
            with input_cols[0]:
                st.text_input(
                    "메시지 입력", 
                    key="user_input_text", 
                    placeholder="여기에 내용을 입력하세요...", 
                    label_visibility="collapsed"
                )
            with input_cols[1]:
                submit_btn = st.form_submit_button("전송")
            
            if submit_btn:
                handle_input()
                st.rerun()

# =========================================================
# 실행
# =========================================================
if st.session_state.page == "context_setting":
    # (간소화된 설정 페이지)
    st.title("🛍️ 쇼핑 에이전트 설정")
    name = st.text_input("이름", "홍길동")
    if st.button("시작하기"):
        st.session_state.nickname = name
        st.session_state.page = "chat"
        # 초기 인사 메시지
        st.session_state.messages.append({"role": "assistant", "content": f"안녕하세요 {name}님! 어떤 헤드셋을 찾으시나요?"})
        st.rerun()
else:
    main_chat_interface()
