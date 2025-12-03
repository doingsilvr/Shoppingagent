import re
import streamlit as st
import time
import html
import json
from openai import OpenAI

client = OpenAI()

# =========================================================
# 세션 상태 초기값 설정 함수
# =========================================================
def ss_init():
    ss = st.session_state

    # 페이지 라우팅 기본값
    ss.setdefault("page", "context_setting")

    # 사용자 정보
    ss.setdefault("nickname", "")
    ss.setdefault("budget", None)

    # 대화 메시지
    ss.setdefault("messages", [])

    # 메모리
    ss.setdefault("memory", [])
    ss.setdefault("just_updated_memory", False)

    # 단계(stage)
    ss.setdefault("stage", "explore")      # 시작은 탐색
    ss.setdefault("summary_text", "")

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
# 기본 설정
# =========================================================
st.set_page_config(
    page_title="AI 쇼핑 에이전트 실험용",
    page_icon="🎧",
    layout="wide"
)

# ================================
# 전역 CSS - 반드시 한 개의 <style>만
# ================================
st.markdown(
    """
    <style>

/* ---------------------------------------
   🔒 기본 스트림릿 요소 숨기기
--------------------------------------- */
#MainMenu, footer, header, .css-1r6q61a {
    visibility: hidden;
    display: none !important;
}

/* ---------------------------------------
   📦 메인 컨테이너 레이아웃
--------------------------------------- */
.block-container {
    max-width: 1180px !important;
    padding: 1rem 1rem 2rem 1rem;
    margin: auto;
}
/* 진행상황 박스 상단 여백 제거 */
.progress-box {
    margin-top: 0px !important;
}

/* st.markdown 기본 마진 제거 */
.block-container div[data-testid="stVerticalBlock"] {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
/* ---------------------------------------
   🧩 타이틀을 박스 형태로 감싸기
--------------------------------------- */
.title-card {
    background: white;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    border: 1px solid #e5e7eb;
    margin-bottom: 1.5rem;
}

/* ===============================
   💬 말풍선 + 대화 박스
=============================== */
.chat-display-area {
    max-height: 620px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    padding: 1rem;
    background: white;
    border-radius: 16px;
    border: 1px solid #e5e7eb;
    box-sizing: border-box;
    max-width: 100% !important;
    width: 100% !important;
    margin: 0 !important;
}

.chat-input-wrapper {
    max-width: 620px;
    margin: 0.75rem auto 0 auto;
}

/* 공통 말풍선 */
.chat-bubble {
    padding: 10px 14px;
    border-radius: 16px;
    margin-bottom: 8px;
    max-width: 78%;
    word-break: break-word;
    font-size: 15px;
    line-height: 1.45;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

/* 사용자 (오른쪽) */
.chat-bubble-user {
    background: #F0F6FF;
    align-self: flex-end;
    text-align: left;
    margin-left: auto;
    border-top-right-radius: 4px;
}

/* AI (왼쪽) */
.chat-bubble-ai {
    background: #F1F0F0;
    align-self: flex-start;
    text-align: left;
    margin-right: auto;
    border-top-left-radius: 4px;
}

/* 폼 카드(info-card) 간격 개선 */
.info-card {
    margin-bottom: 20px !important;
    padding-top: 8px !important;
    padding-bottom: 8px !important;
}

/* 제목과 캡션 간격 줄이기 */
.info-card h4, 
.info-card p,
.info-card strong {
    margin-bottom: 4px !important;
}

/* caption 기본 margin 제거 */
.info-card .markdown-caption, .stCaption {
    margin-top: 0 !important;
    margin-bottom: 4px !important;
}

/* 버튼 위 여백 줄이기 */
.start-btn-area {
    margin-top: -10px !important;
}

/* ======================================================
   🔵 제품 카드 (Product Card)
====================================================== */
.product-card {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 14px !important;
    padding: 10px 8px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
    text-align: center !important;
    width: 230px !important;
    transition: box-shadow 0.2s ease !important;
}

.product-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
}

/* 내부 텍스트 정리 */
.product-card h4,
.product-card p,
.product-card div {
    margin: 0 !important;
    padding: 4px 0 !important;
}

/* 제목 간격 */
.product-card h4,
.product-card h5 {
    margin: 4px 0 8px 0 !important;
}

/* 이미지 */
.product-image {
    width: 100% !important;
    height: 160px !important;
    object-fit: cover !important;
    border-radius: 10px !important;
    margin-bottom: 12px !important;
}

/* 설명 텍스트 */
.product-desc {
    font-size: 13px !important;
    line-height: 1.35 !important;
    margin-top: 6px !important;
}

/* 캐러셀 간격 */
.carousel-wrapper {
    gap: 3px !important;
}
.carousel-item {
    margin-right: 3px !important;
}

/* ---------------------------------------
   🧠 메모리 패널 박스
--------------------------------------- */
.memory-panel-fixed {
    position: -webkit-sticky;
    position: sticky;
    top: 1rem;
    height: 620px;
    overflow-y: auto;
    background-color: #f8fafc;
    border-radius: 16px;
    padding: 1rem;
    border: 1px solid #e2e8f0;
}

.memory-item-text {
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 14px;
    padding: 0.5rem;
    border-radius: 6px;
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    margin-bottom: 0.5rem;
}

/* ---------------------------------------
   🔔 메모리 알림 팝업 위치
--------------------------------------- */
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

/* ---------------------------------------
   ✏️ 입력 폼 전송 버튼 정렬
--------------------------------------- */
div[data-testid="stForm"] > div:last-child {
    display: flex;
    justify-content: flex-end;
    margin-top: 0.5rem;
}

/* ---------------------------------------
   ➕ 메모리 추가/삭제 아이콘
--------------------------------------- */
.memory-action-btn {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    border: 1px solid #d1d5db;
    background: #ffffff;
    color: #6b7280;
    font-size: 16px;
    line-height: 24px;
    padding: 0;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.18s ease;
}

.memory-action-btn:hover {
    color: #111;
    border-color: #9ca3af;
    background: #f9fafb;
}

/* 메모리 삭제 버튼 */
.memory-delete-btn button {
    all: unset !important;
    box-sizing: border-box !important;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    border: 1px solid #d1d5db;
    background: #ffffff;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer;
    font-size: 20px !important;
    font-weight: 700 !important;
    color: #314155 !important;
    line-height: 1 !important;
    vertical-align: middle !important;
    padding: 0 !important;
    margin: 0 !important;
    transition: 0.15s ease-in-out;
}
.memory-delete-btn button:hover {
    background: #fef2f2;
    border-color: #ef4444;
    color: #ef4444;
    box-shadow: 0 0 3px rgba(239, 68, 68, 0.3);
}

/* 통합 대화창 박스 */
.chat-unified-box {
    position: relative;
    height: 620px;
    background: white;
    border-radius: 14px;
    padding: 9px;
    box-shadow: 0 0 4px rgba(0,0,0,0.05);
    border: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 650px;
    margin-bottom: 20px;
}

/* 메시지 영역 */
.chat-messages-area {
    flex: 1;
    overflow-y: auto;
    padding-right: 0.5rem;
    margin-bottom: 1rem;
}
.chat-messages-area::-webkit-scrollbar {
    width: 6px;
}
.chat-messages-area::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 10px;
}
.chat-messages-area::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 10px;
}
.chat-messages-area::-webkit-scrollbar-thumb:hover {
    background: #555;
}

    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# SYSTEM PROMPT (헤드셋 전용 + 규칙 강화)
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
- 1단계: 초기 대화에서는 사용자가 사전에 입력한 정보(중요 기준, 선호 색상)를 바탕으로 사용자 취향을 파악한다.
- 2단계: 구매 목표인 블루투스 헤드셋 기준을 순서대로 질문한다. 
- 질문 순서는 고정이 아니다. **사용자의 (가장 중요) 기준을 최우선으로 다룬다.**
- 사용자의 최우선 기준이 ‘디자인/스타일’이면  
  → 기능이나 음질 질문을 먼저 하지 말고  
  → 디자인 취향·선호 색상 같은 **관련 세부 질문을 우선한다.**
- 사용자의 최우선 기준이 ‘가격/가성비’이면  
  → 기능·디자인 질문보다 예산 확인을 먼저 한다.
- “최우선 기준”이 없을 때에만 아래의 기본 순서를 따른다:
  용도/상황 → 기능(음질) → 착용감 → 배터리 → 디자인/스타일 → 색상 → 예산
- 이미 메모리에 있거나 이미 물어본 항목들(용도, 상황, 기능 등)은 절대 다시 묻지 않고 다음 질문으로 넘어간다.
- 디자인이나 스타일 기준이 파악되면 다음 질문은 **선호 색상 또는 구체적 스타일(깔끔한/레트로 등)**에 대해 한 번 물어본다.
- 추천 단계로 넘어가기 전에 반드시 예산을 확인한다.
- (중요) 메모리가 6개 이상이면 "지금까지 기준을 정리해드릴까요?"라고 말하며, 요약/추천 단계로 넘어갈 수 있음을 알려준다.
- 메모리 기입할 때, 사용자의 발화를 그대로 기입하지 않고, 메모리 양식에 맞게 바꾼다.
- 추천 요청을 받으면 개인화된 이유가 포함된 리스트 형태로 응답한다.
- 절대로 중복된 질문을 던지지 않는다.
- 사용자가 ~가 뭐야?, ~가 중요할까? 등 답변이 아닌 질문을 던질 경우, 기준 확인을 위한 질문 대신 답변을 우선적으로 진행하며, 그 내용을 기준으로 쌓아가도록 리드한다.
- 사용자가 특정 상품 번호를 물어보면 그 제품의 특징, 장단점, 리뷰 요약 등을 제공하고, 사용자의 기준을 반영해 개인화된 설명을 덧붙인다.

[메모리 활용]
- 메모리에 저장된 기준을 항상 반영해 대화를 이어간다.
- 메모리와 사용자의 최신 발언이 충돌하면 
  "기존에 ~라고 하셨는데, 기준을 바꾸실까요? 아니면 둘 다 고려해드릴까요?"라고 정중히 확인한다.

[출력 규칙]
- 한 번에 너무 많은 질문을 하지 않고 자연스럽게 한두 개씩 묻는다.
- 중복 질문은 피하며 꼭 필요한 경우 "다시 한번만 확인할게요"라고 말한다.
- 전체 톤은 부드러운 존댓말을 유지한다.
"""
 # =========================================================
# 메모리 알림 표시 함수
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
# 유틸리티 함수
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

def extract_memory_with_gpt(user_input, memory_text):
    """
    GPT에게 사용자 발화에서 저장할 만한 '쇼핑 기준'을 직접 뽑게 하는 함수.
    JSON 형태로 반환.
    """
    prompt = f"""
당신은 '헤드셋 쇼핑 기준 요약 AI'입니다.
대화는 항상 '블루투스 헤드셋'에 대한 내용입니다.

사용자가 방금 말한 문장:
"{user_input}"

현재까지 저장된 기준:
{memory_text if memory_text else "(없음)"}

위 발화에서 '추가해야 할 쇼핑 기준'이 있으면 아래 JSON 형태로만 출력하세요:

{{
  "memories": [
      "문장1",
      "문장2"
  ]
}}

규칙:
- 기준은 반드시 '블루투스 헤드셋 구매 기준'으로 변환해서 정리한다.
- 문장은 완성된 기준 형태로 출력.
- 브랜드 언급 → "선호하는 브랜드는 ~ 쪽이에요."
- 착용감/귀 아픔/편안 → "착용감이 편한 제품을 선호하고 있어요."
- 음악/노래/감상 → "주로 음악 감상 용도로 사용할 예정이에요."
- 출퇴근 → "출퇴근 시 사용할 용도예요."
- 예쁜/디자인 → "디자인/스타일을 중요하게 생각해요."
- 색상 언급 → "색상은 ~ 계열을 선호해요."
- 노이즈 → "노이즈캔슬링 기능을 고려하고 있어요."
- 예산 N만원 → "예산은 약 N만 원 이내로 생각하고 있어요."
- 기준이 전혀 없으면 memories는 빈 배열로만 출력.
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
# 메모리 추가/수정/삭제
# =========================================================
def _is_color_memory(text: str) -> bool:
    t = text.replace("(가장 중요)", "")
    if "색상" in t and "선호" in t:
        return True
    color_keywords = ["화이트", "블랙", "네이비", "퍼플", "실버", "그레이", "핑크", "보라", "골드"]
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

    # 색상 카테고리 충돌 제거 (평소 색상 ~ 포함해서 전부)
    if _is_color_memory(mem_text_stripped):
        st.session_state.memory = [m for m in st.session_state.memory if not _is_color_memory(m)]

    # 디자인/스타일 기준 충돌 제거
    if any(k in mem_text_stripped for k in ["디자인", "스타일", "깔끔", "레트로", "미니멀", "화려", "세련"]):
        st.session_state.memory = [m for m in st.session_state.memory if "디자인/스타일" not in m]

    # 중복/갱신 처리
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
# 요약 / 추천 관련 유틸
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
# 카탈로그 (생략 없이 그대로 사용)
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
# 추천 섹션 UI
# =========================================================
def recommend_products(name, mems, is_reroll=False):
    products = filter_products(mems, is_reroll)
    budget = extract_budget(mems)

    if st.session_state.stage == "comparison":
        st.session_state.current_recommendation = products

    st.markdown("#### 🎧 추천 후보 리스트")
    st.markdown("고객님의 기준을 반영한 상위 3개 제품입니다. 궁금한 제품에 대해 상세 정보 보기를 클릭해 궁금한 점을 확인하세요.\n")

    cols = st.columns(3, gap="small")

    for i, c in enumerate(products[:3]):
        one_line_reason = f"👉 {c['review_one']}"
        with cols[i]:
            st.markdown(
                f"""
                <div class="product-card">
                    <h4><b>{i+1}. {c['name']}</b></h4>
                    <img src="{c['img']}" class="product-image"/>
                    <div><b>{c['brand']}</b></div>
                    <div>💰 가격: 약 {c['price']:,}원</div>
                    <div>⭐ 평점: {c['rating']:.1f}</div>
                    <div>🏅 특징: {_brief_feature_from_item(c)}</div>
                    <div style="margin-top:8px; font-size:13px; color:#374151;">
                        {one_line_reason}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button(f"후보 {i+1} 상세 정보 보기", key=f"detail_btn_{i}"):
                selected = c
                st.session_state.selected_product = selected
                st.session_state.current_recommendation = [selected]
                st.session_state.stage = "product_detail"
                st.session_state.product_detail_turn = 0

                personalized_reason = generate_personalized_reason(selected, mems, name) if 'generate_personalized_reason' in globals() else ""
                detail_block = (
                    f"**{selected['name']} ({selected['brand']})**\n"
                    f"- 가격: {selected['price']:,}원\n"
                    f"- 평점: {selected['rating']:.1f} / 5.0\n"
                    f"- 색상: {', '.join(selected['color'])}\n"
                    f"- 리뷰 요약: {selected['review_one']}\n\n"
                    f"**추천 이유**\n"
                    f"- 지금까지 말씀해 주신 메모리를 반영해 골라봤어요.\n"
                    f"- {personalized_reason}\n\n"
                    f"**궁금한 점이 있다면?**\n"
                    f"- 예: 배터리 성능은 어때?\n"
                    f"- 예: 부정적인 리뷰는 어떤 내용이야?\n"
                )
                ai_say(detail_block)
                st.rerun()
                return

    if not st.session_state.comparison_hint_shown:
        ai_say("\n궁금한 제품의 상세 보기 버튼을 클릭해 궁금한 점을 질문할 수 있어요 🙂")
        st.session_state.comparison_hint_shown = True

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

# =========================================================
# 제품 상세 프롬프트
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

# =========================================================
# GPT 응답
# =========================================================
def gpt_reply(user_input: str) -> str:
    if not client:
        if "추천" in user_input:
            return "현재 API 키가 없어도, '음질 좋은 헤드셋' 기준으로라면 Sony WH-1000XM5, Bose QC45, JBL 770NC 정도를 예시로 들 수 있어요."
        return "현재 API 키가 설정되지 않아 응답을 생성할 수 없습니다."

    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    nickname = st.session_state.nickname

    # 1) product_detail 단계: SYSTEM 프롬프트 없이, 전용 프롬프트 사용
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
        any(k in m for k in ["디자인", "스타일", "깔끔", "세련", "미니멀", "레트로", "예쁜", "예쁘", "심플"])
        for m in st.session_state.memory
    )
    is_color_in_memory = any("색상" in m for m in st.session_state.memory)
    memory_text_lower = memory_text.lower()
    is_usage_in_memory = any(
        k in memory_text for k in ["용도로", "운동", "게임", "출퇴근", "여행", "음악 감상"]
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

[현재까지 저장된 쇼핑 기준]
{memory_text if memory_text else "아직 저장된 기준이 없습니다."}

[사용자 발화]
{user_input}

위 정보를 참고해, 블루투스 헤드셋 쇼핑 도우미로서 다음 말을 한국어 존댓말로 자연스럽게 이어가세요.
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
# 로그 유틸
# =========================================================
def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})

