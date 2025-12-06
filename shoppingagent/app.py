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

    # 기본 UI 상태
    ss.setdefault("page", "context_setting")
    ss.setdefault("nickname", "")
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

    # 로그용
    ss.setdefault("turn_count", 0)

    # 🔥 추가된 핵심 상태값들 — 여기부터 추가
    ss.setdefault("question_history", [])           # 이미 어떤 질문을 했는지 추적
    ss.setdefault("current_question", None)         # 현재 진행 중인 질문 ID
    ss.setdefault("priority", "")                   # 실험 준비 단계에서 받아오는 최우선 기준
    ss.setdefault("neg_responses", [
        "없어", "몰라", "글쎄", "아니", "별로", "중요하지 않아",
        "그만", "대충", "음…", "모르겠", "선호 없음"
    ])
    ss.setdefault("priority_followup_done", False)
    ss.setdefault("primary_style", "")
    ss.setdefault("product_detail_turn", 0)
    ss.setdefault("selected_product", None)

ss_init()

# ========================================================
# 2. CSS 스타일 (기존 UI 완벽 유지)
# =========================================================
st.markdown("""
<style>
    /* 전체 UI 15% 축소 효과 */
    html, body, [class*="block-container"] {
        font-size: 0.85rem !important;
    }
    
    .chat-display-area {
        transform: scale(0.92);
        transform-origin: top left;
    }
    
    .product-card, .memory-block {
        transform: scale(0.95);
        transform-origin: top left;
    }

    /* 기본 설정 */
    #MainMenu, footer, header, .css-1r6q61a {
        visibility: hidden;
        display: none !important;
    }

    .block-container {
        padding-top: 1.5rem;
        max-width: 900px !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }

    /* ============================================================
       기본 버튼(파란색) 스타일
       ============================================================ */
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


    /* ============================================================
       메모리 삭제 버튼(X → -) 스타일 (흰색 미니멀)
       ============================================================ */
    .memory-delete-btn {
        background-color: #ffffff !important;
        color: #EF4444 !important;
        border: 1px solid #E5E7EB !important;
        padding: 2px 8px !important;
        border-radius: 6px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        min-height: 0px !important;
    }

    .memory-delete-btn:hover {
        background-color: #FFF5F5 !important;
        border-color: #EF4444 !important;
    }


    /* ============================================================
       메모리 추가 버튼(+만) 스타일 (흰색 미니멀)
       ============================================================ */
    .memory-add-btn {
        background-color: #ffffff !important;
        color: #10B981 !important;
        border: 1px solid #E5E7EB !important;
        padding: 4px 10px !important;
        border-radius: 6px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        cursor: pointer !important;
    }

    .memory-add-btn:hover {
        background-color: #ECFDF5 !important;
        border-color: #10B981 !important;
    }



    /* ============================================================
       진행바 스타일
       ============================================================ */
    .progress-container {
        display: flex;
        align-items: center;
        gap: 12px;
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
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: #E5E7EB;
        color: #6B7280;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        margin-right: 10px;
        font-size: 13px;
        flex-shrink: 0;
    }

    .step-title {
        font-size: 16px;
        font-weight: 700;
        color: #374151;
    }

    .step-desc {
        font-size: 13px;
        color: #6B7280;
        padding-left: 38px;
        line-height: 1.4;
        max-width: 90%;
    }

    .memory-section {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 20px 24px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        margin-bottom: 22px;
        max-width: 480px;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* 활성화된 단계 스타일 */
    .step-active .step-circle { background: #2563EB; color: white; }
    .step-active .step-title { color: #2563EB; }
    .step-active .step-desc { color: #4B5563; font-weight: 500; }

    /* 🟢 채팅창 스타일 */
    .chat-display-area {
        height: 450px;
        overflow-y: auto;
        padding: 20px;
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        margin-bottom: 20px;
        display: flex;
        flex-direction: column;   /* ← 여기 수정!! */
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
        background: #FFF9D9;  /* 파스텔 연노랑 */
        border-left: 4px solid #FACC15; /* 진한 옐로우 포인트 */
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 14px;
        color: #333333; /* 진회색 텍스트 */
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .memory-text {
        font-weight: 500;
        color: #333333;
    }

    /* 팁 박스 */
    .tip-box {
        background: #FFFBEB; border: 1px solid #FCD34D; border-radius: 12px;
        padding: 16px; font-size: 12px; color: #92400E; line-height: 1.5; margin-top: 20px;
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
    .product-title { font-weight: 700; font-size: 14px; margin-bottom: 4px; }
    .product-price { color: #2563EB; font-weight: 700; margin-bottom: 10px; }

        /* 🔵 캐러셀 스타일 */
    .carousel-wrapper {
        display: flex;
        gap: 12px;
        margin-top: 12px;
        padding: 10px 0;
        overflow-x: auto;
    }
    .carousel-card {
        flex: 0 0 auto;
        width: 160px;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }
    .carousel-card img {
        width: 100%;
        height: 120px;
        object-fit: cover;
        border-radius: 8px;
    }
    .carousel-title {
        font-size: 14px;
        font-weight: 600;
        margin-top: 8px;
    }
    .carousel-price {
        font-size: 13px;
        margin-top: 4px;
        color: #2563eb;
    }

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

    /* ----------------------------- */
    /*  제목 크기 전체 축소 (h1~h3)  */
    /* ----------------------------- */

    h1, .stMarkdown h1 {
        font-size: 1.6rem !important;    /* 기존보다 약 -35% */
        font-weight: 700 !important;
    }

    h2, .stMarkdown h2 {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
    }

    h3, .stMarkdown h3 {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
    }

</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SYSTEM PROMPT (헤드셋 전용 + 메모리/프로필 강조)
# =========================================================
SYSTEM_PROMPT = r"""
너는 'AI 쇼핑 도우미'이며 **항상 블루투스 헤드셋** 기준을 파악해 추천을 돕는 역할을 한다.
다른 카테고리의 상품을 제안하거나 추천하지 않는다. 대화 전 과정에서 '블루투스 헤드셋'만을 전제로 생각한다.

[역할 규칙]
- 최우선 규칙: 메모리에 이미 저장된 기준(특히 용도, 상황, 기능)은 절대 다시 물어보지 않고 바로 다음 단계의 구체적인 질문으로 전환한다.
- 너의 가장 큰 역할은 **사용자 메모리(쇼핑 기준 프로필)를 읽고, 갱신하고, 설명하면서 추천을 돕는 것**이다.
- 메모리에 이미 저장된 내용(특히 용도, 상황, 기능, 색상, 스타일 등)은 **다시 묻지 말고**, 그 다음 단계의 구체적인 질문으로 넘어간다.
- 메모리에 실제 저장될 경우(제어창에), 이 기준을 기억해둘게요" 혹은 "이번 쇼핑에서는 해당 내용을 고려하지 않을게요", “지금 말씀해주신 내용은 메모리에 추가해두면 좋을 것 같아요.”라고 표현을 먼저 제시한다.
- 사용자가 모호하게 말하면 부드럽게 구체적으로 다시 물어본다
- (매우 매우 중요) 사용자에게 ‘음질 선호(저음/중음/고음)’처럼 세부적인 음향 특성을 묻는 follow-up 질문은 절대 하지 않는다. 음질이라는 기준 자체는 받을 수 있지만, 세부 음역대 관련 질문은 금지한다.
- 사용자가 기준을 바꾸거나 기존 메모리와 충돌하는 발화를 하면  
  “제가 기억하고 있던 내용은 ~였는데, 이번에는 기준을 바꾸실까요? 아니면 둘 다 함께 고려해볼까요?”라고 부드럽게 확인한다.
- 사용자가 “모르겠어요 / 글쎄요 / 아직 생각 안 했어요” 라고 말하면  
  “그렇다면 실제로 쓰실 상황을 떠올려보면 어떨까요? 출퇴근, 공부, 게임 중에 어떤 상황이 가장 많을까요?”처럼 맥락 중심으로 되묻거나, "제 생각은 이 기준이 중요하게 고려되면 좋을 것 같아요."로 안내한다.

[질문 방식 규칙]
1) 메모리 기준을 하나씩 따로 떼어서 물어보지 않는다.
   - 예: "착용감은 어떠세요?" / "음질은 어떠세요?" 같은 단일 속성 질문 금지.

