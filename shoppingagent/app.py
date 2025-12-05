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
# 1. 세션 상태 초기값 설정 (기존 로직 유지 + 색상 추가)
# =========================================================
def ss_init():
    ss = st.session_state

    # 기본 UI 상태
    ss.setdefault("page", "context_setting")
    ss.setdefault("nickname", "")
    ss.setdefault("budget", None)

    # 대화 메시지 / 메모리
    ss.setdefault("messages", [])
    ss.setdefault("memory", [])
    ss.setdefault("just_updated_memory", False)
    
    # 🎨 메모리 태그 색상 저장용 (새로 추가됨)
    ss.setdefault("memory_colors", [])

    # 단계
    ss.setdefault("stage", "explore")
    ss.setdefault("summary_text", "")
    ss.setdefault("detail_mode", False)

    # 추천 관련
    ss.setdefault("recommended_products", [])
    ss.setdefault("selected_product", None)
    ss.setdefault("final_choice", None)

    # 로그용
    ss.setdefault("turn_count", 0)
    ss.setdefault("product_detail_turn", 0)

    # 🔥 핵심 상태값들 (기존 로직 유지)
    ss.setdefault("question_history", [])            # 이미 어떤 질문을 했는지 추적
    ss.setdefault("current_question", None)          # 현재 진행 중인 질문 ID
    ss.setdefault("priority", "")                    # 실험 준비 단계에서 받아오는 최우선 기준
    ss.setdefault("primary_style", "")               # 설문조사 기반 스타일
    ss.setdefault("priority_followup_done", False)   # 우선순위 팔로업 질문 여부
    ss.setdefault("neg_responses", [
        "없어", "몰라", "글쎄", "아니", "별로", "중요하지 않아",
        "그만", "대충", "음…", "모르겠", "선호 없음"
    ])

ss_init()

