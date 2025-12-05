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
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
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

def is_negative_response(text: str) -> bool:
    """
    사용자가 특정 질문에 대해 '없어 / 몰라 / 잘 모르겠어 / 별로 / 그만 / 관심없어' 등
    부정적이거나 회피하는 반응을 했는지 판별하는 함수.
    """
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
- 예쁜/인기많은/트렌디한/유행/귀엽/귀여/디자인 → "인기많은 디자인을 원해요."
- 깔끔/심플/모던 → "깔끔한 스타일을 선호하는 편이에요."
- 화려 → "화려한 스타일을 선호하는 편이에요."
- 레트로 → "레트로 스타일을 선호하는 편이에요."
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
        
def answer_product_question(user_input: str, product: dict) -> str:
    """
    상세보기(product_detail) 단계 전용 Q&A 응답 함수.
    탐색 질문을 절대 하지 않고, 오직 현재 제품에 대한 정보만 답변한다.
    """

    prompt = f"""
당신은 지금 '상품 상세 정보 단계(product_detail)'에 있습니다.
아래 사용자의 질문에 대해, 현재 선택된 헤드셋의 스펙・리뷰・특징 안에서만 간단히 답변하세요.

[사용자 질문]
{user_input}

[선택된 제품 정보]
- 제품명: {product['name']}
- 가격: {product['price']:,}원
- 평점: {product['rating']:.1f}
- 주요 특징: {', '.join(product['tags'])}
- 리뷰 요약: {product['review_one']}
- 색상 옵션: {', '.join(product['color'])}

규칙:
1. 탐색 질문(용도/예산/음질/착용감 등)은 절대 하지 않는다.
2. 비교 추천도 하지 않는다.
3. 오직 **현재 선택된 제품의 정보만 사실 기반으로** 답변한다.
4. 마지막 문장은 반드시 다음 중 하나로 끝낸다:
   - "다른 부분도 더 궁금하신가요?"
   - "추가로 알고 싶은 점 있으신가요?"

한국어로 간결하게 답변하세요.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    return res.choices[0].message.content

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
    """
    메모리가 변경된 뒤 공통으로 해야 할 처리:
    - just_updated_memory / memory_changed 플래그
    - summary 단계면 요약 재생성
    - comparison 단계면 추천 상품 다시 계산
    (알림 문구는 각 함수(add/delete/update)에서 개별 설정)
    """
    st.session_state.just_updated_memory = True
    st.session_state.memory_changed = True

    # summary 단계에서 메모리가 바뀌면 요약도 같이 다시 만들어주기
    if st.session_state.stage == "summary":
        st.session_state.summary_text = build_summary_from_memory(
            st.session_state.nickname,
            st.session_state.memory,
        )

    # comparison 단계에서 메모리가 바뀌면 추천 리스트도 다시 만들기
    if st.session_state.stage == "comparison":
        st.session_state.recommended_products = make_recommendation()


def add_memory(mem_text: str, announce: bool = True):
    """
    메모리 추가 로직
    - 자연스러운 표현으로 정리
    - 예산/색상 기준은 기존 것 제거 후 하나만 유지
    - 내용이 거의 같으면 덮어쓰기(중복 방지)
    - '(가장 중요)'가 붙은 경우, 다른 메모리에서 이 태그 제거 후 승급
    """
    mem_text = mem_text.strip()
    if not mem_text:
        return

    # 1) 자연스러운 표현으로 변환
    mem_text = naturalize_memory(mem_text)
    mem_text_stripped = mem_text.replace("(가장 중요)", "").strip()

    # 2) 예산 중복 처리: "예산은 약 ~만 원" 류가 들어오면 기존 예산 메모리 제거
    if "예산은 약" in mem_text_stripped:
        st.session_state.memory = [
            m for m in st.session_state.memory if "예산은 약" not in m
        ]

    # 3) 색상 기준 충돌 처리: 색상 메모리는 항상 하나만 유지
    if _is_color_memory(mem_text_stripped):
        st.session_state.memory = [
            m for m in st.session_state.memory if not _is_color_memory(m)
        ]

    # 4) 기존 메모리와 내용이 겹치는 경우 처리
    for i, m in enumerate(st.session_state.memory):
        base = m.replace("(가장 중요)", "").strip()

        # 내용이 거의 같으면(포함 관계) 업데이트로 보고 처리
        if mem_text_stripped in base or base in mem_text_stripped:
            # (가장 중요) 승급 케이스
            if "(가장 중요)" in mem_text and "(가장 중요)" not in m:
                # 다른 메모리들에서 '(가장 중요)' 모두 제거
                st.session_state.memory = [
                    mm.replace("(가장 중요)", "").strip()
                    for mm in st.session_state.memory
                ]
                # 현재 메모리를 최우선 기준으로 갱신
                st.session_state.memory[i] = mem_text

                if announce:
                    st.session_state.notification_message = "🌟 최우선 기준으로 설정되었어요."

                _after_memory_change()
                return

            # 중요도 승급이 아니면 그냥 중복으로 보고 아무것도 안 함
            return

    # 5) 완전히 새로운 메모리인 경우 리스트에 추가
    st.session_state.memory.append(mem_text)

    if announce:
        st.session_state.notification_message = "🧩 메모리에 새로운 내용을 추가했어요."

    _after_memory_change()


def delete_memory(idx: int):
    """
    메모리 삭제
    - 인덱스 범위 체크 후 해당 항목 삭제
    - 알림 + 요약/추천 재계산
    """
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]

        st.session_state.notification_message = "🧹 메모리에서 해당 기준을 삭제했어요."
        _after_memory_change()


def update_memory(idx: int, new_text: str):
    """
    메모리 수정
    - '(가장 중요)'가 새로 붙으면 나머지 메모리의 태그는 제거
    - 수정 후 알림 + 요약/추천 재계산
    """
    if not (0 <= idx < len(st.session_state.memory)):
        return

    new_text = naturalize_memory(new_text).strip()

    # '(가장 중요)' 태그가 포함되면 다른 메모리에서는 모두 제거
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
    
def extract_preferred_color(mems):
    """
    메모리에 저장된 선호 색상을 추출하는 함수.
    예: "색상은 화이트 계열을 선호해요." → "화이트"
    """
    for m in mems:
        if "색상은" in m and "선호" in m:
            # "색상은 화이트 계열을 선호해요." → "화이트"
            m = m.replace("(가장 중요)", "")
            m = m.replace("색상은", "").replace("계열", "")
            m = m.replace("을 선호해요", "").replace("를 선호해요", "")
            m = m.replace("선호해요", "")
            return m.strip()
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

import random

def update_color_memory(mems, new_color_sentence):
    clean = [m for m in mems if "색상은" not in m]
    clean.append(new_color_sentence)
    return clean

def match_color_reason(preferred_color, product_colors):
    preferred = preferred_color.replace("계열", "").strip()

    # 완전 일치
    if any(preferred == c for c in product_colors):
        return f"선호하시는 '{preferred}' 색상이 제공됩니다."

    # 계열 유사
    if preferred in " ".join(product_colors):
        return f"선호하신 색상 계열과 유사한 옵션이 있어요."

    # 불일치 → fallback
    return f"선호 색상은 아니지만 '{product_colors[0]}' 색상이 인기 있는 편이에요."

def build_matching_reason(user_mems, product):
    reason_list = []
    tags = " ".join(product.get("tags", []))
    review = product.get("review_one", "")

def generate_personalized_reason(product, mems, name):
    return build_matching_reason(mems, product)
    reasons = []
    tags = " ".join(product["tags"])
    review = product["review_one"]
    price = product["price"]

    # ============================
    # 🎯 1) 메모리 기반 기준 매칭
    # ============================

    # 음질
    if any("음질" in m for m in mems):
        if "음질" in tags or "음질" in review:
            reasons.append("기억상 ‘음질’을 중요하게 여기셨는데, 리뷰에서도 좋은 평가를 받고 있어요.")
        else:
            reasons.append("음질은 보통 수준이라는 평가가 많아요.")

    # 착용감
    if any("착용감" in m or "귀" in m for m in mems):
        if "편안" in review or "가벼움" in tags:
            reasons.append("편안한 착용감에 대한 리뷰가 많아 잘 맞는 선택이에요.")
        else:
            reasons.append("너무 가벼워서 금방 고장날 것 같다는 의견도 있었어요.")

    # 노이즈캔슬링
    if any("노이즈" in m for m in mems):
        if "노이즈캔슬링" in tags:
            reasons.append("노이즈캔슬링 성능이 뛰어나 중요한 기준을 충족해요.")
        else:
            reasons.append("노이즈캔슬링 성능은 무난한 편이에요.")
    # 색상
    for m in mems:
        if "색상은" in m:
            preferred = m.replace("색상은", "").replace("선호해요", "").strip()
            if any(preferred.replace("계열", "").strip() in col for col in product["color"]):
                reasons.append(f"선호하시는 '{preferred}' 색상 옵션이 있어요.")
            else:
                reasons.append(f"선호 색상은 아니지만, 인기 색상 '{product['color'][0]}'이 제공돼요.")
            break

    # ============================
    # 🎯 2) 예산 반영
    # ============================
    budget = extract_budget(mems)
    if budget:
        if price <= budget:
            reasons.append(f"예산 {budget:,}원 안에서 선택 가능한 제품이에요.")
        else:
            reasons.append(
                f"예산({budget:,}원)을 **약간 초과하지만**, 해당 가격대에서 성능·구성이 괜찮은 편이에요."
            )

    # ============================
    # 🎯 3) 기본 특징 보완
    # ============================
    if not reasons:
        reasons.append(f"{name}님의 기억된 취향과 전반적으로 잘 어울리는 제품이에요.")

    return " ".join(reasons)

    # =============================
    # 중복 제거 + 정돈 후 반환
    # =============================
    final = []
    for r in reasons:
        if r not in final:
            final.append(r)

    return "\n".join(final[:2])  # 카드용은 2줄만 보여줌

# =========================================================
# 카드용 이유 문구 생성 함수 (generate_card_reason)
# =========================================================
def generate_card_reason(product, mems, name):
    """카탈로그 태그와 메모리 교집합 기반으로 카드 요약 생성"""

    tags = product.get("tags", [])
    review = product.get("review_one", "")
    price = product.get("price", 0)

    # 예산 초과 체크
    budget = extract_budget(mems)
    budget_line = ""
    if budget and price > budget:
        budget_line = " (예산 초과)"

    # 리뷰 한 문장 + 예산 정보만 반환
    return f"{review} {budget_line}".strip()
    
    # -----------------------
    # 1) 메모리-태그 매칭
    # -----------------------
    mem_text = " ".join(mems)
    joined_tags = " ".join(tags)

    match_phrases = []

    # 음질
    if "음질" in mem_text and "음질" in joined_tags:
        match_phrases.append("음질 성능이 좋은 편이에요.")

    # 노이즈캔슬링
    if "노이즈" in mem_text and "노이즈캔슬링" in joined_tags:
        match_phrases.append("노이즈캔슬링 성능이 괜찮아요.")

    # 착용감
    if ("착용감" in mem_text or "귀" in mem_text) and (
        "편안" in review or "편안" in joined_tags
    ):
        match_phrases.append("착용감이 편하다는 후기가 많아요.")

    # 가성비
    if "가성비" in mem_text and "가성비" in joined_tags:
        match_phrases.append("가성비가 좋아요.")

    # -----------------------
    # 2) 기본 리뷰 문장 fallback
    # -----------------------
    if match_phrases:
        main_reason = match_phrases[0]
    else:
        main_reason = review

    # -----------------------
    # 3) 예산 초과 문구
    # -----------------------
    budget = extract_budget(mems)
    budget_line = ""
    if budget and price > budget:
        budget_line = "(예산 초과)"

    return f"{main_reason} {budget_line}".strip()


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
        "📝 후보 제품들 중 궁금한 점이 있다면 알려주세요!\n"
        "하단에서 궁금한 상품의 상세보기 버튼을 클릭하시면, 자세한 내용을 보실 수 있으며, 해당 상품에 대해 질문하셔도 됩니다.\n\n"
        "예: “부정적 리뷰는 뭐가 있는지 궁금해”, “음질은 괜찮을까?”"
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
4. 반드시 사용자 발화에 자연스럽게 반응하는 한 단락의 답변만 생성해.
5. 탐색 질문(용도/기준 재질문)은 하지 않습니다.
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
- 이미 색상 정보를 알고 있다면 디자인 스타일(깔끔→미니멀/레트로 등)만 물어보세요.
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

    # 탐색(explore) 단계일 때만 메모리 수집
    if st.session_state.stage == "explore":
        memory_before = st.session_state.memory.copy()
        extracted = extract_memory_with_gpt(text, "\n".join(st.session_state.memory))
        for mem in extracted:
            add_memory(mem)
# =========================================================
# 10. 시나리오 박스 출력
# =========================================================
def render_scenario():
    st.markdown(
        """
        <div class="scenario-box">
            🔍 <b>실험 시나리오</b><br>
            매일 지하철을 통해 출퇴근을 하는 당신에게 블루투스 이어폰(버즈/에어팟)은 빼놓을 수 없는 필수템으로 자리잡아왔습니다. <br>
            다만 하루에도 몇 시간씩 이를 끼다보니 귀가 아픈 느낌도 들어, 자연스럽게 블루투스 헤드셋에 관심을 갖게 되었습니다. <br>
            지금부터 에이전트와의 대화를 통해 아래 조건을 충족하고 당신에게 가장 잘 맞는 헤드셋을 추천받아보세요. <br>
            ** 헤드셋의 조건은 1) 귀가 아프지 않은/ 편한 헤드셋 (2) 노이즈캔슬링 기능 필수!
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

    new_mem = st.text_input(
    "추가할 기준",
    key="manual_memory_add",
    placeholder="예: 음질을 중요하게 생각해요 / 귀가 편한 제품이면 좋겠어요"
)
    if st.button("메모리 추가하기"):
        if new_mem.strip():
            add_memory(new_mem.strip())
            st.success("메모리에 추가했어요!")
            st.rerun()