def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})

def summary_step():
    st.session_state.summary_text = generate_summary(
        st.session_state.nickname,
        st.session_state.memory
    )

def comparison_step(is_reroll=False):
    recommend_products(st.session_state.nickname, st.session_state.memory, is_reroll)

# =========================================================
# 유저 입력 처리
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
        user_input.endswith("?")
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
        if mem_count >= 4 and not has_budget:
            ai_say(
                "네, 이제 어느 정도 기준을 파악한 것 같아요. "
                "이제 **예산/가격대**를 알려주시면 추천 단계로 넘어가 볼게요!"
            )
            st.rerun()
            return

        # 기준 6개 이상 + 예산 있음 → 요약 단계로 전환
        if mem_count >= 6 and has_budget:
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
        ai_say("알겠습니다. 지금까지의 기준을 정리한 뒤, 그 기준에 맞는 헤드셋 후보들을 보여드릴게요.")
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
# 메모리 패널
# =========================================================
def top_memory_panel():
    with st.container():
        if len(st.session_state.memory) == 0:
            st.caption("아직 파악된 정보가 없습니다. 대화 중에 기준이 차곡차곡 쌓일 거예요.")
        else:
            for i, item in enumerate(st.session_state.memory):
                cols = st.columns([7, 1])
                with cols[0]:
                    display_text = naturalize_memory(item)
                    st.markdown(f"**기준 {i+1}.**", help=item, unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="memory-item-text">{display_text}</div>',
                        unsafe_allow_html=True
                    )
                with cols[1]:
                    st.markdown('<div class="memory-delete-btn">', unsafe_allow_html=True)
                    if st.button("X", key=f"del_{i}"):
                        delete_memory(i)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### ➕ 새 메모리 추가")
        new_mem = st.text_input(
            "새 메모리 추가",
            placeholder="예: 노이즈캔슬링 필요 / 음질 중요",
            label_visibility="collapsed",
            key="new_mem_input"
        )
        if st.button("추가", key="add_mem_btn", use_container_width=True):
            if new_mem.strip():
                add_memory(new_mem.strip(), announce=True)
                st.session_state.just_updated_memory = True
                st.rerun()

