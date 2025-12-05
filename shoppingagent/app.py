import re
import streamlit as st
import time
import html
import json
import random
from openai import OpenAI

# =========================================================
# 0. 기본 설정
# =========================================================
st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

client = OpenAI()

# =========================================================
# 1. 세션 상태 초기값 설정
# =========================================================
def ss_init():
    ss = st.session_state

    # 기본 UI 상태
    ss.setdefault("page", "context_setting")
    ss.setdefault("nickname", "")
    ss.setdefault("phone_number", "")
    ss.setdefault("budget", None)

    # 대화 메시지 / 메모리
    ss.setdefault("messages", [])
    ss.setdefault("memory", [])
    ss.setdefault("just_updated_memory", False)

    # 단계
    ss.setdefault("stage", "explore")
    ss.setdefault("summary_text", "")
    ss.setdefault("detail_mode", False)

    # 추천 관련
    ss.setdefault("current_recommendation", [])
    ss.setdefault("selected_product", None)
    ss.setdefault("final_choice", None)
    ss.setdefault("recommended_products", [])

    # 로그용
    ss.setdefault("turn_count", 0)

    # 추가 상태값들
    ss.setdefault("question_history", [])           # 이미 어떤 질문을 했는지 추적
    ss.setdefault("current_question", None)         # 현재 진행 중인 질문 ID
    ss.setdefault("priority", "")                   # 최우선 기준
    ss.setdefault("primary_style", "")
    ss.setdefault("priority_followup_done", False)
    ss.setdefault("product_detail_turn", 0)
    ss.setdefault("memory_changed", False)
    ss.setdefault("notification_message", "")

    ss.setdefault("neg_responses", [
        "없어", "몰라", "글쎄", "아니", "별로", "중요하지 않아",
        "그만", "대충", "음…", "모르겠", "선호 없음"
    ])

ss_init()