2) 사용자가 말한 ‘사용 목적’ 또는 ‘사용 맥락’을 반드시 기반으로 후속 질문을 생성한다.
   - 예: "음악 감상용이라고 하셨는데, 보통 어떤 환경에서 들으시나요?"
   - 예: "가성비와 블랙 선호하신다고 하셨는데, 어떤 상황에서 사용할 제품을 찾고 계신가요?"

3) 질문은 ‘카테고리별 체크리스트형 나열’이 아니라
   ‘맥락을 깊게 이해하기 위한 하나의 자연스러운 질문’으로 제시한다.

4) 후속 질문이 필요할 때는 항상 이유를 함께 설명한다.
   - 예: "환경에 따라 추천되는 모델이 달라져서요!"

5) 절대 다음과 같은 패턴을 출력하지 않는다:
   - “제가 기억하고 있는 내용은 ~~ 이고요.” (메모리 나열 금지)
   - "그러면 착용감은 어떠신가요?" 등 단일 요소 질문 금지
   - "음질/착용감/배터리 중 어떤 것이 중요하신가요?" 같은 옵션 나열 금지
   
6) 메모리 내용을 그대로 나열하며 시작하지 않는다.
대신 사용자가 마지막에 말한 내용 + 기억 중 핵심 요소 1~2개만 자연스럽게 문장 중간에 녹여서 말한다.
예: "블랙톤 제품을 선호하신다고 하셨는데…"

[대화 흐름 규칙]
- 1단계(explore): 사용자가 사전에 입력한 정보 + 대화 중 발화를 바탕으로,  
  **용도/상황, 음질, 착용감, 노이즈캔슬링, 배터리, 디자인/스타일, 색상, 예산** 중에서 중요하게 고려하는 기준이 별도로 있는지 묻는다.
- 중요) 만약 "(가장 중요)" 태그가 붙은 기준이 '디자인/스타일'이라면,
  이 기준을 반드시 **우선해서** 1회 질문해야 한다.
  - 예: 색상 정보가 이미 있다면 디자인 스타일(미니멀/트렌디/심플 등)를 먼저 묻는다.
  - 예: (가장 중요)가 가격/가성비인 경우 다른 질문보다 **예산/가격대**를 먼저 묻는다.
- 단, 이미 메모리에 있는 항목이나 한번 물어봤던 질문은 다시 물어보지 않고 다음 기준으로 넘어간다.(예: 음질 물어보면 거기서 끝낸다.)
- 추천 단계로 넘어가기 전에 **예산**은 반드시 한 번은 확인해야 한다.
- 마지막으로 예산까지 다 채워져 요약 및 추천 단계로 넘어가기 전, 최우선 기준이 결국 무엇인지 무조건 물어본다.
- (중요) 메모리가 5개 이상이면 "지금까지 기준을 정리해드릴까요?"라고 추천하기 버튼을 제공하는 단계로 넘어간다.
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
# 4. 유틸리티 함수 (조사, 정규화, 판별, 메모리 추출)
# =========================================================
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

def naturalize_memory(mem: str) -> str:
    """GPT 메모리를 완성 문장만 남기도록 정제"""
    if not mem:
        return None

    mem = mem.strip()

    # 1) 너무 짧거나 비문 제거
    if len(mem) < 6:
        return None
    if not any(mem.endswith(end) for end in ["요.", "예요.", "에요.", "니다.", "."]):
        return None

    # 2) AI 분석 문장 패턴 제거
    forbidden = [
        "사용자는", "강조한", "보입니다", "추정됩니다",
        "것 같아요", "것 같습니다", "요약하면", "분석하면"
    ]
    for f in forbidden:
        if f in mem:
            return None

    # 3) 질문 제거
    if "?" in mem:
        return None

    # 4) 표현 표준화
    mem = mem.replace("노이즈 캔슬링", "노이즈캔슬링")
    mem = mem.replace("필요없", "필요 없음")
    mem = mem.replace("비싼것까진 필요없", "비싼 것 필요 없음")

    mem = re.sub(r'(을|를)\s*선호$', ' 선호해요.', mem)
    mem = re.sub(r'(을|를)\s*고려$', ' 고려해요.', mem)

    return mem


def is_negative_response(text: str) -> bool:
    """사용자가 질문을 회피/거부하는 답을 했는지 판별"""
    if not text:
        return False

    negative_keywords = [
        "없어", "없다고", "몰라", "모르겠", "잘 모르",
        "글쎄", "별로", "아닌데", "굳이",
        "그만", "필요없", "상관없", "안중요", "관심없"
    ]

    return any(k in text for k in negative_keywords)

