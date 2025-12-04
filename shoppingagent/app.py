import re
import streamlit as st
import time
import html
import json
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

    ss.setdefault("page", "context_setting")

    # 사용자 정보
    ss.setdefault("nickname", "")
    ss.setdefault("phone_number", "")

    # 대화 관련
    ss.setdefault("messages", [])
    ss.setdefault("turn_count", 0)

    # 메모리
    ss.setdefault("memory", [])
    ss.setdefault("just_updated_memory", False)
    ss.setdefault("memory_changed", False)
    ss.setdefault("notification_message", "")

    # 단계(stage)
    ss.setdefault("stage", "explore")      # explore → summary → comparison → product_detail → purchase_decision
    ss.setdefault("summary_text", "")
    ss.setdefault("detail_mode", False)

    # 추천/상세 정보 컨트롤
    ss.setdefault("current_recommendation", [])
    ss.setdefault("recommended_products", [])
    ss.setdefault("selected_product", None)
    ss.setdefault("product_detail_turn", 0)
    ss.setdefault("comparison_hint_shown", False)

    # 결정 관련
    ss.setdefault("final_choice", None)
    ss.setdefault("decision_turn_count", 0)
    ss.setdefault("purchase_intent_score", None)

ss_init()

# ========================================================
# 2. CSS 스타일 (기존 UI 완벽 유지)
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
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 14px !important;
        padding: 15px;
        text-align: center;
        min-height: 430px;      /* ← 카드 높이 통일 */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 4px 6px rgba(0,0,0,0.03);
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
# 3. SYSTEM PROMPT (헤드셋 전용 + 메모리/프로필 강조)
# =========================================================
SYSTEM_PROMPT = r"""
너는 'AI 쇼핑 도우미'이며 **항상 블루투스 헤드셋** 기준을 파악해 추천을 돕는 역할을 한다.
스마트폰, 노트북, 태블릿, 일반 전자기기 등 다른 카테고리에 대한 추천이나 질문 유도는 절대 하지 않는다.
이어폰, 인이어 타입, 유선 헤드셋도 추천하지 않는다. 대화 전 과정에서 '블루투스 헤드셋'만을 전제로 생각한다.

[역할 규칙]
- 최우선 규칙: 메모리에 이미 저장된 기준(특히 용도, 상황, 기능)은 절대 다시 물어보지 않고 바로 다음 단계의 구체적인 질문으로 전환한다.
- 너의 가장 큰 역할은 **사용자 메모리(쇼핑 기준 프로필)를 읽고, 갱신하고, 설명하면서 추천을 돕는 것**이다.
- 메모리에 이미 저장된 내용(특히 용도, 상황, 기능, 색상, 스타일 등)은 **다시 묻지 말고**, 그 다음 단계의 구체적인 질문으로 넘어간다.
- 메모리에 실제 저장될 경우(제어창에), 이 기준을 기억해둘게요" 혹은 "이번 쇼핑에서는 해당 내용을 고려하지 않을게요", “지금 말씀해주신 내용은 메모리에 추가해두면 좋을 것 같아요.”라고 표현을 먼저 제시한다.
- 사용자가 모호하게 말하면 부드럽게 구체적으로 다시 물어본다
- 사용자가 기준을 바꾸거나 기존 메모리와 충돌하는 발화를 하면  
  “제가 기억하고 있던 내용은 ~였는데, 이번에는 기준을 바꾸실까요? 아니면 둘 다 함께 고려해볼까요?”라고 부드럽게 확인한다.
- 사용자가 “모르겠어요 / 글쎄요 / 아직 생각 안 했어요” 라고 말하면  
  “그렇다면 실제로 쓰실 상황을 떠올려보면 어떨까요? 출퇴근, 공부, 게임 중에 어떤 상황이 가장 많을까요?”처럼 맥락 중심으로 되묻거나, "제 생각은 이 기준이 중요하게 고려되면 좋을 것 같아요."로 안내한다.

[대화 흐름 규칙]
- 1단계(explore): 사용자가 사전에 입력한 정보 + 대화 중 발화를 바탕으로,  
  **용도/상황, 음질, 착용감, 노이즈캔슬링, 배터리, 디자인/스타일, 색상, 예산** 순서대로 물어보도록 한다.
- “가장 중요한 기준”이 있으면 그 기준을 먼저 다뤄야 한다.
  - 예: (가장 중요)가 디자인/스타일 → 기능 질문보다 **디자인/스타일 + 색상** 관련 질문을 먼저.
  - 예: (가장 중요)가 가격/가성비 → 다른 질문보다 **예산/가격대**를 먼저.
- “최우선 기준”이 없는 경우에만 기본 순서를 따른다:  
  용도/상황 → 음질 → 착용감 → 배터리 → 디자인/스타일 → 색상 → 예산
- 이미 메모리에 있는 항목은 다시 물어보지 않고 다음 기준으로 넘어간다.
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
- 중복 질문이 필요할 때에는 1번만 가능하며, 그것도 “정확한 추천을 위해 한 번만 다시 확인할게요.”라고 이유를 덧붙인다.
- 항상 **헤드셋** 기준으로만 말하며, 다른 기기(스마트폰, 노트북 등)은 예로만 언급하더라도 추천 대상이 되지 않게 한다.
- 말투는 부드러운 존댓말을 유지하되, 너무 딱딱하지 않게 대화하듯 말한다.
"""

