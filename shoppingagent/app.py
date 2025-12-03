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
    ss.setdefault("recommended_products", [])

ss_init()

st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

# =========================================================
# 2. CSS 스타일
# =========================================================
st.markdown("""
<style>
    /* 기본 설정 */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 2rem; max-width: 1200px !important;}

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
    div[data-testid="stBlinkContainer"] button {
        background-color: #ffffff !important;
        color: #2563EB !important;
        border: 1px solid #E5E7EB !important;
        padding: 2px 8px !important;
        min-height: 0px !important;
        height: auto !important;
        margin: 0 !important;
    }
    div[data-testid="stBlinkContainer"] button:hover {
        background-color: #EFF6FF !important;
        border-color: #2563EB !important;
    }

    /* 🟢 시나리오 박스 */
    .scenario-box {
        background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 12px;
        padding: 16px 20px; margin-bottom: 20px; color: #0369A1; font-size: 15px;
    }

    /* 🟢 진행바 (가로 배열 + 설명 포함) */
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

    /* 🟢 채팅창 스타일 */
    .chat-display-area {
        height: 450px; overflow-y: auto; padding: 20px; background: #FFFFFF;
        border: 1px solid #E5E7EB; border-radius: 16px; margin-bottom: 20px;
        display: flex; flex-direction: column;
    }
    .chat-bubble { padding: 12px 16px; border-radius: 16px; margin-bottom: 10px; max-width: 85%; line-height: 1.5; }
    .chat-bubble-user { background: #E0E7FF; align-self: flex-end; margin-left: auto; color: #111; border-top-right-radius: 2px; }
    .chat-bubble-ai { background: #F3F4F6; align-self: flex-start; margin-right: auto; color: #111; border-top-left-radius: 2px; }

    /* 좌측 메모리 패널 스타일 */
    .memory-section-header {
        font-size: 20px; font-weight: 800; margin-top: 0px; margin-bottom: 12px; color: #111; display: flex; align-items: center;
    }
    .memory-guide-box {
        background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;
        padding: 12px; font-size: 13px; color: #64748B; margin-bottom: 15px;
        line-height: 1.4;
    }
    .memory-block {
        background: #F3F4F6;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 10px;
        display: flex; justify-content: space-between; align-items: center;
        font-size: 14px; color: #374151;
    }
    .memory-text { flex-grow: 1; margin-right: 10px; word-break: break-all; }
    
    /* 팁 박스 */
    .tip-box {
        background: #FFFBEB; border: 1px solid #FCD34D; border-radius: 12px;
        padding: 16px; font-size: 14px; color: #92400E; line-height: 1.5; margin-top: 20px;
    }

    /* 상품 카드 */
    .product-card {
        background: #fff; border: 1px solid #e5e7eb; border-radius: 16px;
        padding: 15px; text-align: center; height: 100%; 
        display: flex; flex-direction: column; justify-content: space-between;
        box-shadow: 0 4px 6px rgba(0,0,0,0.03);
        transition: transform 0.2s;
    }
    .product-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px rgba(0,0,0,0.08); }
    .product-img { width: 100%; height: 150px; object-fit: contain; margin-bottom: 12px; }
    .product-title { font-weight: 700; font-size: 16px; margin-bottom: 4px; }
    .product-price { color: #2563EB; font-weight: 700; margin-bottom: 10px; }
    
    /* 첫 페이지 안내 문구 */
    .warning-text {
        font-size: 13px; color: #DC2626; background: #FEF2F2; 
        padding: 10px; border-radius: 6px; margin-top: 4px; margin-bottom: 12px;
        border: 1px solid #FECACA;
    }
    .info-text {
        font-size: 14px; color: #374151; background: #F3F4F6;
        padding: 15px; border-radius: 8px; margin-bottom: 30px;
        border-left: 4px solid #2563EB; line-height: 1.6;
    }
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
        m1 = re.search(r"(\d+)\s*만\s*원", m)
        if m1: return int(m1.group(1)) * 10000
        m2 = re.search(r"(\d{3,})\s*원", m.replace(",", ""))
        if m2: return int(m2.group(1))
    return None

def ai_say(msg):
    st.session_state.messages.append({"role": "assistant", "content": msg})

def user_say(msg):
    st.session_state.messages.append({"role": "user", "content": msg})

def detect_priority(mem_list):
    if not mem_list: return None
    for m in mem_list:
        if "(가장 중요)" in m:
            m_low = m.lower()
            if any(k in m_low for k in ["디자인", "스타일"]): return "디자인/스타일"
            if any(k in m_low for k in ["음질", "소리"]): return "음질"
            if any(k in m_low for k in ["착용감", "편안"]): return "착용감"
            if any(k in m_low for k in ["노이즈", "캔슬링"]): return "노이즈캔슬링"
            if any(k in m_low for k in ["가격", "예산", "가성비"]): return "가격/예산"
            return "기타"
    return None

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

# =========================================================
# 5. 추천 및 규칙 로직 (필터링, 스코어링)
# =========================================================
def filter_products(mems, is_reroll=False):
    mem_text = " ".join(mems)
    budget_val = extract_budget(mems)
    priority = detect_priority(mems)
    
    previously_rec = [p["name"] for p in st.session_state.recommended_products]

    def score(c):
        s = c["rating"] * 2
        # 1. 예산
        if budget_val:
            if c["price"] > budget_val * 1.5: return -999
            if c["price"] <= budget_val: s += 10
            elif c["price"] <= budget_val * 1.2: s += 5
            else: s -= 5
        # 2. 최우선 기준
        if priority == "디자인/스타일" and "디자인" in " ".join(c["tags"]): s += 15
        if priority == "음질" and "음질" in " ".join(c["tags"]): s += 15
        if priority == "착용감" and "착용감" in " ".join(c["tags"]): s += 15
        if priority == "노이즈캔슬링" and "노이즈캔슬링" in " ".join(c["tags"]): s += 15
        # 3. 키워드 매칭
        if "가벼움" in mem_text and "가벼움" in " ".join(c["tags"]): s += 5
        if "배터리" in mem_text and "배터리" in " ".join(c["tags"]): s += 5
        # 4. 색상 매칭
        preferred_color = None
        for m in mems:
            if "색상" in m:
                if "화이트" in m: preferred_color = "화이트"
                elif "블랙" in m: preferred_color = "블랙"
        if preferred_color:
            if preferred_color in c["color"]: s += 10
            else: s -= 5
        # 5. 재추천 패널티
        if c["name"] in previously_rec: s -= 10 if is_reroll else 0
        return s

    ranked = sorted(CATALOG, key=score, reverse=True)
    final = ranked[:3]
    for p in final:
        if p["name"] not in previously_rec:
            st.session_state.recommended_products.append(p)
    return final

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

# =========================================================
# 6. GPT 및 메모리 관련 함수
# =========================================================
SYSTEM_PROMPT = r"""
너는 'AI 쇼핑 도우미'이며 사용자의 블루투스 헤드셋 기준을 파악해 추천을 돕는 역할을 한다.
[역할 규칙]
- 최우선 규칙: 메모리에 이미 저장된 기준(특히 용도, 상황, 기능)은 절대 다시 물어보지 않고 바로 다음 단계의 구체적인 질문으로 전환한다.
- 새로운 기준이 등장하면 "메모리에 추가하면 좋겠다"라고 자연스럽게 제안한다.
- 메모리에 실제 저장될 경우(제어창에), 이 기준을 기억해둘게요" 혹은 "이번 쇼핑에서는 해당 내용을 고려하지 않을게요"라고 표현을 먼저 제시한다.
- 사용자가 모호하게 말하면 부드럽게 구체적으로 다시 물어본다.
- 사용자는 블루투스 헤드셋을 구매하려고 한다. 이어폰이나 인이어 타입에 대한 질문은 하지 않는다.

[대화 흐름 규칙]
- 1단계: 초기 대화에서는 사용자가 사전에 입력한 정보(중요 기준, 선호 색상)를 바탕으로 사용자 취향을 파악한다.
- 2단계: 구매 목표인 블루투스 헤드셋 기준을 순서대로 질문한다. 
- 질문 순서는 고정이 아니다. **사용자의 (가장 중요) 기준을 최우선으로 다룬다.**
- 즉, 사용자의 최우선 기준이 ‘디자인/스타일’이면 기능이나 음질 질문을 먼저 하지 말고 디자인 취향·선호 색상 같은 **관련 세부 질문을 우선한다.**
- 반대로 최우선 기준이 ‘예산’이면 기능·디자인 질문보다 예산 확인을 먼저 한다.
- “최우선 기준”이 없을 때에만 아래의 기본 순서를 따른다:
  용도/상황 → 기능(음질) → 착용감 → 배터리 → 디자인/스타일 → 색상 → 예산
- 이미 메모리에 있거나 이미 물어본 항목들(용도, 상황, 기능 등)은 절대 다시 묻지 않고 다음 질문으로 넘어간다.
- 추천 단계로 넘어가기 전에 반드시 예산을 확인한다.
- (중요) 메모리가 6개 이상이면 "지금까지 기준을 정리해드릴까요?"라고 추천하기 버튼을 제공하는 단계로 넘어간다.
- 메모리 기입할 때, 사용자의 발화를 그대로 기입하지 않고, 메모리 양식에 맞게 바꾼다.
- 추천 요청을 받으면 개인화된 이유가 포함된 리스트 형태로 응답한다.
- 절대로 중복된 질문을 던지지 않는다.
- 사용자가 특정 상품 번호를 물어보면 그 제품의 특징, 장단점, 리뷰 요약 등을 제공하고, 사용자의 기준을 반영해 개인화된 설명을 덧붙인다.

[메모리 활용]
- 메모리에 저장된 기준을 항상 반영해 대화를 이어간다.
- 메모리와 사용자의 최신 발언이 충돌하면 
  "기존에 ~라고 하셨는데, 기준을 바꾸실까요?"라고 정중히 확인한다.

[출력 규칙]
- 한 번에 너무 많은 질문을 하지 않고 자연스럽게 한두 개씩 묻는다.
- 중복 질문은 피하며 꼭 필요한 경우 "다시 한번만 확인할게요"라고 말한다.
- 전체 톤은 부드러운 존댓말을 유지한다.
"""

def extract_memory_with_gpt(user_input, memory_text):
    prompt = f"""
    당신은 '헤드셋 쇼핑 기준 요약 AI'입니다.
    사용자가 방금 말한 문장: "{user_input}"
    현재까지 저장된 기준: {memory_text if memory_text else "(없음)"}
    위 발화에서 '추가해야 할 쇼핑 기준'이 있으면 아래 JSON 형태로만 출력하세요:
    {{ "memories": ["문장1", "문장2"] }}
    반드시 지켜야 하는 규칙:
    - 기준은 반드시 '헤드셋 구매 기준'으로 변환해서 정리한다.
    - 브랜드 언급 → "선호하는 브랜드는 ~ 쪽이에요."
    - 착용감/귀 아픔/편안 → "착용감이 편한 제품을 선호하고 있어요."
    - 음악/노래/감상 → "주로 음악 감상 용도로 사용할 예정이에요."
    - 출퇴근 → "출퇴근 시 사용할 용도예요."
    - 예쁜 → "디자인/스타일을 중요하게 생각해요."
    - 색상 언급 → "색상은 ~ 계열을 선호해요."
    - 노이즈 → "노이즈캔슬링 기능을 고려하고 있어요."
    - 예산 N만원 → "예산은 약 N만 원 이내로 생각하고 있어요."
    기준이 전혀 없으면 memories는 빈 배열로만 출력하세요.
    """
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}],
            temperature=0.0
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
        4. 예산 이야기는 사용자가 직접 가격/예산을 물어본 경우에만 간단히 언급하세요.
        5. 기능/색상/음질/착용감 질문에는 가격/예산 이야기를 절대 꺼내지 마세요.
        6. 답변 후 마지막에 '추가 질문' 한 문장만 자연스럽게 붙이세요.
        """
    else:
        system_prompt = SYSTEM_PROMPT + f"\n\n[기억된 기준]\n{memories}"

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}],
            temperature=0.5
        )
        return res.choices[0].message.content
    except: return "잠시 연결에 문제가 생겼어요."

