import streamlit as st
import time
import random
import re
from openai import OpenAI

# =========================================================
# 기본 설정
# =========================================================
st.set_page_config(page_title="AI 쇼핑 에이전트 실험용", page_icon="🎧", layout="wide")

# =========================================================
# GPT 설정
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
- 사용자가 특정 상품(번호)에 대해 질문하면, 그 상품에 대한 정보, 리뷰, 장단점 등을 자세히 설명하며 구매를 설득하거나 보조하는 대화로 전환한다. - 특히 상품 설명 시, 사용자의 메모리를 활용하여 해당 제품을 사용했을 때의 개인화된 경험을 시뮬레이션하는 톤으로 설명한다.

[메모리 활용]
- 아래에 제공되는 메모리를 기반으로 대화 내용을 유지하라.
- 메모리와 사용자의 최신 발언이 충돌하면, “기존에 ~라고 하셨는데, 기준을 바꾸실까요?”처럼 정중하게 확인 질문을 한다.

[출력 규칙]
- 한 번에 너무 많은 질문을 하지 말고, 자연스럽게 한두 개씩만 묻는다.
- 중복 질문은 피하고, 꼭 필요할 때는 “다시 한 번만 확인할게요”라고 말한다.
- 사용자의 표현을 적당히 따라가되, 전체 톤은 부드러운 존댓말로 유지한다.
"""
# Streamlit Cloud에서는 Secrets에 OPENAI_API_KEY 저장
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except KeyError:
    client = None

# =========================================================
# 세션 상태 초기화
# =========================================================
def ss_init():
    ss = st.session_state
    ss.setdefault("nickname", None)
    ss.setdefault("page", "onboarding")       # onboarding -> context_setting -> chat
    ss.setdefault("stage", "explore")         # explore -> summary -> comparison -> product_detail
    ss.setdefault("initial_purchase_context", None) # 추가: 초기 구매 품목 정보
    ss.setdefault("messages", []) # list[dict]
    ss.setdefault("memory", []) 		 # list[str]
    ss.setdefault("summary_text", "")
    ss.setdefault("just_updated_memory", False)
    ss.setdefault("recommended_products", [])
    ss.setdefault("current_recommendation", [])
    ss.setdefault("notification_message", "") # 메모리 변경 알림 메시지
ss_init()

# =========================================================
# 유틸리티 함수
# =========================================================
def get_eul_reul(noun: str) -> str:
    """명사 뒤에 붙는 목적격 조사 '을/를'을 결정합니다."""
    if not noun or not noun[-1].isalpha():
        return "을" 
        
    last_char = noun[-1]
    
    # 한글 유니코드 범위 확인 (가=44032, 힣=55203)
    if not ('\uAC00' <= last_char <= '\uD7A3'):
        # 한글이 아닌 경우, 복잡한 경우 (안전하게 '을' 선택)
        return "을" 

    # 마지막 글자 코드값을 가져옴
    last_char_code = ord(last_char)
    # 종성(받침)이 있는지 확인: (코드값 - 44032) % 28
    if (last_char_code - 44032) % 28 > 0:
        return "을" # 받침 있음 (e.g., 디자인 -> 디자인을)
    else:
        return "를" # 받침 없음 (e.g., 가성비 -> 가성비를)

def naturalize_memory(text: str) -> str:
    """메모리 문장을 사용자 1인칭 자연어로 다듬기."""
    t = text.strip()
    t = t.replace("노이즈 캔슬링", "노이즈캔슬링")
    
    is_priority = "(가장 중요)" in t
    t = t.replace("(가장 중요)", "").strip()

    if t.endswith(("다", "다.")):
        t = t.rstrip(".")
        if any(kw in t for kw in ["중요", "중시", "중요시", "우선", "생각하고"]):
            t = t + "고 있어요."
        elif "이내" in t or "이상" in t or "정도" in t:
            t = t + "로 생각하고 있어요."
        else:
            t = t + "이에요."
    t = t.replace("생각한고", "생각하고")
    
    if not t.endswith((".", "요", "다")):
        t += "."
            
    if is_priority:
        t = "(가장 중요) " + t
    
    t = t.replace("생각하고 고 있어요.", "생각하고 있어요.")
    
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
            
    # 1) 예산
    m = re.search(r"(\d+)\s*만\s*원", u) 
    if m:
        price = m.group(1)
        st.session_state.memory = [mem for mem in st.session_state.memory if "예산" not in mem]
        mem = f"예산은 약 {price}만 원 이내로 생각하고 있어요."
        mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)

    # 4) 절(clause)별 키워드 규칙
    clauses = _clause_split(u)
    
    for c in clauses:
        base_rules = [
            ("노이즈캔슬링", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("ANC", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("소음 차단", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("가벼운", "가벼운 착용감을 선호하고 있어요."),
            ("가볍", "가벼운 착용감을 선호하고 있어요."),
            
            # --- 구체적 디자인/스타일 추출 ---
            ("클래식", "클래식한 디자인을 선호하고 있어요."),
            ("깔끔", "깔끔한 디자인을 선호하고 있어요."),
            ("미니멀", "미니멀한 디자인을 선호하고 있어요."),
            ("레트로", "레트로 스타일을 선호하고 있어요."),
            
            ("예쁘면", "디자인/스타일을 중요하게 생각하고 있어요."),
            ("디자인", "디자인/스타일을 중요하게 생각하고 있어요."),
            
            # --- 색상 추출 ---
            ("화이트", "색상은 흰색/화이트 계열을 선호하고 있어요."),
            ("블랙", "색상은 검은색/블랙 계열을 선호하고 있어요."),
            ("보라", "색상은 보라색 계열을 선호하고 있어요."),
            ("네이비", "색상은 네이비 계열을 선호하고 있어요."),
            ("실버", "색상은 실버 계열을 선호하고 있어요."),
            
            ("음질", "음질을 중요하게 생각하고 있어요."),
            ("배터리", "배터리 지속시간이 긴 제품을 선호하고 있어요."),
            ("운동", "주로 러닝/운동 용도로 사용할 예정이에요."),
            ("산책", "주로 산책/일상 용도로 사용할 예정이에요."),
            ("게임", "주로 게임 용도로 사용할 예정이며, 이 점을 중요하게 생각하고 있어요."),
        ]
        
        matched = False
        for key, sent in base_rules:
            if key in c:
                mem = sent
                
                if key in ["클래식", "깔끔", "미니멀", "레트로"] and len(c.strip()) > 3:
                     cleaned_c = c.strip().replace("거", "").replace("요", "").replace("느낌", "").replace("스타일", "").strip()
                     if cleaned_c:
                         mem = f"디자인은 '{cleaned_c}' 스타일을 선호해요."
                         
                mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)
                matched = True
                break
            
        # 일반적인 중요 키워드에 대한 처리 ('거' 추가로 '클래식하고 깔끔한거' 포착)
        if re.search(r"(하면 좋겠|좋겠어|가 좋아|선호|필요해|중요해|거)", c) and not matched:
            if len(c.strip()) > 3 and not any(k in c for k in ["예쁘면", "디자인", "스타일"]): 
                mem = c.strip() + "로 생각하고 있어요."
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
        
    mem_text_stripped = mem_text.replace('(가장 중요)', '').strip()
    
    if "예산은 약" in mem_text_stripped:
         st.session_state.memory = [m for m in st.session_state.memory if "예산은 약" not in m]

    if "색상은" in mem_text_stripped:
         st.session_state.memory = [m for m in st.session_state.memory if "색상은" not in m]
         
    if any(k in mem_text_stripped for k in ["클래식", "깔끔", "미니멀", "레트로", "세련", "디자인은"]):
         st.session_state.memory = [m for m in st.session_state.memory if "디자인/스타일" not in m]

    # 기존 중복 및 중요도 체크 로직
    for i, m in enumerate(st.session_state.memory):
        m_stripped = m.replace('(가장 중요)', '').strip()
        
        if mem_text_stripped in m_stripped or m_stripped in mem_text_stripped:
            if '(가장 중요)' in mem_text and '(가장 중요)' not in m:
                for j, existing_m in enumerate(st.session_state.memory):
                    st.session_state.memory[j] = existing_m.replace('(가장 중요)', '').strip()
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
        if '(가장 중요)' in new_text:
            for i, existing_m in enumerate(st.session_state.memory):
                st.session_state.memory[i] = existing_m.replace('(가장 중요)', '').strip()
            
        st.session_state.memory[idx] = new_text.strip()
        st.session_state.just_updated_memory = True
        st.session_state.notification_message = "🔄 메모리가 업데이트되었어요."

# =========================================================
# 요약 / 추천 로직 (가격 필터링 로직 수정됨)
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
    tail = (
        "\n제가 정리한 기준이 맞을까요? 상단 메모리 제어창에서 언제든 수정할 수 있어요.\n"
        "변경이 없다면 아래 버튼을 눌러 추천을 받아보셔도 좋아요 👇"
    )
    return header + body + tail

CATALOG = [
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 179000, "rating": 4.4, "reviews": 1600, "rank": 8, "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"], "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.", "color": ["블랙", "네이비"]},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 129000, "rating": 4.4, "reviews": 2300, "rank": 9, "tags": ["가벼움", "균형형 음질", "노이즈캔슬링"], "review_one": "가볍고 음색이 밝다는 평이 많아요.", "color": ["블랙", "화이트"]},
    {"name": "Sony WH-CH720N", "brand": "Sony", "price": 169000, "rating": 4.5, "reviews": 2100, "rank": 6, "tags": ["노이즈캔슬링", "경량", "무난한 음질"], "review_one": "경량이라 출퇴근용으로 좋다는 후기가 많아요.", "color": ["블랙", "화이트", "블루"]},
    {"name": "Bose QC45", "brand": "Bose", "price": 420000, "rating": 4.7, "reviews": 2800, "rank": 2, "tags": ["최상급 착용감", "자연스러운 사운드", "노이즈캔슬링", "편안함"], "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.", "color": ["블랙", "화이트"]},
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 450000, "rating": 4.8, "reviews": 3200, "rank": 1, "tags": ["최상급 노캔", "균형 음질", "플래그십", "통화품질"], "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.", "color": ["블랙", "화이트"]},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 679000, "rating": 4.6, "reviews": 1500, "rank": 3, "tags": ["프리미엄", "노이즈캔슬링", "디자인", "고급"], "review_one": "디자인과 브랜드 감성 때문에 만족도가 높아요.", "color": ["실버", "스페이스그레이"]},
    {"name": "Sennheiser PXC 550-II", "brand": "Sennheiser", "price": 289000, "rating": 4.3, "reviews": 1200, "rank": 7, "tags": ["착용감", "여행", "배터리", "노이즈캔슬링"], "review_one": "여행 시 장시간 착용에도 압박감이 덜해요.", "color": ["블랙"]},
    {"name": "AKG Y600NC", "brand": "AKG", "price": 149000, "rating": 4.2, "reviews": 1800, "rank": 10, "tags": ["균형 음질", "가성비", "노이즈캔슬링"], "review_one": "가격대비 깔끔하고 균형 잡힌 사운드가 좋아요.", "color": ["블랙", "골드"]},
    {"name": "Microsoft Surface Headphones 2", "brand": "Microsoft", "price": 319000, "rating": 4.5, "reviews": 900, "rank": 11, "tags": ["업무", "통화품질", "디자인", "노이즈캔슬링"], "review_one": "업무용으로 완벽하며 통화 품질이 매우 깨끗합니다.", "color": ["라이트 그레이", "매트 블랙"]},
    {"name": "Bose Noise Cancelling Headphones 700", "brand": "Bose", "price": 490000, "rating": 4.7, "reviews": 2500, "rank": 4, "tags": ["최상급 노캔", "통화품질", "프리미엄"], "review_one": "노이즈캔슬링 성능과 스타일을 모두 갖춘 제품.", "color": ["블랙", "실버"]},
    {"name": "Audio-Technica M50xBT2", "brand": "Audio-Technica", "price": 249000, "rating": 4.6, "reviews": 1100, "rank": 5, "tags": ["스튜디오", "음질", "밸런스", "디자인"], "review_one": "음악 감상용으로 정교하고 명료한 사운드가 일품.", "color": ["블랙"]},
    {"name": "Jabra Elite 85h", "brand": "Jabra", "price": 219000, "rating": 4.3, "reviews": 1400, "rank": 12, "tags": ["배터리", "내구성", "방수", "통화품질"], "review_one": "배터리가 오래가고 튼튼해서 막 쓰기 좋아요.", "color": ["티타늄 블랙", "네이비"]},
]

def generate_personalized_reason(product, mems, nickname):
    mem_str = " ".join([naturalize_memory(m) for m in mems])
    
    # 1. Key Preference Extraction
    preferred_color_match = re.search(r"색상은\s*([^계열]+)\s*계열", mem_str)
    if not preferred_color_match:
         preferred_color_match = re.search(r"색상은\s*([^을를])\s*(을|를)\s*선호", mem_str)
    
    preferred_color_raw = preferred_color_match.group(1).strip().replace("/", "") if preferred_color_match else None
    preferred_color = preferred_color_raw.lower() if preferred_color_raw else None

    preferred_style_match = re.search(r"디자인은\s*['\"]?([^']+?)['\"]?\s*스타일을 선호", mem_str)
    preferred_style = preferred_style_match.group(1).strip() if preferred_style_match else None
    
    preferred_usage = None
    if any("산책" in m for m in mems): preferred_usage = "산책/가벼움/편안함"
    elif any("출퇴근" in m for m in mems): preferred_usage = "출퇴근/가벼움/편안함"
    elif any("운동" in m for m in mems) or any("러닝" in m for m in mems): preferred_usage = "운동/가벼움/착용감"
    
    # 2. Simulation Construction based on Product Match
    product_colors_lower = [c.lower() for c in product["color"]]
    
    if preferred_color and any(c in preferred_color for c in product_colors_lower):
        matched_color = next((c for c in product["color"] if c.lower() in preferred_color), product["color"][0])
        
        if preferred_style:
            return f"**{matched_color} 색상**이 {nickname}님의 **'{preferred_style}'** 스타일에 잘 어울릴 거예요. 특히 이 제품은 **{product['review_one']}** 평을 받고 있어요."
        
        elif any(tag in product["tags"] for tag in ["디자인", "고급"]):
            return f"**{matched_color} 색상**이 준비되어 있고 **디자인** 면에서도 호평을 받는 제품이에요. 시각적 만족도가 높으실 거예요."

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
    
    previously_recommended_names = [p['name'] for p in st.session_state.recommended_products]

    def score(c):
        s = c["rating"]
        
        # --- 🚨 수정된 가격 기준 엄격 적용 로직 ---
        if budget:
            # 1. 예산의 150% 초과 시 강력 감점 (사실상 제외)
            if c["price"] > budget * 1.5: 
                return -1000 
            
            # 2. 가격/가성비가 최우선 기준일 경우 (추가 보너스/감점)
            if priority == "가격/예산":
                if c["price"] <= budget:
                    s += 4.0 
                elif c["price"] <= budget * 1.2:
                    s += 1.0 
                else: 
                    s -= 3.0 
            # 3. 가격/가성비가 최우선 기준이 아닐 경우
            else:
                if c["price"] <= budget: 
                    s += 2.0
                elif c["price"] <= budget * 1.2: 
                    s += 0.5 
                else: 
                    s -= 2.0
        # --- 가격 로직 끝 ---

        # 🚨 NEW: HARD CONSTRAINT CHECK for (가장 중요) criteria (User Request)
        mandatory_pass = True
        for m in mems:
            if "(가장 중요)" in m:
                mem_stripped = m.replace("(가장 중요)", "").strip()
                is_feature_met = False
                
                # Check 1: Budget (Handled by scoring) - Skip hard constraint here
                if "예산" in mem_stripped:
                    continue 

                # Check 2: Features (ANC, Sound, Comfort, Design, Usage)
                if "노이즈캔슬링" in mem_stripped and any(tag in c["tags"] for tag in ["노이즈캔슬링", "최상급 노캔", "ANC"]):
                    is_feature_met = True
                elif ("가벼움" in mem_stripped or "착용감" in mem_stripped) and any(tag in c["tags"] for tag in ["가벼움", "경량", "편안함"]):
                    is_feature_met = True
                elif ("음질" in mem_stripped or "사운드" in mem_stripped) and any(tag in c["tags"] for tag in ["균형 음질", "스튜디오", "밸런스", "자연스러운 사운드"]):
                    is_feature_met = True
                elif ("배터리" in mem_stripped) and "배터리" in c["tags"]:
                    is_feature_met = True
                elif ("디자인" in mem_stripped or "스타일" in mem_stripped) and any(tag in c["tags"] for tag in ["디자인", "고급", "프리미엄"]):
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
        # --- END HARD CONSTRAINT CHECK ---


        # 기능/특징 점수 (기존 로직 유지)
        if "노이즈캔슬링" in mem and "노이즈캔슬링" in " ".join(c["tags"]): s += 1.5
        if ("가벼움" in mem or "가벼운" in mem or "휴대성" in mem) and (("가벼움" in " ".join(c["tags"])) or ("경량" in " ".join(c["tags"]))): s += 2.0
        if ("디자인" in mem or "스타일" in mem) and ("디자인" in " ".join(c["tags"])): s += 1.0
        if "음질" in mem and ("균형" in " ".join(c["tags"]) or "사운드" in " ".join(c["tags"])): s += 0.8
        
        if "브랜드 감성" in mem and c["brand"] in ["Apple", "Bose", "Sony"]: s += 3.0
        if "전문적인 사운드 튜닝" in mem and c["brand"] in ["Sennheiser", "Audio-Technica"]: s += 2.5

        # 순위 점수
        s += max(0, 10 - c["rank"])
        
        # 재추천 감점
        if c['name'] in previously_recommended_names:
            if is_reroll: s -= 10.0
            else: s -= 5.0
        return s

    cands = CATALOG[:]
    cands.sort(key=score, reverse=True)
    
    current_recs = cands[:3]
    st.session_state.current_recommendation = current_recs
    
    for p in current_recs:
        if p['name'] not in previously_recommended_names:
            st.session_state.recommended_products.append(p)
            
    return cands[:3]


def _brief_feature_from_item(c):
    if "가성비" in c["tags"]: return "가성비 인기"
    if c["rank"] <= 3: return "이달 판매 상위"
    if "최상급" in " ".join(c["tags"]): return "프리미엄 추천"
    if "디자인" in " ".join(c["tags"]): return "디자인 강점"
    return "실속형 추천"

def recommend_products(name, mems, is_reroll=False):
    products = filter_products(mems, is_reroll)
    budget = extract_budget(mems)
    
    # --- 🚨 수정된 부분: 모든 기준을 간결하게 나열 (요청 #2) ---
    concise_criteria = []
    for m in mems:
        reason_text = naturalize_memory(m).replace("(가장 중요) ", "").rstrip('.')
        
        # Simplify the reason text for listing
        if "예산은 약" in reason_text:
             concise_criteria.append(reason_text.replace("예산은 약", "예산").replace("로 생각하고 있어요", ""))
        elif "중요시" in reason_text or "중요하게 생각하고 있어요" in reason_text:
             concise_criteria.append(reason_text.replace(" 중요시 여겨요", "").replace(" 중요하게 생각하고 있어요", ""))
        else:
             concise_criteria.append(reason_text.replace("이에요", "").replace("고 있어요", ""))
             
    # Deduplicate and clean up
    concise_criteria = [r.strip() for r in concise_criteria if r.strip()]
    concise_criteria = list(dict.fromkeys(concise_criteria)) 
    # --- END CRITERIA MODIFICATION ---
        
    header = "🎯 추천 제품 3가지\n\n"
    
    blocks = []
    for i, c in enumerate(products):
        
        # --- 🚨 수정된 부분: 예산 초과 여부 확인 및 조건부 문구 생성 (요청 #1) ---
        is_over_budget = budget and c['price'] > budget
        
        personalized_reason_line = generate_personalized_reason(c, mems, name)
        
        if is_over_budget:
            # Case 1: Over Budget - Use explicit warning and mention superior quality
            reason = (
                f"추천 이유: ⚠️ **예산({budget//10000}만 원)을 초과하지만,** "
                f"**{name}님**의 **다른 기준({', '.join(concise_criteria)})**에 **매우 뛰어나** 추천드려요. "
                f"특히 **{personalized_reason_line}**" 
            )
        else:
             # Case 2: Under/Within Budget - Mention compliance with all criteria
             reason = (
                f"추천 이유: **{name}님**의 **모든 기준({', '.join(concise_criteria)})**에 부합하며, "
                f"특히 **{personalized_reason_line}**"
            )
        # --- END CONDITIONAL MODIFICATION ---

        block = (
            f"**{i+1}. {c['name']} ({c['brand']})**\n\n"
            f"- 💰 가격: 약 {c['price']:,}원\n"
            f"- ⭐ 평점: {c['rating']:.1f} (리뷰 {c['reviews']}개)\n"
            f"- 📈 카테고리 판매순위: Top {c['rank']}\n"
            f"- 🗣️ 리뷰 한줄요약: {c['review_one']}\n"
            f"- 🎨 색상 옵션: {', '.join(c['color'])}\n"
            f"- 🏅 특징: {_brief_feature_from_item(c)}\n"
            f"- {reason}"
        )
        blocks.append(block)
        
    tail = "\n\n궁금한 제품을 골라 번호로 물어보시거나, 기준을 바꾸면 추천도 함께 바뀝니다. 새로운 추천을 원하시면 '다시 추천해줘'라고 말해주세요."
    return header + "\n\n---\n\n".join(blocks) + "\n\n" + tail

# ... (나머지 함수들은 변경 없음)

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
        f"답변은 **줄글이 아닌** '**-**' 또는 '**•**'와 같은 기호나 **번호**를 사용하여 핵심 정보별로 **단락을 나누어** 작성하고, **이모티콘**을 적절히 활용하여 가독성을 높여야 합니다."
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
            prompt_content = f"현재 메모리: {memory_text}\n사용자 발화: {user_input}\n 이전에 선택된 상품이 없습니다. 일반적인 대화를 이어가주세요."
            st.session_state.stage = "explore" 
    else:
        stage_hint = ""
        is_design_in_memory = any("디자인/스타일" in m or "디자인은" in m for m in st.session_state.memory)
        is_color_in_memory = any("색상" in m for m in st.session_state.memory)
        
        is_usage_in_memory = any(k in memory_text for k in ["용도로", "운동", "게임", "출퇴근", "여행", "음악 감상"])
        
        if st.session_state.stage == "explore":
             if is_usage_in_memory and len(st.session_state.memory) >= 2:
                  stage_hint += "[필수 가이드: 사용 용도/상황('출퇴근 용도' 등)은 이미 파악되었습니다. 절대 용도/상황을 재차 묻지 말고, 다음 단계인 기능(배터리, 착용감, 통화품질 등)에 대한 질문으로 전환하세요.]"
            
             if is_design_in_memory and not is_color_in_memory:
                 stage_hint += "디자인 기준이 파악되었으므로, 다음 질문은 선호하는 색상이나 구체적인 스타일(레트로, 미니멀 등)에 대한 질문으로 전환되도록 유도하세요. "
            
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

def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})

def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})

def handle_user_input(user_input: str):
    
    # 1) 메모리 추출 / 추가 먼저 실행
    mems = memory_sentences_from_user_text(user_input)
    if mems:
        for m in mems: add_memory(m, announce=True)
        
    st.session_state.notification_message = ""
    
    # 특정 상품 번호 선택 감지 (로직 유지)
    product_re = re.search(r"([1-3]|첫\s*번|두\s*번|세\s*번).*(궁금|골라|선택)", user_input)
    if product_re and st.session_state.stage == "comparison":
        match = product_re.group(1).lower()
        idx = 0 if '첫' in match or '1' in match else 1 if '두' in match or '2' in match else 2 if '세' in match or '3' in match else -1
        if idx >= 0 and idx < len(st.session_state.current_recommendation):
            st.session_state.current_recommendation = [st.session_state.current_recommendation[idx]]
            st.session_state.stage = "product_detail"
            reply = gpt_reply(user_input)
            ai_say(reply)
            return
        else:
             ai_say("죄송해요, 해당 번호의 제품은 추천 목록에 없습니다. 1번부터 3번 중 다시 선택해 주시겠어요?")
             return
    
    # '다시 추천해줘' 요청 감지 (로직 유지)
    if any(k in user_input for k in ["다시 추천", "다른 상품"]):
        if extract_budget(st.session_state.memory) is None:
            if extract_budget(st.session_state.memory) is None:
                ai_say("추천을 다시 받기 전에 **예산/가격대**를 먼저 알려주시겠어요? '몇 만 원 이내'로 생각하고 계신지 말씀해주시면 됩니다.")
                st.session_state.stage = "explore"
                st.rerun() 
                return
        mems = memory_sentences_from_user_text(user_input)
        if mems:
            for m in mems: add_memory(m, announce=True)
        st.session_state.stage = "comparison"
        comparison_step(is_reroll=True) 
        st.rerun()
        return

    # --- 🚨 수정된 부분: 메모리 3개 이상 시 예산 질문 강제, 4개 이상 시 요약 강제 ---
    # 2) 탐색 단계에서 메모리가 3개 이상 모이고 예산이 없으면 예산 질문 강제 (시스템 제어)
    if st.session_state.stage == "explore" and len(st.session_state.memory) >= 3 and extract_budget(st.session_state.memory) is None:
        ai_say("잠깐 멈추고 **예산/가격대**를 먼저 여쭤봐도 될까요? 대략 '**몇 만 원 이내**'로 생각하고 계신지 알려주시면 딱 맞는 제품을 찾아드릴 수 있어요.")
        st.rerun() 
        return
    
    # 3) 탐색 단계에서 메모리가 4개 이상 모이고 예산이 있으면 요약 단계로 강제 전환
    if st.session_state.stage == "explore" and len(st.session_state.memory) >= 4 and extract_budget(st.session_state.memory) is not None:
        st.session_state.stage = "summary"
        st.rerun()
        return
    # --- 수정된 부분 끝 ---
    
    # 4) 추천 직접 요청 시 (🚨 PRICE CHECK: 예산이 없으면 추천 진입 차단)
    if any(k in user_input for k in ["추천해줘", "추천 해줘", "추천좀", "추천", "골라줘"]):
        if extract_budget(st.session_state.memory) is None:
              ai_say("잠시만요! 추천으로 넘어가기 전에 **예산/가격대**를 먼저 여쭤봐도 될까요? 대략 '몇 만 원 이내'로 생각하고 계신지 알려주시면 딱 맞는 제품을 찾아드릴 수 있어요.")
              st.session_state.stage = "explore" 
              st.rerun()
              return
        else:
            st.session_state.stage = "summary"
            st.rerun()
            return

    # 5) "그만/없어/충분" → 탐색 종료 후 요약 단계로
    if any(k in user_input for k in ["없어", "그만", "끝", "충분"]):
        if extract_budget(st.session_state.memory) is None:
              ai_say("추천을 받기 전에 **예산/가격대**만 확인하고 싶어요! 대략 '몇 만 원 이내'로 생각하시나요?")
              st.session_state.stage = "explore" 
              st.rerun()
              return
        else:
            st.session_state.stage = "summary"
            st.rerun()
            return

    # 6) 그 외 일반 대화는 GPT에게 위임
    if st.session_state.stage == "explore" or st.session_state.stage == "product_detail":
        reply = gpt_reply(user_input)
        ai_say(reply)
        return

    # 7) 요약 단계에서는 summary_step이 별도로 호출되므로 여기서는 가볍게 응대만
    if st.session_state.stage == "summary":
        ai_say("정리된 기준을 한 번 확인해보시고, 아래 버튼을 눌러 추천을 받아보셔도 좋아요 🙂")
        return

    # 8) 비교 단계에서의 대화 (상품 번호가 아닌 다른 일반 질문)
    if st.session_state.stage == "comparison":
        reply = gpt_reply(user_input)
        ai_say(reply)
        return

# =========================================================
# 요약/비교 스텝 실행
# =========================================================
def summary_step():
    st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
    ai_say(st.session_state.summary_text)

def comparison_step(is_reroll=False): 
    rec = recommend_products(st.session_state.nickname, st.session_state.memory, is_reroll)
    ai_say(rec)
    
# =========================================================
# 메모리 제어창 (로직 유지)
# =========================================================
def top_memory_panel():
    st.subheader("🧠 현재까지 기억된 나의 쇼핑 기준 (수정 가능)") 
    st.caption("AI가 파악한 기존 취향이 현재 구매 상황과 맞지 않을 경우, 아래에서 수정/삭제하여 추천을 조정할 수 있습니다.")
    with st.container(border=True): 
        if len(st.session_state.memory) == 0:
            st.caption("아직 파악된 정보가 없습니다.")
        else:
            for i, item in enumerate(st.session_state.memory):
                cols = st.columns([6,1])
                with cols[0]:
                    display_text = naturalize_memory(item) 
                    key = f"mem_edit_{i}"
                    new_val = st.text_input(f"메모리 {i+1}", display_text, key=key, label_visibility="collapsed")
                    
                    if new_val != display_text:
                        updated_mem_text = new_val.strip().replace("(가장 중요) ", "").replace(".","")
                        if "이내로 생각하고 있어요" in new_val:
                            updated_mem_text = updated_mem_text
                        elif "디자인/스타일" in new_val:
                              updated_mem_text = "디자인/스타일을 중요시하다" 
                        else:
                              updated_mem_text = updated_mem_text + "다" 
                              
                        if "(가장 중요)" in new_val:
                              updated_mem_text = "(가장 중요) " + updated_mem_text

                        update_memory(i, updated_mem_text)
                        
                        if st.session_state.stage in ("summary", "comparison"):
                            st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
                            ai_say(st.session_state.summary_text)
                        st.rerun()
                with cols[1]:
                    if st.button("삭제", key=f"del_{i}"):
                        delete_memory(i)
                        if st.session_state.stage in ("summary", "comparison"):
                            st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
                            ai_say(st.session_state.summary_text)
                        st.rerun()

        st.markdown("---")
        st.markdown("#### 새로운 기준을 추가하여 AI에게 현재 목표를 알려주세요.")
        new_mem = st.text_input("새 메모리 추가", placeholder="예: 운동용으로 가벼운 제품이 필요해요 / 15만원 이내로 생각해요")
        if st.button("추가"):
            if new_mem.strip():
                add_memory(new_mem.strip(), announce=True)
                if st.session_state.stage in ("summary", "comparison"):
                    st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
                    ai_say(st.session_state.summary_text)
                st.rerun()

# =========================================================
# 채팅 UI
# =========================================================
def chat_interface():
    st.title("🎧 AI 쇼핑 에이전트 실험용")
    st.caption("실험 환경: AI가 파악한 **기준**을 **대화**로 만들며 추천 통제감을 경험하세요.")
    
    top_memory_panel()
    
    if st.session_state.notification_message:
        notification_content = st.session_state.notification_message
        st.session_state.messages.append({"role": "system_notification", "content": notification_content})
        st.session_state.notification_message = "" 

    st.markdown("---") 

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
             with st.chat_message("assistant"):
                st.markdown(msg["content"])
        elif msg["role"] == "system_notification":
             st.info(msg["content"], icon="📝")
        
    if not st.session_state.messages:
        ai_say(
            f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요. "
            "대화를 통해 기준을 기억하며 블루투스 헤드셋을 함께 찾아볼게요. "
            "우선, 어떤 용도로 사용하실 예정인가요?"
        )
        st.rerun() 
            
    
    if st.session_state.stage == "summary":
        summary_message_exists = any("메모리 요약" in m["content"] for m in st.session_state.messages if m["role"]=="assistant")
        
        if not summary_message_exists or st.session_state.just_updated_memory:
            summary_step() 
            st.session_state.just_updated_memory = False
            st.rerun() 
        
        with st.chat_message("assistant"):
            if st.button("🔍 이 기준으로 추천 받기"):
                if extract_budget(st.session_state.memory) is None:
                    ai_say("아직 예산을 여쭤보지 못했어요. 추천을 시작하기 전에 **대략적인 가격대(예: 30만원 이내)**를 말씀해주시겠어요?")
                    st.session_state.stage = "explore"
                    st.rerun() 
                    return
                else:
                    st.session_state.stage = "comparison"
                    comparison_step()
                    st.rerun()

    if st.session_state.stage == "comparison":
        if not any("🎯 추천 제품 3가지" in m["content"] for m in st.session_state.messages if m["role"]=="assistant"):
            comparison_step()

    user_input = st.chat_input("메시지를 입력하세요.")
    if user_input:
        user_say(user_input)
        handle_user_input(user_input)
        
        st.rerun() 

# =========================================================
# 온보딩
# =========================================================
def onboarding():
    st.title("🎧 AI 쇼핑 에이전트 실험용")
    st.caption("실험 시작 전, 본인의 이름(닉네임)을 입력해 주세요.")
    st.markdown("**이름을 적어주세요.**")
    nick = st.text_input("이름 입력", placeholder="예: 홍길동")
    if st.button("다음 단계로"):
        if not nick.strip():
            st.warning("이름을 입력해 주세요.")
            return
        st.session_state.nickname = nick.strip()
        st.session_state.page = "context_setting" 
        st.rerun()

def context_setting():
    st.title("💡 실험 준비: 초기 취향 정보 수집 (2/3단계)")
    st.caption(f"헤드셋 구매에 반영될 {st.session_state.nickname}님의 평소 취향을 파악합니다.")
    
    st.markdown("---")
    
    # 🚨 질문 1: 구매 품목 입력
    st.markdown("#### 1. 최근 3개월 동안 어떤 제품(카테고리)을 구매하셨나요? (하나만 적어주세요)")
    st.caption("예: 옷, 신발, 시계, 태블릿 등")
    purchase_list = st.text_input("최근 구매 품목", placeholder="예: 옷", key="purchase_list_input") 
    
    # 🚨 질문 2: 색상 입력
    st.markdown("#### 2. 그 제품의 선호했던 색상은 무엇인가요? (이 취향이 헤드셋에도 반영됩니다)")
    color_option = st.text_input("선호 색상", placeholder="예: 화이트", key="color_input") 
    
    # 🚨 질문 3: 중요 기준 입력 (라디오 버튼)
    st.markdown("#### 3. 해당 품목을 구매할 때, 다음 중 어떤 점을 가장 중요하게 고려했나요? (최우선 기준)")
    priority_option = st.radio(
        "가장 중요했던 기준",
        ('디자인/스타일', '가격/가성비', '성능/품질', '브랜드 이미지'),
        index=None,
        key="priority_radio"
    )
    
    if st.button("헤드셋 쇼핑 시작 (3/3단계로 이동)"):
        if not purchase_list.strip() or not priority_option or not color_option.strip():
            st.warning("모든 질문에 답해주세요.")
            return
        
        # 🚨 메모리 주입 (자연스러운 문장으로)
        color_mem = f"색상은 {color_option.strip()}을 선호해요."
        
        # 🚨 수정된 부분: get_eul_reul 함수를 사용하여 정확한 목적격 조사 적용
        particle = get_eul_reul(priority_option)
        priority_mem = f"(가장 중요) {priority_option}{particle} 중요시 여겨요."
        
        add_memory(color_mem, announce=False)
        add_memory(priority_mem, announce=False)
        
        st.session_state.messages = [] 
        st.session_state.page = "chat"
        st.rerun()

# =========================================================
# 라우팅
# =========================================================
if st.session_state.page == "onboarding":
    onboarding()
elif st.session_state.page == "context_setting": 
    context_setting()
else:
    chat_interface()
