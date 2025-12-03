import re
import streamlit as st
import time
import html
import json
from openai import OpenAI

# =========================================================
# 0. 기본 설정 (가장 먼저)
# =========================================================
st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

# OpenAI 클라이언트 (API KEY 필요)
client = OpenAI()

# =========================================================
# 1. 전역 CSS 스타일 (✅ 네가 올린 최신 UI 그대로 유지)
# =========================================================
st.markdown("""
<style>
    /* 기본 설정 */
    #MainMenu, footer, header, .css-1r6q61a {visibility: hidden; display: none !important;}
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
        display: flex; justify-content: space-between; margin-bottom: 20px;
        padding: 0 4px; gap: 16px;
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
        margin-bottom: 4px; 
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
        padding: 10px 12px;
        margin-bottom: 8px;
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
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 14px !important;
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

    /* 메모리 알림(Toast) 위치 */
    .stAlert {
        position: fixed;
        top: 1rem;
        right: 1rem;
        width: 380px;
        z-index: 9999;
        margin: 0 !important;
        padding: 0.8rem !important;
        border-radius: 8px;
    }

</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. 세션 상태 초기화
# =========================================================
def ss_init():
    ss = st.session_state

    # 페이지 라우팅 기본값
    ss.setdefault("page", "context_setting")

    # 사용자 정보
    ss.setdefault("nickname", "")
    ss.setdefault("phone_number", "")
    ss.setdefault("budget", None)

    # 대화 메시지
    ss.setdefault("messages", [])

    # 메모리
    ss.setdefault("memory", [])
    ss.setdefault("just_updated_memory", False)

    # 단계(stage)
    ss.setdefault("stage", "explore")      # explore / summary / comparison / product_detail
    ss.setdefault("summary_text", "")
    ss.setdefault("detail_mode", False)

    # 추천/상세 정보 컨트롤
    ss.setdefault("current_recommendation", [])
    ss.setdefault("selected_product", None)

    # 로그용
    ss.setdefault("turn_count", 0)

    # 추가 상태값들
    ss.setdefault("final_choice", None)
    ss.setdefault("decision_turn_count", 0)
    ss.setdefault("purchase_intent_score", None)
    ss.setdefault("notification_message", "")
    ss.setdefault("product_detail_turn", 0)
    ss.setdefault("recommended_products", [])
    ss.setdefault("comparison_hint_shown", False)
    ss.setdefault("memory_changed", False)

ss_init()

# =========================================================
# 3. 유틸 함수 (조사 처리 등)
# =========================================================
def get_eul_reul(noun: str) -> str:
    """조사 '을/를' 자동 선택"""
    if not noun:
        return "을"
    last_char = noun[-1]
    if not ('\uAC00' <= last_char <= '\uD7A3'):
        return "를"
    last_char_code = ord(last_char) - 0xAC00
    jong = last_char_code % 28
    return "를" if jong == 0 else "을"

def naturalize_memory(text: str) -> str:
    """메모리 문장을 조금 더 자연스럽게 정규화"""
    t = text.strip()
    t = t.replace("노이즈 캔슬링", "노이즈캔슬링")
    is_priority = "(가장 중요)" in t
    t = t.replace("(가장 중요)", "").strip()
    t = re.sub(r'로 생각하고 있어요\.?$', '', t)
    t = re.sub(r'이에요\.?$', '', t)
    t = re.sub(r'에요\.?$', '', t)
    t = re.sub(r'다\.?$', '', t)
    t = t.replace('비싼것까진 필요없', '비싼 것 필요 없음')
    t = t.replace('필요없', '필요 없음')
    t = re.sub(r'(을|를)\s*선호$', ' 선호', t)
    t = re.sub(r'(을|를)\s*고려하고$', ' 고려', t)
    t = re.sub(r'(이|가)\s*필요$', ' 필요', t)
    t = re.sub(r'(에서)\s*들을$', '', t)
    t = t.strip()
    if is_priority:
        t = "(가장 중요) " + t
    return t

# =========================================================
# 4. 메모리 알림(Toast) 표시
# =========================================================
def render_notification():
    msg = st.session_state.notification_message
    if not msg:
        return

    st.success(msg)

    hide_js = """
        <script>
        setTimeout(function() {
            var alertBox = window.parent.document.querySelector('.stAlert');
            if(alertBox){
                alertBox.style.transition = "opacity 0.6s ease";
                alertBox.style.opacity = "0";
                setTimeout(() => alertBox.remove(), 600);
            }
        }, 7000);
        </script>
    """
    st.markdown(hide_js, unsafe_allow_html=True)
    st.session_state.notification_message = ""

# =========================================================
# 5. GPT 기반 메모리 추출
# =========================================================
def extract_memory_with_gpt(user_input, memory_text):
    """
    GPT에게 사용자 발화에서 저장할 만한 '쇼핑 기준'을 직접 뽑게 하는 함수.
    JSON 형태로 반환하여 안정적으로 파싱.
    """

    prompt = f"""
당신은 '헤드셋 쇼핑 기준 요약 AI'입니다.

사용자가 방금 말한 문장:
\"{user_input}\"

현재까지 저장된 기준:
{memory_text if memory_text else "(없음)"}

위 발화에서 '추가해야 할 쇼핑 기준'이 있으면 아래 JSON 형태로만 출력하세요:

{{
  "memories": [
      "문장1",
      "문장2"
  ]
}}

반드시 지켜야 하는 규칙:
- 기준은 반드시 '블루투스 헤드셋 구매 기준'으로 변환해서 정리한다.
- 문장을 완성된 기준 형태로 출력.
- 브랜드 언급 → "선호하는 브랜드는 ~ 쪽이에요."
- 착용감/귀 아픔/편안 → "착용감이 편한 제품을 선호하고 있어요."
- 음악/노래/감상 → "주로 음악 감상 용도로 사용할 예정이에요."
- 출퇴근 → "출퇴근 시 사용할 용도예요."
- 예쁜/예뻐 → "디자인/스타일을 중요하게 생각해요."
- 깔끔/화려 → "원하는 디자인/스타일을 중요하게 생각해요."
- 색상 언급 → "색상은 ~ 계열을 선호해요."
- 노이즈 → "노이즈캔슬링 기능을 고려하고 있어요."
- 예산 N만원 → "예산은 약 N만 원 이내로 생각하고 있어요."

기준이 전혀 없으면 memories는 빈 배열로만 출력하세요.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    try:
        data = json.loads(res.choices[0].message.content)
        return data.get("memories", [])
    except Exception:
        return []

# =========================================================
# 6. 메모리 카테고리/추가/삭제/수정
# =========================================================
def _is_color_memory(text: str) -> bool:
    t = text.replace("(가장 중요)", "")
    if "색상" in t and "선호" in t:
        return True
    color_keywords = ["화이트", "블랙", "네이비", "퍼플", "실버", "그레이", "핑크", "보라", "골드", "파스텔"]
    return any(k in t for k in color_keywords)

def add_memory(mem_text: str, announce=True):
    mem_text = mem_text.strip()
    if not mem_text:
        return
    
    mem_text = naturalize_memory(mem_text)
    mem_text_stripped = mem_text.replace("(가장 중요)", "").strip()

    # 예산 카테고리 충돌 제거
    if "예산은 약" in mem_text_stripped:
        st.session_state.memory = [m for m in st.session_state.memory if "예산" not in m]

    # 색상 카테고리 충돌 제거
    if _is_color_memory(mem_text_stripped):
        st.session_state.memory = [m for m in st.session_state.memory if not _is_color_memory(m)]

    # 디자인/스타일 기준 충돌 제거
    if any(k in mem_text_stripped for k in ["디자인", "스타일", "깔끔", "레트로", "미니멀", "화려", "세련"]):
        st.session_state.memory = [m for m in st.session_state.memory if "디자인" in m or "스타일" in m]

    # 중복/갱신 처리
    for i, m in enumerate(st.session_state.memory):
        m_stripped = m.replace("(가장 중요)", "").strip()
        if mem_text_stripped in m_stripped or m_stripped in mem_text_stripped:
            # 최우선 기준 갱신
            if "(가장 중요)" in mem_text and "(가장 중요)" not in m:
                for j, existing_m in enumerate(st.session_state.memory):
                    st.session_state.memory[j] = existing_m.replace("(가장 중요)", "").strip()
                st.session_state.memory[i] = mem_text
                st.session_state.just_updated_memory = True
                if announce and st.session_state.page != "context_setting":
                    st.session_state.notification_message = "🌟 최우선 기준이 업데이트되었어요."
                st.session_state.memory_changed = True
            return

    st.session_state.memory.append(mem_text)
    st.session_state.just_updated_memory = True

    if st.session_state.page != "context_setting" and announce:
        st.session_state.notification_message = "🧩 메모리에 새로운 기준을 추가했어요."
    st.session_state.memory_changed = True

def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.just_updated_memory = True
        if st.session_state.page != "context_setting":
            st.session_state.notification_message = "🧹 메모리에서 기준을 삭제했어요."
        st.session_state.memory_changed = True

def update_memory(idx: int, new_text: str):
    if 0 <= idx < len(st.session_state.memory):
        if "(가장 중요)" in new_text:
            for i, existing_m in enumerate(st.session_state.memory):
                st.session_state.memory[i] = existing_m.replace("(가장 중요)", "").strip()
        st.session_state.memory[idx] = new_text.strip()
        st.session_state.just_updated_memory = True
        if st.session_state.page != "context_setting":
            st.session_state.notification_message = "🔄 메모리가 업데이트되었어요."
        st.session_state.memory_changed = True

# =========================================================
# 7. 요약 / 추천 관련 유틸
# =========================================================
def extract_budget(mems):
    for m in mems:
        m1 = re.search(r"(\d+)\s*만\s*원", m)
        if m1:
            return int(m1.group(1)) * 10000
        txt = m.replace(",", "")
        m2 = re.search(r"(\d{2,7})\s*원", txt)
        if m2:
            return int(m2.group(1))
    return None

def detect_priority(mem_list):
    if not mem_list:
        return None
    for m in mem_list:
        if "(가장 중요)" not in m:
            continue
        m_low = m.lower()
        if any(k in m_low for k in ["디자인", "스타일", "깔끔", "미니멀", "레트로", "세련", "design", "style"]):
            return "디자인/스타일"
        if any(k in m_low for k in ["음질", "sound", "audio"]):
            return "음질"
        if any(k in m_low for k in ["착용감", "편안", "comfortable"]):
            return "착용감"
        if any(k in m_low for k in ["노이즈", "캔슬링"]):
            return "노이즈캔슬링"
        if any(k in m_low for k in ["배터리", "battery", "오래 쓰"]):
            return "배터리"
        if any(k in m_low for k in ["가격", "예산", "가성비", "price", "저렴", "싼", "싸게"]):
            return "가격/예산"
        if any(k in m_low for k in ["브랜드", "인지도", "유명"]):
            return "브랜드"
        return m.replace("(가장 중요)", "").strip()
    return None

def generate_personalized_reason(product, mems, name):
    reasons = []
    mem_str = " ".join(mems)

    # 기준 → 태그 매칭
    if "음질" in mem_str and ("음질" in " ".join(product['tags']) or "균형 음질" in " ".join(product['tags'])):
        reasons.append("중요하게 말씀하셨던 **음질** 만족도가 높아요!")
    if "착용감" in mem_str and any(t in " ".join(product['tags']) for t in ["편안함", "가벼움", "경량", "착용감"]):
        reasons.append("장시간 착용해도 편한 **착용감**이 강점이에요.")
    if "노이즈캔슬링" in mem_str and "노이즈캔슬링" in " ".join(product['tags']):
        reasons.append("원하셨던 **노이즈캔슬링** 성능이 우수한 제품이에요.")
    if "디자인" in mem_str or "스타일" in mem_str:
        if "디자인" in " ".join(product['tags']):
            reasons.append("선호하시는 **디자인/스타일**과 잘 맞는 제품이에요.")

    if reasons:
        reasons.append(
            f"\n또한, 제가 기억하고 있는 {name}님의 취향을 기준으로 보면 이 제품에서 만족감을 느끼실 가능성이 높아요."
        )

    if not reasons:
        return f"{name}님의 전반적인 쇼핑 취향과 잘 맞는 균형 잡힌 제품이에요."

    return "\n".join(reasons)

def generate_summary(nickname, mems):
    if not mems:
        return f"{nickname}님에 대해 제가 별도로 기억하고 있는 기준은 아직 없어요.\n대화를 나누면서 하나씩 쌓아가 볼게요."
    lines = [f"{nickname}님에 대해 제가 지금까지 기억하고 있는 헤드셋 관련 메모리는 다음과 같아요:\n"]
    for i, m in enumerate(mems, start=1):
        lines.append(f"- {naturalize_memory(m)}")
    lines.append("\n이 기준들을 바탕으로 추천 후보를 골라볼게요.")
    return "\n".join(lines)

# =========================================================
# 8. 카탈로그 (제품 리스트)
# =========================================================
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

def _brief_feature_from_item(c):
    tags_str = " ".join(c.get("tags", []))
    if "가성비" in tags_str:
        return "가성비 인기"
    if c.get("rank", 999) <= 3:
        return "이달 판매 상위"
    if "디자인" in tags_str:
        return "디자인 강점"
    return "실속형 추천"

# =========================================================
# 9. SYSTEM PROMPT (헤드셋 전용 + 메모리 기반 설명)
# =========================================================
SYSTEM_PROMPT = r"""
너는 'AI 쇼핑 도우미'이며 **항상 블루투스 헤드셋(오버이어/온이어 헤드폰)** 기준을 파악해 추천을 돕는 역할을 한다.
스마트폰, 노트북, 태블릿, 일반 전자기기 등 다른 카테고리에 대한 추천이나 질문 유도는 절대 하지 않는다.
이어폰, 인이어 타입, 유선 헤드셋도 추천하지 않는다. 대화 전 과정에서 '헤드셋'만을 전제로 생각한다.

[역할 규칙]
- 최우선 규칙: 메모리에 이미 저장된 기준(특히 용도, 상황, 기능)은 절대 다시 물어보지 않고 바로 다음 단계의 구체적인 질문으로 전환한다.
- 새로운 기준이 등장하면 "메모리에 추가하면 좋겠다"라고 자연스럽게 제안한다.
- 메모리에 실제 저장될 경우, "이 기준을 기억해둘게요" 혹은 "이번 쇼핑에서는 해당 내용을 고려하지 않을게요"라고 표현을 먼저 제시한다.
- 사용자가 모호하게 말하면 부드럽게 구체적으로 다시 물어본다.
- 사용자가 "모르겠어", "글쎄", "아직 생각 안 했어"라고 말하면 
  "그렇다면 주로 사용하는 상황에서 어떤 부분이 중요할까요?"라고 자연스럽게 되묻는다.
- 사용자는 **블루투스 헤드셋**을 구매하려고 한다. 이어폰이나 인이어 타입에 대한 질문은 하지 않는다.

[대화 흐름 규칙]
- 1단계(explore): 사용자가 사전에 입력/선택한 정보(과거 취향, 선호 색상)를 바탕으로 현재 헤드셋 쇼핑 기준을 탐색한다.
- 2단계(summary): 지금까지 기억한 메모리를 사용자에게 투명하게 정리해 보여준다.
- 3단계(comparison): 요약된 기준을 반영해 상위 몇 개의 헤드셋 후보를 제시하고, 비교를 돕는다.
- 제품 상세(product_detail): 사용자가 특정 제품을 선택하면, 그 제품 하나만 깊게 설명한다.

- 질문 순서는 고정이 아니다. **사용자의 (가장 중요) 기준을 최우선으로 다룬다.**
- 사용자의 최우선 기준이 ‘디자인/스타일’이면  
  → 기능이나 음질 질문을 먼저 하지 말고  
  → 디자인 취향·선호 색상 같은 **관련 세부 질문을 우선한다.**
- 사용자의 최우선 기준이 ‘가격/가성비’이면  
  → 기능·디자인 질문보다 예산 확인을 먼저 한다.
- “최우선 기준”이 없을 때에만 아래의 기본 순서를 따른다:
  용도/상황 → 기능(음질) → 착용감 → 배터리 → 디자인/스타일 → 색상 → 예산
- 이미 메모리에 있거나 이미 물어본 항목들(용도, 상황, 기능 등)은 절대 다시 묻지 않고 다음 질문으로 넘어간다.
- 추천 단계로 넘어가기 전에 반드시 예산을 확인한다.
- 메모리 기입할 때, 사용자의 발화를 그대로 기입하지 않고, 메모리 양식에 맞게 바꾼다.
- 추천 요청을 받으면 **"제가 기억하고 있는 ~님 메모리 기준"**이라는 표현을 써서, 메모리를 반영했다는 것을 명시한다.
- 절대로 중복된 질문을 던지지 않는다.
- 사용자가 ~가 뭐야?, ~가 중요할까? 등 답변이 아닌 질문을 던질 경우, 기준 확인을 위한 질문 대신 답변을 우선적으로 진행하며, 그 내용을 기준으로 쌓아가도록 리드한다.
- 사용자가 특정 상품 번호를 물어보면 그 제품의 특징, 장단점, 리뷰 요약 등을 제공하고, 사용자의 기준을 반영해 개인화된 설명을 덧붙인다.

[메모리 활용]
- 메모리에 저장된 기준을 항상 반영해 대화를 이어간다.
- 메모리와 사용자의 최신 발언이 충돌하면 
  "기존에 ~라고 하셨는데, 기준을 바꾸실까요? 아니면 둘 다 고려해드릴까요?"라고 정중히 확인한다.
- 답변 속에서 "제가 기억하고 있는 ~님 기준을 바탕으로 보면..." 같은 식으로, 메모리 반영을 **눈에 보이게** 표현한다.

[출력 규칙]
- 한 번에 너무 많은 질문을 하지 않고 자연스럽게 한두 개씩 묻는다.
- 중복 질문은 피하며 꼭 필요한 경우 "다시 한번만 확인할게요"라고 말한다.
- 전체 톤은 부드러운 존댓말을 유지한다.
"""

# =========================================================
# 10. 제품 상세 프롬프트
# =========================================================
def get_product_detail_prompt(product, user_input):
    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    nickname = st.session_state.nickname
    budget = extract_budget(st.session_state.memory)

    budget_line = ""
    budget_rule = ""

    if budget and st.session_state.product_detail_turn == 0:
        if product["price"] > budget:
            budget_line = f"- 사용자가 설정한 예산: 약 {budget:,}원"
            budget_rule = (
                f"4. (첫 답변에서만 적용)\n"
                f"   가격이 예산을 초과한 경우, 답변 첫 문장에 다음 문구 포함:\n"
                f"   - “예산(약 {budget:,}원)을 약간 초과하지만…”\n"
            )

    return f"""
당신은 지금 '상품 상세 정보 단계(product_detail)'에 있습니다.
이 단계에서는 사용자가 선택한 **블루투스 헤드셋 한 제품만** 명확하고 사실 기반으로 설명합니다.

[사용자 질문]
\"{user_input}\"

[선택된 제품 정보]
- 제품명: {product['name']} ({product['brand']})
- 가격: {product['price']:,}원
- 색상 옵션: {', '.join(product['color'])}
- 평점: {product['rating']:.1f}
- 주요 특징: {', '.join(product['tags'])}
- 리뷰 요약: {product['review_one']}
{budget_line}

[응답 규칙]
1. 질문에 대한 핵심 정보만 간단히 답변합니다.
2. 다른 제품과의 비교나 추천 리스트 언급은 하지 않습니다.
3. "현재 선택된 이 헤드셋은~"처럼, 항상 헤드셋 기준으로 설명합니다.
4. 탐색 질문(용도/기준 재질문)은 하지 않습니다.
{budget_rule}5. 답변 마지막 문장은 다음 중 하나로 끝냅니다:
   - "다른 부분도 더 궁금하신가요?"
   - "추가로 알고 싶은 점 있으신가요?"
   - "결정을 내리셨다면 언제든지 구매결정하기 버튼을 누르실 수 있습니다!"

위 규칙을 지키며 자연스럽고 간결한 한국어로 답변하세요.
"""

# =========================================================
# 11. GPT 응답 함수
# =========================================================
def gpt_reply(user_input: str) -> str:
    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    nickname = st.session_state.nickname

    # 1) product_detail 단계: 전용 프롬프트 사용
    if st.session_state.stage == "product_detail":
        product = st.session_state.selected_product
        if not product:
            st.session_state.stage = "explore"
            return "선택된 제품 정보가 없습니다. 다시 추천 단계로 돌아가 볼까요?"
        prompt_content = get_product_detail_prompt(product, user_input)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_content}],
            temperature=0.35,
        )
        st.session_state.product_detail_turn += 1
        return res.choices[0].message.content

    # 2) 탐색/요약/비교 단계
    stage_hint = ""

    is_design_in_memory = any(
        any(k in m for k in ["디자인", "스타일", "깔끔", "세련", "미니멀", "레트로", "예쁜", "예쁘"])
        for m in st.session_state.memory
    )
    is_color_in_memory = any("색상" in m for m in st.session_state.memory)
    memory_text_lower = memory_text.lower()
    is_usage_in_memory = any(
        k in memory_text for k in ["용도로", "운동", "게임", "출퇴근", "여행", "음악 감상", "집중"]
    )

    # 탐색 단계에서 이미 용도 있음 → 다시 묻지 말기
    if st.session_state.stage == "explore":
        if is_usage_in_memory and len(st.session_state.memory) >= 2:
            stage_hint += (
                "[필수 가이드: 사용 용도/상황은 이미 파악되었습니다. 절대 용도/상황을 재차 묻지 말고 다음 기준(기능/착용감/디자인 등)으로 넘어가세요.]\n"
            )

    # 디자인이 (가장 중요) + 아직 색상/스타일 세부정보 없음 → 이번 턴에 반드시 디자인/색상 질문만
    design_priority = is_design_in_memory and "(가장 중요)" in memory_text
    has_style_detail = any(k in memory_text for k in ["깔끔", "레트로", "미니멀", "화려", "세련"])
    has_color_detail = is_color_in_memory

    if st.session_state.stage == "explore" and design_priority and not (has_style_detail and has_color_detail):
        stage_hint += """
[디자인 최우선 규칙 – 이번 턴 필수]
- 지금 턴에는 기능/음질/배터리/예산에 대한 질문을 하지 않습니다.
- 아직 선호 색상이나 구체적인 디자인 스타일(깔끔한, 레트로 등)을 물어보지 않았다면,
  그 중 한 가지에 대해 **단 하나의 질문만** 하세요.
"""

    # 항상 헤드셋 대화라는 힌트
    stage_hint += "\n[중요] 이 대화는 항상 '블루투스 헤드셋 쇼핑'에 대한 대화입니다. 스마트폰/노트북 등 다른 기기를 언급하거나 추천하지 마세요.\n"

    prompt_content = f"""{stage_hint}

[현재까지 저장된 쇼핑 메모리]
{memory_text if memory_text else "아직 저장된 메모리가 없습니다."}

[사용자 발화]
{user_input}

위 정보를 참고해, 블루투스 헤드셋 쇼핑 도우미로서 다음 말을 한국어 존댓말로 자연스럽게 이어가세요.
특히, 메모리를 활용할 수 있을 때는
"제가 기억하고 있는 {nickname}님의 기준을 바탕으로 보면..." 같은 표현을 한 번 이상 포함해 주세요.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content},
        ],
        temperature=0.45,
    )
    return res.choices[0].message.content

# =========================================================
# 12. 로그 유틸
# =========================================================
def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})

def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})

# =========================================================
# 13. 추천 섹션 UI + 필터링
# =========================================================
def filter_products(mems, is_reroll=False):
    mem = " ".join(mems)
    budget = extract_budget(mems)
    priority = detect_priority(mems)
    previously_recommended_names = [p["name"] for p in st.session_state.recommended_products]

    def score(c):
        s = c["rating"]
        # (1) 예산
        if budget:
            if c["price"] > budget * 1.5:
                return -9999
            if priority == "가격/예산":
                if c["price"] <= budget:
                    s += 8
                elif c["price"] <= budget * 1.2:
                    s += 3
                else:
                    s -= 8
            else:
                if c["price"] <= budget:
                    s += 5
                elif c["price"] <= budget * 1.2:
                    s += 1
                else:
                    s -= 6

        # (2) 최우선 기준
        if priority == "디자인/스타일" and "디자인" in " ".join(c["tags"]):
            s += 8
        if priority == "음질" and ("균형 음질" in " ".join(c["tags"]) or "음질" in " ".join(c["tags"])):
            s += 8
        if priority == "착용감" and any(t in c["tags"] for t in ["편안함", "가벼움", "경량", "착용감"]):
            s += 8
        if priority == "노이즈캔슬링" and any("노이즈캔슬링" in t or "노캔" in t for t in c["tags"]):
            s += 8

        # (2-1) 디자인/스타일 + 색상
        if priority == "디자인/스타일":
            preferred_color = None
            for m_ in mems:
                if "색상" in m_:
                    preferred_color = (
                        m_.replace("색상은", "")
                          .replace("선호해요", "")
                          .replace("(가장 중요)", "")
                          .strip()
                    ).lower()
                    break
            if preferred_color:
                if any(preferred_color in col.lower() for col in c["color"]):
                    s += 12
                else:
                    s -= 12

        # (3) 색상 일반 선호
        preferred_color_match = re.search(r"색상은\s*([^계열]+)", mem)
        if preferred_color_match:
            pc = preferred_color_match.group(1).strip().lower()
            if any(pc in col.lower() for col in c["color"]):
                s += 7
            else:
                s -= 7

        # (4) 태그 기반 가점
        if "노이즈캔슬링" in mem and "노이즈캔슬링" in " ".join(c["tags"]):
            s += 2
        if ("가벼움" in mem or "경량" in mem) and ("가벼움" in " ".join(c["tags"]) or "경량" in " ".join(c["tags"])):
            s += 3
        if ("디자인" in mem or "스타일" in mem) and ("디자인" in " ".join(c["tags"])):
            s += 2

        # (5) 랭킹
        s += max(0, 10 - c["rank"])

        # (6) 재추천 페널티
        if c["name"] in previously_recommended_names:
            s -= 10 if is_reroll else 5
        return s

    cands = sorted(CATALOG, key=score, reverse=True)
    final = cands[:3]
    st.session_state.current_recommendation = final
    for p in final:
        if p["name"] not in previously_recommended_names:
            st.session_state.recommended_products.append(p)
    return final

def recommend_products(name, mems, is_reroll=False):
    products = filter_products(mems, is_reroll)
    budget = extract_budget(mems)

    if st.session_state.stage == "comparison":
        st.session_state.current_recommendation = products

    st.markdown("#### 🎧 추천 후보 리스트")
    st.markdown("지금까지 제가 기억하고 있는 기준을 반영해서 고른 상위 3개 제품이에요. 궁금한 제품에 대해 **상세 정보 보기** 버튼을 눌러 계속 질문해 주세요.\n")

    cols = st.columns(3, gap="small")

    for i, c in enumerate(products[:3]):
        one_line_reason = f"👉 {c['review_one']}"
        with cols[i]:
            st.markdown(
                f"""
                <div class="product-card">
                    <div>
                        <div class="product-title">{i+1}. {c['name']}</div>
                        <img src="{c['img']}" class="product-img"/>
                        <div><b>{c['brand']}</b></div>
                        <div class="product-price">약 {c['price']:,}원</div>
                        <div>⭐ 평점: {c['rating']:.1f} / 5.0</div>
                        <div>🏅 특징: {_brief_feature_from_item(c)}</div>
                        <div style="margin-top:8px; font-size:13px; color:#374151;">
                            {one_line_reason}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("상세 정보 보기", key=f"detail_btn_{i}", use_container_width=True):
                st.session_state.selected_product = c
                st.session_state.stage = "product_detail"
                st.session_state.product_detail_turn = 0
                reply = gpt_reply(f"{i+1}번 제품 상세가 궁금해요.")
                ai_say(reply)
                st.rerun()

    if not st.session_state.comparison_hint_shown:
        ai_say("\n궁금한 제품의 번호를 말씀하시거나, 상세 보기 버튼을 눌러 더 물어보실 수 있어요 🙂")
        st.session_state.comparison_hint_shown = True