def extract_memory_with_gpt(user_input: str, memory_text: str):
    """
    GPT에게 사용자 발화에서 저장할 만한 쇼핑 메모리를 추출하게 하는 함수.
    JSON만 출력하도록 강제하며 f-string 오류 방지를 위해 {{ }} 으로 escape.
    """

    prompt = f"""
당신은 '헤드셋 쇼핑 메모리 요약 AI'입니다.

사용자 발화:
\"\"\"{user_input}\"\"\"

현재까지 저장된 메모리:
{memory_text if memory_text else "(없음)"}

아래 조건에 따라 **추가할 가치가 있는 메모리**만 추출하세요.

반드시 아래 JSON 형식으로만 출력하세요:
{{
  "memories": [
      "문장1",
      "문장2"
  ]
}}

### 메모리 추출 규칙 ###

1) **쇼핑 기준이 아닌 문장 금지**
   - 사용자 분석, 감정, 추론형 문장 금지
   - 예: "사용자는 ~로 보입니다", "중요성을 강조한 것 같습니다" → 저장 금지

2) **불완전한 문장 금지**
   - 너무 짧은 단편 (<6자) 금지
   - 질문 형태 금지 (문장 끝에 '?' 금지)

3) **쇼핑 기준으로 재가공**
   - "나는 귀가 자주 아파" → "착용감이 편한 제품을 선호해요."
   - "나는 노래를 자주 들어" → "주로 음악 감상용 용도로 사용할 예정이에요."
   - "디자인이 중요해" → "트렌디하고 디자인으로 인기 많은 제품을 선호해요."


4) **중복 기준이나 이미 있는 기준은 제외**

5) **JSON만 출력**
    다른 설명이나 문장은 절대 출력하지 말 것.
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
# 5. 메모리 추가/수정/삭제 (안정성 강화 버전)
# =========================================================
def _is_color_memory(text: str) -> bool:
    """색상 관련 메모리인지 판별"""
    if not text:
        return False

    t = text.replace("(가장 중요)", "")
    if "색상" in t and "선호" in t:
        return True

    color_keywords = [
        "화이트", "블랙", "네이비", "퍼플", "실버",
        "그레이", "핑크", "보라", "골드"
    ]
    return any(k in t for k in color_keywords)


def _after_memory_change():
    """메모리가 변경된 뒤 공통 처리"""
    st.session_state.just_updated_memory = True
    st.session_state.memory_changed = True

    # 요약 단계면 요약도 재계산
    if st.session_state.stage == "summary":
        st.session_state.summary_text = build_summary_from_memory(
            st.session_state.nickname,
            st.session_state.memory,
        )

    # comparison 단계면 추천도 재생성
    if st.session_state.stage == "comparison":
        st.session_state.recommended_products = make_recommendation()

# =========================================================
#  🔥 add_memory() — 예외 없는 안정 버전 (통째로 복붙)
# =========================================================
def add_memory(mem_text: str, announce: bool = True):
    """메모리 추가 (안정화된 완성본)"""

    if mem_text is None:
        return
    if not isinstance(mem_text, str):
        return
    mem_text = mem_text.strip()
    if not mem_text:
        return

    # 자연화
    mem_text = naturalize_memory(mem_text)

    # naturalize_memory가 None 반환하면 종료
    if not mem_text:
        return

    mem_text_stripped = mem_text.replace("(가장 중요)", "").strip()

    ss = st.session_state

    # 예산 중복 제거
    if "예산은 약" in mem_text_stripped:
        ss.memory = [m for m in ss.memory if "예산은 약" not in str(m)]

    # 색상 중복 제거
    if _is_color_memory(mem_text_stripped):
        ss.memory = [m for m in ss.memory if not _is_color_memory(str(m))]

    # 유사 내용 검사
    for i, m in enumerate(ss.memory):
        if m is None:
            continue

        base = str(m).replace("(가장 중요)", "").strip()

        # 포함 관계 → 업데이트 고려
        if mem_text_stripped in base or base in mem_text_stripped:
            # (가장 중요) 승급
            if "(가장 중요)" in mem_text and "(가장 중요)" not in m:
                ss.memory = [
                    mm.replace("(가장 중요)", "").strip() for mm in ss.memory
                ]
                ss.memory[i] = mem_text
                if announce:
                    ss.notification_message = "🌟 최우선 기준으로 재설정했어요!"
                _after_memory_change()
                return

            return  # 추가 안함

    # 새로운 메모리 추가
    ss.memory.append(mem_text)

    if announce:
        ss.notification_message = "🧩 새로운 기준을 기억해둘게요!"

    _after_memory_change()

def delete_memory(idx: int):
    """메모리 삭제"""
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.notification_message = "🧹 메모리를 삭제했어요."
        _after_memory_change()


def update_memory(idx: int, new_text: str):
    """메모리 수정"""
    if not (0 <= idx < len(st.session_state.memory)):
        return

    if not new_text or not isinstance(new_text, str):
        return

    new_text = naturalize_memory(new_text).strip()

    # '(가장 중요)' 포함 시 다른 메모리들 태그 제거
    if "(가장 중요)" in new_text:
        st.session_state.memory = [
            m.replace("(가장 중요)", "").strip()
            for m in st.session_state.memory
        ]

    st.session_state.memory[idx] = new_text
    st.session_state.notification_message = "🔄 기준이 수정되었어요."
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

def build_carousel_html(product_list):
    cards_html = ""
    for p in product_list:
        cards_html += f"""
        <div class="carousel-card">
            <img src="{p['img']}" />
            <div class="carousel-title">{p['name']}</div>
            <div class="carousel-price">₩{p['price']:,}</div>
        </div>
        """
    return f"<div class='carousel-wrapper'>{cards_html}</div>"

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

import random

import random

def generate_personalized_reason(product, mems, name):
    reasons = []
    mem_str = " ".join(mems)
    tags = product.get("tags", [])

    # ============================================
    # 🔥 핵심 가치 기반 초간단 요약 (카드용)
    # ============================================
    # 우선순위: 메모리 → 제품 태그 순으로 하나 또는 두 개만 선택

    if "음질" in mem_str and "음질" in tags:
        reasons.append("음질 중심 사용자에게 잘 맞아요.")

    if "착용감" in mem_str and any(t in tags for t in ["편안함", "경량", "가벼움", "착용감"]):
        reasons.append("장시간 착용 용도로 적합해요.")

    if "노이즈캔슬링" in mem_str and "노이즈캔슬링" in tags:
        reasons.append("노이즈캔슬링 성능이 뛰어나요.")

    # 제품 태그 기반 보조 문장
    if "배터리" in tags:
        reasons.append("배터리가 오래가는 편이에요.")

    if "가성비" in tags:
        reasons.append("가성비가 뛰어난 선택이에요.")

    if "통화품질" in tags:
        reasons.append("통화 품질도 준수해서 업무용으로 좋아요.")

    if "음질" in tags and "음질" not in mem_str:
        reasons.append("음질 평가도 좋아요.")

    # ============================================
    # ✨ 마지막 문장 — 제품 특성과 사용자 취향 기반 랜덤 선택
    # ============================================

    closing_templates = [
        f"{name}님의 취향과 잘 맞는 조합이에요!",
        f"{name}님이 선호하시는 기준과 잘 어울리는 제품이에요.",
        f"여러 기준을 고려하면 {name}님께 특히 잘 맞을 것 같아요.",
        f"{name}님의 사용 스타일과 궁합이 좋아 보여요!",
        f"{name}님이 말씀하신 조건들과 자연스럽게 맞닿아 있어요."
    ]

    # 태그 기반 특정 버전 추가
    if "음질" in tags:
        closing_templates.append(f"특히 음질을 중시하는 {name}님께 잘 맞는 타입이에요.")
    if "배터리" in tags:
        closing_templates.append(f"오래 쓰는 사용 패턴을 가진 {name}님께도 잘 맞아요.")
    if "가성비" in tags:
        closing_templates.append(f"실속 있는 선택을 찾는 {name}님께 잘 어울려요.")

    reasons.append(random.choice(closing_templates))

    # ============================================
    # 중복 제거 + 2~3줄 이내로 제한
    # ============================================
    unique_reasons = []
    for r in reasons:
        if r not in unique_reasons:
            unique_reasons.append(r)

    # 카드에는 너무 길면 안되므로 2~3개 정도만 노출
    return "\n".join(unique_reasons[:3])

def send_product_detail_message(product):
    """
    선택된 제품의 상세 정보를 '채팅 메시지' 형태로 한 번에 보내는 함수.
    별도 페이지로 이동하지 않고, 대화 흐름 안에서 보여주기 위함.
    """
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
# 7. 상품 카탈로그 (기존 그대로)
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
    """GPT가 단계(stage)별로 다르게 응답하도록 제어하는 핵심 함수"""

    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    nickname = st.session_state.nickname
    stage = st.session_state.stage

    # =========================================================
    # 1) product_detail 단계: 전용 프롬프트 강제 사용
    # =========================================================
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

    # =========================================================
    # 2) 탐색(explore) / 요약(summary) / 비교(comparison) 단계
    # =========================================================
    stage_hint = ""

    # 🔒 항상 헤드셋 대화 규칙
    stage_hint += (
        "[중요 규칙] 이 대화는 항상 '블루투스 헤드셋' 기준입니다. "
        "스마트폰·노트북 등 다른 기기 추천이나 질문은 하지 마세요.\n\n"
    )

    # ---------------------------------------------------------
    # A. 디자인/스타일 최우선 감지
    # ---------------------------------------------------------
    design_keywords = ["디자인", "스타일", "예쁜", "깔끔", "세련", "미니멀", "레트로", "감성", "스타일리시"]

    is_design_in_memory = any(
        any(k in m for k in design_keywords)
        for m in st.session_state.memory
    )

    design_priority = any(
        "(가장 중요)" in m and any(k in m for k in design_keywords)
        for m in st.session_state.memory
    )

    # 색상 정보 있는지
    has_color_detail = any("색상" in m for m in st.session_state.memory)

    # ---------------------------------------------------------
    # B. explore 단계에서 ‘디자인이 최우선’이면
    #    → 이번 턴엔 반드시 ‘디자인 or 색상’ 질문만 1개
    # ---------------------------------------------------------
    if stage == "explore" and design_priority:
        stage_hint += """
