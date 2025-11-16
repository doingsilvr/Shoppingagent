import streamlit as st
import time
import random
import re
from openai import OpenAI

# =========================================================
# 기본 설정
# =========================================================
st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

# =========================================================
# GPT 설정
# =========================================================
SYSTEM_PROMPT = """
너는 'AI 쇼핑 도우미'이며 사용자의 블루투스 헤드셋 기준을 파악해 추천을 돕는 역할을 한다.

[역할 규칙]
- 너는 챗봇이 아니라 '개인 컨시어지' 같은 자연스러운 톤으로 말한다.
- 사용자가 말한 기준은 아래의 [메모리]를 참고해 반영한다.
- 기준을 잘못 기억하면 안 되고, **이미 언급되거나 메모리에 있는 내용은 절대 다시 물어보지 않는다.**
- 새로운 기준이 등장하면, '메모리에 추가하면 좋겠다'라고 자연스럽게 제안한다.
- 단, 실제 메모리 추가/수정/삭제는 시스템(코드)이 처리하므로, 너는 "내가 메모리에 저장했다"라고 단정적으로 말하지 말고
  "이 기준을 기억해둘게요" 정도로 표현한다.
- 사용자가 모호하게 말하면 부드럽게 구체적으로 다시 물어본다.
- 사용자가 “잘 모르겠어 / 글쎄 / 아직 생각 안 했어”라고 말하면,
  “그렇다면 주로 어떤 상황에서 사용하실 때 중요할까요?”와 같이 사용 상황을 묻는다.
- 사용자는 블루투스 '헤드셋(오버이어/온이어)'을 구매하려고 한다. '이어폰' 또는 '인이어' 타입에 대한 질문은 피하라.

[대화 흐름 규칙]
- 대화 초반에는 사용 용도/상황 → 기능/착용감/배터리/디자인/브랜드/색상 → 예산 순으로 자연스럽게 넓혀 간다.
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
    st.error("⚠️ Streamlit Secrets에서 OPENAI_API_KEY를 찾을 수 없습니다. 설정 후 다시 실행해 주세요.")
    client = None

# =========================================================
# 세션 상태 초기화 (🚨 알림 메시지 상태 추가)
# =========================================================
def ss_init():
    ss = st.session_state
    ss.setdefault("nickname", None)
    ss.setdefault("page", "onboarding")       # onboarding -> chat
    ss.setdefault("stage", "explore")         # explore -> summary -> comparison -> product_detail
    ss.setdefault("messages", [])
    ss.setdefault("memory", [])               # list[str]
    ss.setdefault("summary_text", "")
    ss.setdefault("just_updated_memory", False)
    ss.setdefault("fixed_second_done", False)
    ss.setdefault("await_priority_choice", False)
    ss.setdefault("recommended_products", []) # 이전에 추천했던 상품 이름 기록
    ss.setdefault("current_recommendation", []) # 현재 화면에 표시된 추천 상품 목록 저장
    ss.setdefault("notification_message", "") # 🚨 추가: 커스텀 알림 메시지
ss_init()

# =========================================================
# 유틸: 메모리 문장 자연화 (변경 없음)
# =========================================================
def naturalize_memory(text: str) -> str:
    """메모리 문장을 사용자 1인칭 자연어로 다듬기."""
    t = text.strip()
    t = t.replace("노이즈 캔슬링", "노이즈캔슬링")
    
    # 최우선 기준 표시 유지
    is_priority = "(가장 중요)" in t
    t = t.replace("(가장 중요)", "").strip()

    # 이전에 잘못 저장된 메모리 표준화
    if "예쁘면 좋겠어로 생각하고 있어요" in t or "예쁘면 좋겠어" in t:
        t = "디자인/스타일을 중요하게 생각하고 있어요."
        
    # 일반적인 문장 완성 로직
    if t.endswith(("다", "다.")):
        t = t.rstrip(".")
        if any(kw in t for kw in ["중요", "중시", "중요시", "우선"]):
            t = t + "고 있어요."
        elif "이내" in t or "이상" in t or "정도" in t:
            t = t + "로 생각하고 있어요."
        else:
            t = t + "이에요."
    t = t.replace("생각한고", "생각하고")
    t = t.replace("이내다", "이내로 생각하고 있어요")
    
    # Fix for generic suffixing
    if not t.endswith(("요.", "다.", "요")):
        if t.endswith("요"):
            t += "."
        else:
            t += " "
            
    if is_priority:
        t = "(가장 중요) " + t

    return t

# =========================================================
# 메모리 추출 규칙 (변경 없음)
# =========================================================
def _clause_split(u: str) -> list[str]:
    # 다양한 접속사(및, 하고, 고, & 등)를 쉼표로 변환하여 복수의 기준을 분리
    repl = re.sub(r"(그리고|랑|및|하고|고|&|·)", ",", u)
    parts = [p.strip() for p in re.split(r"[，,]", repl) if p.strip()]
    return parts if parts else [u.strip()]

def memory_sentences_from_user_text(utter: str):
    """사용자 발화에서 복수의 쇼핑 기준/맥락을 추출."""
    u = utter.strip().replace("  ", " ")
    mems = []

    # 단답형 응답은 메모리 추출을 건너뛰어 불필요한 메모리 기입을 방지
    if len(u) <= 3 and u in ["응", "네", "예", "아니", "둘다", "둘 다", "맞아", "맞아요", "ㅇㅇ", "o", "x"]:
         return None
         
    # 최우선 기준 감지
    is_priority_clause = False
    if re.search(r"(가장|제일|최우선|젤)\s*(중요|우선)", u):
        is_priority_clause = True
        # 기존 최우선 기준 제거
        for i, m in enumerate(st.session_state.memory):
            st.session_state.memory[i] = m.replace("(가장 중요)", "").strip()
            
    # 1) 예산
    m = re.search(r"(\d+)\s*만\s*원", u) 
    if m:
        price = m.group(1)
        # 이미 예산 메모리가 있다면 기존 것을 삭제하고 새로운 것으로 업데이트
        st.session_state.memory = [mem for mem in st.session_state.memory if "예산" not in mem]
        
        mem = f"예산은 약 {price}만 원 이내로 생각하고 있어요."
        mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)

    # 2) 브랜드 (생략)
    # 3) 색상 단답 (생략)
    
    # 4) 절(clause)별 키워드 규칙
    clauses = _clause_split(u)
    
    for c in clauses:
        base_rules = [
            ("노이즈캔슬링", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("ANC", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("소음 차단", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("소음차단", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("외부 소음", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("시끄럽지 않게", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("조용해", "노이즈캔슬링 기능을 고려하고 있어요."),
            
            ("예쁘면", "디자인/스타일을 중요하게 생각하고 있어요."),
            ("예쁜", "디자인/스타일을 중요하게 생각하고 있어요."),
            ("디자인", "디자인/스타일을 중요하게 생각하고 있어요."),
            ("스타일", "디자인/스타일을 중요하게 생각하고 있어요."),
            
            ("가벼운", "가벼운 착용감을 선호하고 있어요."),
            ("가볍", "가벼운 착용감을 선호하고 있어요."),
            ("착용감", "착용감을 중요하게 생각하고 있어요."),
            
            # 컬러 키워드
            ("하얀색", "색상은 흰색/화이트 계열을 선호하고 있어요."),
            ("흰색", "색상은 흰색/화이트 계열을 선호하고 있어요."),
            ("화이트", "색상은 흰색/화이트 계열을 선호하고 있어요."),
            ("블랙", "색상은 검은색/블랙 계열을 선호하고 있어요."),
            ("검은색", "색상은 검은색/블랙 계열을 선호하고 있어요."),
            ("검정", "색상은 검은색/블랙 계열을 선호하고 있어요."),
            ("네이비", "색상은 네이비 계열을 선호하고 있어요."),
            ("파란색", "색상은 파란색 계열을 선호하고 있어요."),
            ("실버", "색상은 실버 계열을 선호하고 있어요."),
            ("은색", "색상은 실버 계열을 선호하고 있어요."),
            
            # 기타
            ("음질", "음질을 중요하게 생각하고 있어요."),
            ("배터리", "배터리 지속시간이 긴 제품을 선호하고 있어요."),
            ("출퇴근", "출퇴근길에 사용할 예정이에요."),
            ("운동", "주로 러닝/운동 용도로 사용할 예정이에요."),
            ("게임", "주로 게임 용도로 사용할 예정이며, 이 점을 중요하게 생각하고 있어요."),
        ]
        
        matched = False
        for key, sent in base_rules:
            if key in c:
                mem = sent
                mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)
                matched = True
                break
        
        # 명시적 규칙에 걸리지 않고 "~좋겠어/~필요해" 패턴에 걸리는 경우만 처리
        if re.search(r"(하면 좋겠|좋겠어|가 좋아|선호|필요해|중요해)", c) and not matched:
            if len(c.strip()) > 3 and not any(k in c for k in ["예쁘면", "디자인", "스타일"]): 
                mem = c.strip() + "로 생각하고 있어요."
                mems.append(f"(가장 중요) {mem}" if is_priority_clause else mem)
            matched = True

    # 중복 제거 및 최종 정리
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
# 메모리 추가/수정/삭제 (🚨 st.toast -> st.session_state.notification_message)
# =========================================================
def add_memory(mem_text: str, announce=True):
    mem_text = mem_text.strip()
    if not mem_text:
        return
        
    mem_text_stripped = mem_text.replace('(가장 중요)', '').strip()
    
    # 예산은 기존 메모리를 덮어쓰도록 처리
    if "예산은 약" in mem_text_stripped and "이내로 생각하고 있어요" in mem_text_stripped:
         st.session_state.memory = [m for m in st.session_state.memory if "예산은 약" not in m]

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
        st.rerun() 

def update_memory(idx: int, new_text: str):
    if 0 <= idx < len(st.session_state.memory):
        if '(가장 중요)' in new_text:
            for i, existing_m in enumerate(st.session_state.memory):
                st.session_state.memory[i] = existing_m.replace('(가장 중요)', '').strip()
            
        st.session_state.memory[idx] = new_text.strip()
        st.session_state.just_updated_memory = True
        st.session_state.notification_message = "🔄 메모리가 업데이트되었어요."

# =========================================================
# 요약 / 추천 로직 (변경 없음)
# =========================================================
def extract_budget(mems):
    # 가격대 메모리가 설정되었는지 확인
    for m in mems:
        mm = re.search(r"약\s*([0-9]+)\s*万\s*원\s*이내", m)
        if mm:
            return int(mm.group(1)) * 10000
        mm2 = re.search(r"([0-9]+)\s*万\s*원\s*이내", m)
        if mm2:
            return int(mm2.group(1)) * 10000
    return None

def detect_priority(mem_list):
    for m in mem_list:
        if "(가장 중요)" in m:
            m = m.replace("(가장 중요)", "").strip()
            for key in ["음질", "착용감", "가격", "예산", "노이즈캔슬링", "배터리", "디자인", "스타일"]:
                if key in m:
                    if key in ["디자인", "스타일"]:
                        return "디자인/스타일"
                    if key in ["가격", "예산"]:
                        return "가격/예산"
                    return key
            return m
    return None

def generate_summary(name, mems):
    if not mems:
        return ""
    
    # 메모리 자연화 적용
    naturalized_mems = [naturalize_memory(m) for m in mems]
    
    lines = [f"- {m}" for m in naturalized_mems]
    prio = detect_priority(mems)
    header = f"[@{name}님의 메모리 요약_지금 나의 쇼핑 기준은?]\n\n"
    if st.session_state.just_updated_memory:
        body = "업데이트된 메모리를 바탕으로 " + name + "님이 중요하게 생각하신 기준을 다시 정리해봤어요:\n\n"
    else:
        body = "지금까지 대화를 바탕으로 " + name + "님이 헤드셋을 고를 때 중요하게 생각하신 기준을 정리해봤어요:\n\n"
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
    # 6개 원본 상품
    {
        "name": "Anker Soundcore Q45", "brand": "Anker",
        "price": 179000, "rating": 4.4, "reviews": 1600, "rank": 8,
        "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"],
        "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.",
        "color": ["블랙", "네이비"]
    },
    {
        "name": "JBL Tune 770NC", "brand": "JBL",
        "price": 129000, "rating": 4.4, "reviews": 2300, "rank": 9,
        "tags": ["가벼움", "균형형 음질", "노이즈캔슬링"],
        "review_one": "가볍고 음색이 밝다는 평이 많아요.",
        "color": ["블랙", "화이트"]
    },
    {
        "name": "Sony WH-CH720N", "brand": "Sony",
        "price": 169000, "rating": 4.5, "reviews": 2100, "rank": 6,
        "tags": ["노이즈캔슬링", "경량", "무난한 음질"],
        "review_one": "경량이라 출퇴근용으로 좋다는 후기가 많아요.",
        "color": ["블랙", "화이트", "블루"]
    },
    {
        "name": "Bose QC45", "brand": "Bose",
        "price": 420000, "rating": 4.7, "reviews": 2800, "rank": 2,
        "tags": ["최상급 착용감", "자연스러운 사운드", "노이즈캔슬링", "편안함"],
        "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.",
        "color": ["블랙", "화이트"]
    },
    {
        "name": "Sony WH-1000XM5", "brand": "Sony",
        "price": 450000, "rating": 4.8, "reviews": 3200, "rank": 1,
        "tags": ["최상급 노캔", "균형 음질", "플래그십", "통화품질"],
        "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.",
        "color": ["블랙", "화이트"]
    },
    {
        "name": "Apple AirPods Max", "brand": "Apple",
        "price": 679000, "rating": 4.6, "reviews": 1500, "rank": 3,
        "tags": ["프리미엄", "노이즈캔슬링", "디자인", "고급"],
        "review_one": "디자인과 브랜드 감성 때문에 만족도가 높아요.",
        "color": ["실버", "스페이스그레이"]
    },
    # 6개 추가 상품
    {
        "name": "Sennheiser PXC 550-II", "brand": "Sennheiser",
        "price": 289000, "rating": 4.3, "reviews": 1200, "rank": 7,
        "tags": ["착용감", "여행", "배터리", "노이즈캔슬링"],
        "review_one": "여행 시 장시간 착용에도 압박감이 덜해요.",
        "color": ["블랙"]
    },
    {
        "name": "AKG Y600NC", "brand": "AKG",
        "price": 149000, "rating": 4.2, "reviews": 1800, "rank": 10,
        "tags": ["균형 음질", "가성비", "노이즈캔슬링"],
        "review_one": "가격대비 깔끔하고 균형 잡힌 사운드가 좋아요.",
        "color": ["블랙", "골드"]
    },
    {
        "name": "Microsoft Surface Headphones 2", "brand": "Microsoft",
        "price": 319000, "rating": 4.5, "reviews": 900, "rank": 11,
        "tags": ["업무", "통화품질", "디자인", "노이즈캔슬링"],
        "review_one": "업무용으로 완벽하며 통화 품질이 매우 깨끗합니다.",
        "color": ["라이트 그레이", "매트 블랙"]
    },
    {
        "name": "Bose Noise Cancelling Headphones 700", "brand": "Bose",
        "price": 490000, "rating": 4.7, "reviews": 2500, "rank": 4,
        "tags": ["최상급 노캔", "통화품질", "프리미엄"],
        "review_one": "노이즈캔슬링 성능과 스타일을 모두 갖춘 제품.",
        "color": ["블랙", "실버"]
    },
    {
        "name": "Audio-Technica M50xBT2", "brand": "Audio-Technica",
        "price": 249000, "rating": 4.6, "reviews": 1100, "rank": 5,
        "tags": ["스튜디오", "음질", "밸런스", "디자인"],
        "review_one": "음악 감상용으로 정교하고 명료한 사운드가 일품.",
        "color": ["블랙"]
    },
    {
        "name": "Jabra Elite 85h", "brand": "Jabra",
        "price": 219000, "rating": 4.3, "reviews": 1400, "rank": 12,
        "tags": ["배터리", "내구성", "방수", "통화품질"],
        "review_one": "배터리가 오래가고 튼튼해서 막 쓰기 좋아요.",
        "color": ["티타늄 블랙", "네이비"]
    },
]


def filter_products(mems, is_reroll=False):
    mem = " ".join(mems)
    budget = extract_budget(mems)
    
    # 이전에 추천된 상품 제외/감점 로직
    previously_recommended_names = [p['name'] for p in st.session_state.recommended_products]

    def score(c):
        s = c["rating"]
        if "노이즈캔슬링" in mem and "노이즈캔슬링" in " ".join(c["tags"]): s += 1.5
        if ("가벼움" in mem or "가벼운" in mem or "휴대성" in mem) and (("가벼움" in " ".join(c["tags"])) or ("경량" in " ".join(c["tags"]))): s += 1.3
        if ("디자인" in mem or "스타일" in mem) and ("디자인" in " ".join(c["tags"])): s += 1.2
        if "음질" in mem and ("균형" in " ".join(c["tags"]) or "사운드" in " ".join(c["tags"])): s += 0.8
        
        # 운동용도 가점
        if ("러닝" in mem or "운동" in mem) and (("가벼움" in " ".join(c["tags"])) or ("경량" in " ".join(c["tags"]))): s += 1.0
        
        s += max(0, 10 - c["rank"])
        
        if c['name'] in previously_recommended_names:
            if is_reroll: 
                s -= 10.0 # 재추천 요청 시 -10점으로 거의 제외
            else:
                s -= 5.0
        return s

    cands = CATALOG[:]
    if budget:
        cands_strict = [c for c in cands if c["price"] <= budget] 

        if not cands_strict:
            cands = [c for c in CATALOG if c["price"] <= budget * 1.2] 
            if not cands:
                 cands = CATALOG[:] 
            else:
                 cands = cands_strict
        else:
            cands = cands_strict 
        
    cands.sort(key=score, reverse=True)
    
    current_recs = cands[:3]
    st.session_state.current_recommendation = current_recs
    
    for p in current_recs:
        if p['name'] not in previously_recommended_names:
            st.session_state.recommended_products.append(p)
            
    return current_recs

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
    base_reasons = []
    budget = extract_budget(mems)
    
    # 모든 관련 기준을 base_reasons에 포함
    if budget:
        base_reasons.append(f"예산 {budget//10000}만 원 이내")
    if any("음질" in x for x in mems):
        base_reasons.append("음질 중시")
    if any("착용감" in x or "가벼움" in x for x in mems):
        base_reasons.append("착용감/무게 중시")
    if any("노이즈캔슬링" in x for x in mems):
        base_reasons.append("노이즈캔슬링 고려")
    if any("러닝/운동" in x for x in mems): 
        base_reasons.append("운동 용도 고려")
    if any("배터리" in x for x in mems): 
        base_reasons.append("배터리 지속 시간 중시")
    if any("디자인/스타일" in x for x in mems) or any("예쁘면" in x for x in mems): 
        base_reasons.append("디자인/스타일 고려")
        
    header = "🎯 추천 제품 3가지\n\n"
    
    blocks = []
    for i, c in enumerate(products):
        reason = f"추천 이유: **{name}님**의 기준({', '.join(base_reasons)})과 잘 맞아요." if base_reasons else f"추천 이유: 전체 평가와 활용성을 고려했을 때 균형이 좋아요."
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

# =========================================================
# GPT 호출 (변경 없음)
# =========================================================
def get_product_detail_prompt(product, user_input, memory_text, nickname):
    """상품 상세 정보를 포함한 GPT 프롬프트 생성"""
    
    detail = (
        f"--- 상품 상세 정보 ---\n"
        f"제품명: {product['name']} ({product['brand']})\n"
        f"가격: {product['price']:,}원\n"
        f"평점: {product['rating']} (리뷰 {product['reviews']}개)\n"
        f"특징 태그: {', '.join(product['tags'])}\n"
        f"리뷰 요약: {product['review_one']}\n"
        f"----------------------\n"
    )
    
    # 시뮬레이션 기반 설득 톤 가이드
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
        return "죄송합니다. OpenAI API 클라이언트 초기화에 문제가 있어 응답을 생성할 수 없습니다."
        
    memory_text = "\n".join(st.session_state.memory)
    nickname = st.session_state.nickname
    
    # 상품 상세 질문인 경우
    if st.session_state.stage == "product_detail":
        if st.session_state.current_recommendation:
            product = st.session_state.current_recommendation[0]
            prompt_content = get_product_detail_prompt(product, user_input, memory_text, nickname)
        else:
            prompt_content = f"현재 메모리: {memory_text}\n사용자 발화: {user_input}\n 이전에 선택된 상품이 없습니다. 일반적인 대화를 이어가주세요."
            st.session_state.stage = "explore" # 상품 정보가 없으면 탐색으로 복귀
    else:
        # 일반 탐색 단계 프롬프트
        stage_hint = ""
        # 디자인 기준이 있으면 색상/스타일 질문 유도
        is_design_in_memory = any("디자인/스타일" in m for m in st.session_state.memory)
        is_color_in_memory = any("색상" in m for m in st.session_state.memory)
        if st.session_state.stage == "explore":
            if is_design_in_memory and not is_color_in_memory:
                 stage_hint += "디자인 기준이 파악되었으므로, 다음 질문은 선호하는 색상이나 구체적인 스타일(레트로, 미니멀 등)에 대한 질문으로 전환되도록 유도하세요. "
            
            # 메모리가 4개 이상 모였고, 예산이 없으면 예산 질문 강제
            if len(st.session_state.memory) >= 4 and extract_budget(st.session_state.memory) is None and not any(k in user_input for k in ["예산", "가격", "얼마"]):
                 stage_hint = "현재 많은 기준이 모였습니다. 이제 **예산/가격대**만 확인되면 추천으로 넘어갈 수 있습니다. 마지막으로 '몇 만 원 이내'와 같이 예산을 여쭤봐주세요."

            elif len(st.session_state.memory) >= 3:
                stage_hint += "현재 메모리가 3개 이상 모였습니다. 시스템 프롬프트의 [대화 흐름 규칙]에 따라 용도/상황이 파악되었다고 판단되면 다음 단계(기능, 착용감, 디자인 등)로 질문을 넘겨주세요. 재질문은 피하세요."
        
        prompt_content = f"""
{stage_hint}

