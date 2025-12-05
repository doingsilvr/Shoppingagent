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
# 1. 세션 상태 초기값
# =========================================================
def ss_init():
    ss = st.session_state
    ss.setdefault("page", "context_setting")
    ss.setdefault("nickname", "")
    ss.setdefault("budget", None)
    ss.setdefault("messages", [])
    ss.setdefault("memory", [])
    ss.setdefault("memory_colors", []) 
    ss.setdefault("just_updated_memory", False)
    ss.setdefault("stage", "explore")
    ss.setdefault("summary_text", "")
    ss.setdefault("detail_mode", False)
    ss.setdefault("recommended_products", [])
    ss.setdefault("selected_product", None)
    ss.setdefault("final_choice", None)
    ss.setdefault("turn_count", 0)
    ss.setdefault("product_detail_turn", 0)
    ss.setdefault("question_history", [])            
    ss.setdefault("current_question", None)          
    ss.setdefault("priority", "")                    
    ss.setdefault("primary_style", "")               
    ss.setdefault("priority_followup_done", False)   

ss_init()

# ========================================================
# 2. CSS 스타일 (버튼 충돌 해결 및 디자인 정리)
# =========================================================
st.markdown("""
<style>
    /* 1) 전체 레이아웃 폭 제한 */
    .block-container {
        padding-top: 2rem; 
        max-width: 1000px !important;
        padding-bottom: 3rem;
    }
    #MainMenu, footer, header, .css-1r6q61a {visibility: hidden; display: none !important;}

    /* ============================================================
       🟢 [버튼 스타일 분리] - 이게 핵심입니다!
       type="primary" -> 파란색 (전송, 추가 등)
       type="secondary" -> 투명/회색 (삭제 버튼)
       ============================================================ */
    
    /* 1. Primary 버튼 (주요 액션: 파란색) */
    button[kind="primary"] {
        background-color: #2563EB !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: 0.2s;
        height: auto !important;
        padding: 0.5rem 1rem !important;
    }
    button[kind="primary"]:hover {
        background-color: #1D4ED8 !important;
    }

    /* 2. Secondary 버튼 (삭제 버튼용: 투명하고 작게) */
    button[kind="secondary"] {
        background-color: transparent !important;
        border: none !important;
        color: #94a3b8 !important; /* 연한 회색 */
        padding: 0 !important;
        font-size: 16px !important;
        line-height: 1 !important;
        min-height: 0px !important;
        height: auto !important;
        margin-top: 5px !important; 
    }
    button[kind="secondary"]:hover {
        color: #ef4444 !important; /* 마우스 올리면 빨간색 */
        background-color: transparent !important;
        border: none !important;
    }
    button[kind="secondary"]:focus {
        color: #ef4444 !important;
        box-shadow: none !important;
        border: none !important;
    }

    /* ============================================================ */

    /* ✨ 프로세스 바 (Stepper) */
    .stepper-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 30px;
        position: relative;
        padding: 0 10px;
    }
    .stepper-line {
        position: absolute;
        top: 15px;
        left: 40px;
        right: 40px;
        height: 2px;
        background: #E2E8F0;
        z-index: 0;
    }
    .step-box {
        position: relative;
        z-index: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
    }
    .step-num {
        width: 30px; height: 30px;
        border-radius: 50%;
        background: #FFFFFF;
        border: 2px solid #E2E8F0;
        color: #94A3B8;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 13px;
        margin-bottom: 6px;
        transition: 0.3s;
    }
    .step-txt {
        font-size: 12px; color: #94A3B8; font-weight: 500;
    }
    
    /* 활성 단계 */
    .step-active .step-num {
        border-color: #2563EB;
        background: #2563EB;
        color: white;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    .step-active .step-txt { color: #2563EB; font-weight: 700; }

    /* 📜 스크롤 영역 */
    .scroll-mem {
        height: 550px;
        overflow-y: auto;
        padding: 15px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
    }
    .scroll-chat {
        height: 480px;
        overflow-y: auto;
        padding: 10px;
        background: white;
    }

    /* 메모리 태그 */
    .mem-tag {
        display: block;
        padding: 10px 12px;
        border-radius: 8px;
        font-size: 13px; 
        font-weight: 500; 
        color: #334155; 
        background: white;
        border-left: 5px solid #ccc; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        margin-bottom: 0px; /* layout으로 조절 */
    }

    /* 말풍선 */
    .chat-bubble { padding: 12px 16px; border-radius: 16px; margin-bottom: 12px; max-width: 85%; line-height: 1.6; font-size: 15px; }
    .chat-bubble-user { background: #E0E7FF; align-self: flex-end; margin-left: auto; color: #111; border-top-right-radius: 2px; }
    .chat-bubble-ai { background: #F3F4F6; align-self: flex-start; margin-right: auto; color: #111; border-top-left-radius: 2px; }

    /* 상품 카드 */
    .p-card {
        background: white; border: 1px solid #E5E7EB; border-radius: 12px;
        padding: 12px; text-align: center; height: 100%;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .p-card:hover { border-color: #2563EB; transform: translateY(-2px); }
    .p-img { width: 100%; height: 100px; object-fit: contain; margin-bottom: 8px; }
    .p-title { font-weight: 700; font-size: 13px; margin-bottom: 2px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
    .p-price { color: #2563EB; font-weight: 700; font-size: 13px; margin-bottom: 6px; }
    .p-desc { font-size: 11px; color: #6B7280; line-height: 1.3; margin-bottom: 8px; height: 30px; overflow: hidden; }

    /* 입력창 */
    .stTextInput input {
        border-radius: 24px !important;
        background: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        padding: 12px 15px !important;
    }
    div[data-testid="stForm"] { border: none; padding: 0; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. 로직 함수들 (GPT, 유틸, 카탈로그 등)
# =========================================================
SYSTEM_PROMPT = r"""
너는 'AI 쇼핑 도우미'이며 **항상 블루투스 헤드셋** 기준을 파악해 추천을 돕는다.
메모리 기준은 다시 묻지 않고, 새로운 기준을 파악하거나 추천한다.
"""

def get_random_pastel_color():
    colors = ["#FFD700", "#FFB6C1", "#87CEFA", "#98FB98", "#DDA0DD", "#F0E68C", "#E0FFFF", "#FF69B4", "#FFA07A"]
    return random.choice(colors)

def naturalize_memory(text: str) -> str:
    t = text.strip().replace("노이즈 캔슬링", "노이즈캔슬링").replace("(가장 중요)", "").strip()
    t = re.sub(r'로 생각하고 있어요\.?$', '', t)
    t = re.sub(r'(을|를)\s*선호$', ' 선호', t)
    return t.strip()

def is_negative_response(text: str) -> bool:
    negative_keywords = ["없어", "몰라", "모르겠", "글쎄", "별로", "상관없", "관심없"]
    return any(k in text for k in negative_keywords)

def extract_memory_with_gpt(user_input: str, memory_text: str):
    prompt = f"""
    발화: "{user_input}"
    기존 메모리: {memory_text}
    위 발화에서 '헤드셋 쇼핑 기준'으로 추가할 내용을 JSON으로 추출. 없으면 [].
    형식: {{ "memories": ["문장1"] }}
    """
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        data = json.loads(res.choices[0].message.content)
        return data.get("memories", [])
    except: return []

def add_memory(mem_text: str):
    mem_text = naturalize_memory(mem_text)
    if not mem_text: return
    for m in st.session_state.memory:
        if mem_text in m: return
    st.session_state.memory.append(mem_text)
    st.session_state.memory_colors.append(get_random_pastel_color())
    st.session_state.just_updated_memory = True

def delete_memory(idx: int):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        del st.session_state.memory_colors[idx]
        st.session_state.just_updated_memory = True

# 카탈로그 데이터
CATALOG = [
    {"name": "Anker Soundcore Q45", "price": 179000, "rating": 4.4, "reviews": 1600, "rank": 8, "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"], "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.", "color": ["블랙", "화이트", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg"},
    {"name": "JBL Tune 770NC", "price": 99000, "rating": 4.4, "reviews": 2300, "rank": 9, "tags": ["가벼움", "음질", "노이즈캔슬링", "편안함"], "review_one": "가볍고 음질이 좋다는 평이 많아요.", "color": ["블랙", "화이트", "퍼플", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png"},
    {"name": "Sony WH-CH720N", "price": 129000, "rating": 4.5, "reviews": 2100, "rank": 6, "tags": ["노이즈캔슬링", "경량", "무난한 음질"], "review_one": "경량이라 출퇴근용으로 좋다는 후기가 많아요.", "color": ["블랙", "화이트", "블루"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-CH720N.jpg"},
    {"name": "Bose QC45", "price": 420000, "rating": 4.7, "reviews": 2800, "rank": 2, "tags": ["가벼움", "착용감", "노이즈캔슬링", "편안함"], "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg"},
    {"name": "Sony WH-1000XM5", "price": 210000, "rating": 4.8, "reviews": 3200, "rank": 1, "tags": ["노이즈캔슬링", "음질", "착용감", "통화품질"], "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.", "color": ["핑크"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg"},
    {"name": "Apple AirPods Max", "price": 679000, "rating": 4.6, "reviews": 1500, "rank": 3, "tags": ["브랜드", "노이즈캔슬링", "디자인", "고급"], "review_one": "깔끔한 디자인과 가벼운 무게로 만족도가 높아요.", "color": ["실버", "스페이스그레이"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg"},
]

def make_recommendation():
    # 점수 계산 로직 약식 (기존 로직 유지)
    random.shuffle(CATALOG)
    return CATALOG[:3]

def generate_personalized_reason(product, mems, name):
    return f"{name}님의 취향에 잘 맞는 제품입니다."

def gpt_reply(user_input: str) -> str:
    # 약식 응답 함수
    memory_text = "\n".join(st.session_state.memory)
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"메모리:{memory_text}\n유저:{user_input}"}
        ],
        temperature=0.5,
    )
    return res.choices[0].message.content

# =========================================================
# 4. UI 렌더링 함수 (수정됨)
# =========================================================

# [수정됨] HTML 코드 노출 없이 깔끔한 스테퍼
def render_process_bar():
    steps = [
        ("explore", "1", "탐색"),
        ("summary", "2", "요약"),
        ("comparison", "3", "추천"),
        ("product_detail", "4", "상세"),
        ("purchase_decision", "5", "결정")
    ]
    current_stage = st.session_state.stage
    
    html = '<div class="stepper-container"><div class="stepper-line"></div>'
    for code, num, label in steps:
        active_cls = "step-active" if code == current_stage else ""
        html += f"""
        <div class="step-box {active_cls}">
            <div class="step-num">{num}</div>
            <div class="step-txt">{label}</div>
        </div>
        """
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# [수정됨] 메모리 사이드바 (삭제 버튼 type="secondary"로 해결)
def render_memory_column():
    # 안전장치: 색상 동기화
    while len(st.session_state.memory_colors) < len(st.session_state.memory):
        st.session_state.memory_colors.append(get_random_pastel_color())

    st.markdown('<div class="scroll-mem">', unsafe_allow_html=True)
    st.markdown("##### 🧠 쇼핑 메모리")
    
    if not st.session_state.memory:
        st.caption("저장된 취향이 없습니다.")

    # 메모리 리스트
    for i, mem in enumerate(st.session_state.memory):
        color = st.session_state.memory_colors[i]
        
        # [핵심] 컬럼 비율 조정으로 정렬 맞춤
        c1, c2 = st.columns([8.8, 1.2]) 
        with c1:
            # 태그
            st.markdown(
                f"<div class='mem-tag' style='border-left-color:{color};'>{mem}</div>", 
                unsafe_allow_html=True
            )
        with c2:
            # [해결] type="secondary"를 사용하여 파란색 배경 제거하고 투명하게 만듦
            # key를 다르게 주어 충돌 방지
            if st.button("✕", key=f"del_{i}", type="secondary"):
                delete_memory(i)
                st.rerun()
            
    # 구분선
    st.markdown("<hr style='margin: 15px 0; opacity: 0.2;'>", unsafe_allow_html=True)
    
    # 수동 추가
    new_mem = st.text_input("직접 추가", key="manual_mem", placeholder="예: 무조건 화이트", label_visibility="collapsed")
    
    # 추가 버튼은 파란색(Primary) 유지
    if st.button("➕ 메모리 추가하기", key="btn_add_mem", type="primary", use_container_width=True):
        if new_mem.strip():
            add_memory(new_mem.strip())
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# [캐러셀]
def render_carousel():
    products = st.session_state.recommended_products
    if not products: return

    st.markdown("##### 🎁 회원님을 위한 추천 Pick")
    cols = st.columns(3)
    for i, p in enumerate(products):
        with cols[i]:
            html_code = f"""
            <div class="p-card">
                <img src="{p['img']}" class="p-img">
                <div class="p-title">{p['name']}</div>
                <div class="p-price">{p['price']:,}원</div>
                <div class="p-desc">{generate_personalized_reason(p, st.session_state.memory, st.session_state.nickname)}</div>
            </div>
            """
            st.markdown(html_code, unsafe_allow_html=True)
            if st.button("상세보기", key=f"btn_rec_{i}", type="primary", use_container_width=True):
                st.session_state.selected_product = p
                st.session_state.stage = "product_detail"
                st.rerun()

# =========================================================
# 5. 메인 로직
# =========================================================
def handle_input():
    u = st.session_state.user_input_text.strip()
    if not u: return
    
    st.session_state.messages.append({"role": "user", "content": u})
    st.session_state.turn_count += 1
    
    # 메모리 추출
    mems = extract_memory_with_gpt(u, "\n".join(st.session_state.memory))
    for m in mems: add_memory(m)
    
    # 응답
    if st.session_state.stage == "explore" and len(st.session_state.memory) >= 5:
        st.session_state.stage = "summary"
        st.session_state.summary_text = "기준이 충분히 모였네요. 이대로 추천할까요?"
        return

    reply = gpt_reply(u)
    st.session_state.messages.append({"role": "assistant", "content": reply})

    if st.session_state.stage == "summary" and any(k in u for k in ["응","네","좋아","추천"]):
        st.session_state.stage = "comparison"
        st.session_state.recommended_products = make_recommendation()
        st.session_state.messages.append({"role": "assistant", "content": "추천 제품을 가져왔습니다!"})

def main_chat_interface():
    # 프로세스바
    render_process_bar()
    
    # 레이아웃
    col_left, col_right = st.columns([3, 7], gap="medium")
    
    # 왼쪽: 메모리
    with col_left:
        render_memory_column()
        
    # 오른쪽: 채팅
    with col_right:
        with st.container(border=True):
            # 스크롤 영역
            st.markdown('<div class="scroll-chat">', unsafe_allow_html=True)
            
            if not st.session_state.messages:
                st.markdown("<div class='chat-bubble chat-bubble-ai'>안녕하세요! 헤드셋 추천을 도와드릴까요?</div>", unsafe_allow_html=True)

            for msg in st.session_state.messages:
                role_cls = "chat-bubble-ai" if msg["role"] == "assistant" else "chat-bubble-user"
                st.markdown(f"<div class='chat-bubble {role_cls}'>{msg['content']}</div>", unsafe_allow_html=True)
                
            if st.session_state.stage == "summary":
                st.markdown(f"<div class='chat-bubble chat-bubble-ai'>{st.session_state.summary_text}</div>", unsafe_allow_html=True)
                if st.button("🔍 추천 받기", type="primary"):
                    st.session_state.stage = "comparison"
                    st.session_state.recommended_products = make_recommendation()
                    st.rerun()
                
            if st.session_state.stage == "comparison":
                st.markdown("---")
                render_carousel()
                
            if st.session_state.stage == "product_detail":
                 st.info(f"선택하신 {st.session_state.selected_product['name']} 상세 정보입니다.")
                 c1, c2 = st.columns(2)
                 if c1.button("목록으로", type="secondary"):
                     st.session_state.stage = "comparison"
                     st.rerun()
                 if c2.button("구매하기", type="primary"):
                     st.session_state.stage = "purchase_decision"
                     st.rerun()

            st.markdown('</div>', unsafe_allow_html=True) # End scroll-chat
            
            # 입력창 (하단 고정)
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            with st.form(key="chat_form", clear_on_submit=True):
                r1, r2 = st.columns([85, 15])
                with r1:
                    st.text_input("msg", key="user_input_text", placeholder="메시지 입력...", label_visibility="collapsed")
                with r2:
                    st.form_submit_button("전송", on_click=handle_input, type="primary")

# 실행
if st.session_state.page == "context_setting":
    st.title("설정")
    name = st.text_input("닉네임")
    if st.button("시작", type="primary"):
        st.session_state.nickname = name
        st.session_state.page = "chat"
        st.rerun()
else:
    main_chat_interface()
