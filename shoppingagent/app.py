import re
import streamlit as st
import time
import html
import json
from openai import OpenAI

# =========================================================
# 0. 세션 상태 초기화 & 기본 설정
# =========================================================
def ss_init():
    ss = st.session_state
    ss.setdefault("page", "context_setting")
    ss.setdefault("nickname", "")
    ss.setdefault("phone_number", "")
    ss.setdefault("messages", [])
    ss.setdefault("memory", [])
    ss.setdefault("notification_message", "")
    ss.setdefault("stage", "explore")  # explore / summary / comparison / product_detail / purchase_decision
    ss.setdefault("summary_text", "")
    ss.setdefault("current_recommendation", [])
    ss.setdefault("selected_product", None)
    ss.setdefault("recommended_products", [])
    ss.setdefault("comparison_hint_shown", False)
    ss.setdefault("product_detail_turn", 0)

st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")
ss_init()

client = OpenAI()

# =========================================================
# 2. CSS 스타일 (네가 준 UI 그대로)
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
# 3. SYSTEM PROMPT (헤드셋/메모리/단계 로직)
# =========================================================
SYSTEM_PROMPT = r"""
너는 'AI 쇼핑 도우미'이며 **항상 블루투스 헤드셋(오버이어/온이어 헤드폰)** 기준을 파악해 추천을 돕는 역할을 한다.
스마트폰, 노트북, 태블릿, 일반 전자기기 등 다른 카테고리에 대한 추천이나 질문 유도는 절대 하지 않는다.
이어폰, 인이어 타입, 유선 헤드셋도 추천하지 않는다. 대화 전 과정에서 '헤드셋'만을 전제로 생각한다.

[역할 규칙]
- 최우선 규칙: 메모리에 이미 저장된 기준(특히 용도, 상황, 기능)은 다시 캐묻지 않고, 그다음 중요한 기준들만 묻는다.
- 새로운 기준이 등장하면 "메모리에 추가하면 좋겠다"라고 자연스럽게 언급한다.
- 메모리에 실제 저장될 경우, "이 기준을 기억해둘게요" 혹은 "이번 쇼핑에서는 해당 내용을 고려하지 않을게요"처럼
  메모리 기반으로 동적으로 반영하고 있다는 느낌을 주는 문장을 포함한다.
- 사용자가 모호하게 말하면 부드럽게 구체적으로 다시 물어본다.

[대화 흐름 규칙]
- 1단계(explore): 사전 페이지에서 저장된 메모리를 상기시키면서, 이번 헤드셋 기준을 탐색한다.
- 2단계(summary → comparison): 기준이 어느 정도 쌓이면 지금까지의 메모리를 정리해 주고, 필요하면 추천 단계로 넘어간다.
- 3단계(product_detail / purchase_decision): 특정 후보에 대해 더 자세히 설명해 주거나, 최종 선택을 도와준다.

- 사용자의 "최우선 기준"이 감지되면 그 기준부터 집중해서 묻는다.
  예) '디자인/스타일'이면 디자인/색상부터, '가성비'면 예산부터.
- “최우선 기준”이 없을 때에만 기본 순서를 따른다:
  용도/상황 → 기능(음질/노이즈캔슬링) → 착용감 → 배터리 → 디자인/스타일 → 색상 → 예산
- 추천 단계로 넘어가기 전에 예산을 한 번은 확인하려고 시도한다.
- 메모리가 6개 이상이면 "지금까지 기준을 정리해드릴까요?"라고 스스로 제안해도 좋다.

[메모리 활용]
- 메모리 내용은 가능한 한 자주 화제로 꺼내서, "제가 기억하고 있는 ~님의 메모리를 바탕으로 보면…"처럼 말한다.
- 메모리와 최신 발언이 충돌하면 
  "기존에 ~라고 하셨는데, 기준을 바꾸실까요? 아니면 둘 다 고려해드릴까요?"라고 정중히 확인한다.
- 사용자가 기준 변경을 원하면, 기존 기준을 '덮어쓰기'하도록 유도한다. (실제 삭제는 외부 로직이 한다고 가정)

[출력 규칙]
- 한 번에 질문 1~2개만 하고, 너무 많은 체크리스트를 한꺼번에 던지지 않는다.
- 중복 질문을 해야 할 때는 "다시 한 번만 확인할게요"라고 말한 뒤 질문한다.
- 전체 톤은 부드러운 존댓말, 실험 맥락을 의식하여 과도하게 친한 말투는 피한다.
"""

