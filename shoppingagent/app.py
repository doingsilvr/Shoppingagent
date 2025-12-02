import re
import streamlit as st
import time
import html
import json
from openai import OpenAI

# OpenAI 클라이언트 (API KEY 필요)
client = OpenAI()

# =========================================================
# 1. 초기 세션 설정
# =========================================================
def ss_init():
    ss = st.session_state
    ss.setdefault("page", "context_setting")
    ss.setdefault("nickname", "")
    ss.setdefault("messages", [])
    ss.setdefault("memory", [])
    ss.setdefault("memory_changed", False)
    ss.setdefault("notification_message", "")
    ss.setdefault("stage", "explore") 
    ss.setdefault("waiting_for_priority", False)
    ss.setdefault("current_recommendation", [])
    ss.setdefault("selected_product", None)

ss_init()

st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

# =========================================================
# 2. CSS 스타일 (디자인 전면 개선)
# =========================================================
st.markdown("""
<style>
    /* 기본 헤더/푸터 숨기기 */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem; max-width: 1200px !important;}

    /* 🟢 1. 시나리오 박스 */
    .scenario-box {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
        color: #0369A1;
        font-size: 15px;
        line-height: 1.5;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* 🟢 2. 진행바 스타일 */
    .step-container {
        display: flex;
        justify-content: center;
        margin-bottom: 30px;
    }
    .step-wrapper {
        display: flex;
        background: #FFFFFF;
        padding: 10px 40px;
        border-radius: 50px;
        border: 1px solid #E2E8F0;
        gap: 60px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .step-item {
        font-size: 15px;
        font-weight: 600;
        color: #94A3B8;
        display: flex;
        align-items: center;
    }
    .step-active {
        color: #2563EB;
        font-weight: 800;
    }
    .step-circle {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: #F1F5F9;
        color: #64748B;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 10px;
        font-size: 13px;
        font-weight: 700;
    }
    .step-active .step-circle {
        background: #2563EB;
        color: white;
        box-shadow: 0 2px 5px rgba(37, 99, 235, 0.3);
    }

    /* 🟢 3. 메모리 패널 디자인 (박스 형태) */
    .memory-container {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
    }
    .memory-header {
        font-size: 18px;
        font-weight: 700;
        color: #1F2937;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .memory-list-area {
        margin-bottom: 15px;
    }
    .memory-item-style {
        background: #F3F4F6;
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 8px;
        font-size: 14px;
        color: #374151;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* 🟢 4. 팁 박스 */
    .tip-box {
        background: #FFFBEB;
        border: 1px solid #FCD34D;
        border-radius: 12px;
        padding: 16px;
        font-size: 14px;
        color: #92400E;
        line-height: 1.5;
    }

    /* 🟢 5. 채팅창 디자인 (높이 고정) */
    .chat-display-area {
        height: 400px; /* 높이 적절히 조절 */
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
        max-width: 80%;
        font-size: 15px;
        line-height: 1.5;
        word-break: break-word;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .chat-bubble-user {
        background: #DCF8C6; /* 카톡색 */
        align-self: flex-end;
        margin-left: auto;
        color: #111;
        border-top-right-radius: 2px;
    }
    .chat-bubble-ai {
        background: #F3F4F6; /* 회색 */
        align-self: flex-start;
        margin-right: auto;
        color: #111;
        border-top-left-radius: 2px;
    }

    /* 🟢 6. 상품 카드 디자인 */
    .product-carousel-area {
        margin-top: 10px;
        padding: 10px;
        background: #FAFAFA;
        border-radius: 12px;
        border: 1px solid #EEEEEE;
    }
    .product-card {
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 12px;
        text-align: center;
        transition: 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .product-card:hover { transform: translateY(-3px); box-shadow: 0 8px 16px rgba(0,0,0,0.08); }
    .product-img { 
        width: 100%; 
        height: 140px; 
        object-fit: contain; 
        margin-bottom: 10px; 
    }
    .product-name { font-weight: 700; font-size: 15px; margin: 5px 0; }
    .product-price { color: #2563EB; font-weight: 700; font-size: 14px; }
    .product-desc { font-size: 12px; color: #666; margin-bottom: 8px; line-height: 1.3; }

</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. 로직 함수
# =========================================================
def naturalize_memory(text: str) -> str:
    return text.strip().replace("(가장 중요)", "").strip()

def extract_budget(mems):
    for m in mems:
        if re.search(r"\d+만\s*원|\d{3,}원", m): return True
    return False

# 이미지 URL 복구된 카탈로그
CATALOG = [
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 450000, "rating": 4.8, "reviews": 3200, "tags": ["노이즈캔슬링", "음질", "착용감"], "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.", "color": ["블랙", "실버"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg"},
    {"name": "Bose QC45", "brand": "Bose", "price": 389000, "rating": 4.7, "reviews": 2800, "tags": ["가벼움", "착용감", "노이즈캔슬링"], "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.", "color": ["블랙", "화이트"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg"},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 769000, "rating": 4.6, "reviews": 1500, "tags": ["브랜드", "디자인", "고급"], "review_one": "깔끔한 디자인과 가벼운 무게로 만족도가 높아요.", "color": ["실버", "스페이스그레이"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg"},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 129000, "rating": 4.4, "reviews": 2300, "tags": ["가성비", "배터리", "음질"], "review_one": "가성비가 훌륭하고 가볍다는 평이 많아요.", "color": ["블랙", "화이트"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png"},
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 149000, "rating": 4.4, "reviews": 1600, "tags": ["가성비", "배터리", "노이즈캔슬링"], "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.", "color": ["블랙", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg"},
]

def filter_products(mems):
    # 예산, 키워드 기반 필터링 (간소화됨)
    return CATALOG[:3]

def extract_memory_with_gpt(user_input, memory_list):
    if any(x in user_input for x in ["?", "뭐야", "어때", "알려줘", "추천"]): return []
    current = "\n".join(memory_list) if memory_list else "(없음)"
    prompt = f"""
    [기존 메모리] {current}
    [사용자 발화] "{user_input}"
    사용자 발화에서 쇼핑 기준(가격, 색상, 기능, 용도 등)을 추출해 JSON으로 반환하세요.
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

def gpt_reply(user_input):
    stage = st.session_state.stage
    memories = "\n".join(st.session_state.memory)
    
    if stage == "product_detail":
        p = st.session_state.selected_product
        system_prompt = f"""
        당신은 '{p['name']}' 제품 전문가입니다.
        [제품 정보] 가격: {p['price']:,}원, 특징: {', '.join(p['tags'])}, 리뷰요약: {p['review_one']}
        [규칙]
        1. 오직 이 제품의 스펙과 특징에 대해서만 답변하세요.
        2. 사용자의 과거 취향(색상 선호 등)을 절대 언급하지 마세요. "지난번에~" 금지.
        """
    else:
        system_prompt = f"""
        당신은 AI 쇼핑 에이전트입니다.
        [기억된 기준] {memories}
        [규칙]
        1. 메모리에 있는 내용은 다시 묻지 마세요.
        2. 예산이 없으면 자연스럽게 물어보세요.
        """

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
            temperature=0.5
        )
        return res.choices[0].message.content
    except: return "잠시 연결에 문제가 생겼어요."

