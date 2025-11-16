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
- 기준을 잘못 기억하면 안 되고, 이미 언급된 내용을 다시 물어보지 않는다.
- 새로운 기준이 등장하면, '메모리에 추가하면 좋겠다'라고 자연스럽게 제안한다.
- 단, 실제 메모리 추가/수정/삭제는 시스템(코드)이 처리하므로, 너는 "내가 메모리에 저장했다"라고 단정적으로 말하지 말고
  "이 기준을 기억해둘게요" 정도로 표현한다.
- 사용자가 모호하게 말하면 부드럽게 구체적으로 다시 물어본다.
- 사용자가 “잘 모르겠어 / 글쎄 / 아직 생각 안 했어”라고 말하면,
  “그렇다면 주로 어떤 상황에서 사용하실 때 중요할까요?”와 같이 사용 상황을 묻는다.

[대화 흐름 규칙]
- 대화 초반에는 사용 용도/상황 → 기능/착용감/배터리/디자인/브랜드/색상 → 예산 순으로 자연스럽게 넓혀 간다.
- 메모리가 3개 이상 모이면, 스스로 “지금까지 기준을 정리해보겠다”고 제안해도 된다.
- 정리 후에는 사용자가 원하거나 버튼이 눌리면, 추천을 제안한다.
- 추천을 요청받으면 추천 이유가 포함된 구조화된 리스트 형태로 말한다.
  (실제 가격/모델 정보는 시스템이 카드 형태로 따로 보여줄 수 있다.)

[메모리 활용]
- 아래에 제공되는 메모리를 기반으로 대화 내용을 유지하라.
- 메모리와 사용자의 최신 발언이 충돌하면, “기존에 ~라고 하셨는데, 기준을 바꾸실까요?”처럼 정중하게 확인 질문을 한다.

