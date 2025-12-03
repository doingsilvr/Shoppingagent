# ============================================
# PART 1. Imports, 기본 설정, CSS, ss_init, GPT
# ============================================
import re
import time
import html
import streamlit as st
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
# 전역 CSS (한 번만 선언)
# =========================================================
st.markdown(
    """
    <style>
    /* 기본 스트림릿 UI 숨기기 */
    #MainMenu, footer, header {
        visibility: hidden;
        display: none !important;
    }

    .block-container {
        max-width: 1180px !important;
        padding: 1rem 1rem 2rem 1rem;
        margin: auto;
    }

    /* 타이틀 카드 */
    .title-card {
        background: white;
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        border: 1px solid #E5E7EB;
        margin-bottom: 18px;
    }

    /* 제품 카드 */
    .product-card {
        background: #FFFFFF;
        border-radius: 16px;
        border: 1px solid #E5E7EB;
        padding: 14px 14px 16px 14px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(15,23,42,0.06);
        text-align: left;
    }

    .product-card h4 {
        font-size: 15px;
        margin-bottom: 6px;
    }

    .product-image {
        width: 100%;
        border-radius: 12px;
        margin: 6px 0 8px 0;
        object-fit: cover;
    }

    /* 메모리 패널 */
    .memory-item-text {
        font-size: 13px;
        line-height: 1.5;
        color: #111827;
        background: #F9FAFB;
        border-radius: 10px;
        padding: 8px 10px;
        border: 1px solid #E5E7EB;
        margin-bottom: 6px;
    }

    .memory-delete-btn button {
        border-radius: 999px !important;
        padding: 0.2rem 0.45rem !important;
        font-size: 11px !important;
    }

    /* 채팅 영역 */
    .chat-unified-box {
        background: #FFFFFF;
        border-radius: 18px;
        border: 1px solid #E5E7EB;
        padding: 14px 16px 12px 16px;
        height: 540px;
        display: flex;
        flex-direction: column;
    }

    .chat-messages-area {
        flex: 1;
        overflow-y: auto;
        padding-right: 4px;
    }

    .chat-input-area {
        margin-top: 10px;
        border-top: 1px solid #E5E7EB;
        padding-top: 8px;
    }

    .chat-display-area {
        max-height: 420px;
        overflow-y: auto;
    }

    .summary-btn {
        background: #2563EB;
        color: white;
        border: none;
        border-radius: 999px;
        padding: 8px 16px;
        cursor: pointer;
    }
    .summary-btn:hover {
        opacity: 0.9;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# 세션 상태 초기값
# =========================================================
def ss_init():
    ss = st.session_state

    ss.setdefault("page", "context_setting")   # 첫 화면: 간단 온보딩
    ss.setdefault("nickname", "")
    ss.setdefault("budget", None)

    ss.setdefault("messages", [])
    ss.setdefault("memory", [])
    ss.setdefault("just_updated_memory", False)

    ss.setdefault("stage", "explore")          # explore → summary → comparison → product_detail
    ss.setdefault("summary_text", "")

    ss.setdefault("current_recommendation", [])
    ss.setdefault("selected_product", None)

    # 🔥 새로 필요한 상태들
    ss.setdefault("notification_message", "")
    ss.setdefault("memory_changed", False)
    ss.setdefault("recommended_products", [])
    ss.setdefault("comparison_hint_shown", False)
    ss.setdefault("product_detail_turn", 0)

    ss.setdefault("final_choice", None)
    ss.setdefault("decision_turn_count", 0)

# 최초 1회 초기화
ss_init()

# =========================================================
# GPT SYSTEM_PROMPT
# =========================================================
SYSTEM_PROMPT = r"""
너는 'AI 쇼핑 도우미'이며 사용자의 블루투스 헤드셋 기준을 파악해 추천을 돕는 역할을 한다.
아래 역할 규칙과 대화흐름 규칙은 반드시 지키도록 한다.

[역할 규칙]
- 최우선 규칙: 메모리에 이미 저장된 기준(특히 용도, 상황, 기능)은 절대 다시 물어보지 않고 바로 다음 단계의 구체적인 질문으로 전환한다.
- 새로운 기준이 등장하면 "메모리에 추가하면 좋겠다"라고 자연스럽게 제안한다.
- 메모리에 실제 저장될 경우(제어창에), "이 기준을 기억해둘게요" 혹은 "이번 쇼핑에서는 해당 내용을 고려하지 않을게요"라고 표현을 먼저 제시한다.
- 사용자가 모호하게 말하면 부드럽게 구체적으로 다시 물어본다.
- 사용자가 "모르겠어", "글쎄", "아직 생각 안 했어"라고 말하면 
  "그렇다면 주로 사용하는 상황에서 어떤 부분이 중요할까요?"라고 자연스럽게 되묻는다.
- 사용자는 블루투스 헤드셋을 구매하려고 한다. 이어폰이나 인이어 타입에 대한 질문은 하지 않는다.

[대화 흐름 규칙]
- 1단계: 초기 대화에서는 사용자가 사전에 입력한 정보(중요 기준, 선호 색상)를 바탕으로 사용자 취향을 파악한다.
- 2단계: 구매 목표인 블루투스 헤드셋 기준을 순서대로 질문한다. 
- 질문 순서는 고정이 아니다. 사용자의 (가장 중요) 기준을 최우선으로 다룬다.
- 즉, 사용자의 최우선 기준이 ‘디자인/스타일’이면  
  → 기능이나 음질 질문을 먼저 하지 말고  
  → 디자인 취향·선호 색상 같은 관련 세부 질문을 우선한다.
- 반대로 최우선 기준이 ‘예산’이면  
  → 기능·디자인 질문보다 예산 확인을 먼저 한다.
- “최우선 기준”이 없을 때에만 아래의 기본 순서를 따른다:
  용도/상황 → 기능(음질) → 착용감 → 배터리 → 디자인/스타일 → 색상 → 예산
- 이미 메모리에 있거나 이미 물어본 항목들(용도, 상황, 기능 등)은 절대 다시 묻지 않고 다음 질문으로 넘어간다.
- 디자인이나 스타일 기준이 파악되면 다음 질문은 선호 색상 또는 구체적 스타일에 대해 한번 물어본다.
- 추천 단계로 넘어가기 전에 반드시 예산을 확인한다.
- (중요) 메모리가 6개 이상이면 "지금까지 기준을 정리해드릴까요?"라고 추천하기 버튼을 제공하는 단계로 넘어간다.
- 메모리 기입할 때, 사용자의 발화를 그대로 기입하지 않고, 메모리 양식에 맞게 바꾼다.
- 추천 요청을 받으면 개인화된 이유가 포함된 리스트 형태로 응답한다.
- 절대로 중복된 질문을 던지지 않는다.
- 사용자가 ~가 뭐야?, ~가 중요할까? 등 답변이 아닌 질문을 던질 경우, 기준 확인을 위한 질문 대신 답변을 우선적으로 진행하며, 기준으로 쌓아가도록 리드한다.
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

# =========================================================
# 🔔 메모리 알림 표시 함수
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
# ============================================
# PART 2. Utility & Memory & Catalog & GPT
# ============================================

# =========================================================
# 조사 처리
# =========================================================
def get_eul_reul(noun: str) -> str:
    if not noun:
        return "을"
    last_char = noun[-1]
    if not ('\uAC00' <= last_char <= '\uD7A3'):
        return "를"
    last_char_code = ord(last_char) - 0xAC00
    jong = last_char_code % 28
    return "를" if jong == 0 else "을"


# =========================================================
# 메모리 텍스트 다듬기
# =========================================================
def naturalize_memory(text: str) -> str:
    t = text.strip()
    t = t.replace("노이즈 캔슬링", "노이즈캔슬링")
    is_priority = "(가장 중요)" in t
    t = t.replace("(가장 중요)", "").strip()

    t = re.sub(r'로 생각하고 있어요\.?$|에요\.?$|이에요\.?$|다\.?$', '', t)
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


def _clause_split(u: str) -> list[str]:
    repl = re.sub(r"(그리고|랑|및|하고|고|&|·)", ",", u)
    parts = [p.strip() for p in re.split(r"[，,]", repl) if p.strip()]
    return parts if parts else [u.strip()]


# =========================================================
# 사용자 발화 → 기준 문장 리스트 추출 (룰 기반)
# =========================================================
def memory_sentences_from_user_text(utter: str):
    u = utter.strip().replace("  ", " ")
    u = re.sub(r"(좋겠어|좋겠는데|좋을듯|좋을 듯|좋을 것 같아)", "를 고려하고 있어요", u)

    mems = []
    if len(u) <= 3 and u in ["응", "네", "예", "아니", "둘다", "둘 다", "맞아", "맞아요", "ㅇㅇ", "o", "x"]:
        return None

    is_priority_clause = False
    if re.search(r"(가장|제일|최우선|젤)\s*(중요|우선)", u):
        is_priority_clause = True
        for i, m in enumerate(st.session_state.memory):
            st.session_state.memory[i] = m.replace("(가장 중요)", "").strip()

    m_price = re.search(r"(\d+)\s*만\s*원", u)
    if m_price:
        price = m_price.group(1)
        st.session_state.memory = [mem for mem in st.session_state.memory if "예산" not in mem]
        mem = f"예산은 약 {price}만 원 이내로 생각하고 있어요."
        mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)

    clauses = _clause_split(u)
    for c in clauses:
        base_rules = [
            ("노이즈캔슬링", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("소음 차단", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("가벼운", "가벼운 착용감을 선호하고 있어요."),
            ("가볍", "가벼운 착용감을 선호하고 있어요."),
            ("클래식", "클래식한 디자인을 선호하고 있어요."),
            ("유행", "인기 많은 상품을 선호하고 있어요."),
            ("미니멀", "미니멀한 디자인을 선호하고 있어요."),
            ("레트로", "레트로 스타일을 선호하고 있어요."),
            ("예쁘면", "디자인/스타일을 중요하게 생각하고 있어요."),
            ("디자인", "디자인/스타일을 중요하게 생각하고 있어요."),
            ("화이트", "색상은 흰색/화이트 계열을 선호하고 있어요."),
            ("블랙", "색상은 검은색/블랙 계열을 선호하고 있어요."),
            ("보라", "색상은 보라색 계열을 선호하고 있어요."),
            ("네이비", "색상은 네이비 계열을 선호하고 있어요."),
            ("실버", "색상은 실버 계열을 선호하고 있어요."),
            ("음질", "음질을 중요하게 생각하고 있어요."),
            ("배터리", "배터리 지속시간이 긴 제품을 선호하고 있어요."),
            ("운동", "주로 러닝/운동 용도로 사용할 예정이에요."),
            ("산책", "주로 산책/일상 용도로 사용할 예정이에요."),
            ("착용감", "착용감이 편한 상품을 선호하고 있어요."),
            ("게임", "주로 게임 용도로 사용할 예정이며, 이 점을 중요하게 생각하고 있어요."),
            ("브랜드", "브랜드 인지도가 높은 제품을 선호하고 있어요."),
            ("유명한", "인지도가 높은 제품을 선호하고 있어요."),
            ("인지도", "인지도를 중요하게 생각하고 있어요."),
        ]
        matched = False
        for key, sent in base_rules:
            if key in c:
                mem = sent
                if key in ["클래식", "깔끔", "미니멀", "레트로"] and len(c.strip()) > 3:
                    cleaned_c = (
                        c.strip()
                        .replace("거", "")
                        .replace("요", "")
                        .replace("느낌", "")
                        .replace("스타일", "")
                        .strip()
                    )
                    if cleaned_c:
                        mem = f"디자인은 '{cleaned_c}' 스타일을 선호해요."
                mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)
                matched = True
                break

        if matched:
            continue

        c_low = c.lower()
        if "귀" in c_low and ("아프" in c_low or "안 아프" in c_low or "편" in c_low):
            mem = "착용감이 편한 제품을 선호하고 있어요."
            mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)
            matched = True
        elif "예쁘" in c_low or "깔끔" in c_low:
            mem = "디자인/스타일을 중요하게 생각하고 있어요."
            mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)
            matched = True
        elif "편안" in c_low or "편했으면" in c_low:
            mem = "착용감이 편안한 제품을 선호하고 있어요."
            mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)
            matched = True
        else:
            continue

    dedup = []
    for m in mems:
        m_stripped = m.replace("(가장 중요)", "").strip()
        is_duplicate = False
        for x in dedup:
            x_stripped = x.replace("(가장 중요)", "").strip()
            if m_stripped in x_stripped or x_stripped in m_stripped:
                is_duplicate = True
                break
        if not is_duplicate:
            allowed_keywords = [
                "배터리", "착용감", "음질", "노이즈", "디자인", "인기",
                "스타일", "색상", "브랜드", "가격", "예산", "무게", "가성비",
                "운동", "게임", "출퇴근", "산책", "여행",
            ]
            if not any(k in m_stripped for k in allowed_keywords):
                continue
            dedup.append(m)
    return dedup if dedup else None