# =========================================================
# 14. 단계 전환 함수 (요약/비교)
# =========================================================
def summary_step():
    st.session_state.summary_text = generate_summary(
        st.session_state.nickname,
        st.session_state.memory
    )

def comparison_step(is_reroll=False):
    recommend_products(st.session_state.nickname, st.session_state.memory, is_reroll)

# =========================================================
# 15. 사용자 입력 처리
# =========================================================
def handle_user_input(user_input: str):
    user_input = user_input.strip()
    if not user_input:
        return

    # 0) product_detail 단계는 바로 상세 답변
    if st.session_state.stage == "product_detail":
        reply = gpt_reply(user_input)
        ai_say(reply)
        st.rerun()
        return

    # ============================================
    # 1) 메모리 추출 (질문처럼 보이면 저장 X)
    # ============================================
    lower_input = user_input.lower()
    is_question_like = (
        user_input.endswith("??")
        or ("뭐야" in lower_input)
        or ("뭔데" in lower_input)
        or ("알려" in lower_input)
        or ("뜻" in lower_input)
    )

    mems = None
    if not is_question_like:
        memory_text = "\n".join(st.session_state.memory)
        mems = extract_memory_with_gpt(user_input, memory_text)

    # 1-1) 예산 정규식 인식 (GPT가 못 잡아도 강제 저장)
    budget_match = re.search(r"(\d+)\s*만\s*원?", user_input.replace(" ", ""))
    if budget_match:
        price = budget_match.group(1)
        budget_mem = f"예산은 약 {price}만 원 이내로 생각하고 있어요."
        if not any("예산" in m for m in st.session_state.memory):
            if mems is None:
                mems = []
            mems.append(budget_mem)

    if mems:
        for m in mems:
            add_memory(m, announce=True)

    # =========================================================
    # 2) 비교 단계에서 "1번/2번/3번" 선택
    # =========================================================
    product_re = re.search(r"([1-3]|첫\s*번|두\s*번|세\s*번).*(궁금|골라|선택)", user_input)
    if product_re and st.session_state.stage == "comparison":
        match = product_re.group(1).lower()
        if "첫" in match or "1" in match:
            idx = 0
        elif "두" in match or "2" in match:
            idx = 1
        elif "세" in match or "3" in match:
            idx = 2
        else:
            idx = -1

        if 0 <= idx < len(st.session_state.current_recommendation):
            st.session_state.selected_product = st.session_state.current_recommendation[idx]
            st.session_state.stage = "product_detail"
            st.session_state.product_detail_turn = 0
            reply = gpt_reply(user_input)
            ai_say(reply)
            st.rerun()
            return
        else:
            ai_say("죄송해요, 후보 번호는 1번, 2번, 3번 중에서 골라주세요.")
            st.rerun()
            return

    # =========================================================
    # 3) 다시 추천 요청
    # =========================================================
    if any(k in user_input for k in ["다시 추천", "다른 상품", "다른 제품"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say("추천을 다시 받기 전에 **예산/가격대**를 먼저 알려주실까요?")
            st.session_state.stage = "explore"
            st.rerun()
            return
        st.session_state.stage = "comparison"
        comparison_step(is_reroll=True)
        return

    # =========================================================
    # 4) 탐색 단계 종료 조건 (요약/비교로 이어지게)
    # =========================================================
    if st.session_state.stage == "explore":
        mem_count = len(st.session_state.memory)
        has_budget = extract_budget(st.session_state.memory) is not None

        # 기준이 어느 정도 모였는데 예산 없음 → 예산 요청
        if mem_count >= 6 and not has_budget:
            ai_say(
                "네, 이제 어느 정도 기준을 파악한 것 같아요. "
                "이제 **예산/가격대**를 알려주시면 추천 단계로 넘어가 볼게요!"
            )
            st.rerun()
            return

        # 기준 6개 이상 + 예산 있음 → 요약 단계로 전환
        if mem_count >= 7 and has_budget:
            ai_say("지금까지 말씀해주신 기준을 한 번 정리해보고, 그 기준에 맞는 헤드셋을 추천해볼게요.")
            st.session_state.stage = "summary"
            summary_step()
            st.rerun()
            return

    # =========================================================
    # 5) 명시적 추천 요청
    # =========================================================
    if any(k in user_input for k in ["추천해줘", "추천 좀", "골라줘", "추천 부탁", "추천", "후보 보여줘"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say(
                "추천 전에 **예산**을 먼저 알려주세요! "
                "예: 10만 원 이내 / 20만 원 전후처럼 말씀해주시면 돼요."
            )
            st.session_state.stage = "explore"
            st.rerun()
            return
        ai_say("알겠습니다. 지금까지의 메모리를 정리한 뒤, 그 기준에 맞는 헤드셋 후보들을 보여드릴게요.")
        st.session_state.stage = "summary"
        summary_step()
        st.rerun()
        return

    # 6) “없어 / 그만 / 끝 / 충분” → 기준 마무리
    if any(k in user_input for k in ["없어", "그만", "끝", "충분"]):
        if st.session_state.stage == "comparison":
            ai_say("알겠습니다! 다른 부분이 궁금하시면 언제든 말씀해주세요 🙂")
            st.rerun()
            return
        if extract_budget(st.session_state.memory) is None:
            ai_say("추천 전 **예산**을 알려주세요! 예: 10만 원 이내, 20만 원 전후 등으로 말씀해주시면 돼요.")
            st.session_state.stage = "explore"
            st.rerun()
            return
        ai_say("알겠습니다. 지금까지의 기준을 바탕으로 정리한 뒤 추천을 이어가볼게요.")
        st.session_state.stage = "summary"
        summary_step()
        st.rerun()
        return

    # =========================================================
    # 7) 단계별 일반 처리
    # =========================================================
    if st.session_state.stage == "explore":
        reply = gpt_reply(user_input)
        ai_say(reply)
        st.rerun()
        return

    if st.session_state.stage == "summary":
        ai_say("정리된 기준을 확인해보시고, 아래 버튼으로 추천을 받아보셔도 좋아요 🙂")
        st.rerun()
        return

    if st.session_state.stage == "comparison":
        reply = gpt_reply(user_input)
        ai_say(reply)
        st.rerun()
        return

    # 기타 단계 fallback
    reply = gpt_reply(user_input)
    ai_say(reply)
    st.rerun()
    return

# =========================================================
# 16. 메모리 패널 UI (좌측)
# =========================================================
def render_progress_header():
    stage_to_step = {
        "explore": 1,
        "summary": 2,
        "comparison": 2,
        "product_detail": 3
    }
    current = stage_to_step.get(st.session_state.stage, 1)

    steps = [
        ("구매 기준 탐색", "헤드셋을 고를 때 무엇이 중요한지 함께 정리합니다."),
        ("후보 비교", "기억해 둔 기준을 반영해 추천 후보를 비교합니다."),
        ("최종 결정", "선택한 제품의 상세 정보를 확인하고 결정합니다.")
    ]

    html_blocks = ['<div class="progress-container">']
    for i, (title, desc) in enumerate(steps, start=1):
        active_class = "step-item step-active" if i == current else "step-item"
        html_blocks.append(
            f"""
            <div class="{active_class}">
                <div class="step-header-group">
                    <div class="step-circle">{i}</div>
                    <div class="step-title">{title}</div>
                </div>
                <div class="step-desc">{desc}</div>
            </div>
            """
        )
    html_blocks.append("</div>")
    st.markdown("\n".join(html_blocks), unsafe_allow_html=True)

def top_memory_panel():
    st.markdown('<div class="memory-section-header">🧠 메모리</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="memory-guide-box">
            지금까지 제가 파악한 쇼핑 메모리가 이곳에 정리됩니다.<br>
            실제 취향과 다르거나, 이번 헤드셋에는 적용하고 싶지 않은 기준은 X 버튼을 눌러 언제든 삭제하실 수 있어요.
        </div>
        """,
        unsafe_allow_html=True
    )

    if len(st.session_state.memory) == 0:
        st.caption("아직 파악된 정보가 없습니다. 대화 중에 기준이 차곡차곡 쌓일 거예요.")
    else:
        for i, item in enumerate(st.session_state.memory):
            display_text = naturalize_memory(item)
            cols = st.columns([8, 1])
            with cols[0]:
                st.markdown(
                    f'<div class="memory-block"><div class="memory-text">{display_text}</div>',
                    unsafe_allow_html=True
                )
            with cols[1]:
                if st.button("X", key=f"del_{i}"):
                    delete_memory(i)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="tip-box">
            💡 <b>Tip.</b> 이번 헤드셋에는 고려하고 싶지 않은 기준이 있다면<br>
            먼저 삭제한 뒤, 새 기준을 대화로 추가해 보셔도 좋아요.
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# 17. 시나리오 박스
# =========================================================
def render_scenario_box():
    st.markdown(
        """
        <div class="scenario-box">
            <b>시나리오</b><br>
            당신은 지금 AI 쇼핑 에이전트와 함께 <b>블루투스 헤드셋</b>을 구매하는 상황입니다.<br>
            지금까지는 출퇴근 길에 음악을 듣는 용도로 블루투스 이어폰을 써왔지만,<br>
            요즘 이어폰을 오래 끼고 있으니 귀가 아픈 것 같아, 좀 더 착용감이 편한 블루투스 무선 헤드셋을 구매해보고자 합니다.<br>
            이 에이전트는 <b>당신의 취향 메모리</b>를 바탕으로 대화를 이어가며, 취향이 달라졌다면 수정하도록 도와줍니다.
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# 18. 메인 대화 UI
# =========================================================
def chat_interface():
    render_notification()

    # 첫 진입 시 인사 + 기본 안내
    if len(st.session_state.messages) == 0:
        base_msg = (
            f"안녕하세요 {st.session_state.nickname}님! 😊 저는 블루투스 헤드셋 쇼핑을 도와드리는 AI 도우미예요.\n\n"
            "앞에서 선택해 주신 내용을 바탕으로 {0}님의 기본 취향 메모리를 만들어 두었고, "
            "대화를 나누면서 실제와 다르면 언제든지 수정하실 수 있어요.\n\n"
            "먼저, 이번에 구매하실 헤드셋은 주로 어떤 상황에서 사용하실 예정인지 말씀해 주실 수 있을까요?"
        ).format(st.session_state.nickname)
        ai_say(base_msg)

    # 레이아웃: 좌측 메모리 / 우측 진행+채팅
    col_left, col_right = st.columns([0.33, 0.67], gap="large")

    with col_left:
        render_progress_header()
        top_memory_panel()

    with col_right:
        render_scenario_box()

        st.markdown("#### 💬 대화창")

        chat_html = '<div class="chat-display-area">'
        for msg in st.session_state.messages:
            safe = html.escape(msg["content"])
            if msg["role"] == "assistant":
                chat_html += f'<div class="chat-bubble chat-bubble-ai">{safe}</div>'
            else:
                chat_html += f'<div class="chat-bubble chat-bubble-user">{safe}</div>'

        # summary 단계에서는 정리된 메모리 요약도 말풍선으로 노출
        if st.session_state.stage == "summary":
            safe_summary = html.escape(st.session_state.summary_text)
            chat_html += f'<div class="chat-bubble chat-bubble-ai">{safe_summary}</div>'

        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)

        # summary 단계에서 추천 버튼
        if st.session_state.stage == "summary":
            if st.button("🔍 메모리 기반 추천 받아보기", key="go_reco_button", use_container_width=True):
                st.session_state.stage = "comparison"
                st.rerun()

        # comparison 단계에서 추천 리스트 보여주기
        if st.session_state.stage == "comparison":
            comparison_step()

        # 입력 폼
        with st.form(key="chat_form_main", clear_on_submit=True):
            user_text = st.text_area(
                "",
                placeholder="원하는 기준이나 궁금한 점을 알려주세요! (예: 노이즈캔슬링도 필요할까요?)",
                height=80,
            )
            send = st.form_submit_button("전송")
        if send and user_text.strip():
            user_say(user_text)
            handle_user_input(user_text)

# =========================================================
# 19. 실험 준비 페이지 (동적 메모리용 context_setting 재구성)
# =========================================================
def context_setting():
    st.title("🛒 쇼핑 에이전트 실험 준비")

    st.markdown(
        """
    <div class="info-text">
        이 페이지는 <b>AI 에이전트가 귀하의 과거/일반적인 쇼핑 취향을 어떻게 추론하고 기억하는지</b>를 설정하는 단계입니다.<br>
        아래 선택지들은 <u>정답을 맞추는 용도라기보다는</u>, 에이전트가 만들어낼 <b>초기 메모리 프로필</b>을 구성하는 데 사용됩니다.<br>
        이후 대화에서 실제 취향과 다르다고 느끼시면, 메모리를 직접 수정하거나 삭제하실 수 있습니다.
    </div>
    """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.subheader("📝 기본 정보")
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("이름 (닉네임)", placeholder="홍길동")
            st.markdown(
                '<div class="warning-text">⚠️ 사전 설문에 작성한 이름과 동일하게 입력해 주세요. (불일치 시 불성실 응답 간주 가능)</div>',
                unsafe_allow_html=True,
            )
        with c2:
            phone = st.text_input("전화번호 (뒷 4자리)", placeholder="1234")
            
        st.markdown("---")
        st.subheader("🧭 평소 쇼핑 취향 선택")

        # Q1. 카테고리
        category = st.selectbox(
            "Q1. 평소에 더 자주 보거나 관심 있게 보는 제품 카테고리는 무엇인가요?",
            [
                "스마트폰/태블릿",
                "노트북/PC",
                "이어폰/헤드셋",
                "생활가전(청소기/공기청정기 등)",
                "기타/특정하지 않음",
            ],
        )

        # Q2. 기준 스타일
        style_pref = st.selectbox(
            "Q2. 아래 세 가지 중, '나와 더 비슷하다'고 느껴지는 쪽은 어느 쪽인가요?",
            ["가성비가 좋은 제품", "디자인이 예쁜 제품", "성능이 가장 좋은 제품"],
        )
        
        # Q3. 색상 취향
        color_pref = st.selectbox(
            "Q3. 아래 색상 중, 실제로 온라인 쇼핑에서 더 자주 클릭해볼 것 같은 색상은?",
            ["블랙", "화이트", "파스텔톤(핑크/민트 등)", "블루/네이비"],
        )

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("쇼핑 시작하기 (초기 메모리 생성 후 진행)", type="primary", use_container_width=True):
            if not name.strip():
                st.warning("닉네임(이름)을 입력해 주세요.")
                return

            # 1) 세션에 기본 정보 저장
            st.session_state.nickname = name.strip()
            st.session_state.phone_number = phone.strip()

            # 2) 기존 메모리 초기화 후, 선택 기반 '추론 메모리' 생성
            st.session_state.memory = []

            # Q1 → 카테고리 기반 추론
            if category == "스마트폰/태블릿":
                add_memory("평소 전자기기를 살 때는 성능과 최신 스펙을 꽤 중요하게 보는 편이에요.", announce=False)
            elif category == "노트북/PC":
                add_memory("평소 전자기기를 살 때는 성능과 배터리 지속시간을 함께 중요하게 보는 편이에요.", announce=False)
            elif category == "이어폰/헤드셋":
                add_memory("평소 오디오 기기를 살 때는 휴대성과 음질을 함께 살펴보는 편이에요.", announce=False)
            elif category == "생활가전(청소기/공기청정기 등)":
                add_memory("평소에는 가성비와 실용성을 중심으로 제품을 고르는 편이에요.", announce=False)
            else:
                add_memory("상황에 맞는 기본 기능이 잘 갖춰진 제품을 선호하는 편이에요.", announce=False)

            # Q2 → 최우선 기준 (가장 중요) 추론
            if style_pref == "가성비가 좋은 제품":
                add_memory("(가장 중요) 평소에는 가격 대비 효용이 높은, 가성비 좋은 제품을 더 선호하는 편이에요.", announce=False)
            elif style_pref == "디자인이 예쁜 제품":
                add_memory("(가장 중요) 평소에는 디자인/스타일이 마음에 드는지를 가장 먼저 보는 편이에요.", announce=False)
            else:
                add_memory("(가장 중요) 평소에는 성능과 스펙이 충분히 좋은 제품을 우선으로 고려하는 편이에요.", announce=False)

            # Q3 → 색상 취향 추론
            if color_pref == "블랙":
                add_memory("색상은 블랙 계열을 자주 선택하시는 편이에요.", announce=False)
            elif color_pref == "화이트":
                add_memory("색상은 화이트처럼 밝고 깔끔한 계열을 자주 선택하시는 편이에요.", announce=False)
            elif color_pref == "파스텔톤(핑크/민트 등)":
                add_memory("색상은 파스텔톤처럼 포인트가 되는 색을 선호하시는 편이에요.", announce=False)
            else:
                add_memory("색상은 블루·네이비처럼 차분한 계열을 선호하시는 편이에요.", announce=False)

            # 3) 초기 메모리 프로필을 한 번 메시지로도 남겨둠
            summary = generate_summary(st.session_state.nickname, st.session_state.memory)
            ai_say("먼저, 선택해 주신 내용을 바탕으로 제가 기억해둘 기본 메모리를 이렇게 정리해보았어요.\n\n" + summary +
                   "\n\n이제 실제 대화를 나누면서, 취향과 다르다고 느껴지는 부분이 있으면 자유롭게 말씀해 주세요!")

            # 4) 페이지 전환
            st.session_state.page = "chat"
            st.session_state.stage = "explore"
            st.session_state.messages = []  # 인사 메시지를 chat_interface에서 다시 넣기 위해 초기화
            st.rerun()

# =========================================================
# 20. 라우팅
# =========================================================
if "page" not in st.session_state:
    st.session_state.page = "context_setting"

if st.session_state.page == "context_setting":
    context_setting()
else:
    chat_interface()


