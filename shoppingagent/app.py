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
    
    # 추가 세션 변수 (기존 코드 호환)
    ss.setdefault("budget", None)
    ss.setdefault("summary_text", "")
    ss.setdefault("turn_count", 0)
    ss.setdefault("final_choice", None)
    ss.setdefault("decision_turn_count", 0)
    ss.setdefault("purchase_intent_score", None)
    ss.setdefault("product_detail_turn", 0)
    ss.setdefault("recommended_products", [])
    ss.setdefault("just_updated_memory", False)

ss_init()

st.set_page_config(page_title="AI 쇼핑 에이전트 실험용", page_icon="🎧", layout="wide")

# =========================================================
# 2. CSS 스타일 (기존 UI 100% 유지 + 파란 버튼만 적용)
# =========================================================
st.markdown("""
<style>
    /* 기본 설정 숨기기 */
    #MainMenu, footer, header, .css-1r6q61a { visibility: hidden; display: none !important; }
    .block-container { max-width: 1180px !important; padding: 1rem 1rem 2rem 1rem; margin: auto; }
    .progress-box { margin-top: 0px !important; }
    .block-container div[data-testid="stVerticalBlock"] { margin-top: 0 !important; padding-top: 0 !important; }

    /* 🔵 [수정] 버튼 파란색 통일 (#1766F9) */
    div.stButton > button {
        background-color: #1766F9 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: background-color 0.2s ease;
    }
    div.stButton > button:hover { background-color: #1049B5 !important; }

    /* 타이틀 카드 */
    .title-card {
        background: white; border-radius: 16px; padding: 1.4rem 1.6rem; border: 1px solid #e5e7eb; margin-bottom: 1.5rem;
    }

    /* 대화 박스 */
    .chat-display-area {
        max-height: 620px; overflow-y: auto; display: flex; flex-direction: column;
        padding: 1rem; background: white; border-radius: 16px; border: 1px solid #e5e7eb;
        box-sizing: border-box; width: 100% !important; margin: 0 !important;
    }
    .chat-bubble {
        padding: 10px 14px; border-radius: 16px; margin-bottom: 8px; max-width: 78%;
        word-break: break-word; font-size: 15px; line-height: 1.45; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .chat-bubble-user { background: #F0F6FF; align-self: flex-end; text-align: left; margin-left: auto; border-top-right-radius: 4px; }
    .chat-bubble-ai { background: #F1F0F0; align-self: flex-start; text-align: left; margin-right: auto; border-top-left-radius: 4px; }

    /* 제품 카드 */
    .product-card {
        background: #ffffff !important; border: 1px solid #e5e7eb !important; border-radius: 14px !important;
        padding: 10px 8px !important; margin-bottom: 12px !important; box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
        text-align: center !important; width: 230px !important; transition: box-shadow 0.2s ease !important;
    }
    .product-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important; }
    .product-card h4, .product-card p, .product-card div { margin: 0 !important; padding: 4px 0 !important; }
    .product-card h4, .product-card h5 { margin: 4px 0 8px 0 !important; }
    .product-image { width: 100% !important; height: 160px !important; object-fit: cover !important; border-radius: 10px !important; margin-bottom: 12px !important; }
    .product-desc { font-size: 13px !important; line-height: 1.35 !important; margin-top: 6px !important; }

    /* 메모리 패널 */
    .memory-panel-fixed {
        position: sticky; top: 1rem; height: 620px; overflow-y: auto;
        background-color: #f8fafc; border-radius: 16px; padding: 1rem; border: 1px solid #e2e8f0;
    }
    .memory-item-text {
        white-space: pre-wrap; word-wrap: break-word; font-size: 14px; padding: 0.5rem;
        border-radius: 6px; background-color: #ffffff; border: 1px solid #e5e7eb; margin-bottom: 0.5rem;
    }
    
    /* 메모리 알림 */
    .stAlert { position: fixed; top: 1rem; right: 1rem; width: 380px; z-index: 9999; margin: 0 !important; padding: 0.8rem !important; border-radius: 8px; }
    
    /* 입력 폼 버튼 */
    div[data-testid="stForm"] > div:last-child { display: flex; justify-content: flex-end; margin-top: 0.5rem; }
    
    /* 메모리 삭제 아이콘 (기존 스타일 유지) */
    .memory-action-btn {
        width: 26px; height: 26px; border-radius: 50%; border: 1px solid #d1d5db; background: #ffffff;
        color: #6b7280; font-size: 16px; line-height: 24px; padding: 0; cursor: pointer;
        display: flex; align-items: center; justify-content: center; transition: all 0.18s ease;
    }
    .memory-action-btn:hover { color: #111; border-color: #9ca3af; background: #f9fafb; }
    
    /* 메모리 삭제 버튼 (Streamlit 버튼 오버라이드) */
    .memory-delete-btn button {
        all: unset !important; box-sizing: border-box !important;
        width: 30px; height: 30px; border-radius: 50%; border: 1px solid #d1d5db; background: #ffffff;
        display: flex !important; align-items: center !important; justify-content: center !important;
        cursor: pointer; font-size: 20px !important; font-weight: 700 !important; color: #314155 !important;
        line-height: 1 !important; vertical-align: middle !important; padding: 0 !important; margin: 0 !important;
        transition: 0.15s ease-in-out;
    }
    .memory-delete-btn button:hover {
        background: #fef2f2; border-color: #ef4444; color: #ef4444; box-shadow: 0 0 3px rgba(239, 68, 68, 0.3);
    }

    /* Info Card (첫 페이지) */
    .info-card { margin-bottom: 20px !important; padding-top: 8px !important; padding-bottom: 8px !important; }
    .info-card h4, .info-card p, .info-card strong { margin-bottom: 4px !important; }
    .info-card .markdown-caption, .stCaption { margin-top: 0 !important; margin-bottom: 4px !important; }
    .start-btn-area { margin-top: -10px !important; }
</style>
""", unsafe_allow_html=True)