# =========================================================
# 13. 추천 UI (3개 카드)
# =========================================================
# ============================================================
# 상품 상세 메시지 생성
# ============================================================
def format_product_detail_msg(product):
    features = ""
    if "features" in product:
        for f in product["features"]:
            features += f"- {f}\n"

    return f"""
[@{product['name']} 상세 정보]

📌 **가격:** {product['price']:,}원  
⭐ **평점:** {product['rating']:.1f}점 ({product['reviews']}개 리뷰)

**주요 특징:**  
{features if features else "등록된 상세 특징이 없어요."}

궁금하신 점을 자유롭게 물어보세요!  
예: "노이즈캔슬링 강한가요?", "착용감 어떤 편인가요?"
"""


# ============================================================
# 카드 하이라이트 CSS
# ============================================================
def inject_card_css():
    st.markdown("""
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
    """, unsafe_allow_html=True)


# ============================================================
# 추천 UI (★ 완전 교체)
# ============================================================
import html

def recommend_products_ui(name, mems):
    products = st.session_state.recommended_products
    
    st.markdown("""
    <div style="font-size:13px; color:#6b7280; margin-top:-10px; margin-bottom:20px;">
    ♻️ 현재 추천 상품이 마음에 들지 않으신가요? 왼쪽 쇼핑 메모리를 수정하시면 추천 후보가 바로 달라질 수 있어요.<br>
    예를 들어 <b>예산, 색상, 노이즈캔슬링, 착용감</b> 같은 기준을 바꿔보시는 것도 좋아요.
    </div>
    """, unsafe_allow_html=True)

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

            # 선택 여부 체크
            is_sel = (
                st.session_state.selected_product is not None and
                st.session_state.selected_product["name"] == p["name"]
            )

            # border + badge 정의는 여기서!
            border = "#2563EB" if is_sel else "#e5e7eb"
            badge = (
                '<div style="position:absolute; top:8px; right:8px; '
                'background:#2563EB; color:white; padding:3px 6px; '
                'border-radius:6px; font-size:11px;">선택됨</div>'
                if is_sel else ""
            )

            # 카드 HTML 시작
            html_parts = []
            html_parts.append(f'<div class="product-card" style="border:2px solid {border};">')

            if badge:
                html_parts.append(badge)

            # 이미지
            html_parts.append(f'<img src="{p["img"]}" class="product-img">')

            # 상품명
            html_parts.append(f'<div style="font-weight:700; font-size:15px;">{p["name"]}</div>')

            # 가격
            html_parts.append(f'<div style="color:#2563EB; font-weight:600;">{p["price"]:,}원</div>')

            # 평점
            html_parts.append(
                f'<div style="font-size:13px; color:#6b7280;">⭐ {p["rating"]:.1f} / 리뷰 {p["reviews"]}</div>'
            )

            # 추천 이유
            html_parts.append(
                '<div style="margin-top:10px; font-size:13px; color:#4b5563;">'
                + html.escape(generate_card_reason(p, mems, name))
                + '</div>'
            )

            # 색상 옵션
            html_parts.append(
                f'<div style="margin-top:6px; font-size:12px; color:#6b7280;">'
                f'색상 옵션: {", ".join(p["color"])}'
                '</div>'
            )

            html_parts.append('</div>')

            # HTML 출력
            card_html = "".join(html_parts)
            st.markdown(card_html, unsafe_allow_html=True)

            # 상세보기 버튼
            if st.button("상세보기", key=f"detail_{p['name']}"):
                st.session_state.selected_product = p
                st.session_state.stage = "product_detail"   # ★ 정확한 단계 이름
                st.session_state.product_detail_turn = 0    # ★ 첫 질문
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
            st.session_state.stage = "rate_product"   # << 여기 변경!
            ai_say(f"좋습니다! 이제 마지막으로 **'{p['name']}'**에 대한 만족도를 알려주세요 😊")
            st.rerun()

    else:
        st.info("한 제품을 자세히 보고 싶으시면 위 카드 중 하나를 선택해주세요. 😊")