# ========================================================
# 2. CSS 스타일 (피드백 반영: 전체 비율 축소 + 메모리 태그 + 입력창 밀착)
# =========================================================
st.markdown("""
<style>
    /* 1) 화면 비율 조정 (1200px -> 1000px) */
    .block-container {
        padding-top: 2rem; 
        max-width: 1000px !important;
        padding-bottom: 5rem;
    }

    /* 기본 설정 숨김 */
    #MainMenu, footer, header, .css-1r6q61a {visibility: hidden; display: none !important;}

    /* 🔵 [버튼 스타일] 파란색(#2563EB) 통일 */
    div.stButton > button {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
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
    .memory-delete-btn {
        background-color: transparent !important;
        color: #94a3b8 !important;
        border: none !important;
        padding: 0px 5px !important;
        font-size: 14px !important;
        min-height: 0px !important;
        line-height: 1 !important;
    }
    .memory-delete-btn:hover {
        color: #ef4444 !important; /* 빨간색 호버 */
        background-color: transparent !important;
    }

    /* 🟢 시나리오 박스 */
    .scenario-box {
        background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 12px;
        padding: 16px 20px; margin-bottom: 20px; color: #0369A1; font-size: 15px;
        line-height: 1.6;
    }

    /* 🟢 진행바 (가로 배열 + 설명 포함) */
    .progress-container {
        display: flex; justify-content: space-between; margin-bottom: 30px;
        padding: 0 10px; gap: 20px;
    }
    .step-item {
        display: flex; flex-direction: column; align-items: flex-start; flex: 1; position: relative;
    }
    .step-header-group { display: flex; align-items: center; margin-bottom: 6px; }
    .step-circle {
        width: 28px; height: 28px; border-radius: 50%; background: #E5E7EB;
        color: #6B7280; display: flex; align-items: center; justify-content: center;
        font-weight: 700; margin-right: 10px; font-size: 13px; flex-shrink: 0;
    }
    .step-title { font-size: 15px; font-weight: 700; color: #374151; }
    .step-desc {
        font-size: 12px; color: #6B7280; padding-left: 38px; line-height: 1.4; max-width: 95%;
    }
    
    /* 활성화된 단계 스타일 */
    .step-active .step-circle { background: #2563EB; color: white; }
    .step-active .step-title { color: #2563EB; }
    .step-active .step-desc { color: #4B5563; font-weight: 500; }

    /* 🟢 채팅창 컨테이너 (입력창과 붙이기 위한 래퍼) */
    .chat-container-wrapper {
        background: #FFFFFF;
        border: 1px solid #E5E7EB; 
        border-radius: 16px; 
        padding: 20px;
        min-height: 500px;
        display: flex; 
        flex-direction: column;
    }

    /* 말풍선 스타일 */
    .chat-bubble { padding: 12px 16px; border-radius: 16px; margin-bottom: 12px; max-width: 85%; line-height: 1.6; font-size: 15px; }
    .chat-bubble-user { background: #E0E7FF; align-self: flex-end; margin-left: auto; color: #111; border-top-right-radius: 2px; }
    .chat-bubble-ai { background: #F3F4F6; align-self: flex-start; margin-right: auto; color: #111; border-top-left-radius: 2px; }

    /* 🧠 메모리 사이드바 (피드백: 눈에 띄게 개선) */
    .memory-sidebar {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 15px;
        height: 100%;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .memory-section-header {
        font-size: 18px; font-weight: 800; margin-bottom: 15px; color: #1E293B; display: flex; align-items: center;
    }
    
    /* 메모리 태그 (알록달록 칩 스타일) */
    .memory-tag {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        margin-bottom: 8px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        color: #334155;
        background: white;
        border-left: 5px solid #ccc; /* 동적으로 색상 변경됨 */
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        transition: transform 0.1s;
    }
    .memory-tag:hover { transform: translateX(2px); }

    /* 상품 카드 (채팅 내 삽입용) */
    .product-card-chat {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        transition: transform 0.2s;
        height: 100%;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .product-card-chat:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #2563EB;
    }
    .product-img { width: 100%; height: 120px; object-fit: contain; margin-bottom: 10px; }
    .product-title { font-weight: 700; font-size: 14px; margin-bottom: 4px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
    .product-price { color: #2563EB; font-weight: 700; font-size: 14px; margin-bottom: 6px; }
    .product-desc { font-size: 12px; color: #6B7280; line-height: 1.3; margin-bottom: 10px; height: 32px; overflow: hidden; }

    /* 입력창 스타일 */
    .stTextInput > div > div > input {
        border-radius: 24px !important;
        padding: 10px 15px !important;
        border: 1px solid #CBD5E1 !important;
    }
    /* 입력창 폼 여백 제거 */
    div[data-testid="stForm"] { border: none; padding: 0; margin-top: 10px; }
    
    .info-text {
        font-size: 14px; color: #374151; background: #F3F4F6;
        padding: 15px; border-radius: 8px; margin-bottom: 30px;
        border-left: 4px solid #2563EB; line-height: 1.6;
    }
    .warning-text {
        font-size: 13px; color: #DC2626; background: #FEF2F2; 
        padding: 10px; border-radius: 6px; margin-top: 4px; margin-bottom: 12px;
        border: 1px solid #FECACA;
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
- 사용자에게 ‘음질 선호(저음/중음/고음)’처럼 세부적인 음향 특성을 묻는 follow-up 질문은 절대 하지 않는다. 음질이라는 기준 자체는 받을 수 있지만, 세부 음역대 관련 질문은 금지한다.
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
- 사용자에게 ‘음질 선호(저음/중음/고음)’처럼 세부적인 음향 특성을 묻는 follow-up 질문은 절대 하지 않는다. 음질이라는 기준 자체는 받을 수 있지만, 세부 음역대 관련 질문은 금지한다.
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
def get_random_pastel_color():
    """메모리 태그용 파스텔 색상 랜덤 반환"""
    colors = ["#FFD700", "#FFB6C1", "#87CEFA", "#98FB98", "#DDA0DD", "#F0E68C", "#E0FFFF", "#FF69B4", "#FFA07A"]
    return random.choice(colors)

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

def is_negative_response(text: str) -> bool:
    """사용자의 부정/회피 반응 감지"""
    if not text:
        return False
    negative_keywords = [
        "없어", "없다고", "몰라", "모르겠", "잘 모르", 
        "글쎄", "별로", "아닌데", "굳이",
        "그만", "필요없", "상관없", "안중요", "관심없"
    ]
    return any(k in text for k in negative_keywords)


def extract_memory_with_gpt(user_input: str, memory_text: str):
    """GPT를 이용해 사용자 발화에서 쇼핑 기준 추출"""
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
- 저장할 만한 메모리가 전혀 없다면 {{ "memories": [] }} 만 출력하세요.
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
    """색상 관련 메모리인지 판별"""
    t = text.replace("(가장 중요)", "")
    if "색상" in t and "선호" in t:
        return True
    color_keywords = ["화이트", "블랙", "네이비", "퍼플", "실버", "그레이", "핑크", "보라", "골드"]
    return any(k in t for k in color_keywords)

def _after_memory_change():
    """메모리 변경 후 처리"""
    st.session_state.just_updated_memory = True
    
    # summary 단계면 요약 재생성
    if st.session_state.stage == "summary":
        st.session_state.summary_text = build_summary_from_memory(
            st.session_state.nickname,
            st.session_state.memory,
        )
    # comparison 단계면 추천 리스트 재계산
    if st.session_state.stage == "comparison":
        st.session_state.recommended_products = make_recommendation()

def add_memory(mem_text: str, announce: bool = True):
    mem_text = mem_text.strip()
    if not mem_text: return

    mem_text = naturalize_memory(mem_text)
    mem_text_stripped = mem_text.replace("(가장 중요)", "").strip()

    # 예산 중복 처리
    if "예산은 약" in mem_text_stripped:
        indices_to_remove = [i for i, m in enumerate(st.session_state.memory) if "예산은 약" in m]
        for idx in reversed(indices_to_remove):
            delete_memory(idx) # 내부에서 colors도 같이 삭제됨

    # 색상 기준 충돌 처리
    if _is_color_memory(mem_text_stripped):
        indices_to_remove = [i for i, m in enumerate(st.session_state.memory) if _is_color_memory(m)]
        for idx in reversed(indices_to_remove):
            delete_memory(idx)

    # 기존 메모리와 중복 확인
    for i, m in enumerate(st.session_state.memory):
        base = m.replace("(가장 중요)", "").strip()
        if mem_text_stripped in base or base in mem_text_stripped:
            # 중요도 승급 체크
            if "(가장 중요)" in mem_text and "(가장 중요)" not in m:
                # 다른 메모리 태그 제거
                st.session_state.memory = [mm.replace("(가장 중요)", "").strip() for mm in st.session_state.memory]
                st.session_state.memory[i] = mem_text
                if announce:
                    st.session_state.notification_message = "🌟 최우선 기준으로 설정되었어요."
                _after_memory_change()
                return
            return # 단순 중복이면 패스

    # 새로운 메모리 추가
    st.session_state.memory.append(mem_text)
    # 색상도 같이 추가 (피드백 반영)
    st.session_state.memory_colors.append(get_random_pastel_color())

    if announce:
        st.session_state.notification_message = "🧩 메모리에 새로운 내용을 추가했어요."
    _after_memory_change()

def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        del st.session_state.memory_colors[idx] # 색상도 같이 삭제
        st.session_state.notification_message = "🧹 메모리에서 해당 기준을 삭제했어요."
        _after_memory_change()

# =========================================================
# 6. 요약/추천 관련 유틸
# =========================================================
def extract_budget(mems):
    for m in mems:
        m1 = re.search(r"(\d+)\s*만\s*원", m)
        if m1: return int(m1.group(1)) * 10000
        txt = m.replace(",", "")
        m2 = re.search(r"(\d{2,7})\s*원", txt)
        if m2: return int(m2.group(1))
    return None

def generate_personalized_reason(product, mems, name):
    reasons = []
    mem_str = " ".join(mems)
    tags = product.get("tags", [])

    if "음질" in mem_str and "음질" in tags:
        reasons.append("음질 중심 사용자에게 잘 맞아요.")
    if "착용감" in mem_str and any(t in tags for t in ["편안함", "경량", "가벼움", "착용감"]):
        reasons.append("장시간 착용해도 편안해요.")
    if "노이즈캔슬링" in mem_str and "노이즈캔슬링" in tags:
        reasons.append("노이즈캔슬링 성능이 뛰어나요.")
    if "배터리" in tags:
        reasons.append("배터리가 오래가는 편이에요.")
    if "가성비" in tags:
        reasons.append("가성비가 뛰어난 선택이에요.")

    # 랜덤 맺음말
    closing_templates = [
        f"{name}님의 취향과 잘 맞는 조합이에요!",
        f"{name}님이 선호하시는 기준과 잘 어울려요."
    ]
    reasons.append(random.choice(closing_templates))
    
    unique_reasons = []
    for r in reasons:
        if r not in unique_reasons: unique_reasons.append(r)
    return "\n".join(unique_reasons[:2])

def send_product_detail_message(product):
    detail_text = (
        f"📌 **{product['name']} 상세 정보 안내드릴게요!**\n\n"
        f"- **가격:** {product['price']:,}원\n"
        f"- **평점:** ⭐ {product['rating']:.1f} (리뷰 {product['reviews']}개)\n"
        f"- **주요 특징:** {', '.join(product.get('tags', []))}\n"
        f"- **리뷰 한 줄 요약:** {product.get('review_one', '정보 없음')}\n\n"
        "🔄 맘에 들지 않으시면 좌측 **쇼핑 메모리**를 수정해보세요! 추천 후보가 달라집니다."
    )
    ai_say(detail_text)

# =========================================================
# 7. 상품 카탈로그
# =========================================================
CATALOG = [
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 179000, "rating": 4.4, "reviews": 1600, "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"], "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.", "color": ["블랙", "화이트", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg"},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 99000, "rating": 4.4, "reviews": 2300, "tags": ["가벼움", "음질", "노이즈캔슬링", "편안함"], "review_one": "가볍고 음질이 좋다는 평이 많아요.", "color": ["블랙", "화이트", "퍼플", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png"},
    {"name": "Sony WH-CH720N", "brand": "Sony", "price": 129000, "rating": 4.5, "reviews": 2100, "tags": ["노이즈캔슬링", "경량", "무난한 음질"], "review_one": "경량이라 출퇴근용으로 좋다는 후기가 많아요.", "color": ["블랙", "화이트", "블루"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-CH720N.jpg"},
    {"name": "Bose QC45", "brand": "Bose", "price": 420000, "rating": 4.7, "reviews": 2800, "tags": ["가벼움", "착용감", "노이즈캔슬링", "편안함"], "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg"},
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 450000, "rating": 4.8, "reviews": 3200, "tags": ["노이즈캔슬링", "음질", "착용감", "통화품질"], "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.", "color": ["핑크"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg"},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 679000, "rating": 4.6, "reviews": 1500, "tags": ["브랜드", "노이즈캔슬링", "디자인", "고급"], "review_one": "깔끔한 디자인과 가벼운 무게로 만족도가 높아요.", "color": ["실버", "스페이스그레이"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg"},
    {"name": "Sennheiser PXC 550-II", "brand": "Sennheiser", "price": 289000, "rating": 4.3, "reviews": 1200, "tags": ["착용감", "여행", "배터리", "노이즈캔슬링"], "review_one": "여행 시 장시간 착용에도 압박감이 덜해요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sennheiser%20PXC%2055.jpeg"},
    {"name": "Bose Noise Cancelling Headphones 700", "brand": "Bose", "price": 490000, "rating": 4.7, "reviews": 2500, "tags": ["노이즈캔슬링", "배터리", "음질", "프리미엄"], "review_one": "노이즈캔슬링 성능과 음질을 모두 갖춘 최고급 프리미엄 제품.", "color": ["블랙", "화이트"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20Headphones%20700.jpg"},
]

# =========================================================
# 8. GPT 응답 로직
# =========================================================
def get_product_detail_prompt(product, user_input):
    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    budget = extract_budget(st.session_state.memory)
    budget_line = f"- 사용자가 설정한 예산: 약 {budget:,}원" if budget else ""

    return f"""
당신은 '상품 상세 정보 단계'입니다. 선택된 **블루투스 헤드셋 한 제품**만 설명합니다.

[사용자 질문]
"{user_input}"

[선택된 제품 정보]
- 제품명: {product['name']} ({product['brand']})
- 가격: {product['price']:,}원
- 특징: {', '.join(product['tags'])}
{budget_line}

[응답 규칙]
1. 핵심 정보만 간단히 답변.
2. 비교/추천 리스트 언급 금지.
3. 탐색 질문(용도 재질문) 금지.
4. 답변 끝에 "다른 부분도 궁금하신가요?" 혹은 "구매 결정하시겠어요?" 등을 붙일 것.
"""

def gpt_reply(user_input: str) -> str:
    """GPT 응답 생성 (단계별 프롬프트 제어)"""
    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    stage = st.session_state.stage

    # 1) 상세 정보 단계
    if stage == "product_detail":
        product = st.session_state.selected_product
        if not product:
            st.session_state.stage = "comparison"
            return "선택된 제품 정보가 없어서 목록으로 돌아갈게요!"
        prompt = get_product_detail_prompt(product, user_input)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
        )
        st.session_state.product_detail_turn += 1
        return res.choices[0].message.content

    # 2) 일반 대화 단계
    stage_hint = ""
    design_priority = any("(가장 중요)" in m and "디자인" in m for m in st.session_state.memory)
    
    if stage == "explore" and design_priority:
        stage_hint += "\n[규칙] 디자인이 최우선입니다. 기능 질문보다 디자인/색상 질문을 먼저 하세요.\n"

    prompt_content = f"""
{stage_hint}
[현재 저장된 쇼핑 메모리]
{memory_text if memory_text else "(아직 없음)"}

[사용자 발화]
{user_input}

위 정보를 참고해 AI 쇼핑 도우미로서 자연스럽게 답변하세요.
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
# 9. 로그 및 UI 유틸
# =========================================================
def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})