# =========================================================
# 유틸리티 함수 (요청하신 함수들 모두 반영)
# =========================================================
def get_eul_reul(noun: str) -> str:
    if not noun: return "을"
    last_char = noun[-1]
    if not ('\uAC00' <= last_char <= '\uD7A3'): return "를"
    last_char_code = ord(last_char) - 0xAC00
    jong = last_char_code % 28
    return "를" if jong == 0 else "을"

def naturalize_memory(text: str) -> str:
    t = text.strip()
    t = t.replace("노이즈 캔슬링", "노이즈캔슬링")
    is_priority = "(가장 중요)" in t
    t = t.replace("(가장 중요)", "").strip()
    t = re.sub(r'로 생각하고 있어요\.?$|에요\.?$|이에요\.?$|다\.?$', '', t)
    t = t.replace('비싼것까진 필요없', '비싼 것 필요 없음').replace('필요없', '필요 없음')
    t = re.sub(r'(을|를)\s*선호$', ' 선호', t)
    t = re.sub(r'(을|를)\s*고려하고$', ' 고려', t)
    t = re.sub(r'(이|가)\s*필요$', ' 필요', t)
    t = re.sub(r'(에서)\s*들을$', '', t)
    t = t.strip()
    if is_priority: t = "(가장 중요) " + t
    return t

def _clause_split(u: str) -> list[str]:
    repl = re.sub(r"(그리고|랑|및|하고|고|&|·)", ",", u)
    parts = [p.strip() for p in re.split(r"[，,]", repl) if p.strip()]
    return parts if parts else [u.strip()]