# =========================================================
# 4. 유틸리티 함수 (조사, 정규화 등)
# =========================================================
def get_eul_reul(noun: str) -> str:
    """을/를 자동 선택"""
    if not noun:
        return "을"
    last_char = noun[-1]
    if not ('\uAC00' <= last_char <= '\uD7A3'):
        return "를"
    last_char_code = ord(last_char) - 0xAC00
    jong = last_char_code % 28
    return "를" if jong == 0 else "을"


def naturalize_memory(text: str) -> str:
    """메모리 문장을 통일된 형태로 정리"""
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


def extract_memory_with_gpt(user_input: str, memory_text: str):
    """
    GPT에게 사용자 발화에서 저장할 만한 '헤드셋 쇼핑 메모리'를 뽑게 하는 함수.
    JSON 형태로만 응답하게 해서 안정적으로 파싱.
    """
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
- 아래 규칙들을 참고해 문장을 만들어도 좋습니다.

[변환 규칙 예시]
- 브랜드 언급 → "선호하는 브랜드는 ~ 쪽이에요."
- 착용감/귀 아픔/편안 → "착용감이 편한 제품을 선호하고 있어요."
- 음악/노래/감상 → "주로 음악 감상 용도로 사용할 예정이에요."
- 출퇴근 → "출퇴근 시 사용할 용도예요."
- 예쁜/디자인 → "디자인/스타일을 중요하게 생각해요."
- 깔끔/화려/레트로/심플 → "원하는 디자인/스타일이 뚜렷한 편이에요."
- 색상 언급 → "색상은 ~ 계열을 선호해요."
- 노이즈 → "노이즈캔슬링 기능을 고려하고 있어요."
- 예산 N만원 → "예산은 약 N만 원 이내로 생각하고 있어요."

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


def add_memory(mem_text: str, announce: bool = True):
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

    # 중복/갱신 처리
    for i, m in enumerate(st.session_state.memory):
        m_stripped = m.replace("(가장 중요)", "").strip()
        if mem_text_stripped in m_stripped or m_stripped in mem_text_stripped:
            # (가장 중요) 플래그 승급
            if "(가장 중요)" in mem_text and "(가장 중요)" not in m:
                for j, existing_m in enumerate(st.session_state.memory):
                    st.session_state.memory[j] = existing_m.replace("(가장 중요)", "").strip()
                st.session_state.memory[i] = mem_text
                st.session_state.just_updated_memory = True
                if announce:
                    st.session_state.notification_message = "🌟 최우선 메모리가 업데이트되었어요."
                st.session_state.memory_changed = True
            return

    st.session_state.memory.append(mem_text)
    st.session_state.just_updated_memory = True
    st.session_state.memory_changed = True

    if announce:
        st.session_state.notification_message = "🧩 메모리에 새로운 내용을 추가했어요."


def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.just_updated_memory = True
        st.session_state.memory_changed = True
        st.session_state.notification_message = "🧹 메모리에서 해당 기준을 삭제했어요."


