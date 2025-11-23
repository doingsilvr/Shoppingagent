import streamlit as st
import time
import random
import re
from openai import OpenAI

# =========================================================
# 기본 설정 + 전역 스타일
# =========================================================
st.set_page_config(
    page_title="AI 쇼핑 에이전트 실험용",
    page_icon="🎧",
    layout="wide"
)

# 💡 [UI/iframe 해결] 전역 CSS 업데이트: 불필요한 UI 제거 및 레이아웃 안정화
st.markdown(
    """
    <style>
    /* 🚨 필수: 불필요한 Streamlit UI 요소 숨기기 */
    #MainMenu, footer, header, .css-1r6q61a {
        visibility: hidden;
        display: none !important;
    }

    /* 🚨 필수: 메인 컨테이너 최대 폭 설정 (iframe에 맞게 유동적으로) */
    .block-container {
        max-width: 860px !important; 
        padding: 1rem 1rem 1rem 1rem;
        margin: auto;
    }

    /* 🚨 [알림 시간 조정] 알림이 5배 더 오래 유지되도록 CSS 조정 (브라우저 종속적) */
    .stAlert {
        position: fixed; 
        top: 1rem;
        right: 1rem;
        width: 400px;
        z-index: 1000;
        margin: 0 !important;
        padding: 0.8rem !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border-radius: 8px;
        /* 💡 노출 시간 연장 시도 (Streamlit 자체 기능은 아님) */
        animation-duration: 5s !important; 
        transition: opacity 5s ease-out !important; 
    }
    
    /* 메모리 패널 (좌측) 높이 고정 및 스크롤 */
    .memory-panel-fixed {
        position: -webkit-sticky;
        position: sticky;
        top: 1rem; 
        height: 620px; 
        overflow-y: auto;
        padding-right: 0.5rem;
        background-color: #f8fafc;
        border-radius: 16px;
        padding: 1rem;
        border: 1px solid #e2e8f0;
    }
    
    /* 🚨 [대화창 하단 시작 문제 해결] 채팅창 영역을 정상적인 스크롤 컨테이너로 복원 */
    .chat-display-area {
        height: 520px; 
        overflow-y: auto;
        padding-right: 1rem;
        padding-bottom: 1rem;
        /* 메시지를 아래에서부터 쌓이도록 하는 CSS 제거 */
    }

    /* 🚨 [UI 잘림 해결] 삭제 버튼 크기 강제 */
    .stButton > button[kind="secondary"] {
        min-width: 45px !important; 
        padding: 0.2rem 0.1rem !important; 
    }

    /* 🚨 [캐러셀 UI 스타일] */
    .product-card {
        padding: 10px;
        border: 1px solid #ddd;
        border-radius: 8px;
        margin-bottom: 10px;
        height: 100%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    .product-image {
        width: 90%;
        height: auto; 
        border-radius: 6px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 🚨 [스크롤 해결] 스크롤 다운을 강제하는 JavaScript 실행 (매 턴마다)
def run_js_scroll():
    # 스크롤을 맨 아래로 이동
    st.markdown(
        """
        <script>
        const chatArea = document.querySelector('.chat-display-area');
        if (chatArea) {
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        </script>
        """, 
        unsafe_allow_html=True
    )
    
# =========================================================
# GPT 설정 (기존 로직 유지)
# =========================================================
SYSTEM_PROMPT = """
너는 'AI 쇼핑 도우미'이며 사용자의 블루투스 헤드셋 기준을 파악해 추천을 돕는 역할을 한다.
[역할 규칙]
- 너는 챗봇이 아니라 '개인 컨시어지' 같은 자연스러운 톤으로 말한다.
- 사용자가 말한 기준은 아래의 [메모리]를 참고해 반영한다.
- **🚨 [최우선 규칙] 메모리에 이미 저장된 기준(특히 용도/상황/기능)은 절대 다시 물어보지 않고, 바로 다음 단계의 구체적인 질문으로 전환한다.**
- 새로운 기준이 등장하면, '메모리에 추가하면 좋겠다'라고 자연스럽게 제안한다.
- 단, 실제 메모리 추가/수정/삭제는 시스템(코드)이 처리하므로, 너는 "내가 메모리에 저장했다"라고 단정적으로 말하지 말고
  "이 기준을 기억해둘게요" 정도로 표현한다.
- 사용자가 모호하게 말하면 부드럽게 구체적으로 다시 물어본다.
- 사용자가 “잘 모르겠어 / 글쎄 / 아직 생각 안 했어”라고 말하면,
  “그렇다면 주로 어떤 상황에서 사용하실 때 중요할까요?”와 같이 사용 상황을 묻는다.
- 사용자는 블루투스 '헤드셋(오버이어/온이어)'을 구매하려고 한다. '이어폰' 또는 '인이어' 타입에 대한 질문은 피하라.
[대화 흐름 규칙]
- **🚨 1. 초기 대화는 [이전 구매 내역]을 바탕으로 사용자의 일반적인 취향을 파악하는 데 집중한다. (예: 디자인, 색상, 가격 중시 여부)**
- **🚨 2. 일반적인 취향이 파악된 후(메모리 1~2개 추가 후), 대화는 현재 구매 목표인 블루투스 헤드셋의 기준(용도/상황 → 기능/착용감/배터리/디자인/브랜드/색상 → 예산) 순으로 자연스럽게 넓혀 간다.**
- 메모리에 이미 용도/상황/기능 등의 기준이 파악되었다면, 다음 단계의 질문으로 넘어가라.
- 🚨 디자인/스타일 기준이 파악되면, 다음 질문은 선호하는 색상이나 구체적인 스타일(레트로, 미니멀 등)에 대한 질문으로 전환하라.
- **🚨 [필수] 추천으로 넘어가기 전, 반드시 예산(가격대)을 확인하라.**
- 메모리가 3개 이상 모이면, 스스로 “지금까지 기준을 정리해보겠다”고 제안해도 된다.
- 정리 후에는 사용자가 원하거나 버튼이 눌리면, 추천을 제안한다.
- 추천을 요청받으면 추천 이유가 포함된 구조화된 리스트 형태로 말한다.
  (실제 가격/모델 정보는 시스템이 카드 형태로 따로 보여줄 수 있다.)
- 사용자가 특정 상품(번호)에 대해 질문하면, 그 상품에 대한 정보, 리뷰, 장단점 등을 자세히 설명하며 구매를 설득하거나 보조하는 대화로 전환한다.
  특히 상품 설명 시, 사용자의 메모리를 활용하여 해당 제품을 사용했을 때의 개인화된 경험을 시뮬레이션하는 톤으로 설명한다.
[메모리 활용]
- 아래에 제공되는 메모리를 기반으로 대화 내용을 유지하라.
- 메모리와 사용자의 최신 발언이 충돌하면, “기존에 ~라고 하셨는데, 기준을 바꾸실까요?”처럼 정중하게 확인 질문을 한다.
[출력 규칙]
- 한 번에 너무 많은 질문을 하지 말고, 자연스럽게 한두 개씩만 묻는다.
- 중복 질문은 피하고, 꼭 필요할 때는 “다시 한 번만 확인할게요”라고 말한다.
- 사용자의 표현을 적당히 따라가되, 전체 톤은 부드러운 존댓말로 유지한다.
"""

try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except KeyError:
    client = None

# =========================================================
# 세션 상태 초기화 (기존 로직 유지)
# =========================================================
def ss_init():
    ss = st.session_state
    ss.setdefault("nickname", None)
    ss.setdefault("page", "context_setting")
    ss.setdefault("stage", "explore")
    ss.setdefault("initial_purchase_context", None)
    ss.setdefault("messages", [])
    ss.setdefault("memory", [])
    ss.setdefault("summary_text", "")
    ss.setdefault("just_updated_memory", False)
    ss.setdefault("recommended_products", [])
    ss.setdefault("current_recommendation", [])
    ss.setdefault("notification_message", "")

ss_init()

# =========================================================
# 유틸리티 함수 (기존 로직 유지)
# =========================================================
def get_eul_reul(noun: str) -> str:
    """명사 뒤에 붙는 목적격 조사 '을/를'을 결정합니다."""
    if not noun or not noun[-1].isalpha():
        return "을"
    last_char = noun[-1]
    if not ('\uAC00' <= last_char <= '\uD7A3'):
        return "을"
    last_char_code = ord(last_char)
    if (last_char_code - 44032) % 28 > 0:
        return "을"
    else:
        return "를"

def naturalize_memory(text: str) -> str:
    """🚨 [메모리 반영 어색함 문제 해결] 메모리 문장을 사용자 1인칭 자연어로 간결하게 다듬기."""
    t = text.strip()
    t = t.replace("노이즈 캔슬링", "노이즈캔슬링")
    is_priority = "(가장 중요)" in t
    t = t.replace("(가장 중요)", "").strip()

    # 1. '생각하고 있어요', '이에요', '다' 제거 및 간결화
    t = re.sub(r'로 생각하고 있어요\.?$|에요\.?$|이에요\.?$|다\.?$', '', t)
    
    # 2. '필요없음'과 같은 부정적인 키워드 정리
    t = t.replace('비싼것까진 필요없', '비싼 것 필요 없음')
    t = t.replace('필요없', '필요 없음')
    
    # 3. 불필요한 조사 제거 및 키워드 유지
    t = re.sub(r'(을|를)\s*선호$', ' 선호', t)
    t = re.sub(r'(을|를)\s*고려하고$', ' 고려', t)
    t = re.sub(r'(이|가)\s*필요$', ' 필요', t)
    t = re.sub(r'(에서)\s*들을$', '', t) # '지하철에서 들을' -> '지하철'
    
    # 4. 최종적으로 문장 끝 공백 제거
    t = t.strip()
        
    if is_priority:
        t = "(가장 중요) " + t
        
    return t

def _clause_split(u: str) -> list[str]:
    repl = re.sub(r"(그리고|랑|및|하고|고|&|·)", ",", u)
    parts = [p.strip() for p in re.split(r"[，,]", repl) if p.strip()]
    return parts if parts else [u.strip()]

def memory_sentences_from_user_text(utter: str):
    """사용자 발화에서 복수의 쇼핑 기준/맥락을 추출."""
    u = utter.strip().replace("  ", " ")
    mems = []
    if len(u) <= 3 and u in ["응", "네", "예", "아니", "둘다", "둘 다", "맞아", "맞아요", "ㅇㅇ", "o", "x"]:
        return None
    is_priority_clause = False
    if re.search(r"(가장|제일|최우선|젤)\s*(중요|우선)", u):
        is_priority_clause = True
        for i, m in enumerate(st.session_state.memory):
            st.session_state.memory[i] = m.replace("(가장 중요)", "").strip()
    m = re.search(r"(\d+)\s*만\s*원", u)
    if m:
        price = m.group(1)
        st.session_state.memory = [mem for mem in st.session_state.memory if "예산" not in mem]
        mem = f"예산은 약 {price}만 원 이내로 생각하고 있어요."
        mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)
    clauses = _clause_split(u)
    for c in clauses:
        base_rules = [
            ("노이즈캔슬링", "노이즈캔슬링 기능 고려"),
            ("ANC", "노이즈캔슬링 기능 고려"),
            ("소음 차단", "노이즈캔슬링 기능 고려"),
            ("가벼운", "가벼운 착용감 선호"), # 🚨 [메모리 미반영 수정]
            ("가볍", "가벼운 착용감 선호"),  # 🚨 [메모리 미반영 수정]
            ("클래식", "클래식 디자인 선호"),
            ("깔끔", "깔끔한 디자인 선호"),
            ("미니멀", "미니멀 디자인 선호"),
            ("레트로", "레트로 스타일 선호"),
            ("예쁘면", "디자인/스타일 중요시"),
            ("디자인", "디자인/스타일 중요시"),
            ("화이트", "색상은 흰색 선호"),
            ("블랙", "색상은 검은색 선호"),
            ("보라", "색상은 보라색 선호"),
            ("네이비", "색상은 네이비 선호"),
            ("실버", "색상은 실버 선호"),
            ("음질", "음질 중요시"),
            ("배터리", "배터리 지속시간 김"),
            ("운동", "주로 러닝/운동 용도"),
            ("산책", "주로 산책/일상 용도"),
            ("게임", "주로 게임 용도"),
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
                        mem = f"디자인은 '{cleaned_c}' 스타일 선호"
                mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)
                matched = True
                break
        if re.search(r"(하면 좋겠|좋겠어|가 좋아|선호|필요해|중요해|거|~함|~없음|필요없|비싼것까진)", c) and not matched:
            if len(c.strip()) > 3 and not any(k in c for k in ["예쁘면", "디자인", "스타일"]):
                # 🚨 [메모리 어색함 수정] 사용자의 문장 그대로 저장 (naturalize_memory가 후처리)
                mem = c.strip() 
                mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)
            matched = True
            
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
            dedup.append(m)
    return dedup if dedup else None

# =========================================================
# 메모리 추가/수정/삭제
# =========================================================
def add_memory(mem_text: str, announce=True):
    mem_text = mem_text.strip()
    if not mem_text:
        return
    mem_text_stripped = mem_text.replace("(가장 중요)", "").strip()
    if "예산은 약" in mem_text_stripped:
        st.session_state.memory = [m for m in st.session_state.memory if "예산은 약" not in m]
    if "색상은" in mem_text_stripped:
        st.session_state.memory = [m for m in st.session_state.memory if "색상은" not in m]
    if any(k in mem_text_stripped for k in ["클래식", "깔끔", "미니멀", "레트로", "세련", "디자인은"]):
        st.session_state.memory = [m for m in st.session_state.memory if "디자인/스타일" not in m]
    for i, m in enumerate(st.session_state.memory):
        m_stripped = m.replace("(가장 중요)", "").strip()
        if mem_text_stripped in m_stripped or m_stripped in mem_text_stripped:
            if "(가장 중요)" in mem_text and "(가장 중요)" not in m:
                for j, existing_m in enumerate(st.session_state.memory):
                    st.session_state.memory[j] = existing_m.replace("(가장 중요)", "").strip()
                st.session_state.memory[i] = mem_text
                st.session_state.just_updated_memory = True
                if announce:
                    st.session_state.notification_message = "🌟 최우선 기준이 업데이트되었어요."
                return
            return
    st.session_state.memory.append(mem_text)
    st.session_state.just_updated_memory = True
    if announce:
        st.session_state.notification_message = "🧩 메모리에 새로운 기준을 추가했어요."

def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.just_updated_memory = True
        st.session_state.notification_message = "🧹 메모리에서 기준을 삭제했어요."

def update_memory(idx: int, new_text: str):
    if 0 <= idx < len(st.session_state.memory):
        if "(가장 중요)" in new_text:
            for i, existing_m in enumerate(st.session_state.memory):
                st.session_state.memory[i] = existing_m.replace("(가장 중요)", "").strip()
        st.session_state.memory[idx] = new_text.strip()
        st.session_state.just_updated_memory = True
        st.session_state.notification_message = "🔄 메모리가 업데이트되었어요."

# =========================================================
# 요약 / 추천 로직 (기존 로직 유지)
# =========================================================
def extract_budget(mems):
    for m in mems:
        mm = re.search(r"약\s*([0-9]+)\s*만\s*원\s*이내", m)
        if mm:
            return int(mm.group(1)) * 10000
    return None

def detect_priority(mem_list):
    for m in mem_list:
        if "(가장 중요)" in m:
            m = m.replace("(가장 중요)", "").strip()
            for key in ["음질", "착용감", "가격", "예산", "노이즈캔슬링", "배터리", "디자인", "스타일", "가성비"]:
                if key in m:
                    if key in ["디자인", "스타일"]:
                        return "디자인/스타일"
                    if key in ["가격", "예산", "가성비"]:
                        return "가격/예산"
                    return key
            return m
    return None

def generate_summary(name, mems):
    if not mems:
        return ""
    # 🚨 [요약 중복 문제 해결] naturalize_memory를 거치지 않고, 저장된 원본 메모리를 간결하게 사용
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
        "\n제가 정리한 기준이 맞을까요? **좌측 메모리 패널**에서 언제든 수정할 수 있어요.\n"
        "변경이 없다면 아래 버튼을 눌러 추천을 받아보셔도 좋아요 👇"
    )
    return header + body + tail

CATALOG = [
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 179000, "rating": 4.4, "reviews": 1600, "rank": 8, "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"], "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.", "color": ["블랙", "네이비"], "img": "https://dummyimage.com/600x400/424242/fff&text=Anker+Q45"},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 129000, "rating": 4.4, "reviews": 2300, "rank": 9, "tags": ["가벼움", "균형형 음질", "노이즈캔슬링"], "review_one": "가볍고 음색이 밝다는 평이 많아요.", "color": ["블랙", "화이트"], "img": "https://dummyimage.com/600x400/3949AB/fff&text=JBL+770NC"},
    {"name": "Sony WH-CH720N", "brand": "Sony", "price": 169000, "rating": 4.5, "reviews": 2100, "rank": 6, "tags": ["노이즈캔슬링", "경량", "무난한 음질"], "review_one": "경량이라 출퇴근용으로 좋다는 후기가 많아요.", "color": ["블랙", "화이트", "블루"], "img": "https://dummyimage.com/600x400/03A9F4/fff&text=Sony+720N"},
    {"name": "Bose QC45", "brand": "Bose", "price": 420000, "rating": 4.7, "reviews": 2800, "rank": 2, "tags": ["최상급 착용감", "자연스러운 사운드", "노이즈캔슬링", "편안함"], "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.", "color": ["블랙", "화이트"], "img": "https://dummyimage.com/600x400/795548/fff&text=Bose+QC45"},
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 450000, "rating": 4.8, "reviews": 3200, "rank": 1, "tags": ["최상급 노캔", "균형 음질", "플래그십", "통화품질"], "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.", "color": ["블랙", "화이트"], "img": "https://dummyimage.com/600x400/212121/fff&text=Sony+XM5"},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 679000, "rating": 4.6, "reviews": 1500, "rank": 3, "tags": ["프리미엄", "노이즈캔슬링", "디자인", "고급"], "review_one": "디자인과 브랜드 감성 때문에 만족도가 높아요.", "color": ["실버", "스페이스그레이"], "img": "https://dummyimage.com/600x400/bdbdbd/000&text=AirPods+Max"},
    {"name": "Sennheiser PXC 550-II", "brand": "Sennheiser", "price": 289000, "rating": 4.3, "reviews": 1200, "rank": 7, "tags": ["착용감", "여행", "배터리", "노이즈캔슬링"], "review_one": "여행 시 장시간 착용에도 압박감이 덜해요.", "color": ["블랙"], "img": "https://dummyimage.com/600x400/616161/fff&text=Sennheiser+550"},
    {"name": "AKG Y600NC", "brand": "AKG", "price": 149000, "rating": 4.2, "reviews": 1800, "rank": 10, "tags": ["균형 음질", "가성비", "노이즈캔슬링"], "review_one": "가격대비 깔끔하고 균형 잡힌 사운드가 좋아요.", "color": ["블랙", "골드"], "img": "https://dummyimage.com/600x400/FFCCBC/000&text=AKG+Y600"},
    {"name": "Microsoft Surface Headphones 2", "brand": "Microsoft", "price": 319000, "rating": 4.5, "reviews": 900, "rank": 11, "tags": ["업무", "통화품질", "디자인", "노이즈캔슬링"], "review_one": "업무용으로 완벽하며 통화 품질이 매우 깨끗합니다.", "color": ["라이트 그레이", "매트 블랙"], "img": "https://dummyimage.com/600x400/0078D4/fff&text=Surface+HP2"},
    {"name": "Bose Noise Cancelling Headphones 700", "brand": "Bose", "price": 490000, "rating": 4.7, "reviews": 2500, "rank": 4, "tags": ["최상급 노캔", "통화품질", "프리미엄"], "review_one": "노이즈캔슬링 성능과 스타일을 모두 갖춘 제품.", "color": ["블랙", "실버"], "img": "https://dummyimage.com/600x400/222222/fff&text=Bose+700"},
    {"name": "Audio-Technica M50xBT2", "brand": "Audio-Technica", "price": 249000, "rating": 4.6, "reviews": 1100, "rank": 5, "tags": ["스튜디오", "음질", "밸런스", "디자인"], "review_one": "음악 감상용으로 정교하고 명료한 사운드가 일품.", "color": ["블랙"], "img": "https://dummyimage.com/600x400/333333/fff&text=AT+M50x"},
    {"name": "Jabra Elite 85h", "brand": "Jabra", "price": 219000, "rating": 4.3, "reviews": 1400, "rank": 12, "tags": ["배터리", "내구성", "방수", "통화품질"], "review_one": "배터리가 오래가고 튼튼해서 막 쓰기 좋아요.", "color": ["티타늄 블랙", "네이비"], "img": "https://dummyimage.com/600x400/455A64/fff&text=Jabra+85h"},
]

def generate_personalized_reason(product, mems, nickname):
    mem_str = " ".join([naturalize_memory(m) for m in mems])

    preferred_color_match = re.search(r"색상은\s*([^계열]+)\s*계열", mem_str)
    if not preferred_color_match:
        preferred_color_match = re.search(r"색상은\s*([^을를])\s*(을|를)\s*선호", mem_str)

    preferred_color_raw = preferred_color_match.group(1).strip().replace("/", "") if preferred_color_match else None
    preferred_color = preferred_color_raw.lower() if preferred_color_raw else None

    preferred_style_match = re.search(r"디자인은\s*['\"]?([^']+?)['\"]?\s*스타일을 선호", mem_str)
    preferred_style = preferred_style_match.group(1).strip() if preferred_style_match else None

    preferred_usage = None
    if any("산책" in m for m in mems):
        preferred_usage = "산책/가벼움/편안함"
    elif any("출퇴근" in m for m in mems):
        preferred_usage = "출퇴근/가벼움/편안함"
    elif any("운동" in m for m in mems) or any("러닝" in m for m in mems):
        preferred_usage = "운동/가벼움/착용감"

    product_colors_lower = [c.lower() for c in product["color"]]

    if preferred_color and any(c in preferred_color for c in product_colors_lower):
        matched_color = next((c for c in product["color"] if c.lower() in preferred_color), product["color"][0])

        if preferred_style:
            return (
                f"**{matched_color} 색상**이 {nickname}님의 **'{preferred_style}'** 스타일에 잘 어울릴 거예요. "
                f"특히 이 제품은 **{product['review_one']}** 평을 받고 있어요."
            )
        elif any(tag in product["tags"] for tag in ["디자인", "고급"]):
            return (
                f"**{matched_color} 색상**이 준비되어 있고 **디자인** 면에서도 호평을 받는 제품이에요. "
                "시각적 만족도가 높으실 거예요."
            )

    if preferred_usage == "산책/가벼움/편안함" and any(tag in product["tags"] for tag in ["가벼움", "경량", "편안함"]):
        tag_match = next((tag for tag in ["가벼움", "경량", "편안함"] if tag in product["tags"]), "편안한 착용감")
        reason = f"**{tag_match}**이 강조되어 {nickname}님께서 **산책**처럼 장시간 사용하실 때 **가장 편안함**을 느끼실 수 있을 거예요."
        return reason

    if preferred_usage == "운동/가벼움/착용감" and any(tag in product["tags"] for tag in ["가벼움", "내구성"]):
        return f"내구성과 **가벼운 착용감** 덕분에 **운동** 중 움직임에도 안정적으로 귀를 잡아줄 거예요."

    return f"**{product['brand']}**의 이 제품은 {product['review_one']}와 같이 **전반적으로 좋은 평가**를 받고 있어, {nickname}님의 기준을 충족할 거예요."

def filter_products(mems, is_reroll=False):
    mem = " ".join(mems)
    budget = extract_budget(mems)
    priority = detect_priority(mems)

    previously_recommended_names = [p["name"] for p in st.session_state.recommended_products]

    def score(c):
        s = c["rating"]

        if budget:
            if c["price"] > budget * 1.5:
                return -1000

            if priority == "가격/예산":
                if c["price"] <= budget:
                    s += 4.0
                elif c["price"] <= budget * 1.2:
                    s += 1.0
                else:
                    s -= 3.0
            else:
                if c["price"] <= budget:
                    s += 2.0
                elif c["price"] <= budget * 1.2:
                    s += 0.5
                else:
                    s -= 2.0

        mandatory_pass = True
        for m in mems:
            if "(가장 중요)" in m:
                mem_stripped = m.replace("(가장 중요)", "").strip()
                is_feature_met = False

                if "예산" in mem_stripped:
                    continue

                if "노이즈캔슬링" in mem_stripped and any(tag in c["tags"] for tag in ["노이즈캔슬링", "최상급 노캔", "ANC"]):
                    is_feature_met = True
                elif ("가벼움" in mem_stripped or "착용감" in mem_stripped) and any(
                    tag in c["tags"] for tag in ["가벼움", "경량", "편안함"]
                ):
                    is_feature_met = True
                elif ("음질" in mem_stripped or "사운드" in mem_stripped) and any(
                    tag in c["tags"] for tag in ["균형 음질", "스튜디오", "밸런스", "자연스러운 사운드"]
                ):
                    is_feature_met = True
                elif "배터리" in mem_stripped and "배터리" in c["tags"]:
                    is_feature_met = True
                elif ("디자인" in mem_stripped or "스타일" in mem_stripped) and any(
                    tag in c["tags"] for tag in ["디자인", "고급", "프리미엄"]
                ):
                    is_feature_met = True
                elif "색상" in mem_stripped:
                    preferred_color_raw = re.search(r"색상은\s*([^을를]+)", mem_stripped)
                    if preferred_color_raw:
                        preferred_color = preferred_color_raw.group(1).strip().lower()
                        if any(preferred_color in pc.lower() for pc in c["color"]):
                            is_feature_met = True

                if not is_feature_met:
                    mandatory_pass = False
                    break

        if not mandatory_pass:
            return -10000

        if "노이즈캔슬링" in mem and "노이즈캔슬링" in " ".join(c["tags"]):
            s += 1.5
        if ("가벼움" in mem or "가벼운" in mem or "휴대성" in mem) and (
            ("가벼움" in " ".join(c["tags"])) or ("경량" in " ".join(c["tags"]))
        ):
            s += 2.0
        if ("디자인" in mem or "스타일" in mem) and ("디자인" in " ".join(c["tags"])):
            s += 1.0
        if "음질" in mem and ("균형" in " ".join(c["tags"]) or "사운드" in " ".join(c["tags"])):
            s += 0.8
        if "브랜드 감성" in mem and c["brand"] in ["Apple", "Bose", "Sony"]:
            s += 3.0
        if "전문적인 사운드 튜닝" in mem and c["brand"] in ["Sennheiser", "Audio-Technica"]:
            s += 2.5

        s += max(0, 10 - c["rank"])

        if c["name"] in previously_recommended_names:
            if is_reroll:
                s -= 10.0
            else:
                s -= 5.0

        return s

    cands = CATALOG[:]
    cands.sort(key=score, reverse=True)

    current_recs = cands[:3]
    st.session_state.current_recommendation = current_recs

    for p in current_recs:
        if p["name"] not in previously_recommended_names:
            st.session_state.recommended_products.append(p)

    return cands[:3]

def _brief_feature_from_item(c):
    if "가성비" in c["tags"]:
        return "가성비 인기"
    if c["rank"] <= 3:
        return "이달 판매 상위"
    if "최상급" in " ".join(c["tags"]):
        return "프리미엄 추천"
    if "디자인" in " ".join(c["tags"]):
        return "디자인 강점"
    return "실속형 추천"

def recommend_products(name, mems, is_reroll=False):
    products = filter_products(mems, is_reroll)
    budget = extract_budget(mems)

    concise_criteria = []
    for m in mems:
        reason_text = naturalize_memory(m).replace("(가장 중요) ", "").rstrip(".")
        if "예산은 약" in reason_text:
            concise_criteria.append(reason_text.replace("예산은 약", "예산").replace("로 생각하고 있어요", ""))
        elif "중요시" in reason_text or "중요하게 생각하고 있어요" in reason_text:
            concise_criteria.append(reason_text.replace(" 중요시 여겨요", "").replace(" 중요하게 생각하고 있어요", ""))
        else:
            concise_criteria.append(reason_text.replace("이에요", "").replace("고 있어요", ""))

    concise_criteria = [r.strip() for r in concise_criteria if r.strip()]
    concise_criteria = list(dict.fromkeys(concise_criteria))

    # 🚨 [캐러셀 UI 구현] GPT 응답 대신 UI를 직접 렌더링하고, 텍스트는 메시지 리스트에 추가
    
    # 1. 헤더 생성 및 출력
    header = "🎯 추천 제품 3가지\n\n"
    st.markdown(header)
    
    # 2. 캐러셀 컨테이너 생성 (3열)
    cols = st.columns(3, gap="small")

    for i, c in enumerate(products):
        if i >= 3: continue
        
        # 3. 개인화 추천 이유 생성
        is_over_budget = budget and c["price"] > budget
        personalized_reason_line = generate_personalized_reason(c, mems, name)

        if is_over_budget:
            reason_prefix = f"⚠️ **예산({budget//10000}만 원) 초과**지만, "
        else:
            reason_prefix = ""
        
        reason = (
            f"**{reason_prefix}** {name}님의 기준({', '.join(concise_criteria)})에 부합하며, "
            f"**{personalized_reason_line}**"
        )

        with cols[i]:
            # 🚨 [UI 개선] 캐러셀 카드 형태로 제품 정보 및 이미지 표시
            st.markdown(f'<div class="product-card">', unsafe_allow_html=True)
            st.markdown(f"**{i+1}. {c['name']}**")
            st.markdown(f'<img src="{c["img"]}" class="product-image">', unsafe_allow_html=True)
            st.markdown(f"**{c['brand']}**")
            st.markdown(f"• 💰 가격: 약 {c['price']:,}원")
            st.markdown(f"• ⭐ 평점: {c['rating']:.1f}")
            st.markdown(f"• 🏅 특징: {_brief_feature_from_item(c)}")
            
            # 💡 [가독성 개선] '더 알아보기' 버튼 추가
            if st.button(f"후보 {i+1} 상세 정보 보기", key=f"detail_btn_{i}"):
                # 버튼 클릭 시 해당 상품 번호로 handle_user_input을 호출하여 상세 정보 출력 단계로 전환
                st.session_state.current_recommendation = [c]
                st.session_state.stage = "product_detail"
                ai_say(f"사용자: 후보 {i+1}에 대해 더 알려줘.")
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        # 4. GPT가 대화창에 설명할 텍스트를 메시지 리스트에 추가 (캐러셀 아래에 메시지 형식으로 출력)
        block_text = (
            f"**{i+1}. {c['name']} ({c['brand']})**\n"
            f"• 💰 가격: 약 {c['price']:,}원 / ⭐ 평점: {c['rating']:.1f}\n"
            f"• 추천 이유: {reason}"
        )
        # 🚨 [가독성 개선] 엔터 없이 나열하는 대신, 핵심 정보만 간결하게 메시지로 추가
        ai_say(block_text)

    tail = (
        "\n\n궁금한 제품을 골라 번호로 물어보시거나, 기준을 바꾸면 추천도 함께 바뀝니다. "
        "새로운 추천을 원하시면 '다시 추천해줘'라고 말해주세요."
    )
    ai_say(tail)
    
    return None

def get_product_detail_prompt(product, user_input, memory_text, nickname):
    detail = (
        f"--- 상품 상세 정보 ---\n"
        f"제품명: {product['name']} ({product['brand']})\n"
        f"가격: {product['price']:,}원\n"
        f"평점: {product['rating']} (리뷰 {product['reviews']}개)\n"
        f"특징 태그: {', '.join(product['tags'])}\n"
        f"리뷰 요약: {product['review_one']}\n"
        f"----------------------\n"
    )
    selling_instruction = (
        f"사용자의 메모리({memory_text})를 바탕으로 이 제품을 구매했을 때 {nickname}님이 어떤 경험을 할지 구체적으로 시뮬레이션하여 설명해주세요. "
        f"답변은 **줄글이 아닌** '**-**' 또는 '**•**'와 같은 기호나 **번호**를 사용하여 핵심 정보별로 **단락을 나누어** 작성하고, "
        f"**이모티콘**을 적절히 활용하여 가독성을 높여야 합니다."
    )
    return f"""
[현재 상태] 사용자가 추천 상품 목록 중에서 {product['name']}에 대해 더 궁금해하고 있습니다.
[사용자 요청] {user_input}

{detail}
{selling_instruction}

위 정보를 바탕으로, 사용자의 질문에 답변하고 이 제품을 구매하도록 설득하거나 장단점을 설명해주세요. 
대화는 이제 이 상품에 대한 상세 정보/설득 단계로 전환됩니다.
"""

def gpt_reply(user_input: str) -> str:
    if not client:
        if "추천해줘" in user_input or "다시 추천" in user_input:
            return "현재 API 키가 설정되지 않아, '음질이 좋은 제품' 위주로 추천해 드릴게요. 1. Sony XM5 2. Bose QC45 3. AT M50xBT2"
        return "현재 API 키가 설정되지 않아 응답을 생성할 수 없습니다. 대신 메모리 기능은 정상 작동합니다."

    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    nickname = st.session_state.nickname

    if st.session_state.stage == "product_detail":
        if st.session_state.current_recommendation:
            product = st.session_state.current_recommendation[0]
            prompt_content = get_product_detail_prompt(product, user_input, memory_text, nickname)
        else:
            prompt_content = (
                f"현재 메모리: {memory_text}\n사용자 발화: {user_input}\n"
                f"이전에 선택된 상품이 없습니다. 일반적인 대화를 이어가주세요."
            )
            st.session_state.stage = "explore"
    else:
        stage_hint = ""
        is_design_in_memory = any("디자인/스타일" in m or "디자인은" in m for m in st.session_state.memory)
        is_color_in_memory = any("색상" in m for m in st.session_state.memory)

        is_usage_in_memory = any(
            k in memory_text for k in ["용도로", "운동", "게임", "출퇴근", "여행", "음악 감상"]
        )

        if st.session_state.stage == "explore":
            if is_usage_in_memory and len(st.session_state.memory) >= 2:
                stage_hint += (
                    "[필수 가이드: 사용 용도/상황('출퇴근 용도' 등)은 이미 파악되었습니다. "
                    "절대 용도/상황을 재차 묻지 말고, 다음 단계인 기능(배터리, 착용감, 통화품질 등)에 대한 질문으로 전환하세요.]"
                )

            if is_design_in_memory and not is_color_in_memory:
                stage_hint += (
                    "디자인 기준이 파악되었으므로, 다음 질문은 선호하는 색상이나 "
                    "구체적인 스타일(레트로, 미니멀 등)에 대한 질문으로 전환되도록 유도하세요. "
                )

            if len(st.session_state.memory) >= 3:
                stage_hint += "현재 메모리가 3개 이상 모였습니다. 재질문은 피하고 다음 단계의 질문으로 넘겨주세요."

        prompt_content = f"""{stage_hint}

[메모리]{memory_text if memory_text else "현재까지 저장된 메모리는 없습니다."}

[사용자 발화]{user_input}

위 메모리를 반드시 참고해 사용자의 말을 이해하고, 다음에 할 말을 한글로 답하세요.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content},
        ],
        temperature=0.5,
    )
    return res.choices[0].message.content