[메모리]
{memory_text if memory_text else "현재까지 저장된 메모리는 없습니다."}

[사용자 발화]
{user_input}

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
# 대화 흐름 (변경 없음)
# =========================================================
def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})

def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})

def handle_user_input(user_input: str):
    
    # 🚨 알림 메시지 초기화
    st.session_state.notification_message = ""
    
    # 특정 상품 번호 선택 감지
    product_re = re.search(r"([1-3]|첫\s*번|두\s*번|세\s*번).*(궁금|골라|선택)", user_input)
    if product_re and st.session_state.stage == "comparison":
        match = product_re.group(1).lower()
        if '첫' in match or '1' in match:
            idx = 0
        elif '두' in match or '2' in match:
            idx = 1
        elif '세' in match or '3' in match:
            idx = 2
        else:
            idx = -1
        
        if idx >= 0 and idx < len(st.session_state.current_recommendation):
            st.session_state.current_recommendation = [st.session_state.current_recommendation[idx]]
            st.session_state.stage = "product_detail"
            reply = gpt_reply(user_input)
            ai_say(reply)
            return
        else:
             ai_say("죄송해요, 해당 번호의 제품은 추천 목록에 없습니다. 1번부터 3번 중 다시 선택해 주시겠어요?")
             return
    
    # '다시 추천해줘' 요청 감지
    if any(k in user_input for k in ["다시 추천", "다른 상품"]):
        # 🚨 PRICE CHECK: 재추천 요청 시에도 예산 체크
        if extract_budget(st.session_state.memory) is None:
            mems = memory_sentences_from_user_text(user_input)
            if mems:
                for m in mems:
                    add_memory(m, announce=True)

            if extract_budget(st.session_state.memory) is None:
                ai_say("추천을 다시 받기 전에 **예산/가격대**를 먼저 알려주시겠어요? '몇 만 원 이내'로 생각하고 계신지 말씀해주시면 됩니다.")
                st.session_state.stage = "explore"
                return
        
        # 1. 메모리 추출/추가 먼저 실행
        mems = memory_sentences_from_user_text(user_input)
        if mems:
            for m in mems:
                add_memory(m, announce=True)

        # 2. 강제 재추천 실행
        st.session_state.stage = "comparison"
        comparison_step(is_reroll=True) 
        st.rerun()
        return

    # 1) 메모리 추출 / 추가 
    mems = memory_sentences_from_user_text(user_input)
    if mems:
        for m in mems:
            add_memory(m, announce=True)

    # 3) 추천 직접 요청 시 (🚨 PRICE CHECK: 예산이 없으면 추천 진입 차단)
    if any(k in user_input for k in ["추천해줘", "추천 해줘", "추천좀", "추천", "골라줘"]):
        if extract_budget(st.session_state.memory) is None:
             ai_say("잠시만요! 추천으로 넘어가기 전에 **예산/가격대**를 먼저 여쭤봐도 될까요? 대략 '몇 만 원 이내'로 생각하고 계신지 알려주시면 딱 맞는 제품을 찾아드릴 수 있어요.")
             st.session_state.stage = "explore" 
             return
        else:
            st.session_state.stage = "summary"
            st.rerun()
            return

    # 2) "그만/없어/충분" → 탐색 종료 후 요약 단계로
    if any(k in user_input for k in ["없어", "그만", "끝", "충분"]):
        # 🚨 PRICE CHECK: 예산이 없으면 예산 질문으로 대체
        if extract_budget(st.session_state.memory) is None:
             ai_say("추천을 받기 전에 **예산/가격대**만 확인하고 싶어요! 대략 '몇 만 원 이내'로 생각하시나요?")
             st.session_state.stage = "explore" 
             return
        else:
            st.session_state.stage = "summary"
            st.rerun()
            return


    # 4) 탐색 단계에서 메모리가 충분히 모이면 요약 단계로 전환
    if st.session_state.stage == "explore" and len(st.session_state.memory) >= 4 and extract_budget(st.session_state.memory) is not None:
        st.session_state.stage = "summary"
        st.rerun()
        return

    # 5) 그 외 일반 대화는 GPT에게 위임
    if st.session_state.stage == "explore" or st.session_state.stage == "product_detail":
        reply = gpt_reply(user_input)
        ai_say(reply)
        return

    # 6) 요약 단계에서는 summary_step이 별도로 호출되므로 여기서는 가볍게 응대만
    if st.session_state.stage == "summary":
        ai_say("정리된 기준을 한 번 확인해보시고, 아래 버튼을 눌러 추천을 받아보셔도 좋아요 🙂")
        return

    # 7) 비교 단계에서의 대화 (상품 번호가 아닌 다른 일반 질문)
    if st.session_state.stage == "comparison":
        reply = gpt_reply(user_input)
        ai_say(reply)
        return