def update_memory(idx: int, new_text: str):
    if 0 <= idx < len(st.session_state.memory):
        if "(가장 중요)" in new_text:
            for i, existing_m in enumerate(st.session_state.memory):
                st.session_state.memory[i] = existing_m.replace("(가장 중요)", "").strip()
        st.session_state.memory[idx] = new_text.strip()
        st.session_state.just_updated_memory = True
        st.session_state.memory_changed = True
        st.session_state.notification_message = "🔄 메모리가 수정되었어요."



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
    tags_str = " ".join(product.get("tags", []))

    if "음질" in mem_str and ("음질" in tags_str or "균형 음질" in tags_str):
        reasons.append("중요하게 말씀하셨던 **음질** 만족도가 높은 편이에요.")
    if "착용감" in mem_str and any(t in tags_str for t in ["편안함", "가벼움", "경량", "착용감"]):
        reasons.append("장시간 착용해도 편한 **착용감**이 강점이에요.")
    if "노이즈캔슬링" in mem_str and "노이즈캔슬링" in tags_str:
        reasons.append("원하셨던 **노이즈캔슬링** 성능이 우수한 제품이에요.")
    if "디자인" in mem_str or "스타일" in mem_str:
        if "디자인" in tags_str:
            reasons.append("말씀해주신 **디자인/스타일 취향**과도 잘 맞는 제품이에요.")

    if reasons:
        reasons.append(f"\n또한 제가 기억하고 있는 {name}님의 취향을 고려했을 때, 이 제품이 꽤 잘 맞을 것 같아요!")

    if not reasons:
        return f"{name}님의 전체 메모리를 기준으로 볼 때, 전반적으로 잘 어울리는 균형 잡힌 선택으로 보입니다."

    return "\n".join(reasons)