# GPT 대신 쓰는 래퍼 (필요시 이 안에서 모델 사용)
def extract_memory_with_gpt(utter: str, memory_text: str):
    # 현재는 rule 기반 함수만 사용 (원하면 여기서 client.chat 호출로 확장)
    return memory_sentences_from_user_text(utter)


# =========================================================
# 메모리 조작 함수
# =========================================================
def add_memory(mem_text: str, announce=True):
    mem_text = mem_text.strip()
    if not mem_text:
        return

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
# 예산 / 우선 기준 탐지
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


# =========================================================
# 요약 텍스트
# =========================================================
def generate_summary(name, mems):
    if not mems:
        return ""
    naturalized_mems = [naturalize_memory(m) for m in mems]
    lines = [f"- {m}" for m in naturalized_mems]
    prio = detect_priority(mems)
    header = f"[@{name}님의 메모리 요약_지금 나의 쇼핑 기준은?]\n\n"
    body = "지금까지 대화를 바탕으로 " + name + "님이 중요하게 생각하신 기준을 정리해봤어요:\n\n"
    body += "\n".join(lines) + "\n"
    if prio:
        prio_text = prio.replace("(가장 중요)", "").strip()
        body += f"\n그중에서도 가장 중요한 기준은 **‘{prio_text}’**이에요.\n"
    tail = (
        "\n제가 정리한 기준이 맞을까요? **좌측 메모리 패널**에서 언제든 수정함으로써 추천 기준을 바꿀 수 있어요.\n"
        "변경이 없다면 아래 버튼을 눌러 추천을 받아보셔도 좋아요 👇"
    )
    return header + body + tail