# (이 함수는 GPT 추출로 대체되었으나, 요청에 따라 포함)
def memory_sentences_from_user_text(utter: str):
    u = utter.strip().replace("  ", " ")
    u = re.sub(r"(좋겠어|좋겠는데|좋을듯|좋을 듯|좋을 것 같아)", "를 고려하고 있어요", u)
    mems = []
    if len(u) <= 3 and u in ["응", "네", "예", "아니", "둘다", "둘 다", "맞아", "맞아요", "ㅇㅇ", "o", "x"]:
        return None
    # ... (기존 로직 생략 없이 포함 가능하나, 현재는 GPT 추출이 메인) ...
    return [] # GPT 함수가 메인이므로 빈 리스트 반환 (오류 방지용)

def extract_memory_with_gpt(user_input, memory_text):
    prompt = f"""
당신은 '헤드셋 쇼핑 기준 요약 AI'입니다.

사용자가 방금 말한 문장:
"{user_input}"

현재까지 저장된 기준:
{memory_text if memory_text else "(없음)"}

위 발화에서 '추가해야 할 쇼핑 기준'이 있으면 아래 JSON 형태로만 출력하세요:
{{ "memories": ["문장1", "문장2"] }}

반드시 지켜야 하는 규칙:
- 기준은 반드시 '헤드셋 구매 기준'으로 변환해서 정리한다.
- 문장을 완성된 기준 형태로 출력.
- 브랜드 언급 → "선호하는 브랜드는 ~ 쪽이에요."
- 착용감/귀 아픔/편안 → "착용감이 편한 제품을 선호하고 있어요."
- 음악/노래/감상 → "주로 음악 감상 용도로 사용할 예정이에요."
- 출퇴근 → "출퇴근 시 사용할 용도예요."
- 예쁜 → "디자인/스타일을 중요하게 생각해요."
- 깔끔/화려 → "원하는 디자인/스타일을 중요하게 생각해요."
- 색상 언급 → "색상은 ~ 계열을 선호해요."
- 노이즈 → "노이즈캔슬링 기능을 고려하고 있어요."
- 예산 N만원 → "예산은 약 N만 원 이내로 생각하고 있어요."

기준이 전혀 없으면 memories는 빈 배열로만 출력하세요.
"""
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], temperature=0.0
        )
        data = json.loads(res.choices[0].message.content)
        return data.get("memories", [])
    except: return []

# =========================================================
# 3. 메모리 관리 함수 (기존 로직 복구)
# =========================================================
def add_memory(mem_text: str, announce=True):
    mem_text = mem_text.strip()
    if not mem_text: return
    mem_text = naturalize_memory(mem_text)
    mem_text_stripped = mem_text.replace("(가장 중요)", "").strip()

    if "예산은 약" in mem_text_stripped:
        st.session_state.memory = [m for m in st.session_state.memory if "예산은 약" not in m]
    if "색상은" in mem_text_stripped:
        st.session_state.memory = [m for m in st.session_state.memory if "색상은" not in m]
    if any(k in mem_text_stripped for k in ["귀여운", "깔끔한", "화려한", "레트로", "세련", "디자인은"]):
        st.session_state.memory = [m for m in st.session_state.memory if "디자인/스타일" not in m]

    for i, m in enumerate(st.session_state.memory):
        m_stripped = m.replace("(가장 중요)", "").strip()
        if mem_text_stripped in m_stripped or m_stripped in mem_text_stripped:
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
    if st.session_state.page == "context_setting": return
    if announce: st.session_state.notification_message = "🧩 메모리에 새로운 기준을 추가했어요."
    st.session_state.memory_changed = True

def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.just_updated_memory = True
        if st.session_state.page != "context_setting":
            st.session_state.notification_message = "🧹 메모리에서 기준을 삭제했어요."
        st.session_state.memory_changed = True

# =========================================================
# 4. 추천 및 예산 로직
# =========================================================
def extract_budget(mems):
    for m in mems:
        m1 = re.search(r"(\d+)\s*만\s*원", m)
        if m1: return int(m1.group(1)) * 10000
        txt = m.replace(",", "")
        m2 = re.search(r"(\d{2,7})\s*원", txt)
        if m2: return int(m2.group(1))
    return None