[디자인/스타일 최우선 규칙 – 이번 턴 필수]
- 이번 턴에는 반드시 ‘디자인’ 또는 ‘색상’ 관련 질문 **단 1개**만 하세요.
- 음질/착용감/배터리/노이즈캔슬링 등 기능 질문은 **이번 턴에서 금지**합니다.
- 이미 색상 정보를 알고 있다면 디자인 스타일(깔끔/트렌디/레트로 등)만 물어보세요.
"""

    # ---------------------------------------------------------
    # C. explore 단계 — 용도는 이미 메모리에 있으면 절대 다시 묻지 않기
    # ---------------------------------------------------------
    usage_keywords = ["용도", "출퇴근", "운동", "게임", "여행", "공부", "음악 감상"]
    is_usage_in_memory = any(any(k in m for k in usage_keywords) for m in st.session_state.memory)

    if stage == "explore" and is_usage_in_memory and len(st.session_state.memory) >= 2:
        stage_hint += (
            "[용도 파악됨] 이미 사용 용도는 기억하고 있습니다. "
            "다시 묻지 말고 다음 기준(음질/착용감/디자인 등)으로 넘어가세요.\n"
        )

    # ---------------------------------------------------------
    # D. GPT 본문 프롬프트 구성
    # ---------------------------------------------------------
    prompt_content = f"""
{stage_hint}

[현재 저장된 쇼핑 메모리]
{memory_text if memory_text else "(아직 없음)"}

[사용자 발화]
{user_input}