# =========================================================
# 대화/메시지 유틸
# =========================================================
def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})

def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})

# =========================================================
# 요약/비교 스텝
# =========================================================
def summary_step():
    # 🚨 [요약 중복 문제 해결] 요약 메시지가 이미 있으면 다시 추가하지 않음
    if not any(
        ("@" in m["content"]) and ("메모리 요약" in m["content"]) 
        for m in st.session_state.messages if m["role"] == "assistant"
    ):
        st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
        ai_say(st.session_state.summary_text)

def comparison_step(is_reroll=False):
    # 🚨 텍스트 출력 대신 캐러셀 UI를 직접 렌더링하고, 텍스트는 메시지 리스트에 추가
    recommend_products(st.session_state.nickname, st.session_state.memory, is_reroll)
    return None

# =========================================================
# 유저 입력 처리
# =========================================================
def handle_user_input(user_input: str):
    if not user_input.strip():
        return
        
    mem_updated = False
    
    mems = memory_sentences_from_user_text(user_input)
    if mems:
        for m in mems:
            add_memory(m, announce=True)
            mem_updated = True
    
    # 제품 번호 선택 (비교 단계)
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

        # 🚨 [선택/인식 오류 해결] 1, 2, 3 외의 번호는 무시하고, 유효한 번호일 때만 상세 정보로 전환
        if idx >= 0 and idx < len(st.session_state.current_recommendation):
            st.session_state.current_recommendation = [st.session_state.current_recommendation[idx]]
            st.session_state.stage = "product_detail"
            reply = gpt_reply(user_input)
            ai_say(reply)
            st.rerun()
            return
        else:
            # 🚨 [GPT 반응 개선] 잘못된 번호 입력 시 오류 메시지 출력
            ai_say("죄송해요, 후보 번호는 1번, 2번, 3번 중에서 골라주세요.")
            st.rerun()
            return

    # 다시 추천
    if any(k in user_input for k in ["다시 추천", "다른 상품"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say(
                "추천을 다시 받기 전에 **예산/가격대**를 먼저 알려주시겠어요? "
                "'몇 만 원 이내'로 생각하고 계신지 말씀해주시면 됩니다."
            )
            st.session_state.stage = "explore"
            st.rerun()
            return

        mems = memory_sentences_from_user_text(user_input)
        if mems:
            for m in mems:
                add_memory(m, announce=True)
        st.session_state.stage = "comparison"
        comparison_step(is_reroll=True)
        return

    # 기준이 충분히 쌓였는데 예산이 없는 경우 예산 먼저 질문
    if (
        st.session_state.stage == "explore"
        and len(st.session_state.memory) >= 3
        and extract_budget(st.session_state.memory) is None
    ):
        ai_say(
            "잠깐 멈추고 **예산/가격대**를 먼저 여쭤봐도 될까요? "
            "대략 '**몇 만 원 이내**'로 생각하고 계신지 알려주시면 딱 맞는 제품을 찾아드릴 수 있어요."
        )
        st.rerun()
        return

    # 기준이 충분하고 예산도 있을 때 자동으로 요약 단계로
    if (
        st.session_state.stage == "explore"
        and len(st.session_state.memory) >= 4
        and extract_budget(st.session_state.memory) is not None
    ):
        st.session_state.stage = "summary"
        summary_step()
        st.rerun()
        return

    # 명시적으로 추천 요청
    if any(k in user_input for k in ["추천해줘", "추천 해줘", "추천좀", "추천", "골라줘"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say(
                "잠시만요! 추천으로 넘어가기 전에 **예산/가격대**를 먼저 여쭤봐도 될까요? "
                "대략 '몇 만 원 이내'로 생각하고 계신지 알려주시면 딱 맞는 제품을 찾아드릴 수 있어요."
            )
            st.session_state.stage = "explore"
            st.rerun()
            return
        else:
            st.session_state.stage = "summary"
            summary_step()
            st.rerun()
            return

    # 더 이상 말할 기준 없다고 할 때
    if any(k in user_input for k in ["없어", "그만", "끝", "충분"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say(
                "추천을 받기 전에 **예산/가격대**만 확인하고 싶어요! "
                "대략 '몇 만 원 이내'로 생각하시나요?"
            )
            st.session_state.stage = "explore"
            st.rerun()
            return
        else:
            st.session_state.stage = "summary"
            summary_step()
            st.rerun()
            return

    # 일반 대화 단계
    if st.session_state.stage in ["explore", "product_detail"]:
        reply = gpt_reply(user_input)
        # 🚨 [GPT 반응 개선] GPT의 응답은 새 메모리가 아닌 경우에도 기존 메모리를 언급하며 대화를 이어가도록 유도됨
        ai_say(reply)
        st.rerun()
        return

    if st.session_state.stage == "summary":
        ai_say("정리된 기준을 한 번 확인해보시고, 아래 버튼을 눌러 추천을 받아보셔도 좋아요 🙂")
        st.rerun()
        return

    if st.session_state.stage == "comparison":
        reply = gpt_reply(user_input)
        ai_say(reply)
        st.rerun()
        return

# =========================================================
# 메모리 제어창 (좌측 패널)
# =========================================================
def top_memory_panel():
    st.markdown("### 🧠 나의 쇼핑 기준")
    st.caption("AI가 파악한 기준이 현재 구매 상황과 다를 경우, 아래에서 직접 수정하거나 삭제할 수 있어요.")

    with st.container():
        if len(st.session_state.memory) == 0:
            st.caption("아직 파악된 정보가 없습니다. 대화 중에 기준이 차곡차곡 쌓일 거예요.")
        else:
            for i, item in enumerate(st.session_state.memory):
                # 🚨 [UI 잘림 해결] 삭제 버튼 찌그러짐 방지를 위해 컬럼 비율 조정
                cols = st.columns([6, 1]) 
                with cols[0]:
                    display_text = naturalize_memory(item)
                    key = f"mem_edit_{i}"
                    st.markdown(f"**기준 {i+1}.**", help=item, unsafe_allow_html=True)
                    new_val = st.text_input(
                        f"메모리 {i+1}",
                        display_text,
                        key=key,
                        label_visibility="collapsed",
                    )

                    # 🚨 [입력 지연 해결] 메모리 텍스트 변경 시 즉시 업데이트 트리거
                    if new_val != display_text:
                        updated_mem_text = new_val.strip().replace("(가장 중요) ", "").replace(".", "")
                        if "이내로 생각하고 있어요" in new_val:
                            updated_mem_text = updated_mem_text
                        elif "디자인/스타일" in new_val:
                            updated_mem_text = "디자인/스타일을 중요시하다"
                        else:
                            updated_mem_text = updated_mem_text + "다"

                        if "(가장 중요)" in new_val:
                            updated_mem_text = "(가장 중요) " + updated_mem_text

                        update_memory(i, updated_mem_text)
                        
                        # 상태 변경 시 바로 rerun
                        st.rerun()

                with cols[1]:
                    # 삭제 버튼을 입력창 옆에 배치
                    if st.button("삭제", key=f"del_{i}", use_container_width=True):
                        delete_memory(i)
                        st.rerun() # 삭제 후 바로 rerun

        st.markdown("---")
        st.markdown("##### ➕ 새로운 기준 추가")
        new_mem = st.text_input(
            "새 메모리 추가",
            placeholder="예: 운동용으로 가벼운 제품이 필요해요 / 15만원 이내로 생각해요",
            label_visibility="collapsed",
            key="new_mem_input"
        )
        if st.button("추가", key="add_mem_btn", use_container_width=True):
            if new_mem.strip():
                add_memory(new_mem.strip(), announce=True)
                st.session_state.just_updated_memory = True
                st.rerun() # 추가 후 바로 rerun

# =========================================================
# 채팅 UI (우측 패널)
# =========================================================
def chat_interface():
    st.markdown("### 🎧 AI 쇼핑 에이전트와 대화하기")
    st.caption("대화를 통해 기준을 정리하고, 그 기준에 맞는 헤드셋 추천을 받아보는 실험입니다.")

    col_mem, col_chat = st.columns([0.38, 0.62], gap="medium") # 🚨 [UI 잘림 해결] 컬럼 비율 조정 (38:62)

    # 📝 [메모리 알림] 알림은 컬럼 시작 시점에 바로 렌더링
    if st.session_state.notification_message:
        st.info(st.session_state.notification_message, icon="📝")
        st.session_state.notification_message = ""

    with col_mem:
        # 🚨 [UI 개선] 메모리 패널에 고정 스크롤 적용 컨테이너
        with st.markdown("<div class='memory-panel-fixed'>", unsafe_allow_html=True):
             top_memory_panel()
        st.markdown("</div>", unsafe_allow_html=True) # close memory-panel-fixed div

    with col_chat:
        st.markdown("#### 💬 대화창")
        
        # 💡 [입력 지연 해결] 초기 웰컴 메시지는 메시지 리스트가 비어있을 때만 추가 (rerun 없이)
        if not st.session_state.messages and st.session_state.nickname:
            ai_say(
                f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요.\n"
                "대화를 통해 기준을 기억하며 블루투스 헤드셋을 함께 찾아볼게요.\n"
                "우선, 어떤 용도로 사용하실 예정인가요?"
            )

        # 기존 메시지 순서대로 출력
        st.markdown("<div class='chat-display-area'>", unsafe_allow_html=True)
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            elif msg["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 🚨 [대화창 하단 시작 문제 해결] 스크롤 다운 JS 실행
        run_js_scroll()


        # 요약 단계일 때: 버튼 제공
        if st.session_state.stage == "summary":
            # 🚨 [요약 중복 문제 해결] 요약 메시지가 이미 있으면 다시 생성하지 않음
            summary_message_exists = any(
                ("@" in m["content"]) and ("메모리 요약" in m["content"]) for m in st.session_state.messages if m["role"] == "assistant"
            )

            if not summary_message_exists or st.session_state.just_updated_memory:
                summary_step()
                st.session_state.just_updated_memory = False
                st.rerun()

            with st.chat_message("assistant"):
                if st.button("🔍 이 기준으로 추천 받기", key="summary_btn"):
                    if extract_budget(st.session_state.memory) is None:
                        ai_say(
                            "아직 예산을 여쭤보지 못했어요. 추천을 시작하기 전에 "
                            "**대략적인 가격대(예: 30만원 이내)**를 말씀해주시겠어요?"
                        )
                        st.session_state.stage = "explore"
                    else:
                        st.session_state.stage = "comparison"
                        comparison_step()
                    st.rerun()

        # 비교 단계 최초 진입 시 추천 메시지 출력 
        if st.session_state.stage == "comparison":
            if not any(
                "🎯 추천 제품 3가지" in m["content"] for m in st.session_state.messages if m["role"] == "assistant"
            ):
                comparison_step()
                # comparison_step 내부에서 메시지 추가 및 rerun 호출됨

        # 🚨 [입력 지연 해결] st.chat_input 대신 st.form과 st.text_area 사용
        with st.form(key="chat_form", clear_on_submit=True):
            user_input_area = st.text_area(
                "메시지를 입력하세요.",
                key="main_text_area",
                placeholder="헤드셋에 대해 궁금한 점이나 원하는 기준을 자유롭게 말씀해주세요.",
                label_visibility="collapsed"
            )
            submit_button = st.form_submit_button(label="전송", use_container_width=False)

        if submit_button and user_input_area:
            user_say(user_input_area) # 폼에서 제출된 값 사용
            handle_user_input(user_input_area) # 값 처리

# =========================================================
# 사전 정보 입력 페이지 (최종 수정)
# =========================================================
def context_setting():
    st.markdown("### 🧾 실험 준비 (1/3단계)")
    st.caption("헤드셋 구매에 반영될 기본 정보와 평소 취향을 간단히 입력해 주세요.")

    st.markdown("---")

    # 1. 이름
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**1. 이름**")
    st.caption("사전 설문에서 작성한 이름과 동일해야 합니다. 추후 대화 여부를 통한 불성실 응답자 판별에 활용될 수 있기 때문에, 반드시 설문에서 작성한 이름과 동일하게 적어주세요.")
    nickname = st.text_input("이름 입력", placeholder="예: 홍길동", key="nickname_input")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 2. 최근 구매 품목 
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**2. 최근에 산 물건 한 가지**")
    st.caption("최근 3개월 동안 구매한 제품 중 하나를 떠올려 주세요. (카테고리 단위면 충분합니다)")
    purchase_list = st.text_input("최근 구매 품목", placeholder="예: 옷 / 신발 / 시계 / 태블릿 등", key="purchase_list_input")
    st.markdown("</div>", unsafe_allow_html=True)

    # 3. 선호 색상
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**3. 선호하는 색상**")
    st.caption("평소 쇼핑할 때 선호하는 색상을 입력해 주세요.")
    color_option = st.text_input("선호 색상", placeholder="예: 화이트 / 블랙 / 네이비 등", key="color_input")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 4. 중요 기준
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**4. 쇼핑할 때 가장 중요하기 보는 기준**")
    st.caption("평소 쇼핑할 때 어떤 기준을 가장 중요하게 고려하시나요?")
    priority_option = st.radio(
        "가장 중요했던 기준을 선택해 주세요.",
        ("디자인/스타일", "가격/가성비", "성능/품질", "브랜드 이미지"),
        index=None,
        key="priority_radio",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("헤드셋 쇼핑 시작하기 (3단계로 이동)"):
        if not nickname.strip() or not purchase_list.strip() or not priority_option or not color_option.strip():
            st.warning("모든 항목을 입력해 주세요.")
            return

        st.session_state.nickname = nickname.strip()

        color_mem = f"색상은 {color_option.strip()}을 선호해요."
        particle = get_eul_reul(priority_option)
        priority_mem = f"(가장 중요) {priority_option}{particle} 중요시 여겨요."

        add_memory(color_mem, announce=False)
        add_memory(priority_mem, announce=False)

        st.session_state.messages = []
        st.session_state.stage = "explore"
        st.session_state.page = "chat"
        st.rerun()

# =========================================================
# 라우팅
# =========================================================
if st.session_state.page == "context_setting":
    context_setting()
else:
    chat_interface()
    