# =========================================================
# 7. 상품 카탈로그 (기존 그대로)
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

    # 1) product_detail 단계: 전용 프롬프트 사용
    if st.session_state.stage == "product_detail":
        product = st.session_state.selected_product
        if not product:
            st.session_state.stage = "comparison"
            return "선택된 제품 정보가 없어서, 다시 추천 목록으로 돌아갈게요."
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
        any(k in m for k in ["디자인", "스타일", "예쁘", "깔끔", "세련", "미니멀", "레트로"])
        for m in st.session_state.memory
    )
    
    design_priority = any(
        "(가장 중요)" in m and any(k in m for k in ["디자인", "스타일", "예쁘", "깔끔"])
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
                "[필수 가이드: 사용 용도/상황은 이미 파악되었습니다. "
                "절대 용도/상황을 재차 묻지 말고 다음 기준(음질/착용감/디자인 등)으로 넘어가세요.]\n"
            )

    # 디자인이 (가장 중요) + 아직 색상/스타일 세부 없음 → 이번 턴에 디자인/색상 질문만
    design_priority = is_design_in_memory and "(가장 중요)" in memory_text
    has_style_detail = any(k in memory_text for k in ["깔끔", "레트로", "미니멀", "화려", "세련"])
    has_color_detail = is_color_in_memory
    if st.session_state.stage == "explore" and design_priority and not (has_style_detail and has_color_detail):
        stage_hint += """
[디자인 최우선 규칙 – 이번 턴 필수]
- 이번 턴에는 기능/음질/배터리/예산 질문을 하지 않습니다.
- 아직 선호 색상이나 구체적인 디자인 스타일(깔끔한, 레트로 등)을 물어보지 않았다면,
  그 중 한 가지만 골라 **단 하나의 질문만** 하세요.
"""

    # 항상 헤드셋 대화라는 힌트
    stage_hint += "\n[중요] 이 대화는 항상 '블루투스 헤드셋 쇼핑'에 대한 대화입니다. 스마트폰/노트북 등 다른 기기를 언급하거나 추천하지 마세요.\n"

    prompt_content = f"""{stage_hint}

[현재까지 저장된 쇼핑 메모리]
{memory_text if memory_text else "아직 저장된 메모리가 없습니다."}

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
# 9. 로그 유틸
# =========================================================
def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})


def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})
    st.session_state.turn_count += 1
# =========================================================
# 10. 시나리오 박스 출력
# =========================================================
def render_scenario():
    st.markdown(
        """
        <div class="scenario-box">
            🔍 <b>실험 시나리오</b><br>
            지금부터 AI 쇼핑 도우미가 사용자의 취향 메모리를 기반으로<br>
            헤드셋 구매 기준을 함께 정리하고, 가장 잘 맞는 제품을 추천해드립니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 11. 단계 진행바 UI
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
            <div class="step-desc">사용자의 취향과 기준을 파악하는 단계입니다.</div>
        </div>
        <div class="step-item {is_active('summary')}">
            <div class="step-header-group">
                <div class="step-circle">2</div>
                <div class="step-title">요약 확인</div>
            </div>
            <div class="step-desc">정리된 기준을 확인한 뒤 추천으로 이동합니다.</div>
        </div>
        <div class="step-item {is_active('comparison')}">
            <div class="step-header-group">
                <div class="step-circle">3</div>
                <div class="step-title">상품 추천</div>
            </div>
            <div class="step-desc">기준에 맞는 헤드셋을 비교합니다.</div>
        </div>
        <div class="step-item {is_active('product_detail')}">
            <div class="step-header-group">
                <div class="step-circle">4</div>
                <div class="step-title">상세 정보</div>
            </div>
            <div class="step-desc">선택한 제품의 상세 정보를 안내합니다.</div>
        </div>
        <div class="step-item {is_active('purchase_decision')}">
            <div class="step-header-group">
                <div class="step-circle">5</div>
                <div class="step-title">구매 결정</div>
            </div>
            <div class="step-desc">최종 결정을 진행하는 단계입니다.</div>
        </div>
    </div>
    """
    st.markdown(step_items, unsafe_allow_html=True)


# =========================================================
# 12. 좌측 메모리 패널
# =========================================================
def render_memory_sidebar():
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
            st.markdown(f"<div class='memory-block'><div class='memory-text'>{mem}</div></div>", unsafe_allow_html=True)
        with c2:
            if st.button("X", key=f"delete_mem_{i}"):
                delete_memory(i)
                st.rerun()

    # --------------------------
    # 📌 수동 메모리 추가 UI
    # --------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**✏️ 메모리 직접 추가하기**")

    new_mem = st.text_input("추가할 기준", key="manual_memory_add")

    if st.button("메모리 추가하기"):
        if new_mem.strip():
            add_memory(new_mem.strip())
            st.success("메모리에 추가했어요!")
            st.rerun()

# =========================================================
# 13. 추천 UI (3개 카드)
# =========================================================
def recommend_products_ui(name, mems):
    stage = st.session_state.stage
    items = st.session_state.recommended_products

    # comparison, product_detail 둘 다 동일하게 렌더
    if stage in ["comparison", "product_detail"]:
        if not items:
            st.info("추천 제품을 준비 중이에요!")
            return

        st.markdown("### 🔎 추천 제품 비교")

        row = st.columns(3)
        for idx, c in enumerate(items[:3]):
            with row[idx]:
                st.markdown(
                    f"""
                    <div class="product-card">
                        <img src="{c['img']}" class="product-img">
                        <div class="product-title">{c['name']}</div>
                        <div class="product-price">{c['price']:,}원</div>
                        <div style="font-size:13px; color:#6b7280;">⭐ {c['rating']:.1f} / 리뷰 {c['reviews']}</div>
                        <div style="margin-top:10px; font-size:13px; color:#4b5563;">
                            {generate_personalized_reason(c, mems, name)}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("상세보기", key=f"detail_{idx}"):
                    # 선택된 제품 상태 저장
                    st.session_state.selected_product = c
                    st.session_state.stage = "product_detail"
                    st.session_state.product_detail_turn = 0
                
                    # 🔥 상세 진입 시 자동 설명 메시지 생성
                    reason = generate_personalized_reason(c, st.session_state.memory, st.session_state.nickname)
                    ai_say(
                        f"선택하신 **{c['name']}** 제품이 {st.session_state.nickname}님께 잘 맞는 이유는 다음과 같아요:\n\n{reason}"
                    )
                
                    st.rerun()

# =========================================================
# 14. 요약 생성 함수
# =========================================================
def build_summary_from_memory(name, mems):
    if not mems:
        return f"{name}님의 취향 기준이 아직 충분하지 않아요. 몇 가지 더 여쭤봐도 될까요?"

    lines = []
    priority_mem = detect_priority(mems)

    if priority_mem:
        lines.append(f"• (가장 중요) {priority_mem}")
    for m in mems:
        if "(가장 중요)" not in m:
            lines.append(f"• {m}")

    summary = (
        f"제가 이해한 {name}님의 헤드셋 쇼핑 기준은 다음과 같아요:\n\n"
        + "\n".join(lines)
        + "\n\n혹시 수정하거나 추가할 부분이 있을까요?"
    )
    return summary