# =========================================================
# 카탈로그 데이터
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

# =========================================================
# 제품 카드용 특징 한 줄
# =========================================================
def _brief_feature_from_item(c):
    tags_str = " ".join(c.get("tags", []))
    if "가성비" in tags_str:
        return "가성비 인기"
    if c.get("rank", 999) <= 3:
        return "이달 판매 상위"
    if "디자인" in tags_str:
        return "디자인 강점"
    return "실속형 추천"
# ============================================
# PART 3. 추천 시스템, GPT 응답, 요약/비교, 채팅 UI
# ============================================

# =========================================================
# 필터링 / 스코어링 (핵심 추천 로직)
# =========================================================
def score_product(prod, mems):
    score = 0
    text = " ".join(mems)

    if "노이즈캔슬링" in text and "노이즈캔슬링" in prod["tags"]:
        score += 3
    if "음질" in text and ("음질" in prod["tags"] or "audio" in prod["review_one"]):
        score += 2
    if "착용감" in text and ("편안" in prod["tags"] or "착용감" in prod["tags"]):
        score += 2
    if "배터리" in text and "배터리" in prod["tags"]:
        score += 2
    if "디자인" in text or "스타일" in text:
        if "디자인" in prod["tags"]:
            score += 2
        if "깔끔" in prod["review_one"].lower():
            score += 1

    return score