위 정보를 참고해서, '블루투스 헤드셋 쇼핑 도우미' 역할로서
다음 말을 자연스럽고 짧게 이어가세요.
"""

    # 실제 GPT 호출
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
#  메모리 사이드바 (완전 안정화 버전)
# =========================================================
def render_memory_sidebar():
    ss = st.session_state

    # --------------------------
    # UI 헤더
    # --------------------------
    st.markdown(
        "<div class='memory-section-header'>🧠 나의 쇼핑 메모리</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class='memory-guide-box'>
            AI가 기억하고 있는 쇼핑 취향이에요.<br>
            필요하면 직접 수정하거나 삭제할 수 있어요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------
    # 기존 메모리 표시
    # --------------------------
    for i, mem in enumerate(ss.memory):
        if mem is None:
            continue

        c1, c2 = st.columns([8, 2])

        with c1:
            st.markdown(
                f"<div class='memory-block'><div class='memory-text'>{mem}</div></div>",
                unsafe_allow_html=True,
            )

        with c2:
            if st.button("X", key=f"delete_mem_{i}"):
                delete_memory(i)
                st.experimental_rerun()

    st.markdown("---")

    # --------------------------
    # ✏️ 메모리 직접 추가
    # --------------------------
    st.markdown("**✏️ 메모리 직접 추가하기**")

    # ❗필수: key가 매번 새롭게 초기화되도록
    new_mem = st.text_input(
        "추가할 기준",
        key="manual_memory_add_input",
        placeholder="예: 귀가 편한 제품이면 좋겠어요",
    )

    if st.button("메모리 추가하기", key="manual_memory_add_btn"):
        if isinstance(new_mem, str) and new_mem.strip():
            add_memory(new_mem.strip())

        # 입력칸 초기화 (명령어 X)
        # Streamlit-safe 방식 → 컴포넌트 키 변경
        ss.manual_memory_add_input = ""

        st.experimental_rerun()

    st.markdown("---")
    
    # --------------------------
    # ✏️ 메모리 직접 추가 UI
    # --------------------------
    st.markdown("**✏️ 메모리 직접 추가하기**")

    new_mem = st.text_input(
        "추가할 기준",
        key="manual_memory_add",
        placeholder="예: 귀가 편한 제품이면 좋겠어요",
    )

    # 🔥 cleaned 변수를 여기에서 반드시 정의
    if st.button("메모리 추가하기", key="manual_memory_add_btn"):
        cleaned = new_mem  # ← 반드시 정의 필요

        # 🔒 None / 비문자열 / 빈 문자열 → 추가 금지
        if cleaned and isinstance(cleaned, str) and cleaned.strip() != "":
            cleaned_text = cleaned.strip()
            add_memory(cleaned_text)      # 정상 추가
            ss.manual_memory_add = ""     # 입력칸 초기화
            st.rerun()

    # 입력칸 리셋
    st.session_state.manual_memory_add = ""

    st.rerun()

def render_product_carousel(products):
    if not products:
        return
    
    st.markdown("""
    <style>
    .carousel-container {
        width: 100%;
        overflow: hidden;
        position: relative;
        margin-top: 12px;
    }
    .carousel-track {
        display: flex;
        transition: transform 0.3s ease;
    }
    .carousel-item {
        min-width: 240px;
        max-width: 240px;
        background: white;
        border-radius: 12px;
        padding: 12px;
        margin-right: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .carousel-img {
        width: 100%;
        height: 180px;
        object-fit: cover;
        border-radius: 8px;
        margin-bottom: 8px;
    }
    .carousel-btn {
        background: #2563eb;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 4px 10px;
        margin-top: 6px;
        cursor: pointer;
    }
    </style>

    <script>
    let currentIndex = 0;

    function moveCarousel(direction){
        const track = document.getElementById("carousel-track");
        const itemWidth = 252;  // 240 + margin 12
        const totalItems = track.children.length;

        currentIndex += direction;
        if (currentIndex < 0) currentIndex = 0;
        if (currentIndex > totalItems - 1) currentIndex = totalItems - 1;

        track.style.transform = `translateX(-${currentIndex * itemWidth}px)`;
    }
    </script>
    """, unsafe_allow_html=True)

    # HTML 렌더링
    html = '<div class="carousel-container">'
    html += '<div id="carousel-track" class="carousel-track">'

    for p in products:
        html += f"""
        <div class="carousel-item">
            <img src="{p['img']}" class="carousel-img"/>
            <div><b>{p['name']}</b></div>
            <div>{p['price']:,}원</div>
            <button class="carousel-btn" onclick="window.location.hash='#detail-{p['name']}'">자세히</button>
        </div>
        """
    html += "</div></div>"

    # 버튼
    html += """
    <div style="margin-top:8px; display:flex; gap:10px;">
        <button class="carousel-btn" onclick="moveCarousel(-1)">◀</button>
        <button class="carousel-btn" onclick="moveCarousel(1)">▶</button>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)

# ============================================================
# 상품 상세 메시지 생성
# ============================================================
def format_product_detail_msg(product):
    features = ""
    if "features" in product:
        for f in product["features"]:
            features += f"- {f}\n"

    return (
        f"[@{product['name']} 상세 정보]\n\n"
        f"📌 **가격:** {product['price']:,}원\n"
        f"⭐ **평점:** {product['rating']:.1f}점 ({product['reviews']}개 리뷰)\n\n"
        f"**주요 특징:**\n"
        f"{features if features else '등록된 상세 특징이 없어요.'}\n\n"
        f"궁금하신 점을 자유롭게 물어보세요!\n"
        f"예: \"노이즈캔슬링 강한가요?\", \"착용감 어떤 편인가요?\""
    )

