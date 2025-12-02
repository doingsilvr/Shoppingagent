import re
import streamlit as st
import time
import html
import json
from openai import OpenAI

# OpenAI 클라이언트 설정 (API Key는 환경 변수나 Streamlit Secrets에서 로드 권장)
client = OpenAI()

# =========================================================
# 1. 세션 상태 초기값 설정 (상태 변수 추가)
# =========================================================
def ss_init():
    ss = st.session_state
    
    # 기본 페이지 및 데이터
    ss.setdefault("page", "context_setting")
    ss.setdefault("nickname", "")
    ss.setdefault("messages", [])
    
    # 메모리 관련
    ss.setdefault("memory", [])
    ss.setdefault("memory_changed", False) # 🔥 메모리 수정 감지 플래그
    ss.setdefault("just_updated_memory", False)
    
    # 쇼핑 단계 제어
    ss.setdefault("stage", "explore") 
    ss.setdefault("waiting_for_priority", False) # 🔥 최종 중요도 질문 대기 상태
    
    # 추천 데이터
    ss.setdefault("summary_text", "")
    ss.setdefault("current_recommendation", [])
    ss.setdefault("selected_product", None)
    ss.setdefault("recommended_products", [])
    
    # UI 제어
    ss.setdefault("notification_message", "")
    ss.setdefault("comparison_hint_shown", False)
    ss.setdefault("product_detail_turn", 0)

ss_init()

# =========================================================
# 2. 전역 CSS 설정
# =========================================================
st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