def filter_products(mems, is_reroll=False):
    scored = sorted(
        CATALOG,
        key=lambda p: (-score_product(p, mems), p["price"])
    )
    top3 = scored[:3]
    if is_reroll:
        return scored[1:4]
    return top3


def generate_personalized_reason(prod, mems, name):
    reasons = []
    if "노이즈캔슬링" in prod["tags"] and any("노이즈" in m for m in mems):
        reasons.append("노이즈캔슬링 성능이 우수해서 소음 많은 환경에서도 좋아요.")
    if "음질" in prod["tags"] and any("음질" in m for m in mems):
        reasons.append("음질 평가가 좋아서 음악 감상 기준과 잘 맞아요.")
    if "편안" in prod["tags"] or "착용감" in prod["tags"]:
        if any("착용감" in m for m in mems):
            reasons.append("장시간 착용에도 편안하다는 점이 장점이에요.")
    if any("디자인" in m for m in mems):
        reasons.append("디자인과 외형 만족도가 높은 상품이에요.")

    if not reasons:
        reasons.append("전체적인 성능·가성비 기준으로 상위에 해당하는 제품이에요.")

    return " ".join(reasons)


# =========================================================
# GPT 응답 (단계별 hint 적용)
# =========================================================
def gpt_reply(user_input: str):
    stage = st.session_state.stage
    mems = st.session_state.memory

    # 상세보기 단계 프롬프트
    if stage == "product_detail":
        pr = st.session_state.selected_product
        prompt = f"""
        아래 제품에 대해 사용자가 질문합니다.
        사용자 질문: {user_input}

        제품 정보:
        - 이름: {pr["name"]}
        - 브랜드: {pr["brand"]}
        - 가격: {pr["price"]:,}원
        - 평점: {pr["rating"]}
        - 특징: {", ".join(pr["tags"])}
        - 리뷰요약: {pr["review_one"]}
        - 색상: {", ".join(pr["color"])}

        출력 규칙:
        - 사용자의 기준과 연결해 개인화된 설명을 덧붙이세요.
        - 한 문단으로 말하되 너무 길게 늘이지 마세요.
        """
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message["content"]

    # 일반 단계: SYSTEM_PROMPT + memory/context
    hint = f"\n현재 단계: {stage}\n메모리: {mems}\n사용자 입력: {user_input}\n"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": hint},
    ]
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return res.choices[0].message["content"]