# ============================================================
# 카드 하이라이트 CSS
# ============================================================
# ============================================================
# 카드 하이라이트 CSS
# ============================================================
def inject_card_css():
    st.markdown(
        """
        <style>
        .product-card {
            transition: 0.15s ease;
            padding: 14px;
            border-radius: 14px;
            background: white;
            border: 1px solid #EEE;
        }
        .product-card.selected {
            border: 3px solid #4A8DFD !important;
            box-shadow: 0 0 15px rgba(74,141,253,0.4) !important;
            transform: scale(1.02);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# 추천 UI (★ 완전 교체)
# ============================================================
import html
def recommend_products_ui(name, mems):
    inject_card_css()  # 카드 강조 CSS 한 번만 주입
    products = st.session_state.recommended_products
    ...

def recommend_products_ui(name, mems):
    products = st.session_state.recommended_products

    if not products:
        st.warning("추천을 위해 기준이 조금 더 필요해요!")
        return

    st.markdown("### 🔍 고객님을 위한 후보들을 비교해보세요!")

    # CSS
    st.markdown("""
        <style>
        .product-card {
            min-height: 360px;
            border-radius: 12px;
            padding: 15px;
            background: white;
            text-align: center;
            position: relative;
        }
        .product-img {
            width: 100%;
            border-radius: 10px;
            margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    cols = st.columns(3)

    for idx, p in enumerate(products):
        with cols[idx]:

            is_sel = (
                st.session_state.selected_product is not None and
                st.session_state.selected_product["name"] == p["name"]
            )

            border = "#2563EB" if is_sel else "#e5e7eb"
            badge = (
                '<div style="position:absolute; top:8px; right:8px; '
                'background:#2563EB; color:white; padding:3px 6px; '
                'border-radius:6px; font-size:11px;">선택됨</div>'
                if is_sel else ""
            )

            # ------- 여기! 한 줄씩 더하기 방식으로 변경 -------
            html_parts = []

            html_parts.append(f'<div class="product-card" style="border:2px solid {border};">')

            if badge:
                html_parts.append(badge)

            html_parts.append(f'<img src="{p["img"]}" class="product-img">')

            html_parts.append(f'<div style="font-weight:700; font-size:15px;">{p["name"]}</div>')
            html_parts.append(f'<div style="color:#2563EB; font-weight:600;">{p["price"]:,}원</div>')
            html_parts.append(f'<div style="font-size:13px; color:#6b7280;">⭐ {p["rating"]:.1f} / 리뷰 {p["reviews"]}</div>')

            html_parts.append(
                '<div style="margin-top:10px; font-size:13px; color:#4b5563;">'
                + html.escape(generate_personalized_reason(p, mems, name))
                + '</div>'
            )

            html_parts.append('</div>')

            # 👉 문자열을 join 해서 한 줄 HTML로 만듦 → 절대 깨지지 않음
            card_html = "".join(html_parts)

            st.markdown(card_html, unsafe_allow_html=True)

            if st.button("상세보기", key=f"detail_{p['name']}"):
                st.session_state.selected_product = p
                send_product_detail_message(p)
                st.rerun()

    # -------------------------
    # 선택된 제품이 있을 때만 하단 결정 버튼
    # -------------------------
    if st.session_state.selected_product:
        p = st.session_state.selected_product

        st.markdown(
            f"""
            <div style="margin-top:15px; padding:12px 16px; background:#ECF5FF;
            border-radius:12px; font-size:15px; border:1px solid #cfe1ff;">
                ✔ <b>{p['name']}</b> 제품을 선택하셨어요.
                아래 버튼으로 최종 결정을 진행할 수 있어요.
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("🛒 이 제품으로 결정하기", key="final_decide_btn"):
            st.session_state.final_choice = p
            st.session_state.stage = "purchase_decision"
            ai_say(f"좋습니다! **'{p['name']}'**(으)로 결정하셨네요. 필요한 정보가 있으면 뭐든지 도와드릴게요.")
            st.rerun()

    else:
        st.info("한 제품을 자세히 보고 싶으시면 위 카드 중 하나를 선택해주세요. 😊")

# =========================================================
# 14. 요약 생성 함수
# =========================================================
def build_summary_from_memory(name, mems):
    if not mems:
        return (
            f"{name}님, 아직 명확한 기준이 정해지지 않았어요. "
            "몇 가지 기준만 알려주시면 추천을 도와드릴게요!"
        )

    # 메모리 내용을 하나의 문장 기반 자료로 연결
    memory_text = " / ".join(mems)

    # 🔵 GPT 요약 요청 (톤 개선 버전)
    prompt = f"""
아래는 사용자가 알려준 ‘쇼핑 기준 메모리 리스트’입니다:

{memory_text}

이 정보를 바탕으로, 다음 조건에 맞는 2~3문장 요약을 작성하세요.

[요약 톤 가이드]
- 메모리를 그대로 옮겨 적지 말 것 (예: "화이트 선호 / 가벼운 헤드셋" 식 나열 금지)
- 사용자의 전반적 경향을 ‘해석한 것처럼’ 자연스럽게 표현
- "제 생각에는 ~" 같은 해석적 표현 1회 포함
- 가장 중요한 기준은 “핵심 기준으로 작동하고 있어요 / 특히 ~가 중심이 되는 것 같아요” 식으로 부드럽게 강조
- 연구 실험 맥락의 AI 보조자처럼 친절하고 자연스러운 말투
- 문장은 총 2~3개로 유지할 것

출력 예시 스타일:
"제가 파악하기로는 ~~~ 전반적으로 ~~~ 균형 있게 고려하고 계신 것 같아요. 
제 생각에는 그중에서도 ~~~ 요소가 핵심 기준으로 작동하고 있는 것 같습니다."
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )

    summary_sentence = res.choices[0].message.content.strip()

    # 최우선 기준(PRIORITY)
    primary = None
    for m in mems:
        if "(가장 중요)" in m:
            primary = m.replace("(가장 중요)", "").strip()
            break

    # 템플릿
    return f"""
[@{name}님의 쇼핑 기준 요약]

{summary_sentence}

혹시 더 중요한 기준이 있거나 빼고 싶은 기준이 있다면  
왼쪽 ‘쇼핑 메모리’에서 수정하실 수 있고,  
저에게 편하게 말씀해주셔도 바로 반영해드릴게요! 😊
"""

# =========================================================
# 15. 추천 모델 (메모리 기반 점수)
# =========================================================
def score_item_with_memory(item, mems):
    score = 0
    
    mtext = " ".join(mems)
    budget = extract_budget(mems)

    # (1) 최우선 기준 강점 보정
    if "(가장 중요)" in mtext:
        if "디자인/스타일" in mtext and "디자인" in item["tags"]:
            score += 50
        if "음질" in mtext and "음질" in item["tags"]:
            score += 50
        if "착용감" in mtext and "착용감" in item["tags"]:
            score += 50

    # (2) 일반 기준 반영
    for m in mems:
        if "노이즈" in m and "노이즈캔슬링" in item["tags"]:
            score += 20
        if "가성비" in m and "가성비" in item["tags"]:
            score += 20
        if "색상" in m:
            for col in item["color"]:
                if col in m:
                    score += 10

    # (3) 랭크 보정
    score -= item["rank"]

    # ---------------------------
    # (4) 🟡 예산 보정 — 가장 중요!
    # ---------------------------
    if budget:
        if item["price"] > budget:
            diff = item["price"] - budget
            if diff > 100000:          # 10만원 초과
                score -= 200
            else:
                score -= 80
        else:
            score += 30  # 예산 이내면 가산점

    return score

def make_recommendation():
    scored = [(score_item_with_memory(item, st.session_state.memory), item) for item in CATALOG]
    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:3]]