# =========================================================
# 4. UI 렌더링 함수들 (여기에 시나리오/진행바 복구)
# =========================================================
def render_scenario():
    """시나리오 박스 렌더링"""
    st.markdown("""
    <div class="scenario-box">
        <b>💡 시나리오 가이드</b><br>
        당신은 출퇴근용 또는 선물용으로 <b>헤드셋</b>을 찾고 있습니다. 
        AI에게 원하는 가격, 색상, 기능을 자유롭게 말해보세요. 
        AI가 대화 내용을 <b>'메모리'</b>에 저장하고 딱 맞는 제품을 추천해줍니다.
    </div>
    """, unsafe_allow_html=True)

def render_progress():
    """단계 표시: 탐색 -> 비교 -> 구매결정"""
    steps = ["탐색", "비교", "구매결정"]
    current_idx = 0
    
    # 내부 stage를 3단계로 매핑
    if st.session_state.stage in ["explore", "summary"]: current_idx = 0
    elif st.session_state.stage in ["comparison", "product_detail"]: current_idx = 1
    elif st.session_state.stage == "purchase_decision": current_idx = 2
    
    html_str = '<div class="step-container"><div class="step-wrapper">'
    for i, step in enumerate(steps):
        active_cls = "step-active" if i == current_idx else ""
        html_str += f'<div class="step-item {active_cls}"><div class="step-circle">{i+1}</div>{step}</div>'
    html_str += "</div></div>"
    st.markdown(html_str, unsafe_allow_html=True)

