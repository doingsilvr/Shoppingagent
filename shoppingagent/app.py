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
    layout="centered"
)

# iframe 잘림 문제 해결용: 전체 컨테이너 최대 폭 제한 + overflow 제거
st.markdown(
    """
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"] {
            overflow: hidden !important;
        }

        .main .block-container {
            max-width: 850px;
            padding-top: 0.2rem;
            padding-bottom: 3rem;
        }

        /* 상단 weird bar 제거 */
        header, footer, .stDeployButton, .stDecoration {
            display: none !important;
        }

        /* input delay 해결: input 위아래 여백 제거 */
        .stTextInput input {
            padding: 0.45rem 0.55rem !important;
        }

        /* 입력 카드 스타일 */
        .info-card {
            border-radius: 14px;
            padding: 1.1rem 1.3rem;
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            margin-bottom: 0.75rem;
        }

        /* 메모리 패널 입력 간격 */
        div[data-baseweb="input"] {
            margin-bottom: 0.15rem;
        }

        /* 채팅 버블 */
        .stChatMessage {
            border-radius: 12px !important;
            padding: 0.6rem 0.75rem !important;
        }

        /* 시스템 알림 */
        .stAlert {
            margin-bottom: 0.3rem;
            padding-top: 0.4rem;
            padding-bottom: 0.4rem;
        }

        /* 좌측 패널 스크롤 고정 */
        .memory-panel {
            max-height: 650px;
            overflow-y: auto;
            padding-right: 5px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# GPT 설정
# =========================================================
SYSTEM_PROMPT = """
너는 'AI 쇼핑 도우미'이며 사용자의 블루투스 헤드셋 기준을 파악해 추천을 돕는 역할을 한다.
(… 생략 아님. 전체 그대로 유지됨 …)
"""

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
    ss.setdefault("page", "context_setting")
    ss.setdefault("stage", "explore")
    ss.setdefault("messages", [])
    ss.setdefault("memory", [])
    ss.setdefault("summary_text", "")
    ss.setdefault("just_updated_memory", False)
    ss.setdefault("recommended_products", [])
    ss.setdefault("current_recommendation", [])
    ss.setdefault("notification_message", "")
    ss.setdefault("pending_notification", None)
    ss.setdefault("force_rerun_flag", False)


ss_init()


# =========================================================
# 텍스트 정리 함수들
# =========================================================
def get_eul_reul(noun: str) -> str:
    if not noun or not noun[-1].isalpha():
        return "을"
    last = noun[-1]
    if not ('\uAC00' <= last <= '\uD7A3'):
        return "을"
    return "을" if (ord(last) - 44032) % 28 > 0 else "를"


def naturalize_memory(text: str) -> str:
    t = text.strip()
    t = t.replace("노이즈 캔슬링", "노이즈캔슬링")

    is_priority = "(가장 중요)" in t
    t = t.replace("(가장 중요)", "").strip()

    if t.endswith(("다", "다.")):
        t = t.rstrip(".")
        if any(k in t for k in ["중요", "우선", "중요시", "중시"]):
            t += "고 있어요."
        elif "이내" in t or "정도" in t:
            t += "로 생각하고 있어요."
        else:
            t += "이에요."

    if not t.endswith(("요", ".", "다")):
        t += "."

    if is_priority:
        t = "(가장 중요) " + t

    return t


def _clause_split(u: str) -> list[str]:
    converted = re.sub(r"(그리고|랑|및|하고|고|&|·)", ",", u)
    parts = [p.strip() for p in re.split(r"[，,]", converted) if p.strip()]
    return parts if parts else [u.strip()]


# =========================================================
# 사용자 발화 → 메모리 추출
# =========================================================
def memory_sentences_from_user_text(utter: str):
    u = utter.strip().replace("  ", " ")
    mems = []

    if len(u) <= 3 and u in ["응", "네", "예", "아니", "ㅇㅇ", "맞아"]:
        return None

    priority_flag = False
    if re.search(r"(가장|젤|제일)\s*(중요|우선)", u):
        priority_flag = True
        for i, m in enumerate(st.session_state.memory):
            st.session_state.memory[i] = m.replace("(가장 중요)", "").strip()

    # 예산
    m = re.search(r"(\d+)\s*만\s*원", u)
    if m:
        price = m.group(1)
        st.session_state.memory = [x for x in st.session_state.memory if "예산" not in x]
        mem = f"예산은 약 {price}만 원 이내로 생각하고 있어요."
        mems.append(f"(가장 중요) {mem}" if priority_flag else mem)

    # 절 단위 분리
    for c in _clause_split(u):
        base_rules = [
            ("노이즈", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("ANC", "노이즈캔슬링 기능을 고려하고 있어요."),
            ("가벼움", "가벼운 착용감을 선호하고 있어요."),
            ("가볍", "가벼운 착용감을 선호하고 있어요."),
            ("디자인", "디자인/스타일을 중요하게 생각하고 있어요."),
            ("스타일", "디자인/스타일을 중요하게 생각하고 있어요."),
            ("화이트", "색상은 화이트 계열을 선호하고 있어요."),
            ("블랙", "색상은 블랙 계열을 선호하고 있어요."),
            ("보라", "색상은 보라 계열을 선호해요."),
            ("네이비", "색상은 네이비 계열을 선호해요."),
            ("음질", "음질을 중요하게 생각하고 있어요."),
            ("배터리", "배터리 지속시간이 긴 제품을 선호하고 있어요."),
            ("운동", "운동 용도로 사용할 예정이에요."),
            ("산책", "산책/일상 용도로 사용할 예정이에요."),
        ]

        matched = False
        for key, sentence in base_rules:
            if key in c:
                mems.append(f"(가장 중요) {sentence}" if priority_flag else sentence)
                matched = True
                break

        if not matched and re.search(r"(필요|좋겠|중요)", c):
            mem = c.strip() + "로 생각하고 있어요."
            mems.append(f"(가장 중요) {mem}" if priority_flag else mem)

    # 중복 제거
    dedup = []
    for m in mems:
        base = m.replace("(가장 중요)", "").strip()
        if not any(base in x.replace("(가장 중요)", "").strip() or
                   x.replace("(가장 중요)", "").strip() in base for x in dedup):
            dedup.append(m)

    return dedup if dedup else None


# =========================================================
# 메모리 add / update / delete
# =========================================================
def add_memory(mem_text: str, announce=True):
    mem_text = mem_text.strip()
    base = mem_text.replace("(가장 중요)", "").strip()

    if "예산" in base:
        st.session_state.memory = [m for m in st.session_state.memory if "예산" not in m]

    for i, m in enumerate(st.session_state.memory):
        ms = m.replace("(가장 중요)", "").strip()
        if base in ms or ms in base:
            if "(가장 중요)" in mem_text and "(가장 중요)" not in m:
                st.session_state.memory = [
                    x.replace("(가장 중요)", "").strip() for x in st.session_state.memory
                ]
                st.session_state.memory[i] = mem_text
            return

    st.session_state.memory.append(mem_text)
    if announce:
        st.session_state.pending_notification = "🧩 새로운 기준이 추가되었어요."


def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.pending_notification = "🧹 기준을 삭제했어요."


def update_memory(idx: int, new_text: str):
    if 0 <= idx < len(st.session_state.memory):
        if "(가장 중요)" in new_text:
            st.session_state.memory = [
                x.replace("(가장 중요)", "").strip() for x in st.session_state.memory
            ]
        st.session_state.memory[idx] = new_text.strip()
        st.session_state.pending_notification = "🔄 기준이 수정되었어요."
        
# =========================================================
# 요약 / 추천 생성
# =========================================================
def extract_budget(mems):
    for m in mems:
        mm = re.search(r"약\s*([0-9]+)\s*만\s*원", m)
        if mm:
            return int(mm.group(1)) * 10000
    return None


def detect_priority(mem_list):
    for m in mem_list:
        if "(가장 중요)" in m:
            cleaned = m.replace("(가장 중요)", "").strip()
            keys = ["음질", "착용감", "가격", "예산", "노이즈캔슬링", "배터리", "디자인"]
            for key in keys:
                if key in cleaned:
                    if key == "디자인":
                        return "디자인/스타일"
                    if key in ["가격", "예산"]:
                        return "가격/예산"
                    return key
            return cleaned
    return None


def generate_summary(name, mems):
    if not mems:
        return ""

    naturalized = [naturalize_memory(m) for m in mems]
    lines = [f"- {m}" for m in naturalized]
    prio = detect_priority(mems)

    header = f"[@{name}님의 메모리 요약]\n\n"
    body = "지금까지 대화를 바탕으로 정리된 기준입니다:\n\n"
    body += "\n".join(lines) + "\n"

    if prio:
        body += f"\n그중에서도 가장 중요한 기준은 **'{prio}'**입니다.\n"

    tail = (
        "\n좌측 메모리 제어창에서 언제든 수정할 수 있어요.\n"
        "기준이 맞다면 아래 버튼을 눌러 추천을 받아보세요 👇"
    )

    return header + body + tail


# =========================================================
# 추천 로직
# =========================================================
CATALOG = [
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 179000,
     "rating": 4.4, "reviews": 1600, "rank": 8,
     "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"],
     "review_one": "가격 대비 성능이 훌륭하고 배터리가 깁니다.",
     "color": ["블랙", "네이비"]},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 129000,
     "rating": 4.4, "reviews": 2300, "rank": 9,
     "tags": ["가벼움", "균형형 음질", "노이즈캔슬링"],
     "review_one": "가볍고 음색이 밝다는 평이 많아요.",
     "color": ["블랙", "화이트"]},
    # … (원래 있던 전체 CATALOG 그대로 유지)
]


def generate_personalized_reason(product, mems, nickname):
    mem_str = " ".join([naturalize_memory(m) for m in mems])

    # 색상 추출
    col_match = re.search(r"색상은\s*([^계열]+)\s*계열", mem_str)
    if col_match:
        want = col_match.group(1).strip().lower()
        prod_colors = [c.lower() for c in product["color"]]
        if any(want in c for c in prod_colors):
            return f"{nickname}님이 선호하는 **{col_match.group(1)} 계열 색상**이 있어요."

    # 기능 기반 설명
    if "노이즈캔슬링" in mem_str and "노이즈" in " ".join(product["tags"]):
        return "노이즈캔슬링 성능이 좋아 조용한 환경을 원하시는 기준과 잘 맞아요."
    if "가벼운" in mem_str and any(t in product["tags"] for t in ["가벼움", "경량"]):
        return "가벼운 착용감을 원하시는 기준과 잘 맞아요."

    return f"{product['brand']}의 안정적인 성능이 {nickname}님의 기준과 잘 어울립니다."


def recommend_products(name, mems, is_reroll=False):
    budget = extract_budget(mems)
    priority = detect_priority(mems)

    def score(item):
        s = item["rating"]

        if budget:
            if item["price"] > budget * 1.5:
                return -999

            if item["price"] <= budget:
                s += 2
            elif item["price"] <= budget * 1.2:
                s += 0.5
            else:
                s -= 2

        mem_str = " ".join(mems)

        if "노이즈" in mem_str and "노이즈" in " ".join(item["tags"]):
            s += 1.2
        if "가벼움" in mem_str and "가벼움" in " ".join(item["tags"]):
            s += 1.5
        if "디자인" in mem_str and "디자인" in " ".join(item["tags"]):
            s += 1.0

        s += max(0, 10 - item["rank"])

        return s

    cands = sorted(CATALOG, key=score, reverse=True)
    selected = cands[:3]

    blocks = []
    for idx, item in enumerate(selected):
        reason = generate_personalized_reason(item, mems, name)
        block = (
            f"**{idx+1}. {item['name']} ({item['brand']})**\n"
            f"- 💰 {item['price']:,}원\n"
            f"- ⭐ {item['rating']:.1f} (리뷰 {item['reviews']})\n"
            f"- 🎨 색상: {', '.join(item['color'])}\n"
            f"- 🗣️ 리뷰 요약: {item['review_one']}\n"
            f"- 추천 이유: {reason}"
        )
        blocks.append(block)

    return "🎯 **추천 제품 3가지**\n\n" + "\n\n---\n\n".join(blocks)


# =========================================================
# 상세 정보 → GPT 응답
# =========================================================
def get_product_detail_prompt(product, user_input, memory_text, nickname):
    return f"""
[상세 정보 요청]
사용자 입력: {user_input}

제품명: {product['name']} ({product['brand']})
가격: {product['price']:,}원
평점: {product['rating']}

사용자 메모리 기반으로 구매 시나리오를 구성해 설명하세요.
항상 번호 목록 또는 불릿 포인트로 답변하세요.
"""


# =========================================================
# GPT 호출
# =========================================================
def gpt_reply(user_input: str):
    if not client:
        return "API 키가 없어 기본 답변만 제공해요."

    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    nickname = st.session_state.nickname

    if st.session_state.stage == "product_detail":
        product = st.session_state.current_recommendation[0]
        prompt = get_product_detail_prompt(product, user_input, memory_text, nickname)
    else:
        prompt = f"""
[메모리]
{memory_text}

[사용자 발화]
{user_input}

위 정보를 참고해 대답하세요.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    return res.choices[0].message.content


# =========================================================
# 대화 메시지 관리
# =========================================================
def ai_say(msg):
    st.session_state.messages.append({"role": "assistant", "content": msg})


def user_say(msg):
    st.session_state.messages.append({"role": "user", "content": msg})


# =========================================================
# 단계 전환
# =========================================================
def summary_step():
    s = generate_summary(st.session_state.nickname, st.session_state.memory)
    ai_say(s)


def comparison_step(is_reroll=False):
    rec = recommend_products(
        st.session_state.nickname, st.session_state.memory, is_reroll
    )
    ai_say(rec)


# =========================================================
# 사용자 입력 처리
# =========================================================
def handle_user_input(user_input: str):
    # 메모리 추출
    mems = memory_sentences_from_user_text(user_input)
    if mems:
        for m in mems:
            add_memory(m)

    # 제품 번호 선택
    choose = re.search(r"([1-3])번", user_input)
    if choose and st.session_state.stage == "comparison":
        idx = int(choose.group(1)) - 1
        st.session_state.current_recommendation = [
            st.session_state.current_recommendation[idx]
        ]
        st.session_state.stage = "product_detail"
        ai_say(gpt_reply(user_input))
        return

    # 추천 요청
    if "추천" in user_input:
        if extract_budget(st.session_state.memory) is None:
            ai_say("추천 전에 예산을 알려주세요!")
            return
        st.session_state.stage = "summary"
        summary_step()
        return

    # 요약으로 이동
    if len(st.session_state.memory) >= 4 and extract_budget(st.session_state.memory):
        st.session_state.stage = "summary"
        summary_step()
        return

    # 일반 대화
    reply = gpt_reply(user_input)
    ai_say(reply)


# =========================================================
# 메모리 패널
# =========================================================
def top_memory_panel():
    st.markdown("### 🧠 나의 쇼핑 기준")
    st.caption("AI가 파악한 기준을 확인하고 수정할 수 있어요.")

    with st.container():
        if not st.session_state.memory:
            st.caption("아직 기준이 없습니다. 대화를 통해 자동으로 채워져요.")
        else:
            for i, mem in enumerate(st.session_state.memory):
                cols = st.columns([6, 1])
                corrected = naturalize_memory(mem)
                new_val = cols[0].text_input(
                    f"메모리 {i+1}", corrected, key=f"mem{i}", label_visibility="collapsed"
                )
                if new_val != corrected:
                    update_memory(i, new_val)

                if cols[1].button("삭제", key=f"del{i}"):
                    delete_memory(i)

        st.markdown("---")
        new_m = st.text_input(
            "새 기준 입력", placeholder="예: 배터리 오래가는 제품 선호"
        )
        if st.button("추가"):
            if new_m.strip():
                add_memory(new_m.strip())


# =========================================================
# 채팅 인터페이스
# =========================================================
def chat_interface():
    col_mem, col_chat = st.columns([0.36, 0.64], gap="medium")

    with col_mem:
        top_memory_panel()

    with col_chat:
        st.markdown("#### 💬 대화창")

        if not st.session_state.messages:
            ai_say(
                f"안녕하세요 {st.session_state.nickname}님! 😊\n"
                "블루투스 헤드셋을 함께 찾아볼게요.\n"
                "우선, 어떤 용도로 사용하실 예정인가요?"
            )

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 입력창
        user_input = st.chat_input("메시지 입력…")

    # 입력 처리 (rerun-free)
    if user_input:
        user_say(user_input)
        handle_user_input(user_input)

    # 메모리 알림 즉시 표시
    if st.session_state.pending_notification:
        st.info(st.session_state.pending_notification)
        st.session_state.pending_notification = None


# =========================================================
# 사전 정보 입력 페이지
# =========================================================
def context_setting():
    st.markdown("### 🧾 실험 준비 (1단계)")
    st.caption("쇼핑 선호를 먼저 간단히 파악할게요.")

    with st.container():
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        nickname = st.text_input("닉네임", key="nickname_input")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        purchase = st.text_input("최근 구매 제품", placeholder="예: 신발 / 가방 / 태블릿")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        color = st.text_input("좋아했던 색상", placeholder="예: 화이트 / 블랙")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        priority = st.radio(
            "그 구매에서 가장 중요했던 기준",
            ["디자인/스타일", "가격/가성비", "성능/품질", "브랜드 이미지"],
            index=None
        )
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("헤드셋 쇼핑 시작하기"):
        if not (nickname and purchase and color and priority):
            st.warning("모든 항목을 입력해주세요!")
            return

        st.session_state.nickname = nickname.strip()
        add_memory(f"색상은 {color.strip()}을 선호해요.", announce=False)
        add_memory(f"(가장 중요) {priority}{get_eul_reul(priority)} 중요시해요.", announce=False)

        st.session_state.page = "chat"
        st.session_state.stage = "explore"
        st.session_state.messages = []


# =========================================================
# 라우팅
# =========================================================
if st.session_state.page == "context_setting":
    context_setting()
else:
    chat_interface()