# =========================================================
# 16. 사용자 입력 처리 (최종 안정화 버전)
# =========================================================
def handle_input():
    ss = st.session_state

    # ---------------------------------------------------------
    # (0) 사용자 입력 로딩
    # ---------------------------------------------------------
    u = ss.user_input_text.strip()
    if not u:
        return

    # ---------------------------------------------------------
    # (1) 메모리 컷오프: 6개 이상 → 질문 중단 + Summary 유도
    # ---------------------------------------------------------
    if len(ss.memory) >= 6:
        ai_say("지금까지 기준을 정리해드릴까요? 추천을 받으실 수 있어요! 🙌")
        ss.stage = "summary"
        ss.summary_text = build_summary_from_memory(ss.nickname, ss.memory)
        return

    # ---------------------------------------------------------
    # (2) 사용자 입력 메시지 저장
    # ---------------------------------------------------------
    user_say(u)

    # ---------------------------------------------------------
    # (3) 카테고리 드리프트 방지
    # ---------------------------------------------------------
    drift_words = ["스마트폰", "휴대폰", "핸드폰", "아이폰", "갤럭시", "폰"]
    if any(w in u for w in drift_words):
        ai_say("앗! 지금은 블루투스 헤드셋 추천 단계예요 😊 헤드셋 기준으로만 도와드릴게요!")
        return
        
    # ---------------------------------------------------------
    # (3-1) 예산 직접 인식 & 메모리 저장
    # ---------------------------------------------------------
    budget_text = u.replace(",", "")
    budget_val = None

    # "20만원", "20만 원" 등
    m_man = re.search(r"(\d+)\s*만\s*원?", budget_text)
    if m_man:
        budget_val = int(m_man.group(1)) * 10000
        budget_mem = f"예산은 약 {m_man.group(1)}만원이에요."
    else:
        # "200000원", "200000 원" 등 숫자 그대로 말할 때
        m_won = re.search(r"(\d{2,7})\s*원", budget_text)
        if m_won:
            raw = int(m_won.group(1))
            # 만원 단위로 대충 반올림해서 메모리에 저장
            man = round(raw / 10000)
            budget_val = man * 10000
            budget_mem = f"예산은 약 {man}만원이에요."

    if budget_val is not None:
        # 예산 관련 기존 메모리 정리 + 새 예산 메모리 추가
        add_memory(budget_mem)
        ai_say(f"네, 예산은 약 {budget_val:,}원 정도로 기억해둘게요. 😊")
        # 여기서 바로 요약/추천으로 넘기고 싶으면 아래처럼 추가해도 됨
        # if len(ss.memory) >= 5 and ss.stage == "explore":
        #     ss.stage = "summary"
        #     ss.summary_text = build_summary_from_memory(ss.nickname, ss.memory)
        #     return

    # ---------------------------------------------------------
    # (4) 질문 응답 처리 (부정/긍정 등)
    # ---------------------------------------------------------
    cur_q = ss.current_question

    # 부정적 응답 → 이 질문은 종료
    if is_negative_response(u):
        if cur_q is not None:
            ss.question_history.append(cur_q)
            ss.current_question = None
        ai_say("네! 그 부분은 중요하지 않다고 이해했어요. 다음으로 넘어가볼게요 😊")
        return

    # 정상 응답 → 질문 종료
    if cur_q is not None:
        ss.question_history.append(cur_q)
        ss.current_question = None

    # ---------------------------------------------------------
    # (5) 메모리 추출 및 충돌 처리
    # ---------------------------------------------------------
    memory_text = "\n".join([naturalize_memory(m) for m in ss.memory])
    extracted = extract_memory_with_gpt(u, memory_text)

    if extracted:
        for mem in extracted:
            before = len(ss.memory)
            add_memory(mem)
            after = len(ss.memory)

            if after > before:
                ss.notification_message = f"🧩 '{mem}' 내용을 기억해둘게요."

    # ---------------------------------------------------------
    # (6) 우선 기준 Follow-up 질문 — 1회만
    # ---------------------------------------------------------
    if not ss.priority_followup_done:
        primary = ss.primary_style  # "design" / "performance" / "price"

        if primary == "design":
            ai_say(
                "디자인/스타일이 가장 중요하시다고 하셔서 여쭤볼게요! "
                "어떤 느낌의 스타일을 선호하시나요? (예: 미니멀, 레트로, 심플, 포인트 컬러 등)"
            )
            ss.priority_followup_done = True
            return

        elif primary == "performance":
            ai_say(
                "성능을 중요하게 보신다고 하셔서 설명드릴게요!\n"
                "보통 음질, 노이즈캔슬링, 배터리, 착용감 네 가지를 많이 비교해요.\n"
                "이 중에서 특히 더 중점적으로 보고 싶은 항목이 있으실까요?"
            )
            ss.priority_followup_done = True
            return

        elif primary == "price":
            ai_say(
                "가성비를 가장 중요하게 보신다고 하셔서 여쭤볼게요!\n"
                "혹시 생각하고 계신 최대 예산은 어느 정도일까요?"
            )
            ss.priority_followup_done = True
            return

    # ---------------------------------------------------------
    # (7) 예산 유도
    # ---------------------------------------------------------
    has_budget = any("예산" in m for m in ss.memory)
    mem_count = len(ss.memory)

    if mem_count >= 5 and not has_budget and ss.priority_followup_done:
        ai_say(
            "추천 전에 **예산**을 알려주시면 더 정확하게 맞춰드릴 수 있어요! "
            "블루투스 헤드셋은 보통 10–60만원 사이에 많이 있어요. "
            "원하시는 가격대를 알려주실 수 있을까요?"
        )
        return

    # ---------------------------------------------------------
    # (8) SUMMARY 진입 조건
    # ---------------------------------------------------------
    if ss.stage == "explore" and has_budget and mem_count >= 5:
        ss.stage = "summary"
        ss.summary_text = build_summary_from_memory(ss.nickname, ss.memory)
        return

    # ---------------------------------------------------------
    # (9) 기본 GPT 응답
    # ---------------------------------------------------------
    reply = gpt_reply(u)
    ai_say(reply)

    # ---------------------------------------------------------
    # (10) GPT가 질문을 생성한 경우 → 질문 ID 자동 기록
    # ---------------------------------------------------------
    qid = None

    if "디자인" in reply:
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

    # 이미 했던 질문이면 무시
    if qid and qid in ss.question_history:
        ss.current_question = None
        return

    # 새 질문이면 저장
    ss.current_question = qid

    # ---------------------------------------------------------
    # (11) Stage 진행
    # ---------------------------------------------------------
    if ss.stage == "summary":
        if any(k in u for k in ["좋아요", "네", "추천", "맞아요"]):
            ss.stage = "comparison"
            ss.recommended_products = make_recommendation()
            ai_say("좋아요! 지금까지 알려주신 기준을 바탕으로 추천을 드릴게요 🙌")
        else:
            ai_say(
                "수정하고 싶은 부분이 있으시면 왼쪽 '쇼핑 메모리'에서 직접 수정하실 수 있어요.\n"
                "또는 채팅창에 편하게 말씀하시면 반영해드릴게요!"
            )

    elif ss.stage == "product_detail":
        if any(k in u for k in ["결정", "구매", "이걸로 할게"]):
            ss.stage = "purchase_decision"
            ss.final_choice = ss.selected_product
            ai_say("좋아요! 이제 구매 결정을 도와드릴게요.")