[출력 규칙]
- 한 번에 너무 많은 질문을 하지 말고, 자연스럽게 한두 개씩만 묻는다.
- 중복 질문은 피하고, 꼭 필요할 때는 “다시 한 번만 확인할게요”라고 말한다.
- 사용자의 표현을 적당히 따라가되, 전체 톤은 부드러운 존댓말로 유지한다.
"""

# Streamlit Cloud에서는 Secrets에 OPENAI_API_KEY 저장
# 이 코드를 로컬에서 실행할 경우, st.secrets["OPENAI_API_KEY"] 대신
# os.environ.get("OPENAI_API_KEY") 또는 직접 키를 넣어 사용해야 합니다.
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except KeyError:
    st.error("⚠️ Streamlit Secrets에서 OPENAI_API_KEY를 찾을 수 없습니다. 설정 후 다시 실행해 주세요.")
    client = None


# =========================================================
# 세션 상태 초기화
# =========================================================
def ss_init():
    ss = st.session_state
    ss.setdefault("nickname", None)
    ss.setdefault("page", "onboarding")      # onboarding -> chat
    ss.setdefault("stage", "explore")        # explore -> summary -> comparison
    ss.setdefault("messages", [])
    ss.setdefault("memory", [])              # list[str]
    ss.setdefault("summary_text", "")
    ss.setdefault("just_updated_memory", False)
    ss.setdefault("fixed_second_done", False)   # 두 번째 고정 멘트 출력 여부
    ss.setdefault("await_priority_choice", False)  # (필요 시) 최우선 기준 대기
ss_init()

# =========================================================
# 유틸: 메모리 문장 자연화
# =========================================================
def naturalize_memory(text: str) -> str:
    """메모리 문장을 사용자 1인칭 자연어로 다듬기."""
    t = text.strip()
    t = t.replace("노이즈 캔슬링", "노이즈캔슬링")
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
    if not t.endswith(("요.", "다.", "요")):
        if t.endswith("요"):
            t += "."
        else:
            t += " "
    return t

# =========================================================
# 메모리 추출 규칙
# =========================================================
def _clause_split(u: str) -> list[str]:
    repl = re.sub(r"(그리고|랑|및|하고|고|&|·)", ",", u)
    parts = [p.strip() for p in re.split(r"[，,]", repl) if p.strip()]
    return parts if parts else [u.strip()]

def memory_sentences_from_user_text(utter: str):
    """
    사용자 발화에서 복수의 쇼핑 기준/맥락을 추출.
    - 키워드 규칙
    - 스타일/디자인/무게/휴대성 확장
    - '~하면 좋겠어/~가 좋아/~선호/~필요해/~중요해' 패턴 반영
    - 예산/브랜드/색상
    """
    u = utter.strip().replace("  ", " ")
    mems = []

    # 1) 예산
    m = re.search(r"(\d+)\s*만\s*원", u)
    if m:
        price = m.group(1)
        mems.append(f"예산은 약 {price}만 원 이내로 생각하고 있어요.")

    # 2) 브랜드
    brands = ["Sony", "BOSE", "Bose", "JBL", "Apple", "Anker", "Soundcore", "Sennheiser", "AKG"]
    for b in brands:
        if b.lower() in u.lower():
            mems.append(f"{b} 브랜드에 관심이 있어요.")
            break

    # 3) 색상 단답
    single = u.replace("색", "").strip()
    if single in ["블랙", "검정"]:
        mems.append("블랙 색상을 선호하고 있어요.")
    elif single in ["화이트", "하양", "하얀", "화이트색"]:
        mems.append("화이트 색상을 선호하고 있어요.")
    elif single in ["파랑", "파란색", "파랑색", "블루"]:
        mems.append("블루 색상을 선호하고 있어요.")
    elif single in ["그레이", "회색", "스페이스 그레이", "스페이스그레이"]:
        mems.append("그레이 색상을 선호하고 있어요.")

    # 4) 절(clause)별 키워드 규칙
    clauses = _clause_split(u)
    design_keys = [
        "예쁘", "이쁘", "유행", "스타일리시", "스타일리쉬", "깔끔",
        "세련", "쿨하", "귀엽", "멋있", "감성", "디자인"
    ]
    weight_mobility_keys = ["가벼워", "무거워", "가벼운", "들고 다니기 편", "휴대성", "휴대하기 편"]

    for c in clauses:
        base_rules = [
            ("노이즈캔슬링", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("ANC", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("가볍", "가벼운 착용감을 선호하고 있어요."),
            ("무겁지", "가벼운 착용감을 선호하고 있어요."),
            ("무겁다", "가벼운 착용감을 선호하고 있어요."),
            ("착용감", "착용감을 중요하게 생각하고 있어요."),
            ("음질", "음질을 중요하게 생각하고 있어요."),
            ("사운드", "음질을 중요하게 생각하고 있어요."),
            ("통화", "통화 품질도 고려하고 있어요."),
            ("배터리", "배터리 지속시간이 긴 제품을 선호하고 있어요."),
            ("출퇴근", "출퇴근길에 사용할 예정이에요."),
            ("등하교", "등하교/이동 중에 사용할 예정이에요."),
            ("버스", "이동 환경(대중교통)에서 사용할 예정이에요."),
        ]
        matched = False
        for key, sent in base_rules:
            if key in c:
                mems.append(sent)
                matched = True

        if any(k in c for k in design_keys):
            mems.append("디자인/스타일을 중요하게 생각하고 있어요.")
            matched = True

        if any(k in c for k in weight_mobility_keys):
            mems.append("가벼움과 휴대성을 중요하게 생각하고 있어요.")
            matched = True

        if re.search(r"(하면 좋겠|좋겠어|가 좋아|선호|필요해|중요해)", c):
            mems.append(c.strip() + "로 생각하고 있어요.")
            matched = True

    dedup = []
    for m in mems:
        if not any(m in x or x in m for x in dedup):
            dedup.append(m)
    return dedup if dedup else None

# =========================================================
# 메모리 추가/수정/삭제
# =========================================================
def add_memory(mem_text: str, announce=True):
    mem_text = mem_text.strip()
    if not mem_text:
        return
    for m in st.session_state.memory:
        if mem_text in m or m in mem_text:
            return
    st.session_state.memory.append(mem_text)
    st.session_state.just_updated_memory = True
    if announce:
        st.toast("🧩 메모리에 추가했어요. (사이드바에서 수정/삭제 가능)", icon="📝")
        time.sleep(0.2)

def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.just_updated_memory = True
        st.toast("🧹 메모리에서 삭제했어요.", icon="🧽")
        time.sleep(0.2)

def update_memory(idx: int, new_text: str):
    if 0 <= idx < len(st.session_state.memory):
        st.session_state.memory[idx] = new_text.strip()
        st.session_state.just_updated_memory = True
        st.toast("🧩 메모리가 업데이트되었어요.", icon="🔄")
        time.sleep(0.2)

# =========================================================
# 요약 / 추천 로직
# =========================================================
def detect_priority(mem_list):
    # 간단한 우선 기준 감지
    for m in mem_list:
        if "(가장 중요)" in m:
            return m.replace("(가장 중요)", "").strip()
    for key in ["음질", "착용감", "가격", "예산", "노이즈캔슬링", "배터리", "디자인", "스타일"]:
        if any(key in m for m in mem_list):
            if key in ["디자인", "스타일"]:
                return "디자인/스타일"
            if key in ["가격", "예산"]:
                return "가격/예산"
            return key
    return None

def generate_summary(name, mems):
    if not mems:
        return ""
    lines = [f"- {naturalize_memory(m)}" for m in mems]
    prio = detect_priority(mems)
    header = f"[@{name}님의 메모리 요약_지금 나의 쇼핑 기준은?]\n\n"
    if st.session_state.just_updated_memory:
        body = "업데이트된 메모리를 바탕으로 " + name + "님이 중요하게 생각하신 기준을 다시 정리해봤어요:\n\n"
    else:
        body = "지금까지 대화를 바탕으로 " + name + "님이 헤드셋을 고를 때 중요하게 생각하신 기준을 정리해봤어요:\n\n"
    body += "\n".join(lines) + "\n"
    if prio:
        body += f"\n그중에서도 가장 중요한 기준은 **‘{prio}’**이에요.\n"
    tail = (
        "\n제가 정리한 기준이 맞을까요? 사이드바 메모리 제어창에서 언제든 수정할 수 있어요.\n"
        "변경이 없다면 아래 버튼을 눌러 추천을 받아보셔도 좋아요 👇"
    )
    return header + body + tail

CATALOG = [
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
        "tags": ["최상급 착용감", "자연스러운 사운드", "노이즈캔슬링"],
        "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.",
        "color": ["블랙", "화이트"]
    },
    {
        "name": "Sony WH-1000XM5", "brand": "Sony",
        "price": 450000, "rating": 4.8, "reviews": 3200, "rank": 1,
        "tags": ["최상급 노캔", "균형 음질", "플래그십"],
        "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.",
        "color": ["블랙", "화이트"]
    },
    {
        "name": "Apple AirPods Max", "brand": "Apple",
        "price": 679000, "rating": 4.6, "reviews": 1500, "rank": 3,
        "tags": ["프리미엄", "노이즈캔슬링", "디자인"],
        "review_one": "디자인과 브랜드 감성 때문에 만족도가 높아요.",
        "color": ["실버", "스페이스그레이"]
    },
]

def extract_budget(mems):
    for m in mems:
        mm = re.search(r"약\s*([0-9]+)\s*만\s*원\s*이내", m)
        if mm:
            return int(mm.group(1)) * 10000
        mm2 = re.search(r"([0-9]+)\s*만\s*원\s*이내", m)
        if mm2:
            return int(mm2.group(1)) * 10000
    return None

def filter_products(mems):
    mem = " ".join(mems)
    budget = extract_budget(mems)

    def score(c):
        s = c["rating"]
        if "노이즈캔슬링" in mem and "노이즈캔슬링" in " ".join(c["tags"]): s += 1.5
        if ("가벼움" in mem or "가벼운" in mem or "휴대성" in mem) and (("가벼움" in " ".join(c["tags"])) or ("경량" in " ".join(c["tags"]))): s += 1.3
        if ("디자인" in mem or "스타일" in mem) and ("디자인" in " ".join(c["tags"])): s += 1.2
        if "음질" in mem and ("균형" in " ".join(c["tags"]) or "사운드" in " ".join(c["tags"])): s += 0.8
        s += max(0, 10 - c["rank"])
        return s

    cands = CATALOG[:]
    if budget:
        cands = [c for c in cands if c["price"] <= budget * 1.3]
        if not cands:
            cands = CATALOG[:]
    cands.sort(key=score, reverse=True)
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

def recommend_products(name, mems):
    products = filter_products(mems)
    base_reasons = []
    budget = extract_budget(mems)
    if budget:
        base_reasons.append(f"예산 {budget//10000}만 원 이내")
    if any("음질" in x for x in mems):
        base_reasons.append("음질 중시")
    if any("착용감" in x or "가벼움" in x for x in mems):
        base_reasons.append("착용감/무게 중시")
    if any("노이즈캔슬링" in x for x in mems):
        base_reasons.append("노이즈캔슬링 고려")
    header = "🎯 추천 제품 3가지\n\n"
    blocks = []
    for c in products:
        reason = f"추천 이유: **{name}님**의 기준({', '.join(base_reasons)})과 잘 맞아요." if base_reasons else f"추천 이유: 전체 평가와 활용성을 고려했을 때 균형이 좋아요."
        block = (
            f"**{c['name']} ({c['brand']})**\n\n"
            f"- 💰 가격: 약 {c['price']:,}원\n"
            f"- ⭐ 평점: {c['rating']:.1f} (리뷰 {c['reviews']}개)\n"
            f"- 📈 카테고리 판매순위: Top {c['rank']}\n"
            f"- 🗣️ 리뷰 한줄요약: {c['review_one']}\n"
            f"- 🎨 색상 옵션: {', '.join(c['color'])}\n"
            f"- 🏅 특징: {_brief_feature_from_item(c)}\n"
            f"- {reason}"
        )
        blocks.append(block)
    tail = "\n\n궁금한 제품을 골라 물어보셔도 좋고, 기준을 바꾸면 추천도 함께 바뀝니다."
    return header + "\n\n---\n\n".join(blocks) + "\n\n" + tail

# =========================================================
# GPT 호출
# =========================================================
def gpt_reply(user_input: str) -> str:
    if not client:
        return "죄송합니다. OpenAI API 클라이언트 초기화에 문제가 있어 응답을 생성할 수 없습니다."
        
    memory_text = "\n".join(st.session_state.memory)
    prompt = f"""
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
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
    )
    return res.choices[0].message.content

