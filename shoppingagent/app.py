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
# 2. CSS 스타일
# =========================================================
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1rem; max-width: 1200px !important;}

    /* 시나리오 박스 */
    .scenario-box {
        background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 12px;
        padding: 16px 20px; margin-bottom: 20px; color: #0369A1; font-size: 15px;
    }

    /* 진행바 */
    .step-container { display: flex; justify-content: center; margin-bottom: 30px; }
    .step-wrapper {
        display: flex; background: #FFFFFF; padding: 10px 40px;
        border-radius: 50px; border: 1px solid #E2E8F0; gap: 60px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .step-item { font-size: 15px; font-weight: 600; color: #94A3B8; display: flex; align-items: center; }
    .step-active { color: #2563EB; font-weight: 800; }
    .step-circle {
        width: 28px; height: 28px; border-radius: 50%; background: #F1F5F9;
        color: #64748B; display: flex; align-items: center; justify-content: center;
        margin-right: 10px; font-size: 13px; font-weight: 700;
    }
    .step-active .step-circle { background: #2563EB; color: white; }

    /* 메모리 패널 */
    .memory-container {
        background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px;
        padding: 20px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.03); margin-bottom: 20px;
    }
    .memory-header { font-size: 18px; font-weight: 700; color: #1F2937; margin-bottom: 12px; }
    .memory-item-style {
        background: #F3F4F6; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px;
        font-size: 14px; color: #374151; display: flex; justify-content: space-between; align-items: center;
    }

    /* 팁 박스 */
    .tip-box {
        background: #FFFBEB; border: 1px solid #FCD34D; border-radius: 12px;
        padding: 16px; font-size: 14px; color: #92400E; line-height: 1.5;
    }

    /* 채팅창 */
    .chat-display-area {
        height: 450px; overflow-y: auto; padding: 20px; background: #FFFFFF;
        border: 1px solid #E5E7EB; border-radius: 16px; margin-bottom: 20px;
        display: flex; flex-direction: column;
    }
    .chat-bubble { padding: 12px 16px; border-radius: 16px; margin-bottom: 10px; max-width: 80%; line-height: 1.5; }
    .chat-bubble-user { background: #DCF8C6; align-self: flex-end; margin-left: auto; color: #111; border-top-right-radius: 2px; }
    .chat-bubble-ai { background: #F3F4F6; align-self: flex-start; margin-right: auto; color: #111; border-top-left-radius: 2px; }

    /* 상품 카드 */
    .product-card {
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 14px !important;
        padding: 10px 8px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
        text-align: center !important;
        transition: box-shadow 0.2s ease !important;
        height: 100%;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .product-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important; }
    .product-card h4 { margin: 4px 0 8px 0 !important; font-size: 15px; font-weight: 700; }
    .product-image {
        width: 100% !important; height: 160px !important; object-fit: contain !important;
        border-radius: 10px !important; margin-bottom: 12px !important;
    }
    
    /* 경고 문구 스타일 */
    .warning-text {
        font-size: 13px; color: #DC2626; background: #FEF2F2; 
        padding: 10px; border-radius: 6px; margin-top: 4px; margin-bottom: 12px;
        border: 1px solid #FECACA;
    }
    .info-text {
        font-size: 14px; color: #374151; background: #F3F4F6;
        padding: 12px; border-radius: 8px; margin-bottom: 20px;
        border-left: 4px solid #3B82F6;
    }
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

def user_say(msg):
    st.session_state.messages.append({"role": "user", "content": msg})

# 카탈로그
CATALOG = [
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 450000, "rank": 1, "rating": 4.8, "reviews": 3200, "tags": ["노이즈캔슬링", "음질", "착용감", "최상급"], "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.", "color": ["블랙", "실버", "로즈골드"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg"},
    {"name": "Bose QC45", "brand": "Bose", "price": 389000, "rank": 2, "rating": 4.7, "reviews": 2800, "tags": ["가벼움", "착용감", "노이즈캔슬링"], "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.", "color": ["블랙", "화이트"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg"},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 769000, "rank": 3, "rating": 4.6, "reviews": 1500, "tags": ["브랜드", "디자인", "고급", "무거움"], "review_one": "깔끔한 디자인과 고급스러움으로 만족도가 높아요.", "color": ["실버", "스페이스그레이", "핑크"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg"},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 129000, "rank": 9, "rating": 4.4, "reviews": 2300, "tags": ["가성비", "배터리", "음질"], "review_one": "가성비가 훌륭하고 가볍다는 평이 많아요.", "color": ["블랙", "화이트", "블루"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png"},
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 149000, "rank": 8, "rating": 4.4, "reviews": 1600, "tags": ["가성비", "배터리", "노이즈캔슬링"], "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.", "color": ["블랙", "네이비", "화이트"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg"},
]

def filter_products(mems, is_reroll=False):
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
# 4. UI 렌더링
# =========================================================
def render_scenario():
    st.markdown("""
    <div class="scenario-box">
        <b>💡 시나리오 가이드</b><br>
        당신은 <b>헤드셋</b>을 찾고 있습니다. AI에게 원하는 가격, 색상, 기능을 자유롭게 말해보세요. 
        AI가 대화 내용을 <b>'메모리'</b>에 저장하고 딱 맞는 제품을 추천해줍니다.
    </div>
    """, unsafe_allow_html=True)

def render_progress():
    steps = ["탐색", "비교", "구매결정"]
    current_idx = 0
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
    st.markdown('<div class="memory-container">', unsafe_allow_html=True)
    st.markdown('<div class="memory-header">🧠 나의 쇼핑 기준</div>', unsafe_allow_html=True)
    
    if not st.session_state.memory:
        st.caption("대화를 통해 기준이 수집됩니다.")
    else:
        for i, mem in enumerate(st.session_state.memory):
            c1, c2 = st.columns([85, 15])
            with c1: st.markdown(f'<div class="memory-item-style">{naturalize_memory(mem)}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("✕", key=f"del_{i}"): delete_memory(i); st.rerun()
    
    st.markdown("<hr style='margin: 10px 0; opacity: 0.2;'>", unsafe_allow_html=True)
    new_mem = st.text_input("기준 직접 추가", placeholder="예: 디자인 중요", label_visibility="collapsed")
    if st.button("➕ 기준 추가하기", use_container_width=True):
        if new_mem: add_memory(new_mem); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def recommend_products_ui(name, mems):
    products = filter_products(mems)
    cols = st.columns(3, gap="small")
    for i, c in enumerate(products):
        if i >= 3: break
        with cols[i]:
            st.markdown(f"""
            <div class="product-card">
                <h4><b>{i+1}. {c['name']}</b></h4>
                <img src="{c['img']}" class="product-image"/>
                <div><b>{c['brand']}</b></div>
                <div>💰 {c['price']:,}원</div>
                <div>⭐ {c['rating']:.1f}</div>
                <div>🏅 {_brief_feature_from_item(c)}</div>
                <div style="margin-top:8px; font-size:13px; color:#374151;">👉 {c['review_one']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"후보 {i+1} 상세 정보 보기", key=f"detail_btn_{i}"):
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
# 5. 페이지 라우팅
# =========================================================
def main_chat_interface():
    if st.session_state.notification_message:
        st.toast(st.session_state.notification_message, icon="✅")
        st.session_state.notification_message = ""

    render_scenario()
    render_progress()

    col1, col2 = st.columns([3, 7], gap="large")

    with col1:
        st.markdown(f"### 👋 {st.session_state.nickname}님")
        render_memory_panel()
        st.markdown("""<div class="tip-box"><b>💡 대화 팁</b><br>"30만원 이하", "노이즈 캔슬링 필수" 처럼 구체적으로 말씀해 주세요.</div>""", unsafe_allow_html=True)

    with col2:
        chat_container = st.container()
        with chat_container:
            html_content = '<div class="chat-display-area">'
            for msg in st.session_state.messages:
                cls = "chat-bubble-ai" if msg['role'] == "assistant" else "chat-bubble-user"
                html_content += f'<div class="chat-bubble {cls}">{msg["content"]}</div>'
            html_content += '</div>'
            st.markdown(html_content, unsafe_allow_html=True)

        if st.session_state.stage in ["comparison", "product_detail", "purchase_decision"]:
            st.markdown("---")
            if st.session_state.stage == "product_detail":
                c1, c2 = st.columns([1, 4])
                with c1:
                    if st.button("⬅️ 목록"):
                        st.session_state.stage = "comparison"
                        st.session_state.selected_product = None
                        st.rerun()
                with c2:
                    if st.button("🛒 구매 결정하기", type="primary"):
                        st.session_state.stage = "purchase_decision"
                        st.rerun()
            recommend_products_ui(st.session_state.nickname, st.session_state.memory)

        if st.session_state.stage == "purchase_decision":
             p = st.session_state.selected_product
             st.success(f"🎉 **{p['name']}** 구매를 결정하셨습니다!")
             st.balloons()

        with st.form(key="chat_form", clear_on_submit=True):
            c1, c2 = st.columns([85, 15])
            with c1: st.text_input("msg", key="user_input_text", label_visibility="collapsed")
            with c2: 
                if st.form_submit_button("전송"): handle_input(); st.rerun()

# [실험 준비 페이지]
if st.session_state.page == "context_setting":
    st.title("🛒 쇼핑 에이전트 실험 준비")
    st.markdown("""
    <div class="info-text">
        이 페이지는 <b>AI 에이전트가 귀하의 과거 쇼핑 취향을 기억하는지</b> 테스트하기 위한 사전 설정 단계입니다.<br>
        평소 본인의 실제 쇼핑 습관이나, 이번 실험에서 연기할 '페르소나'의 정보를 입력해 주세요.
    </div>
    """, unsafe_allow_html=True)
    
    with st.container(border=True):
        st.subheader("📝 기본 정보")
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("이름 (닉네임)", placeholder="홍길동")
            st.markdown('<div class="warning-text">⚠️ 사전 설문에 작성한 이름과 동일하게 입력해주세요. (불일치 시 불성실 응답 간주 가능)</div>', unsafe_allow_html=True)
        with c2:
            phone = st.text_input("전화번호 (뒷 4자리)", placeholder="1234")
            
        st.markdown("---")
        st.subheader("🛍️ 쇼핑 성향 조사")
        
        # Q1. 카테고리
        category = st.selectbox("Q1. 최근 구매한 상품 카테고리는 무엇인가요?", ["패션/의류", "디지털/가전", "생활용품", "뷰티", "식품", "기타"])
        
        # Q2. 최근 디지털 제품 (객관식 + 기타)
        item_options = ["스마트폰", "무선 이어폰/헤드셋", "노트북/태블릿", "스마트워치", "기타 (직접 입력)"]
        selected_item = st.selectbox("Q2. 가장 최근 구매한 디지털/가전 제품은 무엇인가요?", item_options)
        
        if selected_item == "기타 (직접 입력)":
            recent_item = st.text_input("제품명을 직접 입력해 주세요", placeholder="예: 공기청정기")
        else:
            recent_item = selected_item
            
        # Q3. 중요 기준 (객관식)
        criteria = st.selectbox("Q3. 해당 제품 구매 시 가장 중요하게 생각한 기준은?", ["디자인/색상", "가격/가성비", "성능/스펙", "브랜드 인지도", "사용자 리뷰/평점"])
        
        # Q4. 선호 색상
        fav_color = st.text_input("Q4. 평소 쇼핑할 때 선호하는 색상은?", placeholder="예: 화이트, 무광 블랙")
        
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
                
                # 첫 인사
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"안녕하세요 {name}님! 지난번엔 **{recent_item}**을(를) 살 때 **{criteria}**을(를) 중요하게 보셨고, 평소 **{fav_color}** 색상을 좋아하신다고 기억하고 있어요.\n이번 헤드셋 쇼핑에서는 어떤 점을 중요하게 생각하시나요?"
                })
                st.rerun()
            else:
                st.warning("필수 정보를 모두 입력해주세요.")
else:
    main_chat_interface()