# =========================================================
# 17. context_setting 페이지 (정상 동작 버전)
# =========================================================
def context_setting_page():
    st.title("🛒 쇼핑 에이전트에게 정보를 알려주세요.")

    st.markdown(
        """
        <div class="info-text">
            본격적인 쇼핑 전, <b>AI 에이전트가 귀하의 쇼핑 경험, 취향 등</b>을 기억할 수 있도록 에이전트의 초기 메모리를 쌓는 단계입니다.<br>
            평소 본인의 실제 쇼핑 기준이나 성향 등을 바탕으로 선택하면, 에이전트는 그 메모리에 저장한 후 대화를 이어가게 됩니다.
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
        st.subheader("Q1. 쇼핑할 때 가장 중요하게 생각하는 기준은 무엇인가요?")
        shopping_style = st.selectbox(
            "",
            ["가성비 우선형", "디자인/스타일 우선형", "성능·스펙 우선형"],
        )

        # 내부 로직용 primary_style 매핑
        if shopping_style == "가성비 우선형":
            primary_style_value = "price"
        elif shopping_style == "디자인/스타일 우선형":
            primary_style_value = "design"
        else:
            primary_style_value = "performance"

        # -----------------------
        # Q2. 초기 색상 선호도
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
        if st.button("쇼핑 시작하기", type="primary", use_container_width=True):
            if not name:
                st.warning("이름을 입력해주세요.")
                return

            # 사용자 정보 저장
            st.session_state.nickname = name
            st.session_state.phone_number = phone

            # 우선 기준 세팅
            st.session_state.primary_style = primary_style_value
            st.session_state.priority_followup_done = False

            # 초기 메모리 저장
            # ------------------------------------------------------
            # 쇼핑 성향 → 메모리 반영
            # ------------------------------------------------------
            if primary_style_value == "price":
                add_memory("가성비, 가격을 중요하게 생각하는 편이에요.", announce=False)
                # 가격형은 바로 예산 질문 가능하므로 follow-up 스킵
                st.session_state.priority_followup_done = True

            elif primary_style_value == "design":
                add_memory("(가장 중요) 디자인/스타일을 최우선으로 고려하고 있어요.", announce=False)

            else:  # performance
                add_memory("(가장 중요) 성능/스펙을 우선하는 쇼핑 성향이에요.", announce=False)

            # ------------------------------------------------------
            # 초기 색상 메모리 저장
            # ------------------------------------------------------
            add_memory(f"색상은 {color_choice} 계열을 선호해요.", announce=False)

            # 다음 페이지로 이동
            st.session_state.page = "chat"
            st.rerun()

# =========================================================
# 18. main_chat_interface (UI 그대로 사용)
# =========================================================
def main_chat_interface():

    # 🔒 안전 가드 — 세션이 완전 초기화되기 전에 호출될 때 에러 방지
    if "notification_message" not in st.session_state:
        st.session_state.notification_message = ""

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

    # 상단 UI
    render_step_header()

    col1, col2 = st.columns([3, 7], gap="large")

    with col1:
        render_memory_sidebar()

    with col2:
        # 채팅창 렌더링
        chat_container = st.container()
        with chat_container:
            html_content = '<div class="chat-display-area">'
            for msg in st.session_state.messages:
                cls = "chat-bubble-ai" if msg["role"] == "assistant" else "chat-bubble-user"
                safe = html.escape(msg["content"])
                html_content += f'<div class="chat-bubble {cls}">{safe}</div>'
    
            if st.session_state.stage == "summary":
                safe_sum = html.escape(st.session_state.summary_text)
                html_content += f'<div class="chat-bubble chat-bubble-ai">{safe_sum}</div>'
                
            # 🔥 추천 단계 → 캐러셀을 채팅창 안에 렌더링
            if st.session_state.stage == "comparison":
                prods = st.session_state.recommended_products
                if prods:
                    html_content += build_carousel_html(prods)

            html_content += "</div>"
            st.markdown(html_content, unsafe_allow_html=True)
    
        if st.session_state.stage == "summary":
            st.markdown("<br>", unsafe_allow_html=True)
        
            if st.button("🔍 이 기준으로 추천 받기"):
                st.session_state.stage = "comparison"
                st.session_state.recommended_products = make_recommendation()
                st.rerun()
        
            st.info("수정하실 기준이 있으면 아래 입력창에서 말씀해주세요. 😊")
            # ❗ 여기서 return을 제거해야 채팅 입력창이 유지됨
        # ------------------------------------------------
        # 입력폼
        # ------------------------------------------------
        with st.form(key="chat_form", clear_on_submit=True):
            c1, c2 = st.columns([85, 15])
            with c1:
                st.text_input(
                    "msg",
                    key="user_input_text",
                    label_visibility="collapsed",
                    placeholder="메시지를 입력하세요.(답변은 약 3-5초 정도 지연될 수 있습니다.)",
                )
            with c2:
                if st.form_submit_button("전송"):
                    handle_input()
                    st.rerun()

        # ------------------------------------------------
        # 추천 / 상세 / 구매 단계  ← 반드시 SUMMARY 블록과 같은 깊이여야 함
        # ------------------------------------------------
        if st.session_state.stage in ["product_detail", "purchase_decision"]:
            st.markdown("---")
    
            if st.session_state.stage == "product_detail":
                c1, c2 = st.columns([1, 4])
                with c1:
                    if st.button("목록으로(⬅️)"):
                        st.session_state.stage = "comparison"
                        st.session_state.selected_product = None
                        st.rerun()
                with c2:
                    if st.button("이 제품으로 구매 결정하기(🛒)"):
                        st.session_state.stage = "purchase_decision"
                        st.rerun()
    
            recommend_products_ui(st.session_state.nickname, st.session_state.memory)

        # ------------------------------------------------
        # 구매 결정 단계 완성 표시
        # ------------------------------------------------
        if st.session_state.stage == "purchase_decision" and st.session_state.final_choice:
            p = st.session_state.final_choice
            st.success(f"🎉 **{p['name']}** 구매를 결정하셨습니다!")
            st.balloons()

# =========================================================
# 19. 라우팅
# =========================================================
if st.session_state.page == "context_setting":
    context_setting_page()
else:
    main_chat_interface()


































