# =========================================================
# 대화 흐름
# =========================================================
ASK_VARIANTS = [
    "좋아요. 그 외에 제가 기억해두면 좋을 조건이 있을까요? (예: 브랜드, 기능, 착용감 등)",
    "혹시 추가로 고려하실 조건이 있을까요? (브랜드/착용감/노이즈캔슬링 등)",
    "다른 기준도 말씀해 주실 수 있을까요? (예: 배터리, 색상, 무게 등)",
    "추가로 꼭 반영하고 싶은 기준이 또 있을까요?"
]

FOLLOW_CONTEXT = [
    "어떤 용도로 사용하실 예정인가요?",
    "사용 상황(이동/실내/운동 등)에서 무엇이 더 중요할까요?",
]

def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})

def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})

def handle_user_input(user_input: str):
    # 1) 메모리 추출 / 추가
    mems = memory_sentences_from_user_text(user_input)
    if mems:
        for m in mems:
            add_memory(m, announce=True)

    # 2) "그만/없어/충분" → 탐색 종료 후 요약 단계로
    if any(k in user_input for k in ["없어", "그만", "끝", "충분"]):
        st.session_state.stage = "summary"

    # 3) 추천 직접 요청 시
    if any(k in user_input for k in ["추천해줘", "추천 해줘", "추천좀", "추천", "골라줘"]):
        st.session_state.stage = "summary"

    # 4) 탐색 단계에서 두 번째 멘트는 고정 출력
    if st.session_state.stage == "explore":
        assistant_count = sum(1 for m in st.session_state.messages if m["role"] == "assistant")
        if (assistant_count == 1) and (not st.session_state.fixed_second_done):
            ai_say("그렇다면 주로 사용하게 될 상황에서는 어떤 점이 더 중요할까요? (예: 외부라면 노이즈캔슬링 등)")
            st.session_state.fixed_second_done = True
            return

    # 5) 탐색 단계에서 메모리가 충분히 모이면 요약 단계로 전환
    if st.session_state.stage == "explore" and len(st.session_state.memory) >= 4:
        st.session_state.stage = "summary"

    # 6) 그 외 일반 대화는 GPT에게 위임
    if st.session_state.stage == "explore":
        reply = gpt_reply(user_input)
        ai_say(reply)
        return

    # 7) 요약 단계에서는 summary_step이 별도로 호출되므로 여기서는 가볍게 응대만
    if st.session_state.stage == "summary":
        ai_say("정리된 기준을 한 번 확인해보시고, 아래 버튼을 눌러 추천을 받아보셔도 좋아요 🙂")
        return

    # 8) 비교 단계에서의 대화 (추가 질문이 있으면 GPT에 넘길 수도 있음)
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