def render_progress_sidebar():
    stage_to_step = {
        "explore": 1,
        "summary": 1,
        "comparison": 2,
        "product_detail": 3
    }
    current = stage_to_step.get(st.session_state.stage, 1)

    st.markdown("""
    <style>
    .progress-box {
        margin-top: 0px !important;
        background: #F8FAFC;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 20px 18px;
        margin-bottom: 18px;
    }
    .progress-title {
        font-size: 17px;
        font-weight: 700;
        margin-bottom: 12px;
        color: #111;
    }
    .step-item {
        display: flex;
        align-items: center;
        margin-bottom: 12px;
        font-size: 15px;
        color: #4B5563;
    }
    .step-circle {
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: #E5E7EB;
        color: #6B7280;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 14px;
        font-weight: 600;
        margin-right: 10px;
    }
    .step-active {
        background: #3B82F6;
        color: white;
    }
    .step-label-active {
        color: #1D4ED8;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="progress-box">', unsafe_allow_html=True)
    st.markdown('<div class="progress-title">진행 상황</div>', unsafe_allow_html=True)

    steps = ["구매 기준 탐색", "후보 비교", "최종 결정"]
    for i, label in enumerate(steps, start=1):
        is_active = (i == current)
        circle_class = "step-circle step-active" if is_active else "step-circle"
        label_class = "step-label-active" if is_active else ""
        st.markdown(
            f'<div class="step-item">'
            f'<div class="{circle_class}">{i}</div>'
            f'<div class="{label_class}">{label}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

def render_scenario_box():
    st.markdown(
        """
        <div style="
            background:#F0F6FF;
            padding:28px 32px;
            border-radius:18px;
            margin-bottom:24px;
            line-height:1.6;
        ">
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
        """,
        unsafe_allow_html=True
    )

# =========================================================
# 메인 대화 UI
# =========================================================
def chat_interface():
    render_notification()

    if len(st.session_state.messages) == 0:
        ai_say(
            f"안녕하세요 {st.session_state.nickname}님! 😊 저는 블루투스 헤드셋 쇼핑을 도와드리는 AI 도우미예요. "
            "대화를 통해 고객님의 기준을 기억하면서 함께 헤드셋을 찾아볼게요. "
            "먼저, 주로 어떤 용도로 사용하실 예정인가요?"
        )

    render_scenario_box()
    col_mem, col_chat = st.columns([0.23, 0.77], gap="small")

    with col_mem:
        st.markdown(
            """
            <style>
            div[data-testid="stVerticalBlock"]:first-of-type {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        render_progress_sidebar()
        st.markdown("#### 🧠 메모리")
        top_memory_panel()

    with col_chat:
        st.markdown("#### 💬 대화창")

        chat_html = '<div class="chat-display-area">'
        for msg in st.session_state.messages:
            safe = html.escape(msg["content"])
            if msg["role"] == "assistant":
                chat_html += f'<div class="chat-bubble chat-bubble-ai">{safe}</div>'
            else:
                chat_html += f'<div class="chat-bubble chat-bubble-user">{safe}</div>'

        if st.session_state.stage == "summary":
            safe_summary = html.escape(st.session_state.summary_text)
            chat_html += f'<div class="chat-bubble chat-bubble-ai">{safe_summary}</div>'

        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)

        if st.session_state.stage == "summary":
            if st.button("🔍 추천 받아보기", key="go_reco_button", use_container_width=True):
                st.session_state.stage = "comparison"
                st.rerun()

        if st.session_state.stage == "comparison":
            comparison_step()

        with st.form(key="chat_form_main", clear_on_submit=True):
            user_text = st.text_area(
                "",
                placeholder="원하는 기준이나 궁금한 점을 알려주세요!",
                height=80,
            )
            send = st.form_submit_button("전송")
        if send and user_text.strip():
            user_say(user_text)
            handle_user_input(user_text)

# =========================================================
# 사전 정보 입력 페이지
# =========================================================
def context_setting():
    st.markdown("### 🧾 실험 준비 ")
    st.caption("헤드셋 구매에 반영될 기본 정보와 평소 취향을 간단히 입력해 주세요. 이후 실험은 과거에도 대화한 내역이 있다는 가정 하에 진행됩니다.")

    st.markdown("---")

    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**1. 이름**")
    st.caption("사전 설문에서 작성한 이름과 동일해야 합니다.")
    nickname = st.text_input("이름 입력", placeholder="예: 홍길동", key="nickname_input")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**2. 선호하는 색상**")
    st.caption("평소 쇼핑할 때 선호하는 색상을 입력해 주세요.")
    color_option = st.text_input("선호 색상", placeholder="예: 화이트 / 블랙 / 네이비 등", key="color_input")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**3. 쇼핑할 때 가장 중요하게 보는 기준**")
    st.caption("평소 쇼핑할 때 어떤 기준을 가장 중요하게 고려하시나요?")
    priority_option = st.radio(
        "가장 중요했던 기준을 선택해 주세요.",
        ("디자인/스타일", "가격/가성비", "성능/품질"),
        index=None,
        key="priority_radio",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown('<div class="start-btn-area">', unsafe_allow_html=True)
    if st.button("헤드셋 쇼핑 시작하기 (다음 단계로 이동)", use_container_width=True):
        if not nickname.strip() or not priority_option or not color_option.strip():
            st.warning("모든 항목을 입력해 주세요.")
            st.markdown("</div>", unsafe_allow_html=True)
            return
    
        st.session_state.nickname = nickname.strip()
    
        color_particle = get_eul_reul(color_option.strip())
        color_mem = f"색상은 {color_option.strip()}{color_particle} 선호해요."
        priority_particle = get_eul_reul(priority_option.strip())
        priority_mem = f"(가장 중요) {priority_option.strip()}{priority_particle} 중요하게 생각해요."
    
        add_memory(color_mem, announce=False)
        add_memory(priority_mem, announce=False)
    
        st.session_state.messages = []
        st.session_state.stage = "explore"
        st.session_state.page = "chat"
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 라우팅
# =========================================================
if "page" not in st.session_state:
    st.session_state.page = "context_setting"

if st.session_state.page == "context_setting":
    context_setting()
else:
    chat_interface()