def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})
    st.session_state.turn_count += 1

def build_summary_from_memory(name, mems):
    if not mems:
        return f"{name}님, 아직 명확한 기준이 정해지지 않았어요."
    lines = [f"• {m.replace('(가장 중요)', '').strip()}" for m in mems]
    prio = next((m.replace("(가장 중요)", "").strip() for m in mems if "(가장 중요)" in m), None)
    
    body = "지금까지 대화를 기반으로 정리된 쇼핑 기준은 다음과 같아요:\n\n" + "\n".join(lines)
    if prio: body += f"\n\n그중에서도 가장 중요한 기준은 **‘{prio}’**이에요."
    
    tail = "\n\n기준이 맞다면 추천을 진행할까요? 수정하고 싶다면 좌측 메모리를 변경해주세요!"
    return body + tail

def score_item_with_memory(item, mems):
    """(기존 로직 유지) 메모리 기반 점수 계산"""
    score = 0
    mtext = " ".join(mems)
    budget = extract_budget(mems)

    # 태그 매칭 점수
    for tag in item["tags"]:
        if tag in mtext: score += 20
        # 최우선 가중치
        if "(가장 중요)" in mtext:
            if "디자인" in mtext and "디자인" in tag: score += 30
            if "음질" in mtext and "음질" in tag: score += 30

    # 예산 보정
    if budget:
        if item["price"] > budget:
            diff = item["price"] - budget
            score -= 200 if diff > 100000 else 80
        else:
            score += 30
    
    score -= item.get("rank", 10) # 랭킹 보정 (낮을수록 좋음이라 가정하거나, 단순 데이터용)
    return score