# =========================================================
# 2. CSS 스타일 (UI 전체 리디자인)
# =========================================================
st.markdown(
    """
<style>
:root {
    --brand-blue: #2563EB;
    --brand-blue-light: #EFF6FF;
    --brand-blue-soft: #E0EDFF;
    --gray-50: #F9FAFB;
    --gray-100: #F3F4F6;
    --gray-150: #EEF0F4;
    --gray-200: #E5E7EB;
    --gray-300: #D1D5DB;
    --gray-500: #6B7280;
    --gray-700: #374151;
    --radius-lg: 16px;
    --radius-md: 12px;
    --radius-sm: 8px;
}

/* ---------------------------------------------------------
   전체 레이아웃
--------------------------------------------------------- */
#MainMenu, footer, header, .css-1r6q61a {
    visibility: hidden;
    display: none !important;
}

.block-container {
    max-width: 1100px !important;
    padding: 1.5rem 1rem 2.2rem 1rem;
    margin: auto;
    background: var(--gray-50);
}

/* ---------------------------------------------------------
   페이지 공통 텍스트
--------------------------------------------------------- */
h1, h2, h3 {
    font-weight: 800 !important;
    letter-spacing: -0.02em;
}

/* ---------------------------------------------------------
   시나리오 / 안내 박스
--------------------------------------------------------- */
.info-text {
    font-size: 14px;
    color: var(--gray-700);
    background: white;
    border-radius: var(--radius-lg);
    border: 1px solid var(--gray-200);
    padding: 16px 18px;
    line-height: 1.6;
    margin-bottom: 18px;
}

.warning-text {
    font-size: 12px;
    color: #DC2626;
    background: #FEF2F2;
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid #FECACA;
    margin-top: 4px;
}

/* ---------------------------------------------------------
   Progress Bar
--------------------------------------------------------- */
.progress-container {
    display: flex;
    justify-content: space-between;
    padding: 0 6px;
    margin-bottom: 18px;
}

.step-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
}

.step-header-group {
    display: flex;
    align-items: center;
    gap: 8px;
}

.step-circle {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: var(--gray-200);
    color: var(--gray-700);
    font-size: 13px;
    font-weight: 700;
    display: flex;
    justify-content: center;
    align-items: center;
}

.step-title {
    font-size: 14px;
    font-weight: 700;
    color: var(--gray-700);
}

.step-desc {
    font-size: 12px;
    color: var(--gray-500);
    margin-top: 4px;
    padding-left: 34px;
}

.step-active .step-circle {
    background: var(--brand-blue);
    color: white;
}

.step-active .step-title {
    color: var(--brand-blue);
}

/* ---------------------------------------------------------
   메모리 패널 (좌측)
--------------------------------------------------------- */
.memory-panel {
    background: white;
    border-radius: var(--radius-lg);
    border: 1px solid var(--gray-200);
    padding: 16px 16px 14px 16px;
    position: sticky;
    top: 12px;
}

.memory-section-header {
    font-size: 18px !important;
    font-weight: 800 !important;
    margin-bottom: 10px !important;
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--brand-blue);
}

.memory-guide-box {
    background: var(--brand-blue-light);
    border: 1px solid #BFDBFE;
    border-radius: var(--radius-md);
    padding: 10px 12px;
    font-size: 12px;
    color: var(--gray-700);
    margin-bottom: 10px;
    line-height: 1.5;
}

.memory-block {
    background: #F8FAFF;
    border-radius: 999px;
    border: 1px solid #BFDBFE;
    padding: 8px 12px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    color: var(--gray-700);
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

.memory-text {
    flex-grow: 1;
    margin-right: 6px;
}

/* 메모리 삭제 버튼 */
div[data-testid="stBlinkContainer"] button {
    background-color: white !important;
    color: var(--brand-blue) !important;
    border: 1px solid var(--gray-300) !important;
    padding: 3px 8px !important;
    font-size: 11px !important;
    border-radius: 999px !important;
    min-height: 0 !important;
    height: auto !important;
    margin: 0 !important;
}
div[data-testid="stBlinkContainer"] button:hover {
    background: var(--brand-blue-light) !important;
}

/* 메모리 직접 추가 */
.memory-add-title {
    font-size: 13px;
    font-weight: 700;
    margin-top: 10px;
    margin-bottom: 4px;
}

/* ---------------------------------------------------------
   채팅영역 (우측)
--------------------------------------------------------- */
.chat-shell {
    background: white;
    border-radius: var(--radius-lg);
    border: 1px solid var(--gray-200);
    padding: 16px 18px 10px 18px;
}

.chat-display-area {
    height: 360px;
    background: var(--gray-50);
    border-radius: var(--radius-lg);
    padding: 16px 16px 16px 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
}

/* 공통 말풍선 */
.chat-bubble {
    padding: 11px 14px;
    border-radius: 16px;
    margin-bottom: 10px;
    max-width: 80%;
    line-height: 1.5;
    font-size: 14px;
}

/* AI 말풍선 */
.chat-bubble-ai {
    background: white;
    border: 1px solid var(--gray-200);
    align-self: flex-start;
    margin-right: auto;
    border-top-left-radius: 4px;
}

/* 유저 말풍선 */
.chat-bubble-user {
    background: #E0E7FF;
    border: 1px solid #C7D2FE;
    align-self: flex-end;
    margin-left: auto;
    border-top-right-radius: 4px;
}

/* 요약 말풍선 */
.chat-summary-bubble {
    background: #FEF9C3;
    border: 1px solid #FACC15;
    align-self: flex-start;
    margin-right: auto;
    border-radius: 14px;
    padding: 12px 14px;
    font-size: 13px;
}

/* 추천 카드 영역을 감싸는 말풍선 느낌 컨테이너 */
.reco-bubble-wrapper {
    background: white;
    border-radius: 16px;
    border: 1px solid var(--gray-200);
    padding: 12px 12px 8px 12px;
    margin-top: 8px;
}

/* ---------------------------------------------------------
   입력창 / 버튼
--------------------------------------------------------- */
div.stButton > button {
    background-color: var(--brand-blue) !important;
    color: white !important;
    border: none !important;
    border-radius: 999px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    height: 40px !important;
    padding: 0 18px !important;
    box-shadow: 0 2px 4px rgba(37,99,235,0.25);
}
div.stButton > button:hover {
    background-color: #1D4ED8 !important;
}

/* 텍스트 인풋 */
.stTextInput > div > div > input {
    border-radius: 999px !important;
    height: 40px !important;
    font-size: 14px !important;
}

/* ---------------------------------------------------------
   상품 카드
--------------------------------------------------------- */
.product-card {
    min-height: 360px;
    border-radius: 14px;
    padding: 14px;
    background: white;
    border: 1px solid var(--gray-200);
    text-align: center;
    position: relative;
    box-shadow: 0 4px 6px rgba(0,0,0,0.04);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.product-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 14px rgba(0,0,0,0.08);
}

.product-img {
    width: 100%;
    height: 150px;
    object-fit: contain;
    border-radius: 10px;
    margin-bottom: 8px;
}

.product-title {
    font-weight: 700;
    font-size: 15px;
    margin-bottom: 4px;
}

.product-price {
    color: var(--brand-blue);
    font-weight: 700;
    margin-bottom: 4px;
}

.product-meta {
    font-size: 12px;
    color: var(--gray-500);
    margin-bottom: 8px;
}

/* 선택 배지 */
.product-selected-badge {
    position:absolute;
    top:8px;
    right:8px;
    background: var(--brand-blue);
    color:white;
    padding:3px 7px;
    border-radius:999px;
    font-size:11px;
}

/* ---------------------------------------------------------
   1페이지 (context_setting) 스타일
--------------------------------------------------------- */
.basic-info-card {
    background:white;
    border-radius:var(--radius-lg);
    border:1px solid var(--gray-200);
    padding:16px 18px;
    margin-bottom:12px;
}

.select-question {
    margin-top:14px;
    margin-bottom:8px;
    font-weight:700;
    font-size:15px;
}

</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# 3. SYSTEM PROMPT
# =========================================================
SYSTEM_PROMPT = r"""
너는 'AI 쇼핑 도우미'이며 **항상 블루투스 헤드셋** 기준을 파악해 추천을 돕는 역할을 한다.
스마트폰, 노트북, 태블릿, 일반 전자기기 등 다른 카테고리에 대한 추천이나 질문 유도는 절대 하지 않는다.
이어폰, 인이어 타입, 유선 헤드셋도 추천하지 않는다. 대화 전 과정에서 '블루투스 헤드셋'만을 전제로 생각한다.

[역할 규칙]
- 최우선 규칙: 메모리에 이미 저장된 기준(특히 용도, 상황, 기능)은 절대 다시 물어보지 않고 바로 다음 단계의 구체적인 질문으로 전환한다.
- 너의 가장 큰 역할은 **사용자 메모리(쇼핑 기준 프로필)를 읽고, 갱신하고, 설명하면서 추천을 돕는 것**이다.
- 메모리에 이미 저장된 내용(특히 용도, 상황, 기능, 색상, 스타일 등)은 **다시 묻지 말고**, 그 다음 단계의 구체적인 질문으로 넘어간다.
- 메모리에 실제 저장될 경우(제어창에), "이 기준을 기억해둘게요", "이번 쇼핑에서는 해당 내용을 고려하지 않을게요", “지금 말씀해주신 내용은 메모리에 추가해두면 좋을 것 같아요.”라고 표현을 먼저 제시한다.
- 사용자에게 ‘음질 선호(저음/중음/고음)’처럼 세부적인 음향 특성을 묻는 follow-up 질문은 절대 하지 않는다.
- 사용자가 기준을 바꾸거나 기존 메모리와 충돌하는 발화를 하면  
  “제가 기억하고 있던 내용은 ~였는데, 이번에는 기준을 바꾸실까요? 아니면 둘 다 함께 고려해볼까요?”라고 부드럽게 확인한다.
- 사용자가 “모르겠어요 / 글쎄요 / 아직 생각 안 했어요” 라고 말하면  
  “그렇다면 실제로 쓰실 상황을 떠올려보면 어떨까요? 출퇴근, 공부, 게임 중에 어떤 상황이 가장 많을까요?”처럼 맥락 중심으로 되묻거나, "제 생각은 이 기준이 중요하게 고려되면 좋을 것 같아요."로 안내한다.

[대화 흐름 규칙]
- 1단계(explore): 사용자가 사전에 입력한 정보 + 대화 중 발화를 바탕으로,  
  **용도/상황, 음질, 착용감, 노이즈캔슬링, 배터리, 디자인/스타일, 색상, 예산** 순서대로 물어보도록 한다.
- “가장 중요한 기준”이 있으면 그 기준을 먼저 다뤄야 한다.
- “최우선 기준”이 없는 경우에만 기본 순서를 따른다:  
  용도/상황 → 음질 → 착용감 → 배터리 → 디자인/스타일 → 색상 → 예산
- 추천 단계로 넘어가기 전에 **예산**은 반드시 한 번은 확인해야 한다.
- 마지막으로 예산까지 다 채워져 요약 및 추천 단계로 넘어가기 전, 최우선 기준이 결국 무엇인지 무조건 물어본다.
- (중요) 메모리가 6개 이상이면 "지금까지 기준을 정리해드릴까요?"라고 추천하기 버튼을 제공하는 단계로 넘어간다.
- 메모리 기입할 때, 사용자의 발화를 그대로 기입하지 않고, 메모리 양식에 맞게 바꾼다.
- 사용자가 ~가 뭐야?, ~가 중요할까? 등 답변이 아닌 질문을 던질 경우, 기준 확인을 위한 질문 대신 답변을 우선적으로 진행하며, 기준으로 쌓아가도록 리드한다.

[메모리 활용 규칙]
- 대답할 때, 이전 메모리와 새롭게 추가된 메모리가   
  “제가 기억하고 있는 ○○님 취향은 ~였는데요, 그 기준에 비추어 보면 이 선택은 ~ 부분에서 잘 맞을 것 같아요.”  
 처럼 **메모리와 현재 추천을 연결해서 설명**한다.
- 메모리와 최신 발화가 충돌하면  
  “예전에 말씀해주신 내용과 조금 다른데, 이번에는 새 기준을 우선해서 반영할까요?”라고 확인한다.
- 메모리에 색상/디자인/예산이 이미 있으면,  
  “기억하고 있는 메모리 기준(예: 블랙 선호, 가성비 중심)을 바탕으로 후보를 추려볼게요.”처럼 반드시 언급해 준다.

[출력 규칙]
- 한 번에 질문은 1개만, 자연스러운 짧은 턴으로 나눈다.
- 항상 **헤드셋** 기준으로만 말하며, 다른 기기(스마트폰, 노트북 등)은 예로만 언급하더라도 추천 대상이 되지 않게 한다.
- 말투는 부드러운 존댓말을 유지하되, 너무 딱딱하지 않게 대화하듯 말한다.
"""

# =========================================================
# 4. 유틸 함수들
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


def naturalize_memory(text: str) -> str:
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


def is_negative_response(text: str) -> bool:
    if not text:
        return False

    negative_keywords = [
        "없어", "없다고", "몰라", "모르겠", "잘 모르",
        "글쎄", "별로", "아닌데", "굳이",
        "그만", "필요없", "상관없", "안중요", "관심없"
    ]
    return any(k in text for k in negative_keywords)


def extract_memory_with_gpt(user_input: str, memory_text: str):
    prompt = f"""
당신은 '헤드셋 쇼핑 메모리 요약 AI'입니다.

사용자 발화:
\"\"\"{user_input}\"\"\"

현재까지 저장된 메모리:
{memory_text if memory_text else "(없음)"}

위 발화에서 '추가하면 좋은 쇼핑 메모리'가 있다면 아래 JSON 형식으로만 답하세요.

{{
  "memories": [
      "문장1",
      "문장2"
  ]
}}

반드시 지킬 것:
- 메모리는 모두 '블루투스 헤드셋 쇼핑 기준'이어야 합니다.
- user_input을 그대로 복붙하지 말고, 기준 문장 형태로 가공해서 쓰세요.

만약 저장할 만한 메모리가 전혀 없다면
{{
  "memories": []
}}
만 출력하세요.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    try:
        data = json.loads(res.choices[0].message.content)
        return data.get("memories", [])
    except Exception:
        return []

# =========================================================
# 5. 메모리 추가/수정/삭제
# =========================================================
def _is_color_memory(text: str) -> bool:
    t = text.replace("(가장 중요)", "")
    if "색상" in t and "선호" in t:
        return True
    color_keywords = ["화이트", "블랙", "네이비", "퍼플", "실버", "그레이", "핑크", "보라", "골드"]
    return any(k in t for k in color_keywords)


def _after_memory_change():
    st.session_state.just_updated_memory = True
    st.session_state.memory_changed = True

    if st.session_state.stage == "summary":
        st.session_state.summary_text = build_summary_from_memory(
            st.session_state.nickname,
            st.session_state.memory,
        )

    if st.session_state.stage == "comparison":
        st.session_state.recommended_products = make_recommendation()


def add_memory(mem_text: str, announce: bool = True):
    mem_text = mem_text.strip()
    if not mem_text:
        return

    mem_text = naturalize_memory(mem_text)
    mem_text_stripped = mem_text.replace("(가장 중요)", "").strip()

    if "예산은 약" in mem_text_stripped:
        st.session_state.memory = [
            m for m in st.session_state.memory if "예산은 약" not in m
        ]

    if _is_color_memory(mem_text_stripped):
        st.session_state.memory = [
            m for m in st.session_state.memory if not _is_color_memory(m)
        ]

    for i, m in enumerate(st.session_state.memory):
        base = m.replace("(가장 중요)", "").strip()
        if mem_text_stripped in base or base in mem_text_stripped:
            if "(가장 중요)" in mem_text and "(가장 중요)" not in m:
                st.session_state.memory = [
                    mm.replace("(가장 중요)", "").strip()
                    for mm in st.session_state.memory
                ]
                st.session_state.memory[i] = mem_text

                if announce:
                    st.session_state.notification_message = "🌟 최우선 기준으로 설정되었어요."
                _after_memory_change()
                return
            return

    st.session_state.memory.append(mem_text)

    if announce:
        st.session_state.notification_message = "🧩 메모리에 새로운 내용을 추가했어요."
    _after_memory_change()


def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.notification_message = "🧹 메모리에서 해당 기준을 삭제했어요."
        _after_memory_change()


def update_memory(idx: int, new_text: str):
    if not (0 <= idx < len(st.session_state.memory)):
        return

    new_text = naturalize_memory(new_text).strip()

    if "(가장 중요)" in new_text:
        st.session_state.memory = [
            m.replace("(가장 중요)", "").strip()
            for m in st.session_state.memory
        ]

    st.session_state.memory[idx] = new_text
    st.session_state.notification_message = "🔄 메모리가 수정되었어요."
    _after_memory_change()

# =========================================================
# 6. 요약/추천 관련 유틸
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
    tags = product.get("tags", [])

    if "음질" in mem_str and "음질" in tags:
        reasons.append("음질 중심 사용자에게 잘 맞아요.")
    if "착용감" in mem_str and any(t in tags for t in ["편안함", "경량", "가벼움", "착용감"]):
        reasons.append("장시간 착용 용도로 적합해요.")
    if "노이즈캔슬링" in mem_str and "노이즈캔슬링" in tags:
        reasons.append("노이즈캔슬링 성능이 뛰어나요.")
    if "배터리" in tags:
        reasons.append("배터리가 오래가는 편이에요.")
    if "가성비" in tags:
        reasons.append("가성비가 뛰어난 선택이에요.")
    if "통화품질" in tags:
        reasons.append("통화 품질도 준수해서 업무용으로 좋아요.")
    if "음질" in tags and "음질" not in mem_str:
        reasons.append("음질 평가도 좋아요.")

    closing_templates = [
        f"{name}님의 취향과 잘 맞는 조합이에요!",
        f"{name}님이 선호하시는 기준과 잘 어울리는 제품이에요.",
        f"여러 기준을 고려하면 {name}님께 특히 잘 맞을 것 같아요.",
        f"{name}님의 사용 스타일과 궁합이 좋아 보여요!",
        f"{name}님이 말씀하신 조건들과 자연스럽게 맞닿아 있어요."
    ]
    if "음질" in tags:
        closing_templates.append(f"특히 음질을 중시하는 {name}님께 잘 맞는 타입이에요.")
    if "배터리" in tags:
        closing_templates.append(f"오래 쓰는 사용 패턴을 가진 {name}님께도 잘 맞아요.")
    if "가성비" in tags:
        closing_templates.append(f"실속 있는 선택을 찾는 {name}님께 어울려요.")

    reasons.append(random.choice(closing_templates))

    unique = []
    for r in reasons:
        if r not in unique:
            unique.append(r)

    return "\n".join(unique[:3])


def send_product_detail_message(product):
    detail_text = (
        f"📌 **{product['name']} 상세 정보 안내드릴게요!**\n\n"
        f"- **가격:** {product['price']:,}원\n"
        f"- **평점:** ⭐ {product['rating']:.1f} (리뷰 {product['reviews']}개)\n"
        f"- **주요 특징(태그):** {', '.join(product.get('tags', []))}\n"
        f"- **리뷰 한 줄 요약:** {product.get('review_one', '리뷰 요약 정보가 없습니다.')}\n\n"
        "🔄 현재 추천 상품이 마음에 들지 않으신가요?\n"
        "좌측 **쇼핑 메모리**를 수정하시면 추천 후보가 바로 달라질 수 있어요.\n"
        "예를 들어 예산, 색상, 노이즈캔슬링, 착용감 같은 기준을 바꿔보셔도 좋습니다.\n\n"
        "이 제품에 대해 더 궁금한 점이 있으시면 편하게 물어봐 주세요 🙂"
    )
    ai_say(detail_text)

# =========================================================
# 7. 상품 카탈로그
# =========================================================
CATALOG = [
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 179000, "rating": 4.4, "reviews": 1600, "rank": 8, "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"], "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.", "color": ["블랙", "화이트", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg"},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 99000, "rating": 4.4, "reviews": 2300, "rank": 9, "tags": ["가벼움", "음질", "노이즈캔슬링", "편안함"], "review_one": "가볍고 음질이 좋다는 평이 많아요.", "color": ["블랙", "화이트", "퍼플", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png"},
    {"name": "Sony WH-CH720N", "brand": "Sony", "price": 129000, "rating": 4.5, "reviews": 2100, "rank": 6, "tags": ["노이즈캔슬링", "경량", "무난한 음질"], "review_one": "경량이라 출퇴근용으로 좋다는 후기가 많아요.", "color": ["블랙", "화이트", "블루"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-CH720N.jpg"},
    {"name": "Bose QC45", "brand": "Bose", "price": 420000, "rating": 4.7, "reviews": 2800, "rank": 2, "tags": ["가벼움", "착용감", "노이즈캔슬링", "편안함"], "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg"},
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 210000, "rating": 4.8, "reviews": 3200, "rank": 1, "tags": ["노이즈캔슬링", "음질", "착용감", "통화품질"], "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.", "color": ["핑크"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg"},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 679000, "rating": 4.6, "reviews": 1500, "rank": 3, "tags": ["브랜드", "노이즈캔슬링", "디자인", "고급"], "review_one": "깔끔한 디자인과 가벼운 무게로 만족도가 높아요.", "color": ["실버", "스페이스그레이"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg"},
    {"name": "Sennheiser PXC 550-II", "brand": "Sennheiser", "price": 289000, "rating": 4.3, "reviews": 1200, "rank": 7, "tags": ["착용감", "여행", "배터리", "노이즈캔슬링"], "review_one": "여행 시 장시간 착용에도 압박감이 덜해요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sennheiser%20PXC%2055.jpeg"},
    {"name": "AKG Y600NC", "brand": "AKG", "price": 149000, "rating": 4.2, "reviews": 1800, "rank": 10, "tags": ["균형 음질", "가성비", "노이즈캔슬링"], "review_one": "가격대비 깔끔하고 균형 잡힌 사운드가 좋아요.", "color": ["블랙", "골드", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/AKG%20Y6.jpg"},
    {"name": "Microsoft Surface Headphones 2", "brand": "Microsoft", "price": 319000, "rating": 4.5, "reviews": 900, "rank": 11, "tags": ["업무", "통화품질", "디자인", "노이즈캔슬링"], "review_one": "업무용으로 완벽하며 통화 품질이 매우 깨끗합니다.", "color": ["화이트", "블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Microsoft%20Surface%20Headphones%202.jpeg"},
    {"name": "Bose Noise Cancelling Headphones 700", "brand": "Bose", "price": 490000, "rating": 4.7, "reviews": 2500, "rank": 4, "tags": ["노이즈캔슬링", "배터리", "음질", "프리미엄"], "review_one": "노이즈캔슬링 성능과 음질을 모두 갖춘 최고급 프리미엄 제품.", "color": ["블랙", "화이트"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20Headphones%20700.jpg"},
]

# =========================================================
# 8. GPT 응답 로직
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
"{user_input}"

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


def gpt_reply(user_input: str) -> str:
    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    nickname = st.session_state.nickname
    stage = st.session_state.stage

    if stage == "product_detail":
        product = st.session_state.selected_product
        if not product:
            st.session_state.stage = "comparison"
            return "선택된 제품 정보가 없어서 추천 목록으로 다시 돌아갈게요!"

        prompt = get_product_detail_prompt(product, user_input)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
        )
        st.session_state.product_detail_turn += 1
        return res.choices[0].message.content

    stage_hint = ""
    stage_hint += (
        "[중요 규칙] 이 대화는 항상 '블루투스 헤드셋' 기준입니다. "
        "스마트폰·노트북 등 다른 기기 추천이나 질문은 하지 마세요.\n\n"
    )

    design_keywords = ["디자인", "스타일", "예쁜", "깔끔", "세련", "미니멀", "레트로", "감성", "스타일리시"]

    is_design_in_memory = any(
        any(k in m for k in design_keywords)
        for m in st.session_state.memory
    )

    design_priority = any(
        "(가장 중요)" in m and any(k in m for k in design_keywords)
        for m in st.session_state.memory
    )

    has_color_detail = any("색상" in m for m in st.session_state.memory)

    usage_keywords = ["용도", "출퇴근", "운동", "게임", "여행", "공부", "음악 감상"]
    is_usage_in_memory = any(any(k in m for k in usage_keywords) for m in st.session_state.memory)

    if stage == "explore" and design_priority:
        stage_hint += """
[디자인/스타일 최우선 규칙 – 이번 턴 필수]
- 이번 턴에는 반드시 ‘디자인’ 또는 ‘색상’ 관련 질문 **단 1개**만 하세요.
- 음질/착용감/배터리/노이즈캔슬링 등 기능 질문은 **이번 턴에서 금지**합니다.
- 이미 색상 정보를 알고 있다면 디자인 스타일(깔끔→미니멀/레트로 등)만 물어보세요.
"""

    if stage == "explore" and is_usage_in_memory and len(st.session_state.memory) >= 2:
        stage_hint += (
            "[용도 파악됨] 이미 사용 용도는 기억하고 있습니다. "
            "다시 묻지 말고 다음 기준(음질/착용감/디자인 등)으로 넘어가세요.\n"
        )

    prompt_content = f"""
{stage_hint}

[현재 저장된 쇼핑 메모리]
{memory_text if memory_text else "(아직 없음)"}

[사용자 발화]
{user_input}

위 정보를 참고해서, '블루투스 헤드셋 쇼핑 도우미' 역할로서
다음 말을 자연스럽고 짧게 이어가세요.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content},
        ],
        temperature=0.45,
    )

    reply = res.choices[0].message.content
    return reply

# =========================================================
# 9. 로그 유틸
# =========================================================
def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})


def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})
    st.session_state.turn_count += 1

# =========================================================
# 10. 단계 UI
# =========================================================
def render_step_header():
    stage = st.session_state.stage

    def is_active(step_name):
        return "step-active" if step_name == stage else ""

    step_items = f"""
    <div class="progress-container">
        <div class="step-item {is_active('explore')}">
            <div class="step-header-group">
                <div class="step-circle">1</div>
                <div class="step-title">기준 탐색</div>
            </div>
            <div class="step-desc">취향과 핵심 기준을 알아보는 단계</div>
        </div>
        <div class="step-item {is_active('summary')}">
            <div class="step-header-group">
                <div class="step-circle">2</div>
                <div class="step-title">요약 확인</div>
            </div>
            <div class="step-desc">정리된 기준을 확인하고 수정</div>
        </div>
        <div class="step-item {is_active('comparison')}">
            <div class="step-header-group">
                <div class="step-circle">3</div>
                <div class="step-title">상품 비교</div>
            </div>
            <div class="step-desc">후보 헤드셋들을 나란히 비교</div>
        </div>
        <div class="step-item {is_active('product_detail')}">
            <div class="step-header-group">
                <div class="step-circle">4</div>
                <div class="step-title">상세 정보</div>
            </div>
            <div class="step-desc">선택한 헤드셋을 깊게 살펴보기</div>
        </div>
        <div class="step-item {is_active('purchase_decision')}">
            <div class="step-header-group">
                <div class="step-circle">5</div>
                <div class="step-title">구매 결정</div>
            </div>
            <div class="step-desc">최종 선택 정리</div>
        </div>
    </div>
    """
    st.markdown(step_items, unsafe_allow_html=True)

# =========================================================
# 11. 좌측 메모리 패널
# =========================================================
def render_memory_sidebar():
    st.markdown("<div class='memory-panel'>", unsafe_allow_html=True)

    st.markdown("<div class='memory-section-header'>🧠 나의 쇼핑 메모리</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='memory-guide-box'>
            AI가 기억하고 있는 쇼핑 취향이에요.<br>
            필요하면 직접 수정하거나 삭제할 수 있어요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    for i, mem in enumerate(st.session_state.memory):
        c1, c2 = st.columns([8, 2])
        with c1:
            st.markdown(
                f"<div class='memory-block'><div class='memory-text'>{mem}</div></div>",
                unsafe_allow_html=True,
            )
        with c2:
            if st.button("X", key=f"delete_mem_{i}"):
                delete_memory(i)
                st.rerun()

    st.markdown("<div class='memory-add-title'>✏️ 메모리 직접 추가하기</div>", unsafe_allow_html=True)

    new_mem = st.text_input(
        "추가할 기준",
        key="manual_memory_add",
        placeholder="예: 음질을 중요하게 생각해요 / 귀가 편한 제품이면 좋겠어요",
        label_visibility="collapsed",
    )
    if st.button("메모리 추가하기", key="manual_memory_add_btn"):
        if new_mem.strip():
            add_memory(new_mem.strip())
            st.success("메모리에 추가했어요!")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 12. 추천 UI (3개 카드) - 채팅 버블 안에 들어가는 느낌
# =========================================================
def recommend_products_ui(name, mems):
    products = st.session_state.recommended_products

    if not products:
        st.warning("추천을 위해 기준이 조금 더 필요해요!")
        return

    st.markdown(
        "<div class='reco-bubble-wrapper'>"
        "<div style='font-size:14px; font-weight:700; margin-bottom:8px;'>"
        "🛍 지금 기준에 가장 잘 맞는 헤드셋 후보들이에요.</div>",
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    for idx, p in enumerate(products):
        with cols[idx]:
            is_sel = (
                st.session_state.selected_product is not None
                and st.session_state.selected_product["name"] == p["name"]
            )
            border_color = "#2563EB" if is_sel else "#e5e7eb"

            card_html = f"""
            <div class="product-card" style="border:2px solid {border_color};">
            """

            if is_sel:
                card_html += '<div class="product-selected-badge">선택됨</div>'

            card_html += f"""
                <img src="{p['img']}" class="product-img">
                <div class="product-title">{p['name']}</div>
                <div class="product-price">{p['price']:,}원</div>
                <div class="product-meta">⭐ {p['rating']:.1f} / 리뷰 {p['reviews']}개</div>
                <div style="margin-top:8px; font-size:12px; color:#4B5563; white-space:pre-line;">
                    {html.escape(generate_personalized_reason(p, mems, name))}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

            if st.button("상세보기", key=f"detail_{p['name']}"):
                st.session_state.selected_product = p
                st.session_state.stage = "product_detail"
                send_product_detail_message(p)
                st.rerun()

    if st.session_state.selected_product:
        p = st.session_state.selected_product
        st.markdown(
            f"""
            <div style="margin-top:10px; padding:10px 12px; background:#ECF5FF;
            border-radius:12px; font-size:13px; border:1px solid #cfe1ff;">
                ✔ <b>{p['name']}</b> 제품을 선택하신 상태예요.<br>
                아래 <b>이 제품으로 결정하기</b> 버튼을 누르시면 구매 결정을 완료할 수 있어요.
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🛒 이 제품으로 결정하기", key="final_decide_btn"):
            st.session_state.final_choice = p
            st.session_state.stage = "purchase_decision"
            ai_say(f"좋습니다! **'{p['name']}'**(으)로 결정하셨네요. 필요한 정보가 있으면 뭐든지 도와드릴게요.")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 13. 요약 생성 함수
# =========================================================
def build_summary_from_memory(name, mems):
    if not mems:
        return f"{name}님, 아직 명확한 기준이 정해지지 않았어요. 몇 가지 기준만 알려주시면 추천을 도와드릴게요!"

    lines = [f"• {m.replace('(가장 중요)', '').strip()}" for m in mems]

    prio = None
    for m in mems:
        if "(가장 중요)" in m:
            prio = m.replace("(가장 중요)", "").strip()
            break

    header = f"[@{name}님의 메모리 요약_지금 나의 쇼핑 기준은?]\n\n"
    body = "지금까지 대화를 기반으로 정리된 쇼핑 기준은 다음과 같아요:\n\n"
    body += "\n".join(lines) + "\n"

    if prio:
        body += f"\n그중에서도 가장 중요한 기준은 **‘{prio}’**이에요.\n"

    tail = (
        "\n좌측 **쇼핑 메모리 패널에서 언제든지 기준을 수정하실 수 있어요.**\n"
        "기준이 달라지면 추천 후보도 바로 변경됩니다.\n"
        "준비되셨다면 아래 버튼을 눌러 추천을 받아보세요 👇"
    )

    return header + body + tail

# =========================================================
# 14. 추천 모델
# =========================================================
def score_item_with_memory(item, mems):
    score = 0
    mtext = " ".join(mems)
    budget = extract_budget(mems)

    if "(가장 중요)" in mtext:
        if "디자인/스타일" in mtext and "디자인" in item["tags"]:
            score += 50
        if "음질" in mtext and "음질" in item["tags"]:
            score += 50
        if "착용감" in mtext and "착용감" in item["tags"]:
            score += 50

    for m in mems:
        if "노이즈" in m and "노이즈캔슬링" in item["tags"]:
            score += 20
        if "가성비" in m and "가성비" in item["tags"]:
            score += 20
        if "색상" in m:
            for col in item["color"]:
                if col in m:
                    score += 10

    score -= item["rank"]

    if budget:
        if item["price"] > budget:
            diff = item["price"] - budget
            if diff > 100000:
                score -= 200
            else:
                score -= 80
        else:
            score += 30

    return score


def make_recommendation():
    scored = [(score_item_with_memory(item, st.session_state.memory), item) for item in CATALOG]
    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:3]]

# =========================================================
# 15. 사용자 입력 처리
# =========================================================
def handle_input():
    u = st.session_state.user_input_text.strip()
    if not u:
        return

    ss = st.session_state
    user_say(u)

    drift_words = ["스마트폰", "휴대폰", "핸드폰", "아이폰", "갤럭시", "폰"]
    if any(w in u for w in drift_words):
        ai_say("앗! 지금은 블루투스 헤드셋 추천 단계예요 😊 다른 기기보단 헤드셋 기준으로만 도와드릴게요!")
        return

    cur_q = ss.current_question

    if is_negative_response(u):
        if cur_q is not None:
            ss.question_history.append(cur_q)
            ss.current_question = None
        ai_say("네! 그 부분은 중요하지 않다고 이해했어요. 그럼 다음 질문으로 넘어가볼게요. 추가로 고려할 점이 또 있을까요? 😊")
        return

    if cur_q is not None:
        ss.question_history.append(cur_q)
        ss.current_question = None

    memory_before = ss.memory.copy()
    memory_text = "\n".join([naturalize_memory(m) for m in ss.memory])
    extracted = extract_memory_with_gpt(u, memory_text)

    if extracted:
        for mem in extracted:
            before_len = len(ss.memory)
            add_memory(mem)
            after_len = len(ss.memory)
            if after_len > before_len:
                ss.notification_message = f"🧩 '{mem}' 내용을 기억해둘게요."

    primary = ss.primary_style

    if not ss.priority_followup_done:
        if primary == "design":
            ai_say(
                "디자인/스타일을 가장 중요하게 생각하신다고 하셔서 여쭤볼게요. "
                "전체적으로는 어떤 느낌을 선호하시나요? 예를 들어 미니멀한 스타일, 레트로한 느낌, "
                "깔끔하고 심플한 디자인, 아니면 색 포인트가 있는 스타일 중에 더 끌리는 게 있으실까요?"
            )
            ss.priority_followup_done = True
            return

        if primary == "performance":
            ai_say(
                "성능을 중요하게 보고 계신다고 하셔서, 블루투스 헤드셋에서 보통 많이 고려하는 요소들을 알려드릴게요.\n"
                "대표적으로 `음질`, `노이즈캔슬링`, `배터리 지속시간`, `착용감` 같은 부분들이 있어요.\n"
                "이 중에서 특히 더 중요하게 생각하시는 요소가 있으실까요? 편하게 말씀해주세요 :)"
            )
            ss.priority_followup_done = True
            return

    has_budget = any("예산" in m for m in ss.memory)
    mem_count = len(ss.memory)

    if mem_count >= 5 and not has_budget and ss.priority_followup_done:
        ai_say("추천 전에 **예산**을 먼저 알려주세요! 블루투스 헤드셋은 주로 10-60만원까지 가격대가 다양해요. N만원 이내를 원하시는지 알려주세요.")
        return

    enough_memory = mem_count >= 5

    if ss.stage == "explore" and has_budget and enough_memory:
        ss.stage = "summary"
        ss.summary_text = build_summary_from_memory(ss.nickname, ss.memory)
        return

    reply = gpt_reply(u)
    ai_say(reply)

    qid = None
    if "디자인" in reply or "스타일" in reply:
        qid = "design"
    elif "색상" in reply and "선호" in reply:
        qid = "color"
    elif "음질" in reply:
        qid = "sound"
    elif "착용감" in reply:
        qid = "comfort"
    elif "배터리" in reply:
        qid = "battery"
    elif "예산" in reply or "가격대" in reply:
        qid = "budget"

    if qid and qid in ss.question_history:
        ss.current_question = None
    else:
        ss.current_question = qid

    if st.session_state.stage == "explore":
        has_budget = any("예산" in m for m in st.session_state.memory)
        enough_memory = len(st.session_state.memory) >= 4

        if has_budget and enough_memory:
            st.session_state.stage = "summary"
            st.session_state.summary_text = build_summary_from_memory(
                st.session_state.nickname, st.session_state.memory
            )
            return

    elif st.session_state.stage == "summary":
        if any(k in u for k in ["좋아요", "네", "맞아요", "추천"]):
            st.session_state.stage = "comparison"
            st.session_state.recommended_products = make_recommendation()
            ai_say("좋아요! 지금까지의 기준을 기반으로 추천을 드릴게요.")
        else:
            ai_say(
                "수정하거나 추가하고 싶은 부분이 있으시다면, 왼쪽 '쇼핑 메모리'에서 직접 수정하거나 삭제하실 수 있어요.\n"
                "또는 아래 입력창에서 말씀해주셔도 메모리에 반영해드릴게요.\n"
                "준비되셨다면 추천받기 버튼을 눌러주세요!"
            )

    elif st.session_state.stage == "product_detail":
        if any(k in u for k in ["결정", "구매", "이걸로 할게"]):
            st.session_state.stage = "purchase_decision"
            st.session_state.final_choice = st.session_state.selected_product
            ai_say("좋아요! 이제 구매 결정을 도와드릴게요.")

# =========================================================
# 16. context_setting 페이지 (1페이지 UI)
# =========================================================
def context_setting_page():
    st.title("🛒 쇼핑 에이전트 실험 준비")

    st.markdown(
        """
        <div class="info-text">
            이 페이지는 <b>AI 에이전트가 귀하의 쇼핑 취향을 기억하는 방식</b>을 테스트하기 위한 사전 설정 단계입니다.<br>
            평소 본인의 실제 쇼핑 성향을 선택하면, 그 내용을 메모리에 저장한 후 대화를 시작합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="basic-info-card">', unsafe_allow_html=True)
        st.subheader("📝 기본 정보", divider="gray")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름", placeholder="홍길동")
            st.markdown(
                '<div class="warning-text">⚠️ 사전 설문과 동일한 이름으로 입력해주세요.</div>',
                unsafe_allow_html=True,
            )
        with col2:
            phone = st.text_input("전화번호 (뒷 4자리)", placeholder="1234")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="basic-info-card">', unsafe_allow_html=True)
        st.markdown('<div class="select-question">Q1. 아래 3가지 중, 본인과 가장 가까운 쇼핑 성향은 무엇인가요?</div>', unsafe_allow_html=True)
        shopping_style = st.selectbox(
            "",
            ["가성비 우선형", "디자인/스타일 우선형", "성능·스펙 우선형"],
        )

        st.markdown('<div class="select-question">Q2. 제품을 볼 때 가장 먼저 눈이 가는 대표 색상은 무엇인가요?</div>', unsafe_allow_html=True)
        color_choice = st.selectbox(
            "",
            ["블랙", "화이트", "핑크", "네이비"],
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("쇼핑 시작하기", type="primary", use_container_width=True):
            if not name:
                st.warning("이름을 입력해주세요.")
                return

            st.session_state.nickname = name
            st.session_state.phone_number = phone

            st.session_state.primary_style = ""
            st.session_state.priority_followup_done = False

            if shopping_style == "가성비 우선형":
                add_memory("가성비, 가격을 중요하게 생각하는 편이에요.", announce=False)
                st.session_state.primary_style = "price"
                st.session_state.priority_followup_done = True

            elif shopping_style == "디자인/스타일 우선형":
                add_memory("(가장 중요) 디자인/스타일을 최우선으로 고려하고 있어요.", announce=False)
                st.session_state.primary_style = "design"

            else:
                add_memory("(가장 중요) 성능/스펙을 우선하는 쇼핑 성향이에요.", announce=False)
                st.session_state.primary_style = "performance"

            add_memory(f"색상은 {color_choice} 계열을 선호해요.", announce=False)

            st.session_state.page = "chat"
            st.rerun()

# =========================================================
# 17. main_chat_interface
# =========================================================
def main_chat_interface():
    if st.session_state.notification_message:
        try:
            st.toast(st.session_state.notification_message, icon="✅")
        except Exception:
            st.info(st.session_state.notification_message)
        st.session_state.notification_message = ""

    if len(st.session_state.messages) == 0:
        ai_say(
            f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요.\n"
            f"블루투스 헤드셋을 추천해달라고 하셨으니, 이와 관련해 {st.session_state.nickname}님에 대해 더 파악해볼게요. "
            "주로 어떤 용도로 헤드셋을 사용하실 예정인가요?"
        )

    render_step_header()

    col1, col2 = st.columns([4, 6], gap="large")

    with col1:
        render_memory_sidebar()

    with col2:
        st.markdown('<div class="chat-shell">', unsafe_allow_html=True)

        # 채팅 영역
        chat_html = '<div class="chat-display-area">'
        for msg in st.session_state.messages:
            cls = "chat-bubble-ai" if msg["role"] == "assistant" else "chat-bubble-user"
            safe = html.escape(msg["content"])
            chat_html += f'<div class="chat-bubble {cls}">{safe}</div>'

        if st.session_state.stage == "summary":
            safe_sum = html.escape(st.session_state.summary_text)
            chat_html += f'<div class="chat-summary-bubble">{safe_sum}</div>'

        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)

        # SUMMARY 단계에서 버튼
        if st.session_state.stage == "summary":
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔍 이 기준으로 추천 받기"):
                st.session_state.stage = "comparison"
                st.session_state.recommended_products = make_recommendation()
                st.rerun()
            st.info("수정하실 기준이 있으면 왼쪽 메모리 패널이나 아래 입력창에서 말씀해주세요. 😊")

        # 추천 / 상세 / 구매 단계 – 채팅 아래에 카드 버블
        if st.session_state.stage in ["comparison", "product_detail", "purchase_decision"]:
            st.markdown("<br>", unsafe_allow_html=True)
            recommend_products_ui(st.session_state.nickname, st.session_state.memory)

        if st.session_state.stage == "purchase_decision" and st.session_state.final_choice:
            p = st.session_state.final_choice
            st.success(f"🎉 **{p['name']}** 구매를 결정하셨습니다!")
            st.balloons()

        # 입력창 (항상 맨 아래 고정 느낌)
        with st.form(key="chat_form", clear_on_submit=True):
            cc1, cc2 = st.columns([8, 2])
            with cc1:
                st.text_input(
                    "msg",
                    key="user_input_text",
                    label_visibility="collapsed",
                    placeholder="메시지를 입력하세요...",
                )
            with cc2:
                if st.form_submit_button("전송"):
                    handle_input()
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 18. 라우팅
# =========================================================
if st.session_state.page == "context_setting":
    context_setting_page()
else:
    main_chat_interface()