# =========================================================
# 요약 단계 UI
# =========================================================
def summary_step():
    name = st.session_state.nickname or "고객"
    mems = st.session_state.memory
    summary = generate_summary(name, mems)
    st.session_state.summary_text = summary
    return summary


# =========================================================
# 비교 단계 (추천 3개 출력)
# =========================================================
def comparison_step(is_reroll=False):
    st.session_state.stage = "comparison"
    name = st.session_state.nickname or "고객"
    mems = st.session_state.memory

    st.markdown("### 🎧 추천 후보 비교")
    recommend_products(name, mems, is_reroll)


# =========================================================
# 제품 추천 카드 UI
# =========================================================
def recommend_products(name, mems, is_reroll=False):
    products = filter_products(mems, is_reroll)
    concise = []
    for m in mems:
        concise.append(naturalize_memory(m).replace("(가장 중요) ", "").rstrip("."))
    concise = list(dict.fromkeys(concise))

    if st.session_state.stage == "comparison":
        st.session_state.current_recommendation = products

    st.markdown("#### 🎧 추천 후보 리스트")
    st.markdown("고객님의 기준을 반영한 상위 3개 제품입니다. 관심 가는 제품을 눌러보세요.\n")

    cols = st.columns(3, gap="small")
    for i, c in enumerate(products):
        if i >= 3:
            break
        with cols[i]:
            st.markdown(
                f"""
                <div class="product-card">
                    <h4><b>{i+1}. {c['name']}</b></h4>
                    <img src="{c['img']}" class="product-image"/>
                    <div><b>{c['brand']}</b></div>
                    <div>💰 가격: {c['price']:,}원</div>
                    <div>⭐ 평점: {c['rating']:.1f}</div>
                    <div>🏅 특징: {_brief_feature_from_item(c)}</div>
                    <div style="margin-top:8px; font-size:13px; color:#374151;">
                        👉 {c['review_one']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(f"{i+1}번 상세 보기", key=f"detail_btn_{i}"):
                st.session_state.selected_product = c
                st.session_state.current_recommendation = [c]
                st.session_state.stage = "product_detail"
                st.session_state.product_detail_turn = 0

                reason = generate_personalized_reason(c, mems, name)
                detail_block = (
                    f"**{c['name']} ({c['brand']})**\n"
                    f"- 가격: {c['price']:,}원\n"
                    f"- 평점: {c['rating']:.1f}\n"
                    f"- 색상: {', '.join(c['color'])}\n"
                    f"- 리뷰요약: {c['review_one']}\n\n"
                    f"**추천 이유**: {reason}\n\n"
                    "궁금한 점이 있다면 물어보세요! 예: 배터리는 얼마나 가?, 부정 리뷰는 뭐야?"
                )
                ai_say(detail_block)
                st.rerun()
                return

    if not st.session_state.comparison_hint_shown:
        ai_say("궁금한 제품의 상세 버튼을 눌러 세부 내용을 확인해보실 수 있어요 🙂")
        st.session_state.comparison_hint_shown = True


# =========================================================
# 말풍선 출력 (user/assistant)
# =========================================================
def render_message(role, content):
    if role == "user":
        st.markdown(
            f"""
            <div style="width:100%; display:flex; justify-content:flex-end; margin:4px 0;">
                <div style="
                    max-width:75%; background:#DCF8C6; padding:12px 16px;
                    border-radius:16px; border-top-right-radius:4px;
                    font-size:15px; line-height:1.5; color:#111;
                    box-shadow:0 1px 3px rgba(0,0,0,0.1);
                ">{content}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style="width:100%; display:flex; justify-content:flex-start; margin:4px 0;">
                <div style="
                    max-width:75%; background:#F1F0F0; padding:12px 16px;
                    border-radius:16px; border-top-left-radius:4px;
                    font-size:15px; line-height:1.5; color:#111;
                    box-shadow:0 1px 3px rgba(0,0,0,0.1);
                ">{content}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# JS 스크롤
# =========================================================
def run_js_scroll():
    scroll_js = """
        <script>
        var chatBox = window.parent.document.querySelector('.chat-display-area');
        if (chatBox) {
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        </script>
    """
    st.markdown(scroll_js, unsafe_allow_html=True)


# =========================================================
# 채팅창에 메시지 push + 렌더
# =========================================================
def ai_say(text):
    st.session_state.messages.append({"role": "assistant", "content": text})

def user_say(text):
    st.session_state.messages.append({"role": "user", "content": text})
# ============================================
# PART 4. handle_user_input + UI 전체 구조
# ============================================

# =========================================================
# 핵심: handle_user_input (완전 통합본)
# =========================================================
def handle_user_input(user_input: str):
    if not user_input.strip():
        return

    lower_input = user_input.lower()
    is_question_like = (
        user_input.endswith("?")
        or ("뭐야" in lower_input)
        or ("뭔데" in lower_input)
        or ("알려" in lower_input)
        or ("뜻" in lower_input)
    )

    # -------------------------------
    # 0) (상세보기 제외) 메모리 자동추출
    # -------------------------------
    mems = None
    if not is_question_like and st.session_state.stage != "product_detail":
        memory_text = "\n".join(st.session_state.memory)
        mems = extract_memory_with_gpt(user_input, memory_text)
        if mems:
            for m in mems:
                add_memory(m, announce=True)

    # -------------------------------
    # 1) final_decision 단계 처리
    # -------------------------------
    if st.session_state.stage == "final_decision":
        m = re.search(r"(1|2|3)", user_input)
        if m:
            idx = int(m.group(1)) - 1
            if idx < len(st.session_state.current_recommendation):
                st.session_state.selected_product = st.session_state.current_recommendation[idx]
                st.session_state.stage = "purchase_intent"
                p = st.session_state.selected_product
                ai_say(
                    f"좋습니다! **{p['name']} ({p['brand']})**를 선택하셨군요.\n"
                    "이 제품에 대한 구매 의사는 1점~7점 중 어느 정도인가요?"
                )
                st.rerun()
                return
            else:
                ai_say("1~3번 중에서 골라주세요!")
                st.rerun()
                return
        ai_say("1~3번 중에서 선택 번호를 알려주세요!")
        st.rerun()
        return

    # -------------------------------
    # 2) 비교 단계에서 번호 선택
    # -------------------------------
    sel_re = re.search(r"([1-3]|첫|두|세).*(궁금|골라|선택)", user_input)
    if sel_re and st.session_state.stage == "comparison":
        match = sel_re.group(1)
        if "첫" in match or match == "1":
            idx = 0
        elif "두" in match or match == "2":
            idx = 1
        elif "세" in match or match == "3":
            idx = 2
        else:
            idx = -1

        if 0 <= idx < len(st.session_state.current_recommendation):
            c = st.session_state.current_recommendation[idx]
            st.session_state.selected_product = c
            st.session_state.stage = "product_detail"
            st.session_state.product_detail_turn = 0

            reply = gpt_reply(user_input)
            ai_say(reply)
            st.rerun()
            return
        else:
            ai_say("1~3번 중에서 골라주세요!")
            st.rerun()
            return

    # -------------------------------
    # 3) 다시 추천 요청
    # -------------------------------
    if any(k in user_input for k in ["다시 추천", "다른 상품"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say("다시 추천 전 **예산**을 알려주시면 더 정확하게 추천해드릴 수 있어요.")
            st.session_state.stage = "explore"
            st.rerun()
            return
        st.session_state.stage = "comparison"
        comparison_step(is_reroll=True)
        return

    # -------------------------------
    # 4) explore 단계 로직
    # -------------------------------
    if st.session_state.stage == "explore":
        mem_count = len(st.session_state.memory)
        has_budget = extract_budget(st.session_state.memory) is not None

        if mem_count >= 4 and not has_budget:
            ai_say(
                "이제 어느 정도 기준이 정리된 것 같아요.\n"
                "**예산/가격대**를 알려주시면 추천 단계로 넘어갈 수 있어요!"
            )
            st.rerun()
            return

        if mem_count >= 6 and has_budget:
            st.session_state.stage = "summary"
            summary_step()
            st.rerun()
            return

    # -------------------------------
    # 5) 명시적 추천 요청
    # -------------------------------
    if any(k in user_input for k in ["추천해", "추천해줘", "추천", "골라줘"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say(
                "추천 전에 **예산**을 먼저 알려주세요!\n"
                "예: 10만 원대 초반, 20만 원 이내 등"
            )
            st.session_state.stage = "explore"
            st.rerun()
            return
        st.session_state.stage = "summary"
        summary_step()
        st.rerun()
        return

    # -------------------------------
    # 6) '없어/끝/충분' → 기준 종료
    # -------------------------------
    if any(k in user_input for k in ["없어", "끝", "충분", "그만"]):
        if st.session_state.stage == "comparison":
            ai_say("알겠습니다! 다른 내용이 궁금하시면 편하게 물어보세요 🙂")
            st.rerun()
            return

        if extract_budget(st.session_state.memory) is None:
            ai_say("추천 전 **예산**을 알려주세요!")
            st.session_state.stage = "explore"
            st.rerun()
            return

        st.session_state.stage = "summary"
        summary_step()
        st.rerun()
        return

    # -------------------------------
    # 7) 각 단계 기본 처리
    # -------------------------------
    if st.session_state.stage == "explore":
        reply = gpt_reply(user_input)
        ai_say(reply)
        st.rerun()
        return

    if st.session_state.stage == "summary":
        ai_say("정리된 기준이 맞다면 아래 버튼을 눌러 추천을 받을 수 있어요 🙂")
        st.rerun()
        return

    if st.session_state.stage == "comparison":
        reply = gpt_reply(user_input)
        ai_say(reply)
        st.rerun()
        return

    if st.session_state.stage == "product_detail":
        reply = gpt_reply(user_input)
        ai_say(reply)
        st.session_state.product_detail_turn += 1
        st.rerun()
        return

    # -------------------------------
    # 8) fallback
    # -------------------------------
    reply = gpt_reply(user_input)
    ai_say(reply)
    st.rerun()


# =========================================================
# 온보딩 화면
# =========================================================
def onboarding():
    st.markdown("## 🎧 AI 쇼핑 도우미")
    st.markdown("블루투스 헤드셋 구매를 돕기 위해 간단한 정보를 먼저 여쭤볼게요.")

    nickname = st.text_input("닉네임을 입력해주세요", st.session_state.nickname)
    if nickname:
        st.session_state.nickname = nickname

    if st.button("다음 단계로 이동"):
        st.session_state.page = "chat"
        st.rerun()


# =========================================================
# 메모리 패널 렌더링
# =========================================================
def render_memory_panel():
    st.markdown("### 🧠 메모리")

    for idx, mem in enumerate(st.session_state.memory):
        col1, col2 = st.columns([7, 1])
        with col1:
            st.markdown(
                f"<div class='memory-item-text'>{mem}</div>",
                unsafe_allow_html=True
            )
        with col2:
            if st.button("X", key=f"memdel_{idx}"):
                delete_memory(idx)
                st.rerun()

    st.markdown("---")
    st.write("예: 노이즈캔슬링 필요, 착용감 중요, 가격은 10만 원대 등")


# =========================================================
# 메인 챗 인터페이스
# =========================================================
def chat_interface():
    col_left, col_right = st.columns([2, 5])

    with col_left:
        render_memory_panel()
        render_notification()

    with col_right:
        st.markdown("### 💬 대화")
        with st.container():
            st.markdown('<div class="chat-unified-box">', unsafe_allow_html=True)
            st.markdown('<div class="chat-messages-area chat-display-area">', unsafe_allow_html=True)

            for msg in st.session_state.messages:
                render_message(msg["role"], msg["content"])

            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="chat-input-area">', unsafe_allow_html=True)

            user_text = st.text_input("메시지를 입력하세요...", key="user_input_key")
            send_btn = st.button("전송")

            if send_btn and user_text:
                user_say(user_text)
                handle_user_input(user_text)
                run_js_scroll()

            st.markdown("</div></div>", unsafe_allow_html=True)


# =========================================================
# 메인 페이지 라우팅
# =========================================================
if st.session_state.page == "context_setting":
    onboarding()
else:
    chat_interface()