# =========================================================
# 15. 추천 모델 (메모리 기반 점수)
# =========================================================
def score_item_with_memory(item, mems):
    score = 0
    
    mtext = " ".join(mems)

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
    return score
    # 예산 체크
    budget = extract_budget(mems)
    if budget:
        if item["price"] > budget:
            diff = item["price"] - budget
            if diff > 100000:
                score -= 200   # 크게 초과한 경우 강한 패널티
            else:
                score -= 80    # 조금 초과한 경우 약한 패널티
        else:
            score += 30        # 예산 이내면 가산점
            
def make_recommendation():
    scored = [(score_item_with_memory(item, st.session_state.memory), item) for item in CATALOG]
    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:3]]


# =========================================================
# 16. 사용자 입력 처리
# =========================================================
def handle_input():
    # 🔹 text_input 의 key 와 반드시 동일해야 함
    u = st.session_state.user_input_text.strip()
    if not u:
        return

    ss = st.session_state

    user_say(u)

    # ----------------------------
    # 1) 카테고리 드리프트 방지
    # ----------------------------
    drift_words = ["스마트폰", "휴대폰", "핸드폰", "아이폰", "갤럭시", "폰"]
    if any(w in u for w in drift_words):
        ai_say("앗! 지금은 블루투스 헤드셋 추천 단계예요 😊 다른 기기보단 헤드셋 기준으로만 도와드릴게요!")
        return

    # ----------------------------
    # 2) 메모리 추출 및 충돌 처리
    # ----------------------------
    memory_before = ss.memory.copy()
    memory_text = "\n".join([naturalize_memory(m) for m in ss.memory])
    extracted = extract_memory_with_gpt(u, memory_text)

    if extracted:
        for mem in extracted:
            before_len = len(ss.memory)
            add_memory(mem)   # 내부에서 naturalize + 충돌 처리됨
            after_len = len(ss.memory)

            # 추가된 경우에만 토스트 알림
            if after_len > before_len:
                ss.notification_message = f"🧩 '{mem}' 내용을 기억해둘게요."

    # ----------------------------
    # 3) 예산 유도
    # ----------------------------
    has_budget = any("예산" in m for m in ss.memory)
    mem_count = len(ss.memory)

    if mem_count >= 3 and not has_budget:
        ai_say("추천 정확도를 높이려면 예산도 알려주시면 좋아요! 😊 어느 정도 가격대를 생각하고 계실까요?")
        return

    # ----------------------------
    # 4) SUMMARY 진입 조건: 메모리 ≥ 5개 + 예산 있음
    # ----------------------------
    enough_memory = mem_count >= 5

    if ss.stage == "explore" and has_budget and enough_memory:
        ss.stage = "summary"
        ss.summary_text = build_summary_from_memory(ss.nickname, ss.memory)
        return

    # ----------------------------
    # 5) 기본 GPT 응답
    # ----------------------------
    reply = gpt_reply(u)
    ai_say(reply)

    if ss.stage == "explore":
        if len(ss.memory) >= 4:
            ss.stage = "summary"
            ss.summary_text = build_summary_from_memory(
                ss.nickname, ss.memory
            )
            ai_say(ss.summary_text)

    elif ss.stage == "summary":
        if any(k in u for k in ["좋아요", "네", "맞아요", "맞는 것 같아요", "추천"]):
            ss.stage = "comparison"
            ss.recommended_products = make_recommendation()
            ai_say("좋아요! 지금까지의 기준을 기반으로 추천을 드릴게요.")
        else:
            ai_say("수정하거나 추가하고 싶은 부분이 있으실까요?")

    elif ss.stage == "product_detail":
        if any(k in u for k in ["결정", "구매", "이걸로 할게"]):
            ss.stage = "purchase_decision"
            ss.final_choice = ss.selected_product
            ai_say("좋아요! 이제 구매 결정을 도와드릴게요.")

    # 나머지 단계는 main_chat_interface에서 처리