def make_recommendation():
    scored = [(score_item_with_memory(item, st.session_state.memory), item) for item in CATALOG]
    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:3]]

# =========================================================
# 10. 사용자 입력 처리 핸들러 (기존 로직 + 시나리오)
# =========================================================
def handle_input():
    u = st.session_state.user_input_text.strip()
    if not u: return

    ss = st.session_state
    user_say(u)

    # 1) 카테고리 드리프트 방지
    if any(w in u for w in ["스마트폰", "갤럭시", "아이폰"]):
        ai_say("죄송해요, 저는 블루투스 헤드셋만 추천해드릴 수 있어요. 😅")
        return

    # 2) 부정적 반응 처리
    if is_negative_response(u):
        if ss.current_question:
            ss.question_history.append(ss.current_question)
            ss.current_question = None
        ai_say("네, 그 부분은 넘어가고 다른 중요한 점을 살펴볼게요.")
        return

    # 3) 메모리 추출 및 반영
    extracted = extract_memory_with_gpt(u, "\n".join(ss.memory))
    for mem in extracted:
        add_memory(mem)

    # 4) 우선순위 팔로업 (1회성)
    if not ss.priority_followup_done:
        if ss.primary_style == "design":
            ai_say("디자인을 중요하게 생각하시네요! 선호하는 스타일(심플, 레트로 등)이 있나요?")
            ss.priority_followup_done = True
            return
        elif ss.primary_style == "performance":
            ai_say("성능을 중요시하는군요. 음질, 노이즈캔슬링 중 더 중요한게 있나요?")
            ss.priority_followup_done = True
            return
    
    # 5) 요약/추천 단계 진입 체크
    has_budget = any("예산" in m for m in ss.memory)
    if ss.stage == "explore" and len(ss.memory) >= 5 and has_budget:
        ss.stage = "summary"
        ss.summary_text = build_summary_from_memory(ss.nickname, ss.memory)
        # summary 텍스트는 렌더링 시점에 표시됨
        return

    # 6) GPT 응답 생성
    reply = gpt_reply(u)
    ai_say(reply)

    # 7) 질문 추적 로직
    qid = None
    if "디자인" in reply: qid = "design"
    elif "음질" in reply: qid = "sound"
    elif "예산" in reply: qid = "budget"
    
    if qid:
        if qid in ss.question_history: ss.current_question = None
        else: ss.current_question = qid

    # 8) 단계 전환 로직
    if ss.stage == "summary":
        if any(k in u for k in ["좋아", "네", "추천", "응"]):
            ss.stage = "comparison"
            ss.recommended_products = make_recommendation()
            ai_say("좋습니다! 분석된 취향을 바탕으로 추천 제품을 가져왔어요. 👇")
        else:
            ai_say("수정하고 싶은 부분이 있다면 말씀해주세요.")

    elif ss.stage == "product_detail":
        if any(k in u for k in ["결정", "구매", "이걸로"]):
            ss.stage = "purchase_decision"
            ss.final_choice = ss.selected_product
            ai_say("탁월한 선택입니다! 구매 결정을 도와드릴게요.")