def comparison_step():
    rec = recommend_products(st.session_state.nickname, st.session_state.memory)
    ai_say(rec)

# =========================================================
# 사이드바 메모리 제어창
# =========================================================
def top_memory_panel():
    st.subheader("🧠 현재까지 기억된 메모리 정보 (자유 편집·삭제·추가 가능)")
    if len(st.session_state.memory) == 0:
        st.caption("아직 파악된 정보가 없습니다.")
    else:
        for i, item in enumerate(st.session_state.memory):
            cols = st.columns([6,1])
            with cols[0]:
                key = f"mem_edit_{i}"
                new_val = st.text_input(f"메모리 {i+1}", item, key=key)
                if new_val != item:
                    update_memory(i, new_val)
            with cols[1]:
                if st.button("삭제", key=f"del_{i}"):
                    delete_memory(i)
                    if st.session_state.stage in ("summary", "comparison"):
                        st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
                        ai_say(st.session_state.summary_text)
                    **st.rerun()** # st.experimental_rerun() -> st.rerun() 변경

    new_mem = st.text_input("새 메모리 추가", placeholder="예: 음질이 중요해요 / 블랙 색상을 선호해요")
    if st.button("추가"):
        if new_mem.strip():
            add_memory(new_mem.strip(), announce=True)
            if st.session_state.stage in ("summary", "comparison"):
                st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
                ai_say(st.session_state.summary_text)
            **st.rerun()** # st.experimental_rerun() -> st.rerun() 변경