# =========================================================
# 4. 메모리 유틸
# =========================================================
def naturalize_memory(text: str) -> str:
    t = text.strip()
    t = t.replace("노이즈 캔슬링", "노이즈캔슬링")
    is_priority = "(가장 중요)" in t
    t = t.replace("(가장 중요)", "").strip()
    t = t.replace("있음.", "있어요.")
    if is_priority:
        t = "(가장 중요) " + t
    return t

def extract_memory_with_gpt(user_input, memory_text):
    prompt = f"""
당신은 '헤드셋 쇼핑 기준 요약 AI'입니다.

사용자가 방금 말한 문장:
\"{user_input}\"

현재까지 저장된 기준:
{memory_text if memory_text else "(없음)"}

위 발화에서 '추가해야 할 쇼핑 기준'이 있으면 아래 JSON 형태로만 출력하세요:

{{
  "memories": [
      "문장1",
      "문장2"
  ]
}}

반드시 지켜야 하는 규칙:
- 기준은 반드시 '헤드셋 구매 기준'으로 변환해서 정리한다.
- 문장을 완성된 기준 형태로 출력.
- 브랜드 언급 → "선호하는 브랜드는 ~ 쪽이에요."
- 착용감/귀 아픔/편안 → "착용감이 편한 제품을 선호하고 있어요."
- 음악/노래/감상 → "주로 음악 감상 용도로 사용할 예정이에요."
- 출퇴근 → "출퇴근 시 사용할 용도예요."
- 예쁜/디자인 → "디자인/스타일을 중요하게 생각해요."
- 색상 언급 → "색상은 ~ 계열을 선호해요."
- 노이즈 → "노이즈캔슬링 기능을 고려하고 있어요."
- 예산 N만원 → "예산은 약 N만 원 이내로 생각하고 있어요."

기준이 전혀 없으면 memories는 빈 배열로만 출력하세요.
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

def add_memory(mem_text: str, announce=True):
    mem_text = mem_text.strip()
    if not mem_text:
        return
    mem_text = naturalize_memory(mem_text)
    st.session_state.memory.append(mem_text)
    if announce:
        st.session_state.notification_message = "🧩 메모리에 새로운 기준을 추가했어요."

def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.notification_message = "🧹 메모리에서 기준을 삭제했어요."

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

def generate_summary(name, mems):
    if not mems:
        return f"{name}님에 대해 제가 기억하고 있는 쇼핑 메모리는 아직 많지 않아요.\n원하시면 사용 용도나 중요하게 보고 싶은 기준을 조금만 더 알려주세요!"
    lines = [f"지금까지 제가 기억하고 있는 {name}님의 쇼핑 메모리는 다음과 같아요:"]
    for i, m in enumerate(mems, start=1):
        lines.append(f"- {naturalize_memory(m)}")
    lines.append("\n이 메모리를 바탕으로 헤드셋 후보를 추천해 드릴 수 있어요. 필요하면 아래 버튼을 눌러 추천을 받아보세요!")
    return "\n".join(lines)

# =========================================================
# 5. 간단 상품 카탈로그 & 추천 UI
# =========================================================
CATALOG = [
    {
        "name": "Anker Soundcore Q45",
        "brand": "Anker",
        "price": 179000,
        "rating": 4.4,
        "reviews": 1600,
        "rank": 8,
        "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"],
        "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.",
        "color": ["블랙", "화이트", "네이비"],
        "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg",
    },
    {
        "name": "JBL Tune 770NC",
        "brand": "JBL",
        "price": 129000,
        "rating": 4.4,
        "reviews": 2300,
        "rank": 9,
        "tags": ["가벼움", "음질", "노이즈캔슬링", "편안함"],
        "review_one": "가볍고 음질이 좋다는 평이 많아요.",
        "color": ["블랙", "화이트", "퍼플", "네이비"],
        "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png",
    },
]

def filter_products(mems):
    # 지금은 단순 정렬(평점+랭크)만 사용 – 나중에 태그/색/예산 필터로 확장 가능
    return sorted(CATALOG, key=lambda c: (-c["rating"], c["rank"]))[:3]

def recommend_products_ui(name, mems):
    products = filter_products(mems)
    st.session_state.current_recommendation = products

    st.markdown("#### 🎧 추천 후보 리스트")
    cols = st.columns(len(products))
    for i, p in enumerate(products):
        with cols[i]:
            st.markdown(
                f"""
                <div class="product-card">
                    <div>
                        <div class="product-title">{i+1}. {p['name']}</div>
                        <img src="{p['img']}" class="product-img" />
                        <div><b>{p['brand']}</b></div>
                        <div class="product-price">{p['price']:,}원</div>
                        <div>⭐ {p['rating']:.1f} / 5.0</div>
                        <div style="font-size:13px; margin-top:6px;">{p['review_one']}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# =========================================================