def render_memory_panel():
    """왼쪽 메모리 패널을 예쁜 박스로 렌더링"""
    st.markdown('<div class="memory-container">', unsafe_allow_html=True)
    st.markdown('<div class="memory-header">🧠 나의 쇼핑 기준</div>', unsafe_allow_html=True)
    
    if not st.session_state.memory:
        st.caption("아직 대화에서 수집된 정보가 없습니다.")
    else:
        st.markdown('<div class="memory-list-area">', unsafe_allow_html=True)
        for i, mem in enumerate(st.session_state.memory):
            # Streamlit 컬럼을 사용하여 텍스트와 삭제 버튼 배치
            c1, c2 = st.columns([85, 15])
            with c1:
                st.markdown(f'<div class="memory-item-style">{naturalize_memory(mem)}</div>', unsafe_allow_html=True)
            with c2:
                # 삭제 버튼 (작게)
                if st.button("✕", key=f"del_{i}", help="삭제"):
                    delete_memory(i)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 10px 0; opacity: 0.2;'>", unsafe_allow_html=True)
    # 기준 추가 입력창
    new_mem = st.text_input("기준 직접 추가", placeholder="예: 디자인 중요", label_visibility="collapsed")
    if st.button("➕ 기준 추가하기", use_container_width=True):
        if new_mem:
            add_memory(new_mem)
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)