# =========================================================
# 채팅 UI
# =========================================================
def chat_interface():
    st.title("🎧 AI 쇼핑 에이전트")
    st.caption("실험용 환경 - 대화를 통해 취향을 반영하는 개인형 블루투스 헤드셋 쇼핑 도우미입니다.")

    # 사이드바 메모리 패널
    with st.sidebar:
        top_memory_panel()

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
        # 아직 요약이 없다면 생성
        if not any("메모리 요약" in m["content"] for m in st.session_state.messages if m["role"]=="assistant"):
            summary_step()
        with st.chat_message("assistant"):
            st.markdown(st.session_state.summary_text)
            if st.button("🔍 이 기준으로 추천 받기"):
                st.session_state.stage = "comparison"
                comparison_step()
                **st.rerun()** # st.experimental_rerun() -> st.rerun() 변경

    # 비교 단계에서 추천이 없으면 생성
    if st.session_state.stage == "comparison":
        if not any("🎯 추천 제품 3가지" in m["content"] for m in st.session_state.messages if m["role"]=="assistant"):
            comparison_step()

    # 사용자 입력
    user_input = st.chat_input("메시지를 입력하세요.")
    if user_input:
        user_say(user_input)
        handle_user_input(user_input)
        if st.session_state.just_updated_memory and st.session_state.stage in ("summary", "comparison"):
            st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
            ai_say(st.session_state.summary_text)
            st.session_state.just_updated_memory = False
        # st.experimental_rerun() 호출 제거 (AttributeError 발생 주 원인)

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
        **st.rerun()** # st.experimental_rerun() -> st.rerun() 변경
# =========================================================
# 라우팅
# =========================================================
if st.session_state.page == "onboarding":
    onboarding()
else:
    chat_interface()
