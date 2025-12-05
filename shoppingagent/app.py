import streamlit as st
import time
import json
import random
import re
from openai import OpenAI

# =========================================================
# 0. 페이지 및 CSS 설정 (여기가 핵심 디자인)
# =========================================================
st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

st.markdown("""
<style>
    /* 1. 전체 컨테이너: 모바일 앱처럼 좁고 집중도 있게 */
    .block-container {
        max-width: 1000px;
        padding-top: 2rem;
        padding-bottom: 3rem;
        margin: 0 auto;
    }
    #MainMenu, footer, header {visibility: hidden;}

    /* 2. 프로세스 스테퍼 (진행바) 디자인 */
    .step-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
        position: relative;
        padding: 0 20px;
    }
    .step-line {
        position: absolute;
        top: 50%;
        left: 40px;
        right: 40px;
        height: 2px;
        background-color: #E2E8F0;
        z-index: 0;
        transform: translateY(-50%);
    }
    .step-item {
        position: relative;
        z-index: 1;
        background: white;
        padding: 0 10px;
        text-align: center;
    }
    .step-circle {
        width: 32px; height: 32px;
        border-radius: 50%;
        background-color: white;
        border: 2px solid #CBD5E1;
        color: #94A3B8;
        display: flex; align-items: center; justify-content: center;
        font-weight: bold;
        margin: 0 auto 5px auto;
        transition: all 0.3s;
    }
    .step-text {
        font-size: 12px;
        color: #94A3B8;
        font-weight: 500;
    }
    
    /* 활성화 된 단계 스타일 */
    .step-active .step-circle {
        border-color: #2563EB;
        background-color: #2563EB;
        color: white;
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
    }
    .step-active .step-text {
        color: #2563EB;
        font-weight: bold;
    }

    /* 3. 버튼 스타일링 (종류별 분리) */
    
    /* 기본 버튼 (전송, 추가 등) - 파란색 */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        transition: 0.2s;
    }
    
    /* 4. [중요] 삭제 버튼(X)만 콕 집어서 투명하게 만들기 */
    /* Streamlit의 secondary 버튼을 투명 버튼으로 개조 */
    button[kind="secondary"] {
        background-color: transparent !important;
        border: none !important;
        color: #94A3B8 !important;
        padding: 0px 8px !important;
        font-size: 16px !important;
    }
    button[kind="secondary"]:hover {
        color: #EF4444 !important; /* 빨간색 */
        background-color: #FEF2F2 !important;
    }

    /* 5. 메모리 태그 디자인 */
    .memory-box {
        background-color: white;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        border-left: 5px solid #2563EB; /* 포인트 컬러 */
    }
    
    /* 6. 채팅 말풍선 */
    .chat-bubble-ai {
        background-color: #F1F5F9;
        color: #1E293B;
        padding: 12px 16px;
        border-radius: 12px 12px 12px 0;
        margin-bottom: 10px;
        line-height: 1.5;
        font-size: 15px;
    }
    .chat-bubble-user {
        background-color: #EFF6FF;
        color: #1E3A8A;
        padding: 12px 16px;
        border-radius: 12px 12px 0 12px;
        margin-bottom: 10px;
        text-align: right;
        line-height: 1.5;
        font-size: 15px;
        margin-left: auto;
        max-width: 80%;
    }
    
    /* 7. 상품 카드 */
    .product-card {
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 10px;
        background: white;
        text-align: center;
        height: 100%;
        transition: transform 0.2s;
    }
    .product-card:hover {
        border-color: #2563EB;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* 입력창 스타일 */
    .stTextInput input {
        border-radius: 20px;
        padding: 10px 15px;
        border: 1px solid #CBD5E1;
    }
</style>
""", unsafe_allow_html=True)

client = OpenAI()

# =========================================================
# 1. 세션 및 데이터 초기화
# =========================================================
def ss_init():
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.page = "context_setting"
        st.session_state.nickname = ""
        st.session_state.messages = []
        st.session_state.memory = []
        st.session_state.memory_colors = []
        st.session_state.stage = "explore"
        st.session_state.recommended_products = []
        st.session_state.selected_product = None
        st.session_state.final_choice = None
        st.session_state.summary_text = ""

ss_init()