st.markdown("""
<style>
    /* 기본 UI 숨기기 */
    #MainMenu, footer, header {visibility: hidden;}
    
    /* 레이아웃 조정 */
    .block-container {max-width: 1180px !important; padding-top: 1rem;}
    
    /* 말풍선 스타일 */
    .chat-bubble {
        padding: 10px 14px;
        border-radius: 16px;
        margin-bottom: 8px;
        max-width: 78%;
        font-size: 15px;
        line-height: 1.45;
    }
    .chat-bubble-user {
        background: #F0F6FF;
        align-self: flex-end;
        margin-left: auto;
        border-top-right-radius: 4px;
        text-align: right;
    }
    .chat-bubble-ai {
        background: #F1F0F0;
        align-self: flex-start;
        margin-right: auto;
        border-top-left-radius: 4px;
        text-align: left;
    }
    .chat-display-area {
        display: flex;
        flex-direction: column;
        padding: 1rem;
        height: 600px;
        overflow-y: auto;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
    }
    
    /* 메모리 패널 스타일 */
    .memory-item-text {
        font-size: 14px;
        padding: 8px;
        background: #fff;
        border: 1px solid #eee;
        border-radius: 6px;
        margin-bottom: 4px;
    }
    
    /* 상품 카드 스타일 */
    .product-card {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 10px;
        text-align: center;
        background: white;
        height: 100%;
        transition: box-shadow 0.2s;
    }
    .product-card:hover {box-shadow: 0 4px 12px rgba(0,0,0,0.1);}
    .product-image {
        width: 100%;
        height: 150px;
        object-fit: contain;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. 유틸리티 함수
# =========================================================
def get_eul_reul(noun: str) -> str:
    if not noun: return "을"
    last_char = noun[-1]
    if not ('\uAC00' <= last_char <= '\uD7A3'): return "를"
    return "을" if (ord(last_char) - 0xAC00) % 28 != 0 else "를"

def naturalize_memory(text: str) -> str:
    """메모리 문장을 자연스럽게 다듬기"""
    t = text.strip()
    is_priority = "(가장 중요)" in t
    t = t.replace("(가장 중요)", "").strip()
    t = re.sub(r'로 생각하고 있어요\.?$|에요\.?$|이에요\.?$|다\.?$', '', t)
    t = re.sub(r'(을|를)\s*선호$', ' 선호', t)
    t = t.strip()
    if is_priority:
        t = "(가장 중요) " + t
    return t

def extract_budget(mems):
    """메모리에서 예산(숫자) 추출"""
    for m in mems:
        # "20만 원" 패턴
        m1 = re.search(r"(\d+)\s*만\s*원", m)
        if m1: return int(m1.group(1)) * 10000
        # "200000원" 패턴
        m2 = re.search(r"(\d{3,})\s*원", m.replace(",", ""))
        if m2: return int(m2.group(1))
    return None

# =========================================================
# 4. 🔥 GPT 기반 메모리 관리 (핵심 로직 개선)
# =========================================================
def extract_memory_with_gpt(user_input, memory_list):
    """
    GPT를 사용하여 사용자 발화에서 기준을 추출.
    - 문맥 파악 가능
    - JSON 형태로 구조화된 데이터 반환
    """
    current_memories = "\n".join(memory_list) if memory_list else "(없음)"
    
    prompt = f"""
    당신은 쇼핑 기준 추출 전문가입니다.
    
    [현재 저장된 기준]
    {current_memories}
    
    [사용자 발화]
    "{user_input}"
    
    [임무]
    사용자의 발화에서 헤드셋 구매와 관련된 '새로운 기준'이나 '구체적 선호'가 있다면 JSON으로 추출하세요.
    
    [규칙]
    1. 질문("이건 뭐야?"), 단순 응답("응", "아니"), 인사 등은 무시하고 빈 리스트 반환.
    2. 예산 언급 시 "예산은 약 N만 원 이내로 생각하고 있어요."로 통일.
    3. 이미 저장된 기준과 완벽히 동일하면 추출 금지.
    4. 문장은 "~를 선호해요", "~가 필요해요" 형태로 종결.
    
    [출력 포맷]
    {{ "memories": ["문장1", "문장2"] }}
    """
    
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content)
        return data.get("memories", [])
    except:
        return []

def add_memory(mem_text: str, announce=True):
    mem_text = naturalize_memory(mem_text)
    clean_text = mem_text.replace("(가장 중요)", "").strip()
    
    # 중복/충돌 방지 로직
    # 예: 예산이 새로 들어오면 기존 예산 삭제
    if "예산" in clean_text:
        st.session_state.memory = [m for m in st.session_state.memory if "예산" not in m]
    if "색상" in clean_text:
        st.session_state.memory = [m for m in st.session_state.memory if "색상" not in m]

    # 리스트에 추가
    st.session_state.memory.append(mem_text)
    
    # 🔥 실시간 반영 플래그 켜기
    st.session_state.memory_changed = True
    
    if announce and st.session_state.page != "context_setting":
        st.session_state.notification_message = "📝 새로운 기준이 메모리에 추가되었어요!"

def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        st.session_state.memory_changed = True
        st.session_state.notification_message = "🗑️ 기준이 삭제되었습니다."

# =========================================================
# 5. GPT 응답 생성 (시스템 프롬프트 강화)
# =========================================================
SYSTEM_PROMPT = """
당신은 사용자의 '과거 쇼핑 내역(Context)'을 기억하는 AI 쇼핑 에이전트입니다.
사용자는 블루투스 헤드셋을 구매하려고 합니다.

[핵심 규칙]
1. **중복 질문 금지**: 메모리에 이미 있는 정보(용도, 가격, 색상 등)는 절대 다시 묻지 마세요.
2. **과거 연동**: 대화 초반에는 "지난번에 ~를 선호하셨는데, 이번에도 동일한가요?" 처럼 기억을 언급하세요.
3. **예산 필수**: 예산 정보가 없으면 추천 단계로 넘어가지 말고 반드시 정중히 물어보세요.
4. **단계별 행동**:
   - 탐색 단계: 기준을 하나씩 수집합니다.
   - 상세 단계: 선택된 제품에 대한 정보만 답변합니다.
"""

def gpt_reply(user_input: str) -> str:
    memory_text = "\n".join([naturalize_memory(m) for m in st.session_state.memory])
    has_budget = extract_budget(st.session_state.memory) is not None
    
    # 단계별 지침 추가
    instruction = ""
    
    if st.session_state.stage == "explore":
        if not has_budget:
            instruction = "\n[중요] 현재 '예산' 정보가 없습니다. 자연스럽게 가격대를 물어보세요."
        elif len(st.session_state.memory) >= 4:
            instruction = "\n[중요] 기준이 충분히 모였습니다. 더 필요한 게 없는지 묻거나 정리를 유도하세요."

    if st.session_state.stage == "pre_summary_check":
        instruction = "\n[중요] 사용자에게 '지금까지 말한 조건 중(디자인, 가격, 기능 등) 가장 1순위로 중요한 것은 무엇인가요?'라고 물어보세요."

    prompt = f"""
    [현재 메모리 상태]
    {memory_text if memory_text else "(없음)"}
    
    [추가 지침]
    {instruction}
    
    [사용자 입력]
    "{user_input}"
    """
    
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        return res.choices[0].message.content
    except:
        return "죄송합니다. 잠시 연결에 문제가 생겼어요."

# =========================================================
# 6. 추천 및 요약 로직
# =========================================================
CATALOG = [
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 450000, "rating": 4.8, "tags": ["노이즈캔슬링", "음질", "착용감"], "color": ["블랙", "실버", "핑크"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg", "review_one": "노이즈캔슬링 성능이 압도적이에요."},
    {"name": "Bose QC45", "brand": "Bose", "price": 389000, "rating": 4.7, "tags": ["착용감", "가벼움", "노이즈캔슬링"], "color": ["블랙", "화이트"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg", "review_one": "착용감이 구름처럼 편안해요."},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 769000, "rating": 4.6, "tags": ["디자인", "애플생태계", "노이즈캔슬링"], "color": ["실버", "스페이스그레이", "핑크", "그린", "스카이블루"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg", "review_one": "디자인이 예쁘고 마감이 고급스러워요."},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 129000, "rating": 4.4, "tags": ["가성비", "가벼움", "배터리"], "color": ["블랙", "화이트", "블루", "퍼플"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png", "review_one": "가성비가 훌륭하고 가벼워요."},
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 149000, "rating": 4.3, "tags": ["가성비", "배터리", "기능"], "color": ["블랙", "화이트", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg", "review_one": "배터리가 정말 오래가요."}
]

def generate_summary(name, mems):
    lines = [f"- {naturalize_memory(m)}" for m in mems]
    text = "\n".join(lines)
    return f"[{name}님의 쇼핑 기준 요약]\n\n{text}\n\n위 기준으로 제품을 추천해 드릴까요?"

def filter_products(mems):
    """간단한 점수 기반 추천 로직"""
    budget = extract_budget(mems)
    mem_text = " ".join(mems)
    
    def score(p):
        s = 0
        # 예산 체크
        if budget:
            if p['price'] <= budget: s += 10
            elif p['price'] <= budget * 1.2: s += 5
            else: s -= 10
        
        # 태그 매칭
        for tag in p['tags']:
            if tag in mem_text: s += 5
            
        # 브랜드 매칭
        if p['brand'] in mem_text: s += 5
        
        # 색상 매칭
        for color in p['color']:
            if color in mem_text: s += 3
            
        # 우선순위(가장 중요) 처리
        if "(가장 중요)" in mem_text:
            # 예: "디자인"이 중요하면 디자인 태그 점수 2배
            if "디자인" in mem_text and "디자인" in p['tags']: s += 10
            if "음질" in mem_text and "음질" in p['tags']: s += 10
            if "착용감" in mem_text and "착용감" in p['tags']: s += 10
            if "가성비" in mem_text and "가성비" in p['tags']: s += 10
            
        return s

    ranked = sorted(CATALOG, key=score, reverse=True)
    st.session_state.current_recommendation = ranked[:3]
    return ranked[:3]

# =========================================================
# 7. 🔥 메인 컨트롤러 (입력 처리 로직 통합)
# =========================================================
def handle_user_input(user_input: str):
    if not user_input.strip(): return
    
    # [공통] GPT를 통한 메모리 추출 (질문형 제외)
    is_question = any(k in user_input for k in ["뭐야", "알려줘", "?", "어때"])
    if not is_question:
        mems = extract_memory_with_gpt(user_input, st.session_state.memory)
        for m in mems:
            add_memory(m, announce=True)

    # ----------------------------------------------------
    # Case 1: 🔥 최종 중요도 확인 단계 응답 처리
    # ----------------------------------------------------
    if st.session_state.waiting_for_priority:
        # 사용자의 대답을 최우선 기준으로 저장
        prio_mem = f"(가장 중요) {naturalize_memory(user_input)}"
        add_memory(prio_mem, announce=True)
        
        st.session_state.waiting_for_priority = False
        st.session_state.stage = "summary"
        st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
        st.rerun()
        return

    # ----------------------------------------------------
    # Case 2: 탐색(Explore) 단계 종료 조건 체크
    # ----------------------------------------------------
    if st.session_state.stage == "explore":
        has_budget = extract_budget(st.session_state.memory) is not None
        mem_count = len(st.session_state.memory)
        
        # 추천 요청 감지
        if any(k in user_input for k in ["추천", "골라줘", "결과"]):
            if not has_budget:
                user_say(user_input)
                ai_say("추천을 위해 **예산**을 먼저 알려주시겠어요?")
                st.rerun()
                return
            else:
                # 예산 있으면 -> 중요도 질문으로 이동
                user_say(user_input)
                st.session_state.waiting_for_priority = True
                st.session_state.stage = "pre_summary_check"
                ai_say("추천 전 마지막 질문입니다! 지금까지 말씀하신 조건 중 **가장 1순위로 중요한 기준** 하나만 말씀해 주세요.")
                st.rerun()
                return

        # 자동 종료 조건 (기준 4개 이상 + 예산 있음)
        if mem_count >= 4 and has_budget:
            user_say(user_input)
            st.session_state.waiting_for_priority = True
            st.session_state.stage = "pre_summary_check"
            ai_say("꼼꼼하게 잘 말씀해 주셨어요! 👍 마지막으로, **가격, 디자인, 성능, 착용감** 중 **단 하나만** 꼽자면 무엇이 가장 중요하신가요?")
            st.rerun()
            return
            
    # ----------------------------------------------------
    # Case 3: 일반 대화 (GPT 처리)
    # ----------------------------------------------------
    reply = gpt_reply(user_input)
    user_say(user_input)
    ai_say(reply)
    st.rerun()

def ai_say(msg):
    st.session_state.messages.append({"role": "assistant", "content": msg})

def user_say(msg):
    st.session_state.messages.append({"role": "user", "content": msg})

# =========================================================
# 8. UI 컴포넌트
# =========================================================
def render_notification():
    if st.session_state.notification_message:
        st.success(st.session_state.notification_message)
        # 3초 뒤 메시지 비우기 (UI 갱신 시 사라짐)
        time.sleep(1) 
        st.session_state.notification_message = ""

def top_memory_panel():
    if not st.session_state.memory:
        st.caption("아직 수집된 정보가 없습니다.")
    else:
        for i, m in enumerate(st.session_state.memory):
            cols = st.columns([8, 2])
            with cols[0]:
                st.markdown(f'<div class="memory-item-text">{naturalize_memory(m)}</div>', unsafe_allow_html=True)
            with cols[1]:
                if st.button("x", key=f"del_{i}"):
                    delete_memory(i)
                    st.rerun()
                    
    st.markdown("---")
    new_mem = st.text_input("메모리 직접 추가", placeholder="예: 디자인 중요", label_visibility="collapsed")
    if st.button("추가", use_container_width=True):
        if new_mem:
            add_memory(new_mem)
            st.rerun()

def comparison_view():
    st.markdown("### 🎧 추천 제품 비교")
    products = filter_products(st.session_state.memory)
    
    cols = st.columns(3)
    for i, p in enumerate(products):
        with cols[i]:
            st.markdown(
                f"""
                <div class="product-card">
                    <img src="{p['img']}" class="product-image">
                    <h4>{p['name']}</h4>
                    <p style="color:#666; font-size:14px;">{p['brand']}</p>
                    <p><b>{p['price']:,}원</b></p>
                    <p>⭐ {p['rating']}</p>
                    <p style="font-size:12px; color:#888;">{p['review_one']}</p>
                </div>
                """, unsafe_allow_html=True
            )
            if st.button(f"상세보기 ({i+1})", key=f"detail_{i}", use_container_width=True):
                st.session_state.selected_product = p
                st.session_state.stage = "product_detail"
                ai_say(f"**{p['name']}** 제품을 선택하셨군요. 이 제품에 대해 궁금한 점을 물어보세요!")
                st.rerun()

# =========================================================
# 9. 화면 구성 (Context Setting & Chat)
# =========================================================
def context_setting_page():
    st.title("🛒 쇼핑 에이전트 설정")
    st.markdown("실험을 위해 가상의 사용자 정보를 설정합니다. 이 정보는 **과거 기억**으로 작용합니다.")
    
    with st.container(border=True):
        name = st.text_input("이름 (닉네임)", placeholder="홍길동")
        color = st.text_input("선호하는 색상 (과거 기록)", placeholder="블랙, 화이트 등")
        priority = st.selectbox("가장 중요하게 생각하는 요소 (과거 기록)", ["디자인", "가성비", "음질/성능", "착용감"])
        
        if st.button("쇼핑 시작하기", use_container_width=True):
            if name and color:
                st.session_state.nickname = name
                # 과거 기록을 메모리에 주입
                add_memory(f"색상은 {color} 계열을 선호해요.", announce=False)
                add_memory(f"(가장 중요) {priority}을(를) 중요하게 생각해요.", announce=False)
                
                st.session_state.page = "chat"
                st.rerun()
            else:
                st.warning("정보를 모두 입력해주세요.")

def chat_interface():
    # 🔥 1. 과거 기억 연동 인사말 (첫 진입 시)
    if not st.session_state.messages:
        greeting = (
            f"안녕하세요 {st.session_state.nickname}님! 👋\n"
            f"지난번에 **{naturalize_memory(st.session_state.memory[0])}** 그리고 **{naturalize_memory(st.session_state.memory[1])}**라고 하셨던 기억이 나네요.\n"
            "이번에도 이 기준들을 바탕으로 헤드셋을 찾아볼까요? 아니면 새로운 용도가 있으신가요?"
        )
        ai_say(greeting)

    # 🔥 2. 실시간 메모리 변경 감지 및 피드백
    if st.session_state.memory_changed:
        if st.session_state.stage == "summary":
            st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
            ai_say("📝 기준이 변경되어 요약 내용을 업데이트했어요!")
        elif st.session_state.stage == "comparison":
            ai_say("🔄 변경된 기준에 맞춰 추천 리스트를 새로 고쳤습니다.")
        st.session_state.memory_changed = False

    render_notification()

    # 레이아웃
    col1, col2 = st.columns([3, 7])
    
    with col1:
        st.subheader("🧠 나의 쇼핑 기준")
        top_memory_panel()
        
    with col2:
        st.subheader("💬 대화")
        
        # 채팅창 렌더링
        chat_html = '<div class="chat-display-area">'
        for msg in st.session_state.messages:
            role_cls = "chat-bubble-ai" if msg['role'] == "assistant" else "chat-bubble-user"
            chat_html += f'<div class="chat-bubble {role_cls}">{html.escape(msg["content"])}</div>'
        
        # 요약문 표시 (Summary 단계)
        if st.session_state.stage == "summary":
            chat_html += f'<div class="chat-bubble chat-bubble-ai" style="white-space: pre-wrap;">{html.escape(st.session_state.summary_text)}</div>'
            
        chat_html += "</div>"
        st.markdown(chat_html, unsafe_allow_html=True)
        
        # Summary 단계 버튼
        if st.session_state.stage == "summary":
            if st.button("🔍 이 기준으로 추천 받기", use_container_width=True):
                st.session_state.stage = "comparison"
                st.rerun()

        # Comparison 단계 UI
        if st.session_state.stage == "comparison":
            comparison_view()

        # Product Detail 단계 UI (뒤로가기)
        if st.session_state.stage == "product_detail":
            if st.button("🔙 목록으로 돌아가기"):
                st.session_state.stage = "comparison"
                st.rerun()

        # 입력창
        with st.form("chat_input_form", clear_on_submit=True):
            user_input = st.text_input("메시지 입력", placeholder="궁금한 점이나 원하는 조건을 말씀해주세요.")
            if st.form_submit_button("전송"):
                handle_user_input(user_input)

# =========================================================
# 메인 실행
# =========================================================
if st.session_state.page == "context_setting":
    context_setting_page()
else:
    chat_interface()
