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
# 2. CSS 스타일 (스크린샷 기반 디자인 적용)
# =========================================================
st.markdown("""
<style>
    /* 기본설정 */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 2rem; max-width: 1200px !important;}
    
    /* 🟢 좌측 사이드바 스타일 */
    .sidebar-header {
        font-size: 24px; font-weight: 700; margin-bottom: 20px; color: #111;
    }
    
    /* 메모리 패널 스타일 (스크린샷 참조) */
    .memory-section-header {
        font-size: 18px; font-weight: 700; margin-top: 30px; margin-bottom: 15px; color: #111; display: flex; align-items: center;
    }
    .memory-block {
        background: #F3F4F6; /* 연한 회색 */
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 14px;
        color: #374151;
    }
    .memory-text { flex-grow: 1; margin-right: 10px; }
    /* 스트림릿 버튼 스타일 오버라이드 (X 버튼) */
    div[data-testid="stBlinkContainer"] button {
        border: 1px solid #E5E7EB; background: white; color: #9CA3AF;
        padding: 4px 10px; border-radius: 8px; font-size: 12px; line-height: 1; min-height: 0px;
    }
    div[data-testid="stBlinkContainer"] button:hover {
        border-color: #EF4444; color: #EF4444; background: #FEF2F2;
    }

    /* 🟢 상단 가로형 진행바 (스크린샷 내용 반영) */
    .progress-container {
        display: flex; justify-content: space-between; margin-bottom: 40px;
        padding: 0 20px;
    }
    .step-item {
        display: flex; flex-direction: column; align-items: flex-start; flex: 1;
        position: relative;
    }
    .step-header-group { display: flex; align-items: center; margin-bottom: 8px; }
    .step-circle {
        width: 32px; height: 32px; border-radius: 50%; background: #E5E7EB;
        color: #6B7280; display: flex; align-items: center; justify-content: center;
        font-weight: 700; margin-right: 12px; font-size: 14px; flex-shrink: 0;
    }
    .step-title { font-size: 16px; font-weight: 700; color: #374151; }
    .step-desc { font-size: 13px; color: #6B7280; padding-left: 44px; line-height: 1.4; }
    
    /* 활성화 된 단계 스타일 */
    .step-active .step-circle { background: #2563EB; color: white; }
    .step-active .step-title { color: #2563EB; }
    .step-active .step-desc { color: #4B5563; }

    /* 🟢 우측 대화창 영역 */
    .chat-container-box {
        background: #fff; border: 1px solid #E5E7EB; border-radius: 20px;
        padding: 20px; height: 600px; display: flex; flex-direction: column;
    }
    .chat-messages-area {
        flex-grow: 1; overflow-y: auto; padding-right: 10px; margin-bottom: 20px;
    }
    .chat-bubble {
        padding: 14px 18px; border-radius: 18px; margin-bottom: 12px;
        max-width: 85%; font-size: 15px; line-height: 1.5;
    }
    .chat-bubble-ai { background: #F3F4F6; align-self: flex-start; margin-right: auto; color: #1F2937; border-top-left-radius: 4px; }
    .chat-bubble-user { background: #DCF8C6; align-self: flex-end; margin-left: auto; color: #111; border-top-right-radius: 4px; }
    
    /* 상품 카드 스타일 */
    .product-card {
        background: #fff; border: 1px solid #e5e7eb; border-radius: 16px;
        padding: 15px; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: space-between;
        box-shadow: 0 4px 6px rgba(0,0,0,0.03);
    }
    .product-img { width: 100%; height: 150px; object-fit: contain; margin-bottom: 12px; }
    .product-title { font-weight: 700; font-size: 16px; margin-bottom: 4px; }
    .product-price { color: #2563EB; font-weight: 700; margin-bottom: 10px; }
    
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

def ai_say(msg):
    st.session_state.messages.append({"role": "assistant", "content": msg})

# 카탈로그 데이터
CATALOG = [
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 179000, "rating": 4.4, "reviews": 1600, "rank": 8, "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"], "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.", "color": ["블랙", "화이트", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg"},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 129000, "rating": 4.4, "reviews": 2300, "rank": 9, "tags": ["가벼움", "음질", "노이즈캔슬링", "편안함"], "review_one": "가볍고 음질이 좋다는 평이 많아요.", "color": ["블랙", "화이트", "퍼플", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png"},
    {"name": "Sony WH-CH720N", "brand": "Sony", "price": 169000, "rating": 4.5, "reviews": 2100, "rank": 6, "tags": ["노이즈캔슬링", "경량", "무난한 음질"], "review_one": "경량이라 출퇴근용으로 좋다는 후기가 많아요.", "color": ["블랙", "화이트", "블루"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-CH720N.jpg"},
    {"name": "Bose QC45", "brand": "Bose", "price": 420000, "rating": 4.7, "reviews": 2800, "rank": 2, "tags": ["가벼움", "착용감", "노이즈캔슬링", "편안함"], "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg"},
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 450000, "rating": 4.8, "reviews": 3200, "rank": 1, "tags": ["노이즈캔슬링", "음질", "착용감", "통화품질"], "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.", "color": ["핑크"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg"},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 679000, "rating": 4.6, "reviews": 1500, "rank": 3, "tags": ["브랜드", "노이즈캔슬링", "디자인", "고급"], "review_one": "깔끔한 디자인과 가벼운 무게로 만족도가 높아요.", "color": ["실버", "스페이스그레이"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg"},
    {"name": "Sennheiser PXC 550-II", "brand": "Sennheiser", "price": 289000, "rating": 4.3, "reviews": 1200, "rank": 7, "tags": ["착용감", "여행", "배터리", "노이즈캔슬링"], "review_one": "여행 시 장시간 착용에도 압박감이 덜해요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sennheiser%20PXC%2055.jpeg"},
    {"name": "AKG Y600NC", "brand": "AKG", "price": 149000, "rating": 4.2, "reviews": 1800, "rank": 10, "tags": ["균형 음질", "가성비", "노이즈캔슬링"], "review_one": "가격대비 깔끔하고 균형 잡힌 사운드가 좋아요.", "color": ["블랙", "골드", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/AKG%20Y6.jpg"},
    {"name": "Microsoft Surface Headphones 2", "brand": "Microsoft", "price": 319000, "rating": 4.5, "reviews": 900, "rank": 11, "tags": ["업무", "통화품질", "디자인", "노이즈캔슬링"], "review_one": "업무용으로 완벽하며 통화 품질이 매우 깨끗합니다.", "color": ["화이트", "블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Microsoft%20Surface%20Headphones%202.jpeg"},
    {"name": "Bose Noise Cancelling Headphones 700", "brand": "Bose", "price": 490000, "rating": 4.7, "reviews": 2500, "rank": 4, "tags": ["노이즈캔슬링", "배터리", "음질", "프리미엄"], "review_one": "노이즈캔슬링 성능과 음질을 모두 갖춘 최고급 프리미엄 제품.", "color": ["블랙", "화이트"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20Headphones%20700.jpg"},
]

def filter_products(mems):
    # 예시로 상위 3개 리턴 (실제 스코어링 로직 필요 시 대체)
    return CATALOG[:3]

def _brief_feature_from_item(c):
    tags_str = " ".join(c.get("tags", []))
    if "가성비" in tags_str: return "가성비 인기"
    if c.get("rank", 999) <= 3: return "이달 판매 상위"
    if "최상급" in tags_str: return "프리미엄 추천"
    if "디자인" in tags_str: return "디자인 강점"
    return "실속형 추천"

def generate_personalized_reason(product, mems, name):
    reasons = []
    mem_str = " ".join(mems)
    if "음질" in mem_str and "음질" in " ".join(product['tags']): reasons.append("중요하게 생각하신 **음질**이 뛰어난 제품이에요.")
    if "착용감" in mem_str and "착용감" in " ".join(product['tags']): reasons.append("오래 써도 편안한 **착용감**이 장점이에요.")
    if "디자인" in mem_str and "디자인" in " ".join(product['tags']): reasons.append("선호하시는 **디자인** 요소를 갖추고 있어요.")
    if "가성비" in mem_str and "가성비" in " ".join(product['tags']): reasons.append("원하시던 **가성비**가 아주 좋은 모델이에요.")
    if not reasons: return "고객님의 취향과 전반적으로 잘 맞는 인기 제품이에요."
    return " ".join(reasons)

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
        product = st.session_state.selected_product
        system_prompt = f"""
        당신은 현재 '상품 상세 정보 단계(product_detail)'에서 대화하고 있습니다.
        이 단계에서는 오직 **현재 선택된 제품에 대한 정보만** 간단하고 명확하게 제공합니다.

        [선택된 제품 정보]
        - 제품명: {product['name']} ({product['brand']})
        - 가격: {product['price']:,}원
        - 주요 특징: {', '.join(product['tags'])}
        - 리뷰 요약: {product['review_one']}

        [응답 규칙 — 매우 중요]
        1. 사용자의 질문에 대해 현재 선택된 제품에 대한 하나의 핵심 정보만 간단히 대답하세요.
        2. 탐색 질문(기준 물어보기, 용도 물어보기)은 절대 하지 마세요.
        3. "현재 선택된 제품은~" 같은 메타 표현을 쓰세요.
        4. 답변 후 마지막에 '추가 질문' 한 문장만 자연스럽게 붙이세요.
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
# 4. UI 렌더링 함수
# =========================================================
def render_progress_horizontal():
    # 스크린샷 1번 내용 반영한 단계 정의
    steps = [
        ("선호 조건 탐색", "에이전트와 대화하며 헤드셋에 원하는 조건을 정리합니다."), 
        ("후보 비교", "AI가 요약한 기준을 바탕으로 3개 후보를 비교·조정합니다."), 
        ("최종 결정", "관심 있는 제품에 대해 질문하고, 최종 구매 의사를 생각해 봅니다.")
    ]
    
    current_idx = 0
    if st.session_state.stage in ["explore", "summary"]: current_idx = 0
    elif st.session_state.stage in ["comparison", "product_detail"]: current_idx = 1
    elif st.session_state.stage == "purchase_decision": current_idx = 2
    
    html_str = '<div class="progress-container">'
    for i, (title, desc) in enumerate(steps):
        active_cls = "step-active" if i == current_idx else ""
        html_str += f"""
        <div class="step-item {active_cls}">
            <div class="step-header-group">
                <div class="step-circle">{i+1}</div>
                <div class="step-title">{title}</div>
            </div>
            <div class="step-desc">{desc}</div>
        </div>
        """
    html_str += "</div>"
    st.markdown(html_str, unsafe_allow_html=True)

def render_memory_sidebar():
    st.markdown(f'<div class="sidebar-header">👋 {st.session_state.nickname}님</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="memory-section-header">🧠 메모리</div>', unsafe_allow_html=True)
    
    if not st.session_state.memory:
        st.caption("대화를 통해 기준이 수집됩니다.")
    else:
        for i, mem in enumerate(st.session_state.memory):
            # 스크린샷 스타일의 회색 블록 + X 버튼
            c1, c2 = st.columns([85, 15])
            with c1:
                st.markdown(f'<div class="memory-block"><span class="memory-text">{naturalize_memory(mem)}</span></div>', unsafe_allow_html=True)
            with c2:
                # 스트림릿 버튼을 CSS로 커스텀하여 'X' 표시
                if st.button("✕", key=f"del_{i}"):
                    delete_memory(i)
                    st.rerun()
    
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    new_mem = st.text_input("기준 직접 추가", placeholder="예: 디자인 중요", label_visibility="collapsed")
    if st.button("기준 추가하기", use_container_width=True):
        if new_mem: add_memory(new_mem); st.rerun()

def recommend_products_ui(name, mems):
    products = filter_products(mems)
    st.markdown("### 🏆 추천 제품 TOP 3")
    cols = st.columns(3, gap="medium")
    for i, c in enumerate(products):
        if i >= 3: break
        with cols[i]:
            st.markdown(f"""
            <div class="product-card">
                <img src="{c['img']}" class="product-img"/>
                <div class="product-title">{c['name']}</div>
                <div class="product-price">{c['price']:,}원</div>
                <div style="font-size: 13px; color: #666; margin-bottom: 10px;">{_brief_feature_from_item(c)}</div>
                <div style="font-size:12px; color:#374151; background:#F9FAFB; padding:8px; border-radius:8px;">👉 {c['review_one']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"상세보기", key=f"detail_btn_{i}", use_container_width=True):
                st.session_state.selected_product = c
                st.session_state.stage = "product_detail"
                personalized_reason = generate_personalized_reason(c, mems, name)
                ai_say(f"**{c['name']}** 제품을 선택하셨군요.\n\n**추천 이유**\n{personalized_reason}\n\n궁금한 점(배터리, 무게 등)이 있다면 물어보세요!")
                st.rerun()
    
    if not st.session_state.comparison_hint_shown:
        ai_say("\n궁금한 제품의 상세 보기 버튼을 클릭해 궁금한 점을 질문할 수 있어요🙂")
        st.session_state.comparison_hint_shown = True

def handle_input():
    user_text = st.session_state.user_input_text
    if not user_text.strip(): return
    
    st.session_state.messages.append({"role": "user", "content": user_text})
    
    if st.session_state.stage == "explore":
        mems = extract_memory_with_gpt(user_text, st.session_state.memory)
        for m in mems: add_memory(m)
        if "추천" in user_text:
            st.session_state.stage = "comparison"
            st.session_state.messages.append({"role": "assistant", "content": "기준에 맞춰 추천 제품을 가져왔어요! 👇"})
            st.session_state.user_input_text = ""
            return
            
    response = gpt_reply(user_text)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.user_input_text = ""

# =========================================================
# 5. 메인 화면 구성
# =========================================================
def main_chat_interface():
    if st.session_state.notification_message:
        st.toast(st.session_state.notification_message, icon="✅")
        st.session_state.notification_message = ""

    # 2단 레이아웃 (좌측: 사이드바 스타일 / 우측: 메인 컨텐츠)
    col1, col2 = st.columns([3, 7], gap="large")

    # [좌측 컬럼] 닉네임, 메모리 패널
    with col1:
        render_memory_sidebar()

    # [우측 컬럼] 진행바, 대화창, 추천리스트
    with col2:
        # 상단 가로형 진행바
        render_progress_horizontal()
        
        # 대화창 박스
        st.markdown('<div class="chat-container-box">', unsafe_allow_html=True)
        chat_area = st.container()
        with chat_area:
            st.markdown('<div class="chat-messages-area">', unsafe_allow_html=True)
            for msg in st.session_state.messages:
                cls = "chat-bubble-ai" if msg['role'] == "assistant" else "chat-bubble-user"
                st.markdown(f'<div class="chat-bubble {cls}">{msg["content"]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        # 입력창 (대화창 박스 내부 하단)
        with st.form(key="chat_form", clear_on_submit=True):
            c1, c2 = st.columns([85, 15])
            with c1: st.text_input("msg", key="user_input_text", label_visibility="collapsed", placeholder="메시지를 입력하세요...")
            with c2: 
                if st.form_submit_button("전송"): handle_input(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True) # End chat-container-box

        # 추천 리스트 및 하단 버튼 (대화창 박스 아래 표시)
        if st.session_state.stage in ["comparison", "product_detail", "purchase_decision"]:
            st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
            if st.session_state.stage == "product_detail":
                c1, c2 = st.columns([1, 4])
                with c1:
                    if st.button("⬅️ 목록으로"):
                        st.session_state.stage = "comparison"
                        st.session_state.selected_product = None
                        st.rerun()
                with c2:
                    if st.button("🛒 이 제품 구매 결정하기", type="primary"):
                        st.session_state.stage = "purchase_decision"
                        st.rerun()
            
            # 추천 리스트 렌더링
            recommend_products_ui(st.session_state.nickname, st.session_state.memory)

        if st.session_state.stage == "purchase_decision":
             p = st.session_state.selected_product
             st.success(f"🎉 **{p['name']}** 구매를 결정하셨습니다!")
             st.balloons()

# [실험 준비 페이지] (기존 유지)
if st.session_state.page == "context_setting":
    st.title("🛒 쇼핑 에이전트 실험 준비")
    st.markdown("---")
    with st.container(border=True):
        st.subheader("📝 기본 정보")
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("이름 (닉네임)", placeholder="홍길동")
            st.caption("⚠️ 사전 설문에 작성한 이름과 동일하게 입력해주세요.")
        with c2:
            phone = st.text_input("전화번호 (뒷 4자리)", placeholder="1234")
            
        st.markdown("---")
        st.subheader("🛍️ 쇼핑 성향 조사")
        
        category = st.selectbox("Q1. 최근 구매한 상품 카테고리", ["패션/의류", "디지털/가전", "생활용품", "뷰티", "식품", "기타"])
        item_options = ["스마트폰", "무선 이어폰/헤드셋", "노트북/태블릿", "스마트워치", "기타 (직접 입력)"]
        selected_item = st.selectbox("Q2. 가장 최근 구매한 디지털/가전 제품", item_options)
        recent_item = st.text_input("제품명 직접 입력", placeholder="예: 공기청정기") if selected_item == "기타 (직접 입력)" else selected_item
        criteria = st.selectbox("Q3. 해당 제품 구매 시 가장 중요했던 기준", ["디자인/색상", "가격/가성비", "성능/스펙", "브랜드 인지도", "사용자 리뷰/평점"])
        fav_color = st.text_input("Q4. 평소 선호하는 색상", placeholder="예: 화이트, 무광 블랙")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("쇼핑 시작하기 (정보 저장)", type="primary", use_container_width=True):
            if name and recent_item and fav_color:
                st.session_state.nickname = name
                st.session_state.phone_number = phone
                st.session_state.page = "chat"
                
                # 과거 기억 주입
                mem1 = f"과거에 {recent_item} 구매 시 '{criteria}'을(를) 가장 중요하게 생각했음."
                mem2 = f"평소 색상은 '{fav_color}' 계열을 선호함."
                add_memory(mem1, announce=False)
                add_memory(mem2, announce=False)
                
                # 🔥 요청하신 고정 첫 멘트 적용
                fixed_greeting = f"안녕하세요 {name}님! 😊 저는 당신의 AI 쇼핑 도우미예요. 대화를 통해 고객님의 정보를 기억하며 함께 헤드셋을 찾아볼게요. 먼저, 어떤 용도로 사용하실 예정인가요?\n"
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": fixed_greeting
                })
                st.rerun()
            else:
                st.warning("필수 정보를 모두 입력해주세요.")
else:
    main_chat_interface()