def detect_priority(mem_list):
    if not mem_list: return None
    for m in mem_list:
        if "(가장 중요)" in m:
            m_low = m.lower()
            if any(k in m_low for k in ["디자인", "스타일"]): return "디자인/스타일"
            if any(k in m_low for k in ["음질"]): return "음질"
            if any(k in m_low for k in ["착용감"]): return "착용감"
            if any(k in m_low for k in ["노이즈", "캔슬링"]): return "노이즈캔슬링"
            if any(k in m_low for k in ["가격", "예산", "가성비"]): return "가격/예산"
            return m.replace("(가장 중요)", "").strip()
    return None

def generate_summary(name, mems):
    if not mems: return ""
    naturalized_mems = [naturalize_memory(m) for m in mems]
    lines = [f"- {m}" for m in naturalized_mems]
    prio = detect_priority(mems)
    header = f"[@{name}님의 메모리 요약_지금 나의 쇼핑 기준은?]\n\n"
    body = "지금까지 대화를 바탕으로 " + name + "님이 중요하게 생각하신 기준을 정리해봤어요:\n\n"
    body += "\n".join(lines) + "\n"
    if prio:
        prio_text = prio.replace("(가장 중요)", "").strip()
        body += f"\n그중에서도 가장 중요한 기준은 **‘{prio_text}’**이에요.\n"
    tail = "\n제가 정리한 기준이 맞을까요? **좌측 메모리 패널**에서 언제든 수정할 수 있어요."
    return header + body + tail

# =========================================================
# 5. 제품 카탈로그 및 추천 로직
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

def filter_products(mems, is_reroll=False):
    mem = " ".join(mems)
    budget = extract_budget(mems)
    priority = detect_priority(mems)
    
    # 점수 계산 (간소화된 버전)
    def score(c):
        s = c["rating"]
        if budget and c["price"] <= budget: s += 5
        if priority and priority in " ".join(c["tags"]): s += 5
        return s
    
    ranked = sorted(CATALOG, key=score, reverse=True)
    return ranked[:3]

def _brief_feature_from_item(c):
    tags_str = " ".join(c.get("tags", []))
    if "가성비" in tags_str: return "가성비 인기"
    if c.get("rank", 999) <= 3: return "이달 판매 상위"
    return "실속형 추천"

def generate_personalized_reason(product, mems, name):
    # 간단한 개인화 이유 생성
    return "고객님의 기준과 잘 맞는 제품이에요."

# =========================================================
# 6. GPT 프롬프트 및 응답 (수정 사항 1, 2번 반영)
# =========================================================
SYSTEM_PROMPT = r"""
너는 'AI 쇼핑 도우미'이며 사용자의 블루투스 헤드셋 기준을 파악해 추천을 돕는 역할을 한다.

[역할 규칙]
- **착용감 관련 질문 금지**: "오버이어 타입이나 온이어 타입 중 선호하는 것이 있나요?" 같은 질문을 하지 않는다. (사용자가 먼저 말하기 전까지는 묻지 않음)
- 최우선 규칙: 메모리에 이미 저장된 기준(특히 용도, 상황, 기능)은 절대 다시 물어보지 않고 바로 다음 단계의 구체적인 질문으로 전환한다.
- 새로운 기준이 등장하면 "메모리에 추가하면 좋겠다"라고 자연스럽게 제안한다.
- 메모리에 실제 저장될 경우(제어창에), "이 기준을 기억해둘게요"라고 표현을 먼저 제시한다.

[대화 흐름 규칙]
- 1단계: 초기 대화에서는 사용자가 사전에 입력한 정보(중요 기준, 선호 색상)를 바탕으로 사용자 취향을 파악한다.
- 2단계: 구매 목표인 블루투스 헤드셋 기준을 순서대로 질문한다. 
- 질문 순서는 고정이 아니다. **사용자의 (가장 중요) 기준을 최우선으로 다룬다.**
- 즉, 사용자의 최우선 기준이 ‘디자인/스타일’이면 기능이나 음질 질문을 먼저 하지 말고 관련 세부 질문을 우선한다.
- 반대로 최우선 기준이 ‘예산’이면 기능·디자인 질문보다 예산 확인을 먼저 한다.
- “최우선 기준”이 없을 때에만 아래의 기본 순서를 따른다: 용도/상황 → 기능(음질) → 착용감 → 배터리 → 디자인/스타일 → 색상 → 예산
- **착용감 질문 시 주의**: 구체적인 형태(오버이어/온이어)를 묻지 말고, "오래 착용하시나요?", "착용감이 중요한가요?" 정도로만 묻는다.

[출력 규칙]
- 한 번에 너무 많은 질문을 하지 않고 자연스럽게 한두 개씩 묻는다.
- 중복 질문은 피하며 꼭 필요한 경우 "다시 한번만 확인할게요"라고 말한다.
- 전체 톤은 부드러운 존댓말을 유지한다.
"""