# =========================================================
# 요약/비교 스텝 실행 (변경 없음)
# =========================================================
def summary_step():
    st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
    ai_say(st.session_state.summary_text)

def comparison_step(is_reroll=False): 
    rec = recommend_products(st.session_state.nickname, st.session_state.memory, is_reroll)
    ai_say(rec)

# =========================================================
# 메모리 제어창을 메인 화면 상단에 배치 (🚨 고정 배치)
# =========================================================
def top_memory_panel():
    st.subheader("🧠 현재까지 기억된 나의 쇼핑 기준") 
    st.caption("아래에서 기준을 확인하고 필요하면 수정/삭제할 수 있습니다.")
    # 🚨 st.expander 대신 st.container를 사용하여 항상 보이도록 고정
    with st.container(border=True): 
        if len(st.session_state.memory) == 0:
            st.caption("아직 파악된 정보가 없습니다.")
        else:
            for i, item in enumerate(st.session_state.memory):
                cols = st.columns([6,1])
                with cols[0]:
                    # 메모리 텍스트를 naturalize_memory를 통해 한 번 다듬어 보여줌
                    display_text = naturalize_memory(item) 
                    key = f"mem_edit_{i}"
                    # label_visibility="collapsed"로 레이블 숨김
                    new_val = st.text_input(f"메모리 {i+1}", display_text, key=key, label_visibility="collapsed")
                    
                    # 사용자가 수정한 경우, 원래 저장된 메모리를 업데이트
                    if new_val != display_text:
                        # '자연화'된 메모리를 '저장' 형식으로 되돌려 저장
                        if "디자인/스타일" in new_val:
                             update_memory(i, new_val.replace("중요하게 생각하고 있어요.", "디자인/스타일을 중요시하다"))
                        elif "이내로 생각하고 있어요" in new_val:
                             update_memory(i, new_val)
                        else:
                             update_memory(i, new_val.replace("고 있어요.", "다.")) 
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
        new_mem = st.text_input("새 메모리 추가", placeholder="예: 음질이 중요해요 / 블랙 색상을 선호해요")
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
    st.title("🎧 AI 쇼핑 에이전트")
    st.caption("실험용 환경 - 대화를 통해 취향을 반영하는 개인형 블루투스 헤드셋 쇼핑 도우미입니다.")
    
    # 상단에 메모리 패널 배치
    top_memory_panel()
    
    # 🚨 커스텀 알림 메시지 표시
    if st.session_state.notification_message:
        st.info(st.session_state.notification_message, icon="📝")

    st.markdown("---") # 메모리와 채팅 영역 구분

    # 첫 인사
    if not st.session_state.messages:
        ai_say(
            f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요. "
            "대화를 통해 기준을 기억하며 블루투스 헤드셋을 함께 찾아볼게요. "
            "우선, 어떤 용도로 사용하실 예정인가요?"
        )

    # 메시지 렌더링
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 요약 단계 진입 시 요약 + 버튼
    if st.session_state.stage == "summary":
        summary_message_exists = any("메모리 요약" in m["content"] for m in st.session_state.messages if m["role"]=="assistant")
        
        # 🚨 FIX: 요약 메시지가 없거나, 메모리가 방금 업데이트된 경우에만 요약을 출력하고 플래그를 내립니다.
        if not summary_message_exists or st.session_state.just_updated_memory:
            summary_step() 
            st.session_state.just_updated_memory = False
            st.rerun() 
        
        with st.chat_message("assistant"):
            if st.button("🔍 이 기준으로 추천 받기"):
                # 🚨 PRICE CHECK: 버튼 클릭 시 예산 확인
                if extract_budget(st.session_state.memory) is None:
                    ai_say("아직 예산을 여쭤보지 못했어요. 추천을 시작하기 전에 **대략적인 가격대(예: 30만원 이내)**를 말씀해주시겠어요?")
                    st.session_state.stage = "explore"
                    st.rerun() 
                    return
                else:
                    st.session_state.stage = "comparison"
                    comparison_step()
                    st.rerun()

    # 비교 단계에서 추천이 없으면 생성
    if st.session_state.stage == "comparison":
        if not any("🎯 추천 제품 3가지" in m["content"] for m in st.session_state.messages if m["role"]=="assistant"):
            comparison_step()

    # 사용자 입력
    user_input = st.chat_input("메시지를 입력하세요.")
    if user_input:
        user_say(user_input)
        handle_user_input(user_input)
        
        st.rerun() 

# =========================================================
# 온보딩
# =========================================================
def onboarding():
    st.title("🎧 AI 쇼핑 에이전트")
    st.caption("실험용 환경 - 대화를 통해 취향을 반영하는 개인형 에이전트로, 블루투스 헤드셋 추천을 도와드려요.")
    st.markdown("**이름을 적어주세요. 단, 설문 응답 칸에도 동일하게 적어주셔야 보상을 받을 수 있습니다.** *(성 포함/띄어쓰기 주의)*")
    nick = st.text_input("이름 입력", placeholder="예: 홍길동")
    if st.button("시작하기"):
        if not nick.strip():
            st.warning("이름을 입력해 주세요.")
            return
        st.session_state.nickname = nick.strip()
        st.session_state.page = "chat"
        st.rerun()
# =========================================================
# 라우팅
# =========================================================
if st.session_state.page == "onboarding":
    onboarding()
else:
    chat_interface()
