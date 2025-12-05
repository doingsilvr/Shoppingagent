import streamlit as st
import time
import json
import random
import re
from openai import OpenAI

# =========================================================
# 0. 기본 설정 & CSS (최소한의 레이아웃만 조정)
# =========================================================
st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

# CSS: 화면 폭 조절 및 스크롤 영역만 정의 (버튼 스타일링 등 위험한 해킹 제거)
st.markdown("""
<style>
    /* 화면 폭을 1000px로 고정하여 모바일/앱 느낌 */
    .block-container {
        max-width: 1000px;
        padding-top: 2rem;
        padding-bottom: 5rem;
        margin: 0 auto;
    }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* 채팅 영역 스크롤 */
    .chat-container {
        height: 500px;
        overflow-y: auto;
        padding-right: 10px;
        display: flex;
        flex-direction: column-reverse; /* 최신 메시지가 아래에 오도록 */
    }
    
    /* 메모리 태그 스타일 */
    .memory-tag {
        background-color: #f0f2f6;
        padding: 8px 12px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 5px solid #2563EB;
        font-size: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

client = OpenAI()

# =========================================================
# 1. 세션 초기화
# =========================================================
def ss_init():
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.page = "context_setting"
        st.session_state.messages = []
        st.session_state.memory = []
        st.session_state.nickname = ""
        st.session_state.stage = "explore" # explore -> summary -> comparison -> product_detail -> purchase_decision
        st.session_state.recommended_products = []
        st.session_state.selected_product = None
        st.session_state.final_choice = None
        st.session_state.turn_count = 0
        st.session_state.summary_text = ""

ss_init()

# =========================================================
# 2. 로직 함수 (기능 복구)
# =========================================================
CATALOG = [
    {"name": "Sony WH-1000XM5", "price": 450000, "tags": ["노이즈캔슬링", "음질", "착용감", "통화품질"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg", "rank": 1},
    {"name": "Bose QC45", "price": 389000, "tags": ["편안함", "가벼움", "노이즈캔슬링"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg", "rank": 2},
    {"name": "Apple AirPods Max", "price": 769000, "tags": ["디자인", "애플생태계", "노이즈캔슬링", "고급"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg", "rank": 3},
    {"name": "Anker Soundcore Q45", "price": 149000, "tags": ["가성비", "배터리", "노이즈캔슬링"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg", "rank": 4},
    {"name": "JBL Tune 770NC", "price": 99000, "tags": ["가성비", "가벼움", "저음"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png", "rank": 5},
]

def naturalize_memory(text):
    return text.replace("노이즈 캔슬링", "노이즈캔슬링").replace("(가장 중요)", "").strip()

def add_memory(text):
    clean_text = naturalize_memory(text)
    if clean_text and clean_text not in st.session_state.memory:
        st.session_state.memory.append(clean_text)

def delete_memory(idx):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]

def extract_memory_with_gpt(user_input, current_memory):
    try:
        prompt = f"""
        사용자 발화: "{user_input}"
        기존 메모리: {current_memory}
        위 발화에서 '헤드셋 쇼핑 기준(가격, 디자인, 기능 등)'을 JSON 리스트로 추출해. 없으면 빈 리스트.
        형식: {{ "memories": ["~을 선호함", "~가 중요함"] }}
        """
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content).get("memories", [])
    except:
        return []

def get_gpt_reply(user_input):
    system_prompt = f"""
    너는 블루투스 헤드셋 쇼핑 에이전트다. 
    현재 단계: {st.session_state.stage}
    메모리: {st.session_state.memory}
    
    [규칙]
    1. 메모리에 없는 기준(용도, 디자인, 예산 등)을 하나씩 물어봐라.
    2. 이미 메모리에 있는건 다시 묻지 마라.
    3. 메모리가 5개 이상이면 "이제 추천해드릴까요?"라고 요약 단계로 유도해라.
    """
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )
    return res.choices[0].message.content

def recommend_logic():
    # 간단한 점수 로직 복구
    scored = []
    mem_text = " ".join(st.session_state.memory)
    for p in CATALOG:
        score = 0
        for tag in p['tags']:
            if tag in mem_text: score += 10
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in scored[:3]]

# =========================================================
# 3. UI 컴포넌트 (Streamlit 네이티브 기능 활용)
# =========================================================

def render_stepper():
    """상단 진행 단계 표시 (텍스트/메트릭 활용하여 깨짐 방지)"""
    steps = ["1.탐색", "2.요약", "3.추천", "4.상세", "5.결정"]
    current_idx = ["explore", "summary", "comparison", "product_detail", "purchase_decision"].index(st.session_state.stage)
    
    cols = st.columns(5)
    for i, step in enumerate(steps):
        with cols[i]:
            if i == current_idx:
                st.markdown(f"**:blue[{step}]**") # 현재 단계 강조
                st.progress(100)
            elif i < current_idx:
                st.markdown(f"~~{step}~~") # 지난 단계
                st.progress(100)
            else:
                st.markdown(f"{step}")
                st.progress(0)

def render_memory_sidebar():
    """좌측 메모리 영역"""
    with st.container(border=True):
        st.subheader("🧠 쇼핑 메모리")
        if not st.session_state.memory:
            st.info("대화를 통해 취향을 수집합니다.")
        
        for i, mem in enumerate(st.session_state.memory):
            # 태그 하나를 컬럼으로 나누어 삭제 버튼 배치
            c1, c2 = st.columns([8, 2])
            with c1:
                st.markdown(f"**· {mem}**")
            with c2:
                if st.button("삭제", key=f"del_{i}", type="secondary"):
                    delete_memory(i)
                    st.rerun()
        
        st.divider()
        new_mem = st.text_input("직접 추가", placeholder="예: 화이트 색상 선호")
        if st.button("추가하기", type="primary", use_container_width=True):
            if new_mem:
                add_memory(new_mem)
                st.rerun()

def render_chat_area():
    """채팅 영역 (컨테이너 활용)"""
    with st.container(border=True):
        # 채팅 히스토리 표시 영역
        chat_container = st.container(height=400) # 고정 높이 스크롤
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    
            # 요약 단계일 때
            if st.session_state.stage == "summary":
                st.info(f"💡 정리된 기준:\n\n" + "\n".join([f"- {m}" for m in st.session_state.memory]))
                if st.button("이 기준으로 추천 받기 🔍", type="primary"):
                    st.session_state.stage = "comparison"
                    st.session_state.recommended_products = recommend_logic()
                    st.rerun()

            # 추천 단계일 때 (캐러셀 대신 카드형 배치)
            if st.session_state.stage == "comparison":
                st.success("회원님을 위한 추천 제품입니다!")
                cols = st.columns(3)
                for i, p in enumerate(st.session_state.recommended_products):
                    with cols[i]:
                        with st.container(border=True):
                            st.image(p['img'], use_column_width=True)
                            st.write(f"**{p['name']}**")
                            st.caption(f"{p['price']:,}원")
                            if st.button("상세보기", key=f"btn_rec_{i}", use_container_width=True):
                                st.session_state.selected_product = p
                                st.session_state.stage = "product_detail"
                                st.rerun()

            # 상세 정보 단계
            if st.session_state.stage == "product_detail":
                p = st.session_state.selected_product
                st.markdown("---")
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.image(p['img'])
                with c2:
                    st.subheader(p['name'])
                    st.write(f"가격: **{p['price']:,}원**")
                    st.write("특징: " + ", ".join(p['tags']))
                    
                    b1, b2 = st.columns(2)
                    if b1.button("목록으로"):
                        st.session_state.stage = "comparison"
                        st.rerun()
                    if b2.button("구매 확정 🛒", type="primary"):
                        st.session_state.stage = "purchase_decision"
                        st.session_state.final_choice = p
                        st.rerun()

            # 구매 완료
            if st.session_state.stage == "purchase_decision":
                st.balloons()
                st.success(f"🎉 {st.session_state.final_choice['name']} 구매가 완료되었습니다!")

    # 입력창 (컨테이너 밖 하단)
    if st.session_state.stage not in ["purchase_decision"]:
        with st.form("chat_form", clear_on_submit=True):
            c1, c2 = st.columns([8, 2])
            user_input = c1.text_input("메시지 입력", label_visibility="collapsed", placeholder="원하는 헤드셋 조건을 말해주세요...")
            submitted = c2.form_submit_button("전송", type="primary", use_container_width=True)
            
            if submitted and user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # 메모리 추출
                new_mems = extract_memory_with_gpt(user_input, str(st.session_state.memory))
                for m in new_mems: add_memory(m)
                
                # 자동 단계 전환 체크
                if st.session_state.stage == "explore" and len(st.session_state.memory) >= 4:
                    st.session_state.stage = "summary"
                    st.session_state.messages.append({"role": "assistant", "content": "선호하시는 기준이 어느정도 모였네요. 정리해드릴까요?"})
                else:
                    response = get_gpt_reply(user_input)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                
                st.rerun()

# =========================================================
# 4. 메인 실행
# =========================================================
if st.session_state.page == "context_setting":
    st.title("🛒 AI 쇼핑 에이전트 설정")
    st.info("실험을 위한 기본 정보를 입력해주세요.")
    
    with st.container(border=True):
        name = st.text_input("이름 / 닉네임")
        style = st.selectbox("주요 쇼핑 성향", ["가성비", "디자인", "성능", "브랜드"])
        
        if st.button("쇼핑 시작하기", type="primary"):
            if name:
                st.session_state.nickname = name
                add_memory(f"{style}를 중요하게 생각함")
                st.session_state.page = "chat"
                st.rerun()
            else:
                st.warning("이름을 입력해주세요.")

else:
    # 채팅 화면
    render_stepper()
    st.divider()
    
    col_mem, col_chat = st.columns([3, 7])
    
    with col_mem:
        render_memory_sidebar()
        
    with col_chat:
        render_chat_area()