# =========================================================
# 7. UI 렌더링 함수들
# =========================================================
def render_scenario():
    st.markdown("""
    <div class="scenario-box">
        <b>💡 시나리오 가이드</b><br>
        당신은 <b>헤드셋</b>을 찾고 있습니다. AI에게 원하는 가격, 색상, 기능을 자유롭게 말해보세요. 
        AI가 대화 내용을 <b>'메모리'</b>에 저장하고 딱 맞는 제품을 추천해줍니다.
    </div>
    """, unsafe_allow_html=True)

def render_step_header():
    stage = st.session_state.stage
    # 단계 매핑
    if stage in ["explore", "summary"]:
        step_num = 1; title = "선호 조건 탐색"; desc = "최근 구매 제품과 쇼핑 취향을 기반으로 조건을 알려주세요."
    elif stage in ["comparison", "product_detail"]:
        step_num = 2; title = "후보 비교"; desc = "AI가 정리한 기준을 바탕으로 추천 후보를 비교합니다."
    else:
        step_num = 3; title = "최종 결정"; desc = "관심 제품의 궁금한 점을 확인한 뒤 최종 선택을 진행합니다."

    # 프로그레스 바 HTML (가로형 + 설명 포함)
    html_str = '<div class="progress-container">'
    steps = [
        ("탐색", "취향 및 조건 분석"), 
        ("비교", "제품 추천 및 비교"), 
        ("구매결정", "상세 확인 및 선택")
    ]
    for i, (t, d) in enumerate(steps):
        active_cls = "step-active" if (i+1) == step_num else ""
        html_str += f"""
        <div class="step-item {active_cls}">
            <div class="step-header-group">
                <div class="step-circle">{i+1}</div>
                <div class="step-title">{t}</div>
            </div>
            <div class="step-desc">{d}</div>
        </div>
        """
    html_str += "</div>"
    st.markdown(html_str, unsafe_allow_html=True)