# =========================================================
# 14. 요약 생성 함수
# =========================================================
def build_summary_from_memory(name, mems):
    if not mems:
        return f"{name}님, 아직 명확한 기준이 정해지지 않았어요. 몇 가지 기준만 알려주시면 추천을 도와드릴게요!"

    # 메모리 리스트 정리
    lines = [f"• {m.replace('(가장 중요)', '').strip()}" for m in mems]

    # 최우선 기준 찾기
    prio = None
    for m in mems:
        if "(가장 중요)" in m:
            prio = m.replace("(가장 중요)", "").strip()
            break

    # 출력 본문 구성
    header = f"[@{name}님의 메모리 요약_지금 나의 쇼핑 기준은?]\n\n"
    body = "지금까지 대화를 기반으로 정리된 쇼핑 기준은 다음과 같아요:\n\n"
    body += "\n".join(lines) + "\n"

    if prio:
        body += f"\n그중에서도 가장 중요한 기준은 **‘{prio}’**이에요.\n"

    tail = (
        "\nAI의 기억이 정확하지 않다면, 왼쪽의 쇼핑 메모리창에서 삭제 및 추가가 가능합니다:) \n"
        "기준이 달라지면 추천 후보도 바로 변경됩니다.\n"
        "준비되셨다면 아래 버튼을 눌러 추천을 받아보세요 👇"
    )

    return header + body + tail

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
# 16. 사용자 입력 처리
# =========================================================
def handle_input(u):

    ss = st.session_state

    # -------------------------
    # 0) 상세보기 단계에서는 메모리 금지 + 답변만 
    # -------------------------
    if ss.stage == "detail":
        reply = answer_product_question(u, ss.selected_product)
        ai_say(reply)
        return


    # ============================================================
    # 1️⃣ 현재 질문(cur_q)에 대한 답변 처리
    # ============================================================
    cur_q = ss.current_question

    yes_words = ["응", "네", "맞아", "그래", "웅", "ㅇㅇ", "어", "그렇지"]
    no_words = ["아니", "별로", "안", "아닌"]

    def is_yes(text):
        return any(w in text.lower() for w in yes_words)

    def is_no(text):
        return any(w in text.lower() for w in no_words)

    # 부정 응답이면 질문 종료
    if cur_q and is_no(u):
        ss.question_history.append(cur_q)
        ss.current_question = None
        ai_say("네! 그 부분은 중요한 요소가 아니라고 이해했어요. 다음으로 넘어가볼게요! 😊")
        return

    # 긍정 응답이면 해당 질문의 메모리 자동 생성
    if cur_q and is_yes(u):
        generated = f"{cur_q}을(를) 중요하게 생각하고 있어요."
        add_memory(generated)
        ss.question_history.append(cur_q)
        ss.current_question = None


    # ============================================================
    # 2️⃣ 메모리 추출 및 충돌 처리 (handle_input 에서만 수행!!)
    # ============================================================
    memory_before = ss.memory.copy()
    extracted_list = extract_memory_with_gpt(u, "\n".join(ss.memory))

    if extracted_list:
        for mem in extracted_list:
            before = len(ss.memory)
            add_memory(mem)
            after = len(ss.memory)

            if after > before:
                ss.notification_message = f"🧩 '{mem}' 기억해둘게요."


    # ============================================================
    # 3️⃣ SUMMARY 단계일 경우 — 요약 수정 + 추천 버튼 안내
    # ============================================================
    if ss.stage == "summary":

        extracted = extract_memory_with_gpt(u, "\n".join(ss.memory))
        if extracted:
            for mem in extracted:
                add_memory(mem)

            ss.summary_text = build_summary_from_memory(ss.nickname, ss.memory)
            ai_say("말씀해주신 기준이 반영되었어요! 수정된 요약을 확인해보세요. 준비되면 추천 받기 버튼을 눌러주세요 😊")
            return

        if any(k in u for k in ["추천", "좋아요", "네", "맞아요"]):
            ss.stage = "comparison"
            ss.recommended_products = make_recommendation()
            ai_say("좋아요! 고객님께 맞는 후보들을 준비해봤어요 😊")
            return

        ai_say("수정하실 내용이 있다면 편하게 알려주세요!")
        return


    # ============================================================
    # 4️⃣ 탐색 단계 (explore)
    # ============================================================
    if ss.stage == "explore":

        if "explore_step" not in ss:
            ss.explore_step = 1

        yes_words = ["응", "네", "맞아", "그래", "웅", "ㅇㅇ"]
        no_words = ["아니", "별로", "안", "아녀", "노"]

        txt = u.lower()

        # 🔹 Step 1: 성능 항목
        if ss.explore_step == 1:
            ai_say(
                "노이즈캔슬링, 음질, 배터리 등 다양한 요소들이 있어요.\n"
                "이 중 어떤 요소들이 중요한가요? (예: 노이즈캔슬링 중요 / 음질 중요)"
            )
            ss.explore_step = 1.5
            return

        if ss.explore_step == 1.5:
            if "노이즈" in txt:
                add_memory("노이즈캔슬링 기능을 중요하게 생각해요.")
            if "음질" in txt:
                add_memory("음질을 중요하게 생각해요.")
            if "배터리" in txt:
                add_memory("배터리가 오래 가는 제품을 원해요.")
            if any(w in txt for w in yes_words):
                add_memory("음질을 중요하게 생각해요.")
            if any(w in txt for w in no_words):
                add_memory("음질은 크게 중요하지 않아요.")

            ss.explore_step = 2
            ai_say("좋아요! 그렇다면 디자인은 어떠세요? 색상이나 전체적인 스타일도 중요하신가요?")
            return

        # 🔹 Step 2: 디자인
        if ss.explore_step == 2:
            if any(w in txt for w in yes_words) or "디자인" in txt or "색" in txt:
                add_memory("디자인과 색상도 고려하고 있어요.")
            else:
                add_memory("디자인은 크게 중요하지 않아요.")

            ss.explore_step = 3
            ai_say(
                "좋아요! 그렇다면 기능 외에 고려할 만한 부분들이 있어요.\n"
                "많은 분들은 착용감, 배터리, 휴대성 등을 함께 보시더라고요.\n"
                "이 중에서 중요하게 생각하시는 요소가 있으실까요?"
            )
            return

        # 🔹 Step 3: 기타 기준
        if ss.explore_step == 3:
            if "착용" in txt:
                add_memory("착용감을 중요하게 생각해요.")
            if "휴대" in txt:
                add_memory("휴대성을 고려하고 있어요.")
            if "배터리" in txt:
                add_memory("배터리 성능을 중요하게 생각해요.")
            if any(w in txt for w in yes_words):
                add_memory("착용감을 중요하게 생각해요.")

            ss.explore_step = 3.5
            ai_say("그럼 마지막으로, 지금까지 대화를 바탕으로 어떤 기준이 가장 중요하신가요?")
            return

        # 🔹 Step 3.5: 최우선 기준
        if ss.explore_step == 3.5:
            if "음질" in txt:
                add_memory("(가장 중요) 음질을 가장 중요하게 생각해요.")
            elif "노이즈" in txt:
                add_memory("(가장 중요) 노이즈캔슬링이 가장 중요해요.")
            elif "디자인" in txt or "색" in txt:
                add_memory("(가장 중요) 디자인/스타일을 최우선으로 고려하고 있어요.")
            elif "착용" in txt:
                add_memory("(가장 중요) 착용감을 가장 중요하게 생각해요.")
            elif "배터리" in txt:
                add_memory("(가장 중요) 배터리 지속시간을 최우선으로 보고 있어요.")
            else:
                add_memory("(가장 중요) 음질을 가장 중요하게 생각해요.")

            ss.explore_step = 4
            ai_say("좋아요! 이제 마지막으로 예산대를 알려주시면 추천을 준비할게요!")
            return

        # 🔹 Step 4: 예산 → summary
        if ss.explore_step == 4:
            extracted = extract_memory_with_gpt(u, "\n".join(ss.memory))
            for mem in extracted:
                add_memory(mem)

            mem_count = len(ss.memory)
            has_budget = any("예산" in m for m in ss.memory)

            if mem_count >= 5 and not has_budget:
                ai_say("추천 전에 예산대를 알려주세요! 예: 15만원 이하, 20만원 이내")
                return

            if mem_count >= 5 and has_budget:
                ss.stage = "summary"
                ss.summary_text = build_summary_from_memory(ss.nickname, ss.memory)
                return

        reply = gpt_reply(u)
        ai_say(reply)
        return


        # ----------------------------------------------------------
        # (1) 현재 질문 응답 처리 (너가 준 코드)
        # ----------------------------------------------------------
        cur_q = ss.current_question

        # 부정적 답변 → 질문 종료
        if is_negative_response(u):
            if cur_q:
                ss.question_history.append(cur_q)
                ss.current_question = None
            ai_say("네! 그 부분은 중요하지 않다고 이해했어요. 다음 기준으로 넘어가볼게요 😊")
            return

        # 정상 응답 → 질문 완료 처리
        if cur_q:
            ss.question_history.append(cur_q)
            ss.current_question = None


        # ----------------------------------------------------------
        # (2) 메모리 추출 + 충돌 처리
        # ----------------------------------------------------------
        memory_text = "\n".join(ss.memory)
        extracted = extract_memory_with_gpt(u, memory_text)

        if extracted:
            for mem in extracted:
                before = len(ss.memory)
                add_memory(mem)
                after = len(ss.memory)
                if after > before:
                    ss.notification_message = f"🧩 '{mem}' 내용을 기억해둘게요."


        # ----------------------------------------------------------
        # (3) 우선 기준 follow-up (딱 한 번)
        # ----------------------------------------------------------
        primary = ss.primary_style

        if not ss.priority_followup_done:
            # 디자인 우선형
            if primary == "design":
                ai_say(
                    "디자인/스타일을 중요하게 보고 계셔서 여쭤볼게요! "
                    "미니멀/레트로/깔끔/포인트 있는 스타일 중 어떤 느낌을 좋아하시나요?"
                )
                ss.priority_followup_done = True
                return

            # 성능 우선형
            if primary == "performance":
                ai_say(
                    "성능을 중요하게 고려하신다고 하셔서요! "
                    "`음질`, `노이즈캔슬링`, `배터리`, `착용감` 중 어떤 요소가 특히 핵심일까요?"
                )
                ss.priority_followup_done = True
                return


        # ----------------------------------------------------------
        # (4) 예산 유도
        # ----------------------------------------------------------
        mem_count = len(ss.memory)
        has_budget = any("예산" in m for m in ss.memory)

        if mem_count >= 5 and not has_budget and ss.priority_followup_done:
            ai_say("추천 전에 **예산**을 알려주세요! 예: '15만원 이내', '20만원 이하'")
            return


        # ----------------------------------------------------------
        # (5) SUMMARY 진입 조건
        # ----------------------------------------------------------
        if has_budget and mem_count >= 5:
            ss.stage = "summary"
            ss.summary_text = build_summary_from_memory(ss.nickname, ss.memory)
            return


        # ----------------------------------------------------------
        # (6) 기본 GPT 탐색 질문 생성
        # ----------------------------------------------------------
        reply = gpt_reply(u)
        ai_say(reply)

        # 질문 ID 기록
        qid = None
        if "디자인" in reply:
            qid = "design"
        elif "색상" in reply:
            qid = "color"
        elif "음질" in reply:
            qid = "sound"
        elif "착용감" in reply:
            qid = "comfort"
        elif "배터리" in reply:
            qid = "battery"
        elif "예산" in reply:
            qid = "budget"

        if qid and qid not in ss.question_history:
            ss.current_question = qid

        return

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
        if st.button("쇼핑 시작하기", type="primary", use_container_width=True):
            if not name:
                st.warning("이름을 입력해주세요.")
                return

            # 사용자 정보 저장
            st.session_state.nickname = name
            st.session_state.phone_number = phone

            # 🔹 우선 기준 기본값 초기화
            st.session_state.primary_style = ""
            st.session_state.priority_followup_done = False

            # 초기 메모리 + 우선 기준 유형 세팅
            if shopping_style == "가성비 우선형":
                add_memory("가성비, 가격을 중요하게 생각하는 편이에요.", announce=False)
                st.session_state.primary_style = "price"
                # 가격 기준은 예산이 곧 핵심이니까, 바로 예산 질문으로 넘어가도 괜찮으니 True
                st.session_state.priority_followup_done = True

            elif shopping_style == "디자인/스타일 우선형":
                add_memory("(가장 중요) 디자인/스타일을 최우선으로 고려하고 있어요.", announce=False)
                st.session_state.primary_style = "design"
                # 디자인 구체 질문은 아직 안 했으니 False 유지

            else:  # "성능·스펙 우선형"
                add_memory("(가장 중요) 성능/스펙을 우선하는 쇼핑 성향이에요.", announce=False)
                st.session_state.primary_style = "performance"
                # 성능 관련 구체 질문도 아직 안 했으니 False 유지

            add_memory(f"색상은 {color_choice} 계열을 선호해요.", announce=False)

            st.session_state.page = "chat"
            st.rerun()


