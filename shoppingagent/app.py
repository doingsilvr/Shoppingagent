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
# 2. CSS 스타일 (기존 스타일 완벽 복구 + 프로그레스바 수정)
# =========================================================
st.markdown("""
<style>
    /* 기본 설정 */
    #MainMenu, footer, header, .css-1r6q61a {visibility: hidden; display: none !important;}
    .block-container {max-width: 1180px !important; padding: 1rem 1rem 2rem 1rem; margin: auto;}
    
    /* 🔵 [버튼 스타일] 파란색(#2563EB) 통일 */
    div.stButton > button {
        background-color: #2563EB !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: background-color 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #1D4ED8 !important;
    }
    
    /* 🔵 [메모리 삭제 버튼(X)] 예외 스타일 */
    .memory-delete-btn button {
        all: unset !important;
        box-sizing: border-box !important;
        width: 26px; height: 26px;
        border-radius: 50%;
        border: 1px solid #d1d5db;
        background: #ffffff;
        display: flex !important; align-items: center !important; justify-content: center !important;
        cursor: pointer;
        font-size: 16px !important; font-weight: 700 !important; color: #6b7280 !important;
        padding: 0 !important; margin: 0 !important;
        transition: all 0.15s ease-in-out;
    }
    .memory-delete-btn button:hover {
        background: #fef2f2; border-color: #ef4444; color: #ef4444 !important; box-shadow: 0 0 3px rgba(239, 68, 68, 0.3);
    }

    /* 🟢 [복구] 시나리오 박스 */
    .scenario-box {
        background: #F0F6FF; padding: 28px 32px; border-radius: 18px; margin-bottom: 24px; line-height: 1.6;
    }

    /* 🟢 [수정됨] 진행바 (가로 배열 + 설명 포함) */
    .progress-container {
        display: flex; justify-content: space-between; margin-bottom: 30px;
        padding: 0 10px; gap: 20px;
    }
    .step-item {
        display: flex; 
        flex-direction: column; 
        align-items: flex-start; 
        flex: 1; 
        position: relative;
    }
    .step-header-group { 
        display: flex; 
        align-items: center; 
        margin-bottom: 6px; 
    }
    .step-circle {
        width: 28px; height: 28px; border-radius: 50%; background: #E5E7EB;
        color: #6B7280; display: flex; align-items: center; justify-content: center;
        font-weight: 700; margin-right: 10px; font-size: 13px; flex-shrink: 0;
    }
    .step-title { 
        font-size: 16px; font-weight: 700; color: #374151; 
    }
    .step-desc { 
        font-size: 13px; color: #6B7280; 
        padding-left: 38px; 
        line-height: 1.4; 
        max-width: 90%;
    }
    /* 활성화된 단계 스타일 */
    .step-active .step-circle { background: #2563EB; color: white; }
    .step-active .step-title { color: #2563EB; }
    .step-active .step-desc { color: #4B5563; font-weight: 500; }

    /* 🟢 [복구] 채팅창 스타일 */
    .chat-display-area {
        max-height: 620px; overflow-y: auto; display: flex; flex-direction: column;
        padding: 1rem; background: white; border-radius: 16px; border: 1px solid #e5e7eb;
        box-sizing: border-box; width: 100% !important; margin: 0 !important;
    }
    .chat-bubble {
        padding: 10px 14px; border-radius: 16px; margin-bottom: 8px; max-width: 78%;
        word-break: break-word; font-size: 15px; line-height: 1.45; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .chat-bubble-user { background: #F0F6FF; align-self: flex-end; margin-left: auto; border-top-right-radius: 4px; }
    .chat-bubble-ai { background: #F1F0F0; align-self: flex-start; margin-right: auto; border-top-left-radius: 4px; }

    /* 🟢 [복구] 메모리 패널 스타일 */
    .memory-panel-fixed {
        position: sticky; top: 1rem; height: 620px; overflow-y: auto;
        background-color: #f8fafc; border-radius: 16px; padding: 1rem; border: 1px solid #e2e8f0;
    }
    .memory-item-text {
        white-space: pre-wrap; word-wrap: break-word; font-size: 14px; padding: 0.5rem;
        border-radius: 6px; background-color: #ffffff; border: 1px solid #e5e7eb; margin-bottom: 0.5rem;
    }
    .memory-header { font-size: 18px; font-weight: 700; color: #1F2937; margin-bottom: 12px; }

    /* 🟢 [복구] 상품 카드 스타일 */
    .product-card {
        background: #ffffff !important; border: 1px solid #e5e7eb !important; border-radius: 14px !important;
        padding: 10px 8px !important; margin-bottom: 12px !important; box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
        text-align: center !important; width: 100% !important; transition: box-shadow 0.2s ease !important;
    }
    .product-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important; }
    .product-image {
        width: 100% !important; height: 160px !important; object-fit: contain !important;
        border-radius: 10px !important; margin-bottom: 12px !important;
    }
    .product-desc { font-size: 13px !important; line-height: 1.35 !important; margin-top: 6px !important; }
    
    /* 첫 페이지 안내 문구 */
    .info-card { margin-bottom: 20px !important; padding: 8px 0 !important; }
    .warning-text { font-size: 13px; color: #DC2626; background: #FEF2F2; padding: 10px; border-radius: 6px; border: 1px solid #FECACA; }
    .info-text { font-size: 14px; color: #374151; background: #F3F4F6; padding: 15px; border-radius: 8px; border-left: 4px solid #2563EB; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. 로직 및 헬퍼 함수
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

# =========================================================
# 4. 제품 카탈로그 데이터
# =========================================================
CATALOG = [
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 179000, "rating": 4.4, "reviews": 1600, "rank": 8, "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"], "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.", "color": ["블랙", "화이트", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg"},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 129000, "rating": 4.4, "reviews": 2300, "rank": 9, "tags": ["가벼움", "음질", "노이즈캔슬링", "편안함"], "review_one": "가볍고 음질이 좋다는 평이 많아요.", "color": ["블랙", "화이트", "퍼플", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png"},
    {"name": "Sony WH-CH720N", "brand": "Sony", "price": 169000, "rating": 4.5, "reviews": 2100, "rank": 6, "tags": ["노이즈캔슬링", "경량", "무난한 음질"], "review_one": "경량이라 출퇴근용으로 좋다는 후기가 많아요.", "color": ["블랙", "화이트", "블루"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-CH720N.jpg"},
    {"name": "Bose QC45", "brand": "Bose", "price": 420000, "rating": 4.7, "reviews": 2800, "rank": 2, "tags": ["가벼움", "착용감", "노이즈캔슬링", "편안함"], "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg"},
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 450000, "rating": 4.8, "reviews": 3200, "rank": 1, "tags": ["노이즈캔슬링", "음질", "착용감", "통화품질"], "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.", "color": ["핑크"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg"},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 679000, "rating": 4.6, "reviews": 1500, "rank": 3, "tags": ["브랜드", "노이즈캔슬링", "디자인", "고급"], "review_one": "깔끔한 디자인과 고급스러움으로 만족도가 높아요.", "color": ["실버", "스페이스그레이"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg"},
    {"name": "Sennheiser PXC 550-II", "brand": "Sennheiser", "price": 289000, "rating": 4.3, "reviews": 1200, "rank": 7, "tags": ["착용감", "여행", "배터리", "노이즈캔슬링"], "review_one": "여행 시 장시간 착용에도 압박감이 덜해요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sennheiser%20PXC%2055.jpeg"},
    {"name": "AKG Y600NC", "brand": "AKG", "price": 149000, "rating": 4.2, "reviews": 1800, "rank": 10, "tags": ["균형 음질", "가성비", "노이즈캔슬링"], "review_one": "가격대비 깔끔하고 균형 잡힌 사운드가 좋아요.", "color": ["블랙", "골드", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/AKG%20Y6.jpg"},
    {"name": "Microsoft Surface Headphones 2", "brand": "Microsoft", "price": 319000, "rating": 4.5, "reviews": 900, "rank": 11, "tags": ["업무", "통화품질", "디자인", "노이즈캔슬링"], "review_one": "업무용으로 완벽하며 통화 품질이 매우 깨끗합니다.", "color": ["화이트", "블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Microsoft%20Surface%20Headphones%202.jpeg"},
    {"name": "Bose Noise Cancelling Headphones 700", "brand": "Bose", "price": 490000, "rating": 4.7, "reviews": 2500, "rank": 4, "tags": ["노이즈캔슬링", "배터리", "음질", "프리미엄"], "review_one": "노이즈캔슬링 성능과 음질을 모두 갖춘 최고급 프리미엄 제품.", "color": ["블랙", "화이트"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20Headphones%20700.jpg"},
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
# 4. UI 렌더링 함수
# =========================================================
def render_scenario():
    st.markdown("""
    <div class="scenario-box">
        <div style="font-size:18px; font-weight:700; color:#111827; margin-bottom:8px;">
            시나리오 설명
        </div>
        <div style="font-size:15px; color:#374151;">
            당신은 지금 AI 쇼핑 에이전트와 함께 블루투스 헤드셋을 구매하는 상황입니다.
            이제까지는 출퇴근 길에 음악을 듣는 용도로 블루투스 이어폰을 써왔지만,
            요즘 이어폰을 오래 끼고 있으니 귀가 아픈 것 같아, 좀 더 착용감이 편한 블루투스 무선 헤드셋을 구매해보고자 합니다.
            이를 위해 쇼핑을 도와주는 에이전트와 대화하며 당신에게 딱 맞는 헤드셋을 추천받아보세요.
        </div>
    </div>
    """, unsafe_allow_html=True)

# 🟢 [수정됨] 진행바 (가로 배열 + 설명 포함)
def render_progress():
    # 단계 및 설명 정의
    steps = [
        ("탐색", "취향 및 조건 분석"), 
        ("비교", "제품 추천 및 비교"), 
        ("구매결정", "상세 확인 및 선택")
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

def render_memory_panel():
    # 닉네임 대신 '메모리 제어창'으로 헤더 변경 (요청사항 반영)
    st.markdown('<div class="memory-section-header">🛠 메모리 제어창</div>', unsafe_allow_html=True)
    st.markdown('<div class="memory-guide-box">메모리 추가, 삭제 모두 가능합니다.</div>', unsafe_allow_html=True)
    
    if not st.session_state.memory:
        st.caption("대화를 통해 기준이 수집됩니다.")
    else:
        for i, mem in enumerate(st.session_state.memory):
            c1, c2 = st.columns([85, 15])
            with c1:
                st.markdown(f'<div class="memory-item-text">{naturalize_memory(mem)}</div>', unsafe_allow_html=True)
            with c2:
                # 스트림릿 버튼을 CSS 클래스로 감싸서 디자인 적용
                st.markdown('<div class="memory-delete-btn">', unsafe_allow_html=True)
                if st.button("X", key=f"del_{i}"):
                    delete_memory(i)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 20px 0; border-top: 1px solid #E5E7EB;'>", unsafe_allow_html=True)
    new_mem = st.text_input("기준 직접 추가", placeholder="예: 디자인 중요", label_visibility="collapsed")
    if st.button("➕ 기준 추가하기", use_container_width=True):
        if new_mem: add_memory(new_mem); st.rerun()

    st.markdown("""<div class="tip-box"><b>💡 대화 팁</b><br>"30만원 이하로 찾아줘", "노이즈 캔슬링은 필수야" 처럼 구체적으로 말씀해 주세요.</div>""", unsafe_allow_html=True)

def recommend_products_ui(name, mems):
    products = filter_products(mems)
    st.markdown("### 🏆 추천 제품 TOP 3")
    cols = st.columns(3, gap="medium")
    for i, c in enumerate(products):
        if i >= 3: break
        with cols[i]:
            st.markdown(f"""
            <div class="product-card">
                <h4><b>{i+1}. {c['name']}</b></h4>
                <img src="{c['img']}" class="product-image"/>
                <div><b>{c['brand']}</b></div>
                <div class="product-price">{c['price']:,}원</div>
                <div>⭐ {c['rating']:.1f}</div>
                <div>🏅 {_brief_feature_from_item(c)}</div>
                <div style="margin-top:8px; font-size:13px; color:#374151;">👉 {c['review_one']}</div>
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

    # 0) 첫 메시지 자동 생성
    if len(st.session_state.messages) == 0:
        ai_say(
            f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요. "
            "대화를 통해 고객님의 정보를 기억하며 함께 헤드셋을 찾아볼게요. "
            "먼저, 어떤 용도로 사용하실 예정인가요?"
        )

    # 1) 시나리오 박스
    render_scenario()

    # 2) 프로그레스 바 (가로형)
    render_progress()

    # 3) 레이아웃 (메모리 패널 + 대화창)
    col_mem, col_chat = st.columns([0.23, 0.77], gap="small")

    # 좌측: 메모리 패널
    with col_mem:
        render_memory_sidebar()

    # 우측: 대화창
    with col_chat:
        st.markdown("#### 💬 대화창")
        
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
            with c1: st.text_input("msg", key="user_input_text", label_visibility="collapsed", placeholder="메시지를 입력하세요...")
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
        
        category = st.selectbox("Q1. 최근 구매한 상품 카테고리는 무엇인가요?", ["패션/의류", "디지털/가전", "생활용품", "뷰티", "식품", "기타"])
        
        item_options = ["스마트폰", "무선 이어폰/헤드셋", "노트북/태블릿", "스마트워치", "기타 (직접 입력)"]
        selected_item = st.selectbox("Q2. 가장 최근 구매한 디지털/가전 제품은 무엇인가요?", item_options)
        
        if selected_item == "기타 (직접 입력)":
            recent_item = st.text_input("제품명을 직접 입력해 주세요", placeholder="예: 공기청정기")
        else:
            recent_item = selected_item
            
        criteria = st.selectbox("Q3. 해당 제품 구매 시 가장 중요하게 생각한 기준은?", ["디자인/색상", "가격/가성비", "성능/스펙", "브랜드 인지도", "사용자 리뷰/평점"])
        
        fav_color = st.text_input("Q4. 평소 쇼핑할 때 선호하는 색상은?", placeholder="예: 화이트, 무광 블랙")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("쇼핑 시작하기 (정보 저장)", type="primary", use_container_width=True):
            if name and recent_item and fav_color:
                st.session_state.nickname = name
                st.session_state.phone_number = phone
                st.session_state.page = "chat"
                
                mem1 = f"과거에 {recent_item} 구매 시 '{criteria}'을(를) 가장 중요하게 생각했음."
                mem2 = f"평소 색상은 '{fav_color}' 계열을 선호함."
                add_memory(mem1, announce=False)
                add_memory(mem2, announce=False)
                
                st.rerun()
            else:
                st.warning("필수 정보를 모두 입력해주세요.")
else:
    main_chat_interface()