def render_memory_sidebar():
    st.markdown('<div class="memory-section-header">🛠 메모리 제어창</div>', unsafe_allow_html=True)
    st.markdown('<div class="memory-guide-box">메모리 추가, 삭제 모두 가능합니다.</div>', unsafe_allow_html=True)
    
    if not st.session_state.memory:
        st.caption("대화를 통해 기준이 수집됩니다.")
    else:
        for i, mem in enumerate(st.session_state.memory):
            c1, c2 = st.columns([85, 15])
            with c1: st.markdown(f'<div class="memory-item-text">{naturalize_memory(mem)}</div>', unsafe_allow_html=True)
            with c2: 
                if st.button("✕", key=f"del_{i}"): delete_memory(i); st.rerun()
    
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
                <img src="{c['img']}" class="product-image"/>
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
        memory_text = "\n".join(st.session_state.memory)
        mems = extract_memory_with_gpt(user_text, memory_text)
        for m in mems: add_memory(m)
        
        if len(st.session_state.memory) >= 6:
             st.session_state.notification_message = "💡 충분한 기준이 모였습니다. 이제 추천을 받아보세요!"

        if "추천" in user_text:
            st.session_state.stage = "comparison"
            st.session_state.messages.append({"role": "assistant", "content": "기준에 맞춰 추천 제품을 가져왔어요! 👇"})
            return
            
    response = gpt_reply(user_text)
    st.session_state.messages.append({"role": "assistant", "content": response})

# =========================================================
# 8. 메인 화면 구성
# =========================================================
def main_chat_interface():
    if st.session_state.notification_message:
        st.toast(st.session_state.notification_message, icon="✅")
        st.session_state.notification_message = ""

    if len(st.session_state.messages) == 0:
        ai_say(f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요. 먼저, 어떤 용도로 사용하실 예정인가요?")

    render_scenario()
    render_step_header()

    col1, col2 = st.columns([3, 7], gap="large")

    with col1:
        render_memory_sidebar()

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
                    if st.button("🛒 이 제품 구매 결정하기", type="primary"):
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

# =========================================================
# 9. 실험 준비 페이지
# =========================================================
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