# 6. GPT 응답 및 입력 처리
# =========================================================
def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})

def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})

def gpt_reply(user_input: str) -> str:
    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    nickname = st.session_state.nickname or "고객"
    prompt_content = f"""
[현재 단계] {st.session_state.stage}
[사용자 이름] {nickname}
[저장된 메모리]
{memory_text if memory_text else "아직 저장된 메모리가 없습니다."}

[사용자 발화]
{user_input}
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content},
        ],
        temperature=0.4,
    )
    return res.choices[0].message.content

def handle_user_input(raw_text: str):
    user_input = raw_text.strip()
    if not user_input:
        return
    user_say(user_input)

    # 1) 메모리 추출 (질문형이면 스킵)
    lower = user_input.lower()
    is_q = (
        user_input.endswith("??")
        or ("뭐야" in lower)
        or ("뭔데" in lower)
        or ("알려" in lower)
        or ("뜻" in lower)
    )
    if not is_q:
        mems = extract_memory_with_gpt(user_input, "\n".join(st.session_state.memory))
        for m in mems:
            add_memory(m, announce=True)

    # 2) 추천/요약 트리거 – 추천 버튼을 쓰기 위해 stage를 summary로 먼저 보냄
    if any(k in user_input for k in ["추천해줘", "추천 좀", "골라줘", "후보 보여줘", "후보 추천"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say("추천 전에 **예산**을 먼저 알려주시면 좋아요. 예: 10만 원 이내, 20만 원 전후 등으로 말씀해 주세요.")
            st.session_state.stage = "explore"
            return
        st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
        ai_say(st.session_state.summary_text)
        st.session_state.stage = "summary"
        return

    # 3) 일반 대화
    reply = gpt_reply(user_input)
    ai_say(reply)

# =========================================================
# 7. UI 컴포넌트
# =========================================================
def render_scenario():
    st.markdown(
        """
        <div class="scenario-box">
            <b>시나리오</b><br>
            최근 귀가 아파서, 평소 쓰던 블루투스 이어폰 대신 <b>착용감이 편한 블루투스 헤드셋</b>을 하나 장만해보려고 합니다.<br>
            이 에이전트는 당신의 <b>취향 메모리</b>를 바탕으로 대화를 이어가며, 취향이 달라졌다면 언제든지 수정하도록 도와줍니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_step_header():
    stage = st.session_state.stage
    step_map = {"explore": 1, "summary": 2, "comparison": 2, "product_detail": 3, "purchase_decision": 3}
    current = step_map.get(stage, 1)

    labels = [
        ("구매 기준 탐색", "지금까지의 쇼핑 메모리를 확인하고, 이번 헤드셋에 맞게 기준을 잡는 단계입니다."),
        ("후보 비교", "기준에 맞는 헤드셋 후보들을 보고 궁금한 점을 물어보는 단계입니다."),
        ("최종 결정", "마음에 드는 헤드셋을 하나 고르는 단계입니다."),
    ]

    html_steps = '<div class="progress-container">'
    for i, (title, desc) in enumerate(labels, start=1):
        active_class = "step-item step-active" if i == current else "step-item"
        html_steps += f'''
        <div class="{active_class}">
            <div class="step-header-group">
                <div class="step-circle">{i}</div>
                <div class="step-title">{title}</div>
            </div>
            <div class="step-desc">{desc}</div>
        </div>
        '''
    html_steps += "</div>"
    st.markdown(html_steps, unsafe_allow_html=True)