CATALOG = [
    {"name": "Sony WH-1000XM5", "price": 450000, "tags": ["노이즈캔슬링", "음질", "착용감"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg"},
    {"name": "Bose QC45", "price": 389000, "tags": ["편안함", "가벼움", "노이즈캔슬링"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg"},
    {"name": "Apple AirPods Max", "price": 769000, "tags": ["디자인", "애플생태계", "고급"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg"},
    {"name": "Anker Soundcore Q45", "price": 149000, "tags": ["가성비", "배터리", "노이즈캔슬링"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg"},
    {"name": "JBL Tune 770NC", "price": 99000, "tags": ["가성비", "가벼움", "저음"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png"},
]

def get_random_color():
    return random.choice(["#2563EB", "#7C3AED", "#DB2777", "#EA580C", "#059669", "#0891B2"])

def add_memory(text):
    text = text.strip()
    if text and text not in st.session_state.memory:
        st.session_state.memory.append(text)
        st.session_state.memory_colors.append(get_random_color())

def delete_memory(idx):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        del st.session_state.memory_colors[idx]

def extract_memory_gpt(text, current_mem):
    try:
        prompt = f"발화: {text}\n기존메모리: {current_mem}\n쇼핑 기준(가격,디자인 등)을 JSON리스트로 추출. 없으면 []. Key: memories"
        res = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role":"user", "content":prompt}], temperature=0, response_format={"type":"json_object"}
        )
        return json.loads(res.choices[0].message.content).get("memories", [])
    except: return []

def get_gpt_response(text):
    sys_msg = f"너는 블루투스 헤드셋 쇼핑 에이전트야. 현재 단계: {st.session_state.stage}. 메모리: {st.session_state.memory}. 빈말 말고 핵심 질문만 해."
    res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"system", "content":sys_msg}, {"role":"user", "content":text}])
    return res.choices[0].message.content

# =========================================================
# 2. UI 컴포넌트 (디자인 + 기능 결합)
# =========================================================

def render_stepper():
    """HTML로 구현된 깔끔한 스테퍼 (깨짐 없음)"""
    steps = [("explore","1","탐색"), ("summary","2","요약"), ("comparison","3","추천"), ("product_detail","4","상세"), ("purchase_decision","5","결정")]
    curr = st.session_state.stage
    
    html = '<div class="step-container"><div class="step-line"></div>'
    for stage_code, num, label in steps:
        active = "step-active" if stage_code == curr else ""
        html += f"""
        <div class="step-item {active}">
            <div class="step-circle">{num}</div>
            <div class="step-text">{label}</div>
        </div>
        """
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def render_memory_sidebar():
    """파스텔톤 태그 + 투명 삭제 버튼"""
    with st.container(border=True):
        st.markdown("##### 🧠 쇼핑 메모리")
        st.caption("AI가 기억하는 취향입니다.")
        
        # 색상 싱크 맞추기
        while len(st.session_state.memory_colors) < len(st.session_state.memory):
            st.session_state.memory_colors.append(get_random_color())

        if not st.session_state.memory:
            st.info("아직 수집된 정보가 없어요.")

        for i, mem in enumerate(st.session_state.memory):
            col_color = st.session_state.memory_colors[i]
            
            # 레이아웃: 태그 내용(9) + 삭제버튼(1)
            c1, c2 = st.columns([8.5, 1.5])
            with c1:
                # HTML로 예쁜 태그 그리기
                st.markdown(
                    f'<div class="memory-box" style="border-left-color: {col_color};">{mem}</div>', 
                    unsafe_allow_html=True
                )
            with c2:
                # [핵심] type="secondary"를 줘서 CSS에서 투명하게 만듦
                if st.button("✕", key=f"del_{i}", type="secondary", help="삭제"):
                    delete_memory(i)
                    st.rerun()
        
        st.divider()
        new_input = st.text_input("직접 추가", placeholder="예: 무조건 화이트", label_visibility="collapsed")
        if st.button("➕ 추가하기", type="primary", use_container_width=True):
            if new_input:
                add_memory(new_input)
                st.rerun()

def render_carousel():
    """채팅 내 추천 카드"""
    st.markdown("##### 🎁 추천 제품")
    cols = st.columns(3)
    products = st.session_state.recommended_products
    
    for i, p in enumerate(products):
        with cols[i]:
            # 카드 디자인 HTML + 버튼 기능
            with st.container(border=True):
                st.image(p['img'], use_column_width=True)
                st.markdown(f"**{p['name']}**")
                st.caption(f"{p['price']:,}원")
                if st.button("상세보기", key=f"view_{i}", type="primary", use_container_width=True):
                    st.session_state.selected_product = p
                    st.session_state.stage = "product_detail"
                    st.rerun()

# =========================================================
# 3. 메인 실행 로직
# =========================================================

# 1) 설정 페이지
if st.session_state.page == "context_setting":
    st.title("🛒 AI 쇼핑 에이전트")
    st.info("실험을 위해 기본 정보를 입력해주세요.")
    
    with st.container(border=True):
        name = st.text_input("닉네임")
        if st.button("시작하기", type="primary"):
            if name:
                st.session_state.nickname = name
                st.session_state.page = "chat"
                st.rerun()

# 2) 채팅 페이지
else:
    # 상단 스테퍼
    render_stepper()
    
    # 메인 레이아웃 (왼쪽: 메모리 / 오른쪽: 채팅)
    col_mem, col_chat = st.columns([3, 7], gap="medium")
    
    with col_mem:
        render_memory_sidebar()
        
    with col_chat:
        # 채팅창 외관 (컨테이너로 감싸기)
        with st.container(border=True):
            
            # 스크롤 영역 (고정 높이)
            chat_area = st.container(height=500)
            
            with chat_area:
                # 인사말
                if not st.session_state.messages:
                    st.markdown(f"<div class='chat-bubble-ai'>안녕하세요 {st.session_state.nickname}님! 헤드셋 추천을 도와드릴게요. 용도가 어떻게 되세요?</div>", unsafe_allow_html=True)
                
                # 대화 내용 렌더링
                for msg in st.session_state.messages:
                    if msg["role"] == "user":
                        st.markdown(f"<div class='chat-bubble-user'>{msg['content']}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='chat-bubble-ai'>{msg['content']}</div>", unsafe_allow_html=True)
                
                # [단계별 특수 UI 렌더링]
                
                # 요약 단계
                if st.session_state.stage == "summary":
                    st.info("💡 기준이 충분히 모였습니다. 추천을 진행할까요?")
                    if st.button("추천 보기", type="primary"):
                        random.shuffle(CATALOG)
                        st.session_state.recommended_products = CATALOG[:3]
                        st.session_state.stage = "comparison"
                        st.rerun()
                
                # 추천 단계
                if st.session_state.stage == "comparison":
                    st.divider()
                    render_carousel()
                    
                # 상세 단계
                if st.session_state.stage == "product_detail":
                    p = st.session_state.selected_product
                    st.divider()
                    c1, c2 = st.columns([1, 2])
                    with c1: st.image(p['img'])
                    with c2:
                        st.subheader(p['name'])
                        st.write(f"**{p['price']:,}원**")
                        st.write(", ".join(p['tags']))
                        
                        b1, b2 = st.columns(2)
                        if b1.button("목록으로", type="secondary"):
                            st.session_state.stage = "comparison"
                            st.rerun()
                        if b2.button("구매하기", type="primary"):
                            st.session_state.stage = "purchase_decision"
                            st.session_state.final_choice = p
                            st.rerun()
                            
                # 구매 완료
                if st.session_state.stage == "purchase_decision":
                    st.balloons()
                    st.success(f"🎉 {st.session_state.final_choice['name']} 구매 완료!")

            # 입력창 (채팅창 하단에 붙어있음)
            with st.form("chat_input", clear_on_submit=True):
                c1, c2 = st.columns([8.5, 1.5])
                user_input = c1.text_input("메시지", placeholder="입력하세요...", label_visibility="collapsed")
                submit = c2.form_submit_button("전송", type="primary", use_container_width=True)
                
                if submit and user_input:
                    # 유저 메시지 저장
                    st.session_state.messages.append({"role":"user", "content":user_input})
                    
                    # 메모리 추출
                    mems = extract_memory_gpt(user_input, str(st.session_state.memory))
                    for m in mems: add_memory(m)
                    
                    # 상태 자동 전환 (탐색 -> 요약)
                    if st.session_state.stage == "explore" and len(st.session_state.memory) >= 4:
                        st.session_state.stage = "summary"
                    
                    # GPT 응답 (요약/추천 단계가 아닐때만)
                    if st.session_state.stage not in ["summary", "comparison", "product_detail"]:
                        reply = get_gpt_response(user_input)
                        st.session_state.messages.append({"role":"assistant", "content":reply})
                    
                    st.rerun()