def gpt_reply(user_input: str) -> str:
    stage = st.session_state.stage
    
    # [상세 페이지 전용 프롬프트]
    if stage == "product_detail":
        product = st.session_state.selected_product
        budget = extract_budget(st.session_state.memory)
        budget_line = f"- 예산: {budget}원" if budget else ""
        
        prompt = f"""
        당신은 현재 '상품 상세 정보 단계(product_detail)'에서 대화하고 있습니다.
        이 단계에서는 오직 **현재 선택된 제품에 대한 정보만** 간단하고 명확하게 제공합니다.

        [선택된 제품 정보]
        - 제품명: {product['name']} ({product['brand']})
        - 가격: {product['price']:,}원
        - 주요 특징: {', '.join(product['tags'])}
        - 리뷰 요약: {product['review_one']}
        {budget_line}

        [응답 규칙 — 매우 중요]
        1. 사용자의 질문에 대해 현재 선택된 제품에 대한 하나의 핵심 정보만 간단히 대답하세요.
        2. 탐색 질문(기준 물어보기, 용도 물어보기)은 절대 하지 마세요.
        3. "현재 선택된 제품은~" 같은 메타 표현을 쓰세요.
        4. 예산 이야기는 사용자가 직접 가격/예산을 물어본 경우에만 간단히 언급하세요.
        5. 답변 후 마지막에 ‘추가 질문’ 한 문장만 자연스럽게 붙이세요. (예: 배터리 지속시간은?, 장시간 착용감은 어떤지?)
        """
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": user_input}]
    
    # [일반 탐색 단계]
    else:
        memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
        prompt_content = f"""
        [메모리]
        {memory_text if memory_text else "현재까지 저장된 메모리는 없습니다."}

        [사용자 발화]
        {user_input}
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt_content}]

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.45,
    )
    return res.choices[0].message.content

# =========================================================
# 7. UI 렌더링 (기존 UI 완벽 유지)
# =========================================================
def render_notification():
    msg = st.session_state.notification_message
    if not msg: return
    st.success(msg)
    st.session_state.notification_message = ""

def render_progress_sidebar():
    # 기존 프로그레스바 (사이드바용)
    st.markdown('<div class="progress-box"><div class="progress-title">진행 상황</div>', unsafe_allow_html=True)
    steps = ["구매 기준 탐색", "후보 비교", "최종 결정"]
    current_idx = 0
    if st.session_state.stage in ["comparison", "product_detail"]: current_idx = 1
    elif st.session_state.stage == "purchase_decision": current_idx = 2
    
    for i, label in enumerate(steps):
        color = "#3B82F6" if i == current_idx else "#E5E7EB"
        st.markdown(f'<div style="color:{color}; font-weight:700;">{i+1}. {label}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def top_memory_panel():
    # 기존 메모리 패널
    if not st.session_state.memory:
        st.caption("아직 파악된 정보가 없습니다.")
    for i, m in enumerate(st.session_state.memory):
        c1, c2 = st.columns([8, 2])
        with c1: st.markdown(f'<div class="memory-item-text">{naturalize_memory(m)}</div>', unsafe_allow_html=True)
        with c2: 
            if st.button("X", key=f"del_{i}"): delete_memory(i); st.rerun()

def render_scenario_box():
    st.markdown("""
    <div style="background:#F0F6FF; padding:20px; border-radius:12px; margin-bottom:20px;">
        <b>시나리오 설명</b><br>
        당신은 지금 AI 쇼핑 에이전트와 함께 블루투스 헤드셋을 구매하는 상황입니다.
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# 8. 메인 인터페이스
# =========================================================
def chat_interface():
    render_notification()
    if not st.session_state.messages:
        ai_say(f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요. 먼저, 어떤 용도로 사용하실 예정인가요?")

    render_scenario_box()
    
    col_mem, col_chat = st.columns([0.25, 0.75], gap="small")
    
    with col_mem:
        render_progress_sidebar()
        st.markdown("#### 🧠 메모리")
        top_memory_panel()
        
    with col_chat:
        st.markdown("#### 💬 대화창")
        chat_container = st.container()
        with chat_container:
             for msg in st.session_state.messages:
                role_class = "chat-bubble-ai" if msg["role"] == "assistant" else "chat-bubble-user"
                st.markdown(f'<div class="chat-bubble {role_class}">{msg["content"]}</div>', unsafe_allow_html=True)
        
        if st.session_state.stage == "comparison":
             # 추천 UI 렌더링 (기존 로직)
             products = filter_products(st.session_state.memory)
             cols = st.columns(3)
             for i, p in enumerate(products):
                 with cols[i]:
                     st.markdown(f"""<div class="product-card"><h4>{p['name']}</h4><p>{p['price']:,}원</p></div>""", unsafe_allow_html=True)
                     if st.button(f"상세보기 {i+1}", key=f"btn_{i}"):
                         st.session_state.selected_product = p
                         st.session_state.stage = "product_detail"
                         st.rerun()

        with st.form("chat_input", clear_on_submit=True):
            user_input = st.text_area("", height=80, placeholder="메시지를 입력하세요...")
            if st.form_submit_button("전송"):
                user_say(user_input)
                
                # 탐색 단계에서 메모리 추출
                if st.session_state.stage == "explore":
                    mems = extract_memory_with_gpt(user_input, "\n".join(st.session_state.memory))
                    for m in mems: add_memory(m)
                    
                    # 추천 전환 로직
                    if "추천" in user_input:
                        st.session_state.stage = "comparison"
                        ai_say("추천 제품을 보여드릴게요!")
                        st.rerun()
                        return

                reply = gpt_reply(user_input)
                ai_say(reply)
                st.rerun()

# =========================================================
# 9. 실행
# =========================================================
if st.session_state.page == "context_setting":
    # 1번 페이지 (기존 UI 유지)
    st.title("🛒 실험 준비")
    st.caption("헤드셋 구매에 반영될 기본 정보와 평소 취향을 입력해주세요.")
    with st.container():
        name = st.text_input("이름", placeholder="홍길동")
        color = st.text_input("선호 색상")
        priority = st.radio("중요 기준", ["디자인", "가성비", "성능"])
        if st.button("시작하기"):
            st.session_state.nickname = name
            # 초기 메모리 주입
            add_memory(f"색상은 {color} 계열 선호", announce=False)
            add_memory(f"(가장 중요) {priority} 중요", announce=False)
            st.session_state.page = "chat"
            st.rerun()
else:
    chat_interface()