def render_memory_sidebar():
    st.markdown('<div class="memory-section-header">🧠 메모리</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="memory-guide-box">
            지금까지 제가 파악한 <b>쇼핑 메모리</b>가 이곳에 정리됩니다.<br>
            실제 헤드셋에는 다르게 적용하고 싶다면, 아래 기준을 수정하거나 X 버튼을 눌러 언제든 삭제하실 수 있어요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.memory:
        st.caption("아직 저장된 메모리가 없습니다. 대화 중에 차차 쌓일 거예요.")
    else:
        for i, m in enumerate(st.session_state.memory):
            cols = st.columns([8, 1])
            with cols[0]:
                st.markdown(
                    f'''
                    <div class="memory-block">
                        <div class="memory-text">{html.escape(naturalize_memory(m))}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                if st.button("X", key=f"mem_del_{i}"):
                    delete_memory(i)
                    st.rerun()

    st.markdown(
        """
        <div class="tip-box">
            💡 Tip. 이번 헤드셋에는 고려하고 싶지 않은 기준이 있다면<br>
            먼저 삭제한 뒤, 새 기준을 대화로 추가해 보셔도 좋아요.
        </div>
        """,
        unsafe_allow_html=True,
    )

def main_chat_interface():
    # 알림 토스트
    if st.session_state.notification_message:
        try:
            st.toast(st.session_state.notification_message, icon="✅")
        except Exception:
            st.info(st.session_state.notification_message)
        st.session_state.notification_message = ""

    # 첫 인사
    if len(st.session_state.messages) == 0:
        nickname = st.session_state.nickname or "고객"
        ai_say(
            f"안녕하세요 {nickname}님! 😊 저는 블루투스 헤드셋 쇼핑을 도와드리는 AI 도우미예요.\n"
            "앞에서 선택해 주신 내용을 바탕으로 기본 취향 메모리를 만들어두었고, 대화를 나누면서 실시간 기준도 계속 업데이트해볼게요.\n"
            "먼저, 이번에 구매하실 헤드셋은 주로 어떤 상황에서 사용하실 예정인지 말씀해 주실 수 있을까요?"
        )

    render_scenario()
    render_step_header()

    col1, col2 = st.columns([3, 7], gap="large")

    # ---- 좌측: 메모리 패널 ----
    with col1:
        render_memory_sidebar()

    # ---- 우측: 채팅 + 추천 ----
    with col2:
        chat_container = st.container()
        with chat_container:
            html_content = '<div class="chat-display-area">'
            for msg in st.session_state.messages:
                cls = "chat-bubble-ai" if msg["role"] == "assistant" else "chat-bubble-user"
                safe = html.escape(msg["content"])
                html_content += f'<div class="chat-bubble {cls}">{safe}</div>'
            html_content += "</div>"
            st.markdown(html_content, unsafe_allow_html=True)

        # SUMMARY 단계일 때: 아래에 "추천 받기" 버튼 띄우기
        if st.session_state.stage == "summary":
            st.markdown("---")
            if st.button("이 기준으로 헤드셋 후보 추천 받기"):
                st.session_state.stage = "comparison"
                st.rerun()

        # 추천 / 비교 영역
        if st.session_state.stage in ["comparison", "product_detail", "purchase_decision"]:
            st.markdown("---")
            recommend_products_ui(st.session_state.nickname, st.session_state.memory)

        # 입력 폼
        with st.form(key="chat_form", clear_on_submit=True):
            c1, c2 = st.columns([85, 15])
            with c1:
                text = st.text_input(
                    "msg",
                    key="user_input_text",
                    label_visibility="collapsed",
                    placeholder="원하는 기준이나 궁금한 점을 알려주세요! (예: 노이즈캔슬링도 필요할까요?)",
                )
            with c2:
                sent = st.form_submit_button("전송")

        if sent and text.strip():
            handle_user_input(text)
            st.rerun()

# =========================================================
# 8. 컨텍스트 세팅 (사전 설문 페이지)
# =========================================================
def context_setting():
    st.title("🛒 쇼핑 에이전트 실험 준비")
    st.markdown(
        """
    <div class="info-text">
        이 페이지는 <b>AI 에이전트가 귀하의 과거 쇼핑 취향을 기억하는지</b> 테스트하기 위한 사전 설정 단계입니다.<br>
        평소 본인의 실제 쇼핑 습관이나, 이번 실험에서 연기할 '페르소나'의 정보를 입력해 주세요.
    </div>
    """,
        unsafe_allow_html=True,
    )
    
    with st.container(border=True):
        st.subheader("📝 기본 정보")
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("이름 (닉네임)", placeholder="홍길동")
            st.markdown(
                '<div class="warning-text">⚠️ 사전 설문에 작성한 이름과 동일하게 입력해주세요. (불일치 시 불성실 응답 간주 가능)</div>',
                unsafe_allow_html=True,
            )
        with c2:
            phone = st.text_input("전화번호 (뒷 4자리)", placeholder="1234")
            
        st.markdown("---")
        st.subheader("🛍️ 쇼핑 성향 조사")
        
        category = st.selectbox(
            "Q1. 최근 구매 또는 관심이 있었던 디지털/가전 제품 카테고리는 무엇인가요?",
            ["스마트폰/태블릿", "노트북/PC", "오디오/헤드셋", "웨어러블(워치 등)", "기타"],
        )
        
        q2_option = st.selectbox(
            "Q2. 아래 세 가지 중, '나와 더 비슷하다'고 느껴지는 쪽은 어느 쪽인가요?",
            ["가성비가 좋은 제품을 선호하는 편", "디자인이 예쁜 제품을 선호하는 편", "성능이 뛰어난 제품을 선호하는 편"],
        )
        
        color = st.selectbox(
            "Q3. 아래 색상 중, 실제로 온라인 쇼핑에서 더 자주 클릭해볼 것 같은 색상은?",
            ["화이트", "블랙", "네이비", "핑크", "그레이"],
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("쇼핑 시작하기 (초기 메모리 생성 후 진행)", type="primary", use_container_width=True):
            if not name or not color or not q2_option:
                st.warning("필수 정보를 모두 입력해주세요.")
                return
            
            st.session_state.nickname = name
            st.session_state.phone_number = phone

            # 초기 메모리 생성
            base_item = "스마트폰/태블릿" if category == "스마트폰/태블릿" else category
            mem1 = f"과거에 {base_item} 구매 시 '{q2_option}'을(를) 가장 중요하게 생각했어요."
            mem2 = f"평소 색상은 '{color}' 계열을 자주 선택하는 편이에요."
            st.session_state.memory = []
            add_memory(mem1, announce=False)
            add_memory(mem2, announce=False)

            # 대화 관련 상태 초기화
            st.session_state.messages = []
            st.session_state.stage = "explore"
            st.session_state.page = "chat"
            st.rerun()

# =========================================================
# 9. 라우팅
# =========================================================
if st.session_state.page == "context_setting":
    context_setting()
else:
    main_chat_interface()