# =========================================================
# 11. 화면 렌더링 컴포넌트 (피드백 반영된 UI)
# =========================================================
def render_scenario():
    st.markdown(
        """
        <div class="scenario-box">
            🔍 <b>실험 시나리오</b><br>
            매일 지하철 출퇴근을 하는 당신에게 헤드셋이 필요해졌습니다. <br>
            조건: <b>(1) 귀가 편한 착용감 (2) 강력한 노이즈캔슬링 필수!</b>
        </div>
        """, unsafe_allow_html=True
    )

def render_step_header():
    stage = st.session_state.stage
    def active(s): return "step-active" if s == stage else ""
    
    st.markdown(f"""
    <div class="progress-container">
        <div class="step-item {active('explore')}">
            <div class="step-header-group"><div class="step-circle">1</div><div class="step-title">탐색</div></div>
            <div class="step-desc">취향 파악</div>
        </div>
        <div class="step-item {active('summary')}">
            <div class="step-header-group"><div class="step-circle">2</div><div class="step-title">요약</div></div>
            <div class="step-desc">기준 확인</div>
        </div>
        <div class="step-item {active('comparison')}">
            <div class="step-header-group"><div class="step-circle">3</div><div class="step-title">추천</div></div>
            <div class="step-desc">상품 비교</div>
        </div>
        <div class="step-item {active('product_detail')}">
            <div class="step-header-group"><div class="step-circle">4</div><div class="step-title">상세</div></div>
            <div class="step-desc">정보 확인</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_memory_sidebar():
    """피드백 1,3 반영: 눈에 띄는 태그 형태의 메모리"""
    
    # [🔥 긴급 수정] 메모리와 색상 리스트 개수 동기화 (에러 방지용 안전장치)
    # 메모리는 있는데 색상이 없는 경우, 부족한 만큼 색상을 채워넣습니다.
    while len(st.session_state.memory_colors) < len(st.session_state.memory):
        st.session_state.memory_colors.append(get_random_pastel_color())
    
    # 혹시 색상이 더 많으면 잘라냅니다.
    if len(st.session_state.memory_colors) > len(st.session_state.memory):
        st.session_state.memory_colors = st.session_state.memory_colors[:len(st.session_state.memory)]

    st.markdown("<div class='memory-sidebar'>", unsafe_allow_html=True)
    st.markdown("<div class='memory-section-header'>🧠 쇼핑 메모리</div>", unsafe_allow_html=True)
    
    if not st.session_state.memory:
        st.caption("아직 수집된 취향이 없어요. 대화를 시작해보세요!")
    
    for i, mem in enumerate(st.session_state.memory):
        # 안전장치를 거쳤으므로 이제 에러가 나지 않습니다.
        color = st.session_state.memory_colors[i]
        
        # 태그 HTML 직접 구성 (삭제 버튼 포함)
        c1, c2 = st.columns([8.8, 1.2])
        with c1:
            st.markdown(
                f"<div class='memory-tag' style='border-left-color:{color};'>{mem}</div>", 
                unsafe_allow_html=True
            )
        with c2:
            # 삭제 버튼
            if st.button("✕", key=f"del_{i}", help="삭제"):
                delete_memory(i)
                st.rerun()

    # 수동 추가
    st.markdown("<hr style='margin: 15px 0; border-color:#e2e8f0;'>", unsafe_allow_html=True)
    new_mem = st.text_input("직접 추가", key="manual_mem", placeholder="예: 무조건 화이트", label_visibility="collapsed")
    if st.button("추가", key="btn_add_mem", use_container_width=True):
        if new_mem:
            add_memory(new_mem)
            st.rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)
def render_carousel_in_chat():
    """피드백 5 반영: 채팅창 흐름 내부에 추천 카드(캐러셀) 렌더링"""
    products = st.session_state.recommended_products
    if not products: return

    st.markdown("##### 🎁 회원님을 위한 추천 Pick")
    cols = st.columns(3)
    for i, p in enumerate(products):
        with cols[i]:
            # 카드 디자인
            html_code = f"""
            <div class="product-card-chat">
                <img src="{p['img']}" class="product-img">
                <div class="product-title">{p['name']}</div>
                <div class="product-price">{p['price']:,}원</div>
                <div class="product-desc">{generate_personalized_reason(p, st.session_state.memory, st.session_state.nickname)}</div>
            </div>
            """
            st.markdown(html_code, unsafe_allow_html=True)
            if st.button("상세보기", key=f"btn_rec_{i}", use_container_width=True):
                st.session_state.selected_product = p
                st.session_state.stage = "product_detail"
                send_product_detail_message(p) # 상세 메시지를 채팅창에 띄움
                st.rerun()

# =========================================================
# 12. 메인 실행 및 라우팅
# =========================================================

def context_setting_page():
    st.title("🛒 쇼핑 에이전트 실험 준비")
    st.markdown('<div class="info-text">이 페이지는 <b>AI 에이전트 초기 설정</b> 단계입니다.<br>실제 쇼핑 성향을 입력해주세요.</div>', unsafe_allow_html=True)

    with st.container(border=True):
        name = st.text_input("이름", placeholder="홍길동")
        
        st.subheader("Q1. 쇼핑 성향")
        shopping_style = st.selectbox("", ["가성비 우선형", "디자인/스타일 우선형", "성능·스펙 우선형"])
        
        st.subheader("Q2. 선호 색상")
        color_choice = st.selectbox("", ["블랙", "화이트", "핑크", "네이비", "실버"])

        if st.button("쇼핑 시작하기", type="primary", use_container_width=True):
            if not name:
                st.warning("이름을 입력해주세요.")
                return
            
            # 초기화 및 저장
            st.session_state.nickname = name
            
            # 초기 메모리 주입
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

def main_chat_interface():
    # 첫 인사
    if not st.session_state.messages:
        ai_say(f"안녕하세요 {st.session_state.nickname}님! 😊 헤드셋 추천을 도와드릴게요. 주로 어떤 용도로 사용하실 계획인가요?")

    # 상단 정보
    render_scenario()
    render_step_header()

    # 메인 레이아웃 (3:7 비율)
    col_left, col_right = st.columns([3, 7], gap="medium")

    with col_left:
        render_memory_sidebar()

    with col_right:
        # 채팅창 + 입력창을 하나의 박스로 감싸기 (피드백 4 반영)
        with st.container(border=True):
            
            # 1. 채팅 영역 컨테이너
            chat_container = st.container()
            with chat_container:
                # 메시지 렌더링
                for msg in st.session_state.messages:
                    role_cls = "chat-bubble-ai" if msg["role"] == "assistant" else "chat-bubble-user"
                    st.markdown(f"<div class='chat-bubble {role_cls}'>{msg['content']}</div>", unsafe_allow_html=True)
                
                # 요약문 (summary 단계일 때만 표시)
                if st.session_state.stage == "summary":
                    st.markdown(f"<div class='chat-bubble chat-bubble-ai'>{st.session_state.summary_text}</div>", unsafe_allow_html=True)

            # 2. 추천 캐러셀 (comparison 단계일 때 채팅창 내부에 표시 - 피드백 5)
            if st.session_state.stage == "comparison":
                st.markdown("---")
                render_carousel_in_chat()

            # 3. 상세 화면 버튼 (product_detail 단계)
            if st.session_state.stage == "product_detail":
                st.markdown("---")
                c1, c2 = st.columns(2)
                if c1.button("⬅️ 목록으로"):
                    st.session_state.stage = "comparison"
                    st.session_state.selected_product = None
                    st.rerun()
                if c2.button("🛒 구매 확정"):
                    st.session_state.stage = "purchase_decision"
                    st.session_state.final_choice = st.session_state.selected_product
                    st.rerun()

            # 4. 구매 완료 메시지
            if st.session_state.stage == "purchase_decision" and st.session_state.final_choice:
                st.success(f"🎉 **{st.session_state.final_choice['name']}** 구매를 완료했습니다!")
                st.balloons()

            # 5. 입력창 (채팅 컨테이너 최하단에 밀착)
            st.markdown("---")
            with st.form(key="chat_form", clear_on_submit=True):
                r1, r2 = st.columns([85, 15])
                with r1:
                    st.text_input(
                        "input", 
                        key="user_input_text", 
                        placeholder="메시지를 입력하세요...", 
                        label_visibility="collapsed"
                    )
                with r2:
                    st.form_submit_button("전송", on_click=handle_input)

# 앱 진입점
if st.session_state.page == "context_setting":
    context_setting_page()
else:
    main_chat_interface()
    
    # 토스트 알림
    if st.session_state.get("notification_message"):
        st.toast(st.session_state.notification_message)
        st.session_state.notification_message = ""