# =========================================================
# 18. main_chat_interface (UI 그대로 사용)
# =========================================================
# =========================================================
# 18. main_chat_interface (UI 그대로 사용 + 평가 단계 추가)
# =========================================================
def main_chat_interface():

    # 🔒 안전 가드
    if "notification_message" not in st.session_state:
        st.session_state.notification_message = ""

    # 알림/토스트 처리
    if st.session_state.notification_message:
        try:
            st.toast(st.session_state.notification_message, icon="✅")
        except Exception:
            st.info(st.session_state.notification_message)
        st.session_state.notification_message = ""

    # 첫 메시지 출력
    if len(st.session_state.messages) == 0:
        ai_say(
            f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요.\n"
            f"블루투스 헤드셋 추천을 도와드릴게요! 먼저 어떤 용도로 사용하실 예정인가요?"
        )

    # 상단 UI
    render_scenario()
    render_step_header()

    col1, col2 = st.columns([3, 7], gap="large")

    # -----------------------------
    # 좌측: 메모리 패널
    # -----------------------------
    with col1:
        render_memory_sidebar()

    # -----------------------------
    # 우측: 채팅/추천/평가
    # -----------------------------
    with col2:
        # -----------------------------------------------------------
        # 채팅 UI
        # -----------------------------------------------------------
        chat_container = st.container()
        with chat_container:
            html_content = '<div class="chat-display-area">'
            for msg in st.session_state.messages:
                cls = "chat-bubble-ai" if msg["role"] == "assistant" else "chat-bubble-user"
                safe = html.escape(msg["content"])
                html_content += f'<div class="chat-bubble {cls}">{safe}</div>'

            # SUMMARY 단계일 때 요약 말풍선 한 번 더 출력
            if st.session_state.stage == "summary":
                safe_sum = html.escape(st.session_state.summary_text)
                html_content += f'<div class="chat-bubble chat-bubble-ai">{safe_sum}</div>'

            html_content += "</div>"
            st.markdown(html_content, unsafe_allow_html=True)

        # -----------------------------------------------------------
        # SUMMARY 버튼 UI
        # -----------------------------------------------------------
        if st.session_state.stage == "summary":
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🔍 이 기준으로 추천 받기"):
                st.session_state.stage = "comparison"
                st.session_state.recommended_products = make_recommendation()
                st.rerun()

            st.info("수정하실 기준이 있으면 아래 입력창에서 말씀해주시거나 왼쪽 메모리 제어창에서 수정 가능합니다😊")
            # return 없음 → 입력창 유지

        # -----------------------------------------------------------
        # 추천 / 상세 / 구매 단계
        # -----------------------------------------------------------
        if st.session_state.stage in ["comparison", "product_detail", "purchase_decision"]:
            st.markdown("---")

            # 상세보기 전용 상단 버튼들
            if st.session_state.stage == "product_detail":
                c1, c2 = st.columns([1, 4])
                with c1:
                    if st.button("⬅️ 목록으로"):
                        st.session_state.stage = "comparison"
                        st.session_state.selected_product = None
                        st.rerun()
                with c2:
                    if st.button("🛒 이 제품으로 결정하기"):
                        # 여기서는 '구매 결정 단계'로만 넘기고,
                        # 실제 만족도 평가는 recommend_products_ui에서 버튼 누르면 stage를 rate_product로 바꿔줌
                        st.session_state.stage = "purchase_decision"
                        st.rerun()

            # 후보 3개 카드 + "이 제품으로 결정하기" 버튼 (→ rate_product로 전환)
            recommend_products_ui(st.session_state.nickname, st.session_state.memory)

        # -----------------------------------------------------------
        # 구매 결정 완료 메시지 (final_choice가 있을 때)
        # -----------------------------------------------------------
        if st.session_state.stage == "purchase_decision" and st.session_state.final_choice:
            p = st.session_state.final_choice
            st.success(f"🎉 **{p['name']}** 구매를 결정하셨습니다!")
            st.balloons()

        # -----------------------------------------------------------
        # 🧡 제품 만족도 평가 단계
        #   - 여기서 슬라이더 UI만 보여주고, 채팅 입력은 막음
        # -----------------------------------------------------------
        if st.session_state.stage == "rate_product":
            st.markdown("---")
            render_rating_ui()
            return   # ← 함수 안이기 때문에 OK! 이 아래 입력창은 안 보이게 됨

    # -----------------------------------------------------------
    # 입력 폼 UI (항상 마지막, 함수 밖이 아니라 main_chat_interface 안 맨 끝!)
    # → 폼은 이거 하나만 두고, 기존에 중복된 다른 st.form("user_input_form")은 전부 삭제
    # -----------------------------------------------------------
    with st.form(key="chat_form", clear_on_submit=True):
        c1, c2 = st.columns([85, 15])
        with c1:
            st.text_input(
                "msg",
                key="user_input_text",
                label_visibility="collapsed",
                placeholder="메시지를 입력하세요...",
            )
        with c2:
            if st.form_submit_button("전송"):
                handle_input(st.session_state.user_input_text)
                st.rerun()

# =========================================================
# 19. 라우팅
# =========================================================
if st.session_state.page == "context_setting":
    context_setting_page()
else:
    main_chat_interface()









