def render_product_carousel():
    """제품 리스트를 가로형 카드(캐러셀 느낌)로 렌더링"""
    st.markdown("### 🏆 추천 제품 TOP 3")
    products = filter_products(st.session_state.memory)
    
    cols = st.columns(3)
    for idx, p in enumerate(products):
        with cols[idx]:
            st.markdown(f"""
            <div class="product-card">
                <img src="{p['img']}" class="product-img">
                <div class="product-name">{p['name']}</div>
                <div class="product-price">{p['price']:,}원</div>
                <div class="product-desc">{p['review_one']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 상세보기 버튼
            if st.button("상세보기", key=f"btn_detail_{idx}", use_container_width=True):
                st.session_state.selected_product = p
                st.session_state.stage = "product_detail"
                # 상세 진입 메시지 자동 추가
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"**{p['name']}** 제품을 선택하셨군요! 이 제품에 대해 궁금한 점(배터리, 무게, 단점 등)을 물어보세요."
                })
                st.rerun()

def handle_input():
    user_text = st.session_state.user_input_text
    if not user_text.strip(): return

    st.session_state.messages.append({"role": "user", "content": user_text})

    # 탐색 단계에서만 메모리 추출
    if st.session_state.stage == "explore":
        mems = extract_memory_with_gpt(user_text, st.session_state.memory)
        for m in mems: add_memory(m)
        
        if "추천" in user_text:
            st.session_state.stage = "comparison"
            st.session_state.messages.append({"role": "assistant", "content": "분석된 기준에 맞춰 추천 제품을 가져왔어요! 👇"})
            st.session_state.user_input_text = ""
            return

    response = gpt_reply(user_text)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.user_input_text = ""

# =========================================================
# 5. 메인 화면 구성
# =========================================================
def main_chat_interface():
    # 1. 알림 Toast
    if st.session_state.notification_message:
        st.toast(st.session_state.notification_message, icon="✅")
        st.session_state.notification_message = ""

    # 2. 상단: 시나리오 & 진행바
    render_scenario()
    render_progress()

    col1, col2 = st.columns([3, 7], gap="large")

    # [왼쪽] 메모리 패널 & 팁
    with col1:
        st.markdown(f"### 👋 {st.session_state.nickname}님")
        render_memory_panel()
        
        st.markdown("""
        <div class="tip-box">
            <b>💡 대화 팁</b><br>
            "30만원 이하로 찾아줘"<br>
            "노이즈 캔슬링은 필수야"<br>
            "흰색 디자인이 좋아"<br>
            처럼 구체적으로 말씀해 주시면 더 정확해집니다.
        </div>
        """, unsafe_allow_html=True)

    # [오른쪽] 대화 & 쇼핑 영역
    with col2:
        # (A) 대화창
        chat_container = st.container()
        with chat_container:
            html_content = '<div class="chat-display-area">'
            for msg in st.session_state.messages:
                cls = "chat-bubble-ai" if msg['role'] == "assistant" else "chat-bubble-user"
                html_content += f'<div class="chat-bubble {cls}">{msg["content"]}</div>'
            html_content += '</div>'
            st.markdown(html_content, unsafe_allow_html=True)

        # (B) 추천 제품 영역 (비교 단계 or 상세 단계일 때 모두 표시)
        # 중요: 상세 단계여도 이 리스트는 유지됩니다.
        if st.session_state.stage in ["comparison", "product_detail", "purchase_decision"]:
            st.markdown("---")
            # 만약 상세 단계라면 '뒤로가기'와 '구매하기' 버튼 표시
            if st.session_state.stage == "product_detail":
                nav_c1, nav_c2 = st.columns([1, 5])
                with nav_c1:
                    if st.button("⬅️ 목록으로"):
                        st.session_state.stage = "comparison"
                        st.session_state.selected_product = None
                        st.rerun()
                with nav_c2:
                    if st.button("🛒 이 제품 구매 결정하기", type="primary"):
                        st.session_state.stage = "purchase_decision"
                        st.rerun()
            
            # 제품 리스트 렌더링 (항상 보임)
            render_product_carousel()

        # (C) 구매 결정 피드백
        if st.session_state.stage == "purchase_decision":
             p = st.session_state.selected_product
             st.success(f"🎉 **{p['name']}** 구매를 고려하시네요!")
             st.balloons()

        # (D) 입력창 (고정)
        with st.form(key="chat_form", clear_on_submit=True):
            cols = st.columns([85, 15])
            with cols[0]:
                st.text_input("메시지", key="user_input_text", placeholder="메시지를 입력하세요...", label_visibility="collapsed")
            with cols[1]:
                if st.form_submit_button("전송"):
                    handle_input()
                    st.rerun()

# =========================================================
# 실행 진입점
# =========================================================
if st.session_state.page == "context_setting":
    st.title("🛒 쇼핑 에이전트 시작하기")
    st.markdown("---")
    with st.container():
        name = st.text_input("이름(닉네임)을 입력해주세요", "홍길동")
        if st.button("쇼핑 시작", type="primary"):
            st.session_state.nickname = name
            st.session_state.page = "chat"
            st.session_state.messages.append({"role": "assistant", "content": f"안녕하세요 {name}님! 원하시는 헤드셋의 용도나 가격대를 말씀해 주세요."})
            st.rerun()
else:
    main_chat_interface()