# =========================================================
# 17. context_setting 페이지 (Q1/Q2 새 구조 적용)
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

    with st.container(border=True):
        st.subheader("📝 기본 정보")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("이름", placeholder="홍길동")
            st.markdown(
                '<div class="warning-text">⚠️ 사전 설문과 동일한 이름으로 입력해주세요.</div>',
                unsafe_allow_html=True,
            )
        with col2:
            phone = st.text_input("전화번호 (뒷 4자리)", placeholder="1234")

        st.markdown("---")

        # -----------------------
        # Q1. 쇼핑 성향
        # -----------------------
        st.subheader("Q1. 아래 3가지 중, 본인과 가장 가까운 쇼핑 성향은 무엇인가요?")
        shopping_style = st.selectbox(
            "",
            ["가성비 우선형", "디자인/스타일 우선형", "성능·스펙 우선형"],
        )

        # -----------------------
        # Q2. 선호 색상
        # -----------------------
        st.subheader("Q2. 아래 색상 중, 제품을 고를 때 가장 먼저 눈이 가는 색상은 무엇인가요?")
        color_choice = st.selectbox(
            "",
            ["블랙", "화이트", "핑크", "네이비"],
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # -----------------------
        # 저장 버튼
        # -----------------------
        if st.button("쇼핑 시작하기 (정보 저장)", type="primary", use_container_width=True):
            if not name:
                st.warning("이름을 입력해주세요.")
                return

            # 사용자 정보 저장
            st.session_state.nickname = name
            st.session_state.phone_number = phone

            # 초기 메모리 구성
            if shopping_style == "가성비 우선형":
                add_memory("가성비, 가격을 중요하게 생각하는 편이에요.", announce=False)
            elif shopping_style == "디자인/스타일 우선형":
                add_memory("(가장 중요) 디자인/스타일을 최우선으로 고려하고 있어요.", announce=False)
            else:
                add_memory("(가장 중요) 성능/스펙을 우선하는 쇼핑 성향이에요.", announce=False)

            add_memory(f"색상은 {color_choice} 계열을 선호해요.", announce=False)

            st.session_state.page = "chat"
            st.rerun()


# =========================================================
# 18. main_chat_interface (UI 그대로 사용)
# =========================================================
def main_chat_interface():
    # 알림/토스트 처리
    if st.session_state.notification_message:
        try:
            st.toast(st.session_state.notification_message, icon="✅")
        except Exception:
            st.info(st.session_state.notification_message)
        st.session_state.notification_message = ""

    # 첫 메시지
    if len(st.session_state.messages) == 0:
        ai_say(
            f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요.\n"
            f"블루투스 헤드셋을 추천해달라고 하셨으니, 이와 관련해 {st.session_state.nickname}님에 대해 더 파악해볼게요. 주로 어떤 용도로 헤드셋을 사용하실 예정인가요?"
        )

    render_scenario()
    render_step_header()

    col1, col2 = st.columns([3, 7], gap="large")

    with col1:
        render_memory_sidebar()

    with col2:
        # 채팅창 렌더
        chat_html = '<div class="chat-display-area">'
        for msg in st.session_state.messages:
            cls = "chat-bubble-ai" if msg["role"] == "assistant" else "chat-bubble-user"
            safe = html.escape(msg["content"])
            chat_html += f'<div class="chat-bubble {cls}">{safe}</div>'
        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)

        # summary 단계면 요약 표시
        if st.session_state.stage == "summary":
            st.session_state.summary_text = build_summary_from_memory(
                st.session_state.nickname, st.session_state.memory
            )
            st.markdown(st.session_state.summary_text)

        # 추천/상세 단계 카드
        if st.session_state.stage in ["comparison", "product_detail"]:
            recommend_products_ui(st.session_state.nickname, st.session_state.memory)

        # 🔵 입력창 (여기 딱 한 개만!)
        st.markdown("<br>", unsafe_allow_html=True)
        user_text = st.text_input("메시지를 입력하세요...", key="user_input_text")

        if st.button("전송", key="send_btn"):
            if user_text.strip():
                handle_input()
                st.rerun()

# =========================================================
# 19. 라우팅
# =========================================================
if st.session_state.page == "context_setting":
    context_setting_page()
else:
    main_chat_interface()












