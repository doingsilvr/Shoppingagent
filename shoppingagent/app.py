
import re
import streamlit as st
import time
import html
import json
import random
from openai import OpenAI

# =========================================================
# 0. 페이지 및 CSS 설정 (최종 디자인 반영)
# =========================================================
st.set_page_config(page_title="AI 쇼핑 에이전트", page_icon="🎧", layout="wide")

st.markdown("""
<style>
    /* 1. 전체 컨테이너: 모바일 앱처럼 좁고 집중도 있게 */
    .block-container {
        max-width: 1000px;
        padding-top: 2rem;
        padding-bottom: 3rem;
        margin: 0 auto;
    }
    #MainMenu, footer, header {visibility: hidden;}

    /* 2. 프로세스 스테퍼 (진행바) 디자인 */
    .step-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
        position: relative;
        padding: 0 20px;
    }
    .step-line {
        position: absolute;
        top: 50%;
        left: 40px;
        right: 40px;
        height: 2px;
        background-color: #E2E8F0;
        z-index: 0;
        transform: translateY(-50%);
    }
    .step-item {
        position: relative;
        z-index: 1;
        background: white;
        padding: 0 10px;
        text-align: center;
    }
    .step-circle {
        width: 32px; height: 32px;
        border-radius: 50%;
        background-color: white;
        border: 2px solid #CBD5E1;
        color: #94A3B8;
        display: flex; align-items: center; justify-content: center;
        font-weight: bold;
        margin: 0 auto 5px auto;
        transition: all 0.3s;
    }
    .step-text {
        font-size: 12px;
        color: #94A3B8;
        font-weight: 500;
    }
    
    /* 활성화 된 단계 스타일 */
    .step-active .step-circle {
        border-color: #2563EB;
        background-color: #2563EB;
        color: white;
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
    }
    .step-active .step-text {
        color: #2563EB;
        font-weight: bold;
    }

    /* 3. 버튼 스타일링 (종류별 분리) */
    
    /* 기본 버튼 (전송, 추가 등) - 파란색 */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        transition: 0.2s;
    }
    
    /* 4. [중요] 삭제 버튼(X)만 콕 집어서 투명하게 만들기 */
    /* Streamlit의 secondary 버튼을 투명 버튼으로 개조 */
    button[kind="secondary"] {
        background-color: transparent !important;
        border: none !important;
        color: #94A3B8 !important;
        padding: 0px 8px !important;
        font-size: 16px !important;
    }
    button[kind="secondary"]:hover {
        color: #EF4444 !important; /* 빨간색 */
        background-color: #FEF2F2 !important;
    }

    /* 5. 메모리 태그 디자인 */
    .memory-box {
        background-color: white;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        border-left: 5px solid #2563EB; /* 포인트 컬러 (동적 변경됨) */
        font-size: 13px;
        font-weight: 500;
        color: #334155;
    }
    
    /* 6. 채팅 말풍선 */
    .chat-bubble-ai {
        background-color: #F1F5F9;
        color: #1E293B;
        padding: 12px 16px;
        border-radius: 12px 12px 12px 0;
        margin-bottom: 10px;
        line-height: 1.5;
        font-size: 15px;
    }
    .chat-bubble-user {
        background-color: #EFF6FF;
        color: #1E3A8A;
        padding: 12px 16px;
        border-radius: 12px 12px 0 12px;
        margin-bottom: 10px;
        text-align: right;
        line-height: 1.5;
        font-size: 15px;
        margin-left: auto;
        max-width: 80%;
    }
    
    /* 7. 상품 카드 */
    .product-card {
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 10px;
        background: white;
        text-align: center;
        height: 100%;
        transition: transform 0.2s;
    }
    .product-card:hover {
        border-color: #2563EB;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* 입력창 스타일 */
    .stTextInput input {
        border-radius: 20px;
        padding: 10px 15px;
        border: 1px solid #CBD5E1;
    }
</style>
""", unsafe_allow_html=True)

client = OpenAI()

# =========================================================
# 1. 세션 및 데이터 초기화 (풀 로직)
# =========================================================
def ss_init():
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.page = "context_setting"
        st.session_state.nickname = ""
        st.session_state.messages = []
        st.session_state.memory = []
        st.session_state.memory_colors = []
        st.session_state.stage = "explore"
        st.session_state.recommended_products = []
        st.session_state.selected_product = None
        st.session_state.final_choice = None
        st.session_state.summary_text = ""
        st.session_state.turn_count = 0
        st.session_state.question_history = []
        st.session_state.current_question = None

ss_init()

# 전체 카탈로그 (생략 없음)
CATALOG = [
    {"name": "Anker Soundcore Q45", "brand": "Anker", "price": 179000, "rating": 4.4, "reviews": 1600, "rank": 8, "tags": ["가성비", "배터리", "노이즈캔슬링", "편안함"], "review_one": "가격 대비 성능이 훌륭하고 배터리가 길어요.", "color": ["블랙", "화이트", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Anker%20Soundcore%20Q45.jpg"},
    {"name": "JBL Tune 770NC", "brand": "JBL", "price": 99000, "rating": 4.4, "reviews": 2300, "rank": 9, "tags": ["가벼움", "음질", "노이즈캔슬링", "편안함"], "review_one": "가볍고 음질이 좋다는 평이 많아요.", "color": ["블랙", "화이트", "퍼플", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/JBL%20Tune%20770NC.png"},
    {"name": "Sony WH-CH720N", "brand": "Sony", "price": 129000, "rating": 4.5, "reviews": 2100, "rank": 6, "tags": ["노이즈캔슬링", "경량", "무난한 음질"], "review_one": "경량이라 출퇴근용으로 좋다는 후기가 많아요.", "color": ["블랙", "화이트", "블루"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-CH720N.jpg"},
    {"name": "Bose QC45", "brand": "Bose", "price": 420000, "rating": 4.7, "reviews": 2800, "rank": 2, "tags": ["가벼움", "착용감", "노이즈캔슬링", "편안함"], "review_one": "장시간 써도 귀가 편하다는 리뷰가 많아요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20QC45.jpg"},
    {"name": "Sony WH-1000XM5", "brand": "Sony", "price": 450000, "rating": 4.8, "reviews": 3200, "rank": 1, "tags": ["노이즈캔슬링", "음질", "착용감", "통화품질"], "review_one": "소음 많은 환경에서 확실히 조용해진다는 평가.", "color": ["핑크"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sony%20WH-1000XM5.jpg"},
    {"name": "Apple AirPods Max", "brand": "Apple", "price": 769000, "rating": 4.6, "reviews": 1500, "rank": 3, "tags": ["브랜드", "노이즈캔슬링", "디자인", "고급"], "review_one": "깔끔한 디자인과 가벼운 무게로 만족도가 높아요.", "color": ["실버", "스페이스그레이"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Apple%20Airpods%20Max.jpeg"},
    {"name": "Sennheiser PXC 550-II", "brand": "Sennheiser", "price": 289000, "rating": 4.3, "reviews": 1200, "rank": 7, "tags": ["착용감", "여행", "배터리", "노이즈캔슬링"], "review_one": "여행 시 장시간 착용에도 압박감이 덜해요.", "color": ["블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Sennheiser%20PXC%2055.jpeg"},
    {"name": "AKG Y600NC", "brand": "AKG", "price": 149000, "rating": 4.2, "reviews": 1800, "rank": 10, "tags": ["균형 음질", "가성비", "노이즈캔슬링"], "review_one": "가격대비 깔끔하고 균형 잡힌 사운드가 좋아요.", "color": ["블랙", "골드", "네이비"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/AKG%20Y6.jpg"},
    {"name": "Microsoft Surface Headphones 2", "brand": "Microsoft", "price": 319000, "rating": 4.5, "reviews": 900, "rank": 11, "tags": ["업무", "통화품질", "디자인", "노이즈캔슬링"], "review_one": "업무용으로 완벽하며 통화 품질이 매우 깨끗합니다.", "color": ["화이트", "블랙"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Microsoft%20Surface%20Headphones%202.jpeg"},
    {"name": "Bose Noise Cancelling Headphones 700", "brand": "Bose", "price": 490000, "rating": 4.7, "reviews": 2500, "rank": 4, "tags": ["노이즈캔슬링", "배터리", "음질", "프리미엄"], "review_one": "노이즈캔슬링 성능과 음질을 모두 갖춘 최고급 프리미엄 제품.", "color": ["블랙", "화이트"], "img": "https://raw.githubusercontent.com/doingsilvr/Shoppingagent/main/shoppingagent/img/Bose%20Headphones%20700.jpg"},
]

# 상세 시스템 프롬프트 (생략 없음)
SYSTEM_PROMPT = r"""
너는 'AI 쇼핑 도우미'이며 **항상 블루투스 헤드셋** 기준을 파악해 추천을 돕는 역할을 한다.
스마트폰, 노트북, 태블릿, 일반 전자기기 등 다른 카테고리에 대한 추천이나 질문 유도는 절대 하지 않는다.

[역할 규칙]
- 최우선 규칙: 메모리에 이미 저장된 기준은 절대 다시 물어보지 않고 바로 다음 단계 질문으로 넘어간다.
- 너의 가장 큰 역할은 **사용자 메모리(쇼핑 기준)를 읽고, 갱신하고, 설명하면서 추천을 돕는 것**이다.
- 메모리에 저장될 경우 "이 기준을 기억해둘게요" 혹은 "메모리에 추가해둘게요"라고 표현한다.
- 사용자에게 세부 음역대(저음/중음) 질문은 금지한다.
- 사용자가 모호하게 말하면 구체적인 상황(출퇴근, 공부 등)을 예시로 들어 되묻는다.

[대화 흐름]
1. 용도/상황 -> 2. 음질/기능 -> 3. 디자인/색상 -> 4. 예산 순서로 파악하되,
사용자가 먼저 언급한 "최우선 기준"이 있다면 그것을 먼저 구체화한다.
추천 단계 전 **예산**은 반드시 확인한다.
메모리가 5개 이상이면 "기준을 정리해드릴까요?"라고 묻고 요약 단계로 유도한다.
"""

# =========================================================
# 2. 유틸리티 & 로직 함수
# =========================================================

def get_random_color():
    return random.choice(["#2563EB", "#7C3AED", "#DB2777", "#EA580C", "#059669", "#0891B2", "#E11D48", "#0EA5E9"])

def naturalize_memory(text: str) -> str:
    """메모리 문장 정규화"""
    t = text.strip()
    t = t.replace("노이즈 캔슬링", "노이즈캔슬링")
    is_priority = "(가장 중요)" in t
    t = t.replace("(가장 중요)", "").strip()
    t = re.sub(r'로 생각하고 있어요\.?$', '', t)
    t = re.sub(r'(을|를)\s*선호$', ' 선호', t)
    t = t.strip()
    if is_priority:
        t = "(가장 중요) " + t
    return t

def is_negative_response(text: str) -> bool:
    """부정/회피 반응 감지"""
    negative_keywords = ["없어", "몰라", "모르겠", "글쎄", "별로", "상관없", "관심없", "안중요"]
    return any(k in text for k in negative_keywords)

def extract_budget(mems):
    """예산 추출"""
    for m in mems:
        m1 = re.search(r"(\d+)\s*만\s*원", m)
        if m1: return int(m1.group(1)) * 10000
        txt = m.replace(",", "")
        m2 = re.search(r"(\d{2,7})\s*원", txt)
        if m2: return int(m2.group(1))
    return None

def extract_memory_gpt(text, current_mem):
    """GPT를 이용한 메모리 추출"""
    try:
        prompt = f"""
        발화: "{text}"
        기존메모리: {current_mem}
        위 발화에서 '헤드셋 쇼핑 기준(가격,디자인,기능,용도 등)'을 JSON 리스트로 추출하세요. 없으면 빈 리스트.
        형식: {{ "memories": ["~을 선호함", "~가 중요함"] }}
        """
        res = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role":"user", "content":prompt}], 
            temperature=0, 
            response_format={"type":"json_object"}
        )
        return json.loads(res.choices[0].message.content).get("memories", [])
    except: return []

def add_memory(text):
    text = naturalize_memory(text)
    if text:
        # 중복 체크
        for m in st.session_state.memory:
            if text in m: return
        st.session_state.memory.append(text)
        st.session_state.memory_colors.append(get_random_color())

def delete_memory(idx):
    if 0 <= idx < len(st.session_state.memory):
        del st.session_state.memory[idx]
        del st.session_state.memory_colors[idx]

def score_item_with_memory(item, mems):
    """메모리 기반 추천 점수 계산 (Full Logic)"""
    score = 0
    mtext = " ".join(mems)
    budget = extract_budget(mems)

    # 1. 태그 매칭
    for tag in item["tags"]:
        if tag in mtext: score += 20
        if "(가장 중요)" in mtext:
            if "디자인" in mtext and "디자인" in tag: score += 30
            if "음질" in mtext and "음질" in tag: score += 30

    # 2. 예산 보정
    if budget:
        if item["price"] > budget:
            diff = item["price"] - budget
            score -= 200 if diff > 100000 else 80
        else:
            score += 30
    
    # 3. 랭킹 보정
    score -= item.get("rank", 10)
    return score

def make_recommendation():
    """점수 기반 추천 리스트 생성"""
    scored = [(score_item_with_memory(item, st.session_state.memory), item) for item in CATALOG]
    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:3]]

def get_gpt_response(user_input):
    """GPT 응답 생성 (상황별 프롬프트 제어)"""
    memory_text = "\n".join(st.session_state.memory)
    stage = st.session_state.stage
    
    # 시스템 프롬프트 + 현재 상태 주입
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"현재 단계: {stage}\n메모리:\n{memory_text}\n\n사용자 발화: {user_input}"}
    ]
    
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.5
    )
    return res.choices[0].message.content

# =========================================================
# 3. UI 컴포넌트 (디자인 + 기능 결합)
# =========================================================

def render_stepper():
    """HTML로 구현된 깔끔한 스테퍼"""
    steps = [("explore","1","탐색"), ("summary","2","요약"), ("comparison","3","추천"), ("product_detail","4","상세"), ("purchase_decision","5","결정")]
    curr = st.session_state.stage
    
    html = '<div class="step-container"><div class="step-line"></div>'
    for stage_code, num, label in steps:
        active = "step-active" if stage_code == curr else ""
        html += f"""
        <div class="step-item {active}">
            <div class="step-circle">{num}</div>
            <div class="step-text">{label}</div>
        </div>
        """
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def render_memory_sidebar():
    """파스텔톤 태그 + 투명 삭제 버튼 (CSS 클래스 활용)"""
    with st.container(border=True):
        st.markdown("##### 🧠 쇼핑 메모리")
        st.caption("AI가 기억하는 취향입니다.")
        
        # 색상 싱크 맞추기 (안전장치)
        while len(st.session_state.memory_colors) < len(st.session_state.memory):
            st.session_state.memory_colors.append(get_random_color())

        if not st.session_state.memory:
            st.info("아직 수집된 정보가 없어요.")

        for i, mem in enumerate(st.session_state.memory):
            col_color = st.session_state.memory_colors[i]
            
            # 레이아웃: 태그 내용(9) + 삭제버튼(1)
            c1, c2 = st.columns([8.8, 1.2])
            with c1:
                # HTML로 예쁜 태그 그리기 (CSS .memory-box 사용)
                st.markdown(
                    f'<div class="memory-box" style="border-left-color: {col_color};">{mem}</div>', 
                    unsafe_allow_html=True
                )
            with c2:
                # [핵심] type="secondary"를 줘서 CSS에서 투명하게 만듦
                if st.button("✕", key=f"del_{i}", type="secondary", help="삭제"):
                    delete_memory(i)
                    st.rerun()
        
        st.divider()
        new_input = st.text_input("직접 추가", placeholder="예: 무조건 화이트", label_visibility="collapsed")
        if st.button("➕ 추가하기", type="primary", use_container_width=True):
            if new_input:
                add_memory(new_input)
                st.rerun()

def render_carousel():
    """채팅 내 추천 카드"""
    st.markdown("##### 🎁 추천 제품")
    cols = st.columns(3)
    products = st.session_state.recommended_products
    
    for i, p in enumerate(products):
        with cols[i]:
            # 카드 디자인 HTML + 버튼 기능
            with st.container(border=True):
                st.image(p['img'], use_column_width=True)
                st.markdown(f"**{p['name']}**")
                st.caption(f"{p['price']:,}원")
                if st.button("상세보기", key=f"view_{i}", type="primary", use_container_width=True):
                    st.session_state.selected_product = p
                    st.session_state.stage = "product_detail"
                    st.rerun()

# =========================================================
# 4. 메인 실행 로직
# =========================================================

# 1) 설정 페이지
if st.session_state.page == "context_setting":
    st.title("🛒 AI 쇼핑 에이전트")
    st.info("실험을 위해 기본 정보를 입력해주세요.")
    
    with st.container(border=True):
        name = st.text_input("닉네임")
        if st.button("시작하기", type="primary"):
            if name:
                st.session_state.nickname = name
                st.session_state.page = "chat"
                st.rerun()

# 2) 채팅 페이지
else:
    # 상단 스테퍼
    render_stepper()
    
    # 메인 레이아웃 (왼쪽: 메모리 / 오른쪽: 채팅)
    col_mem, col_chat = st.columns([3, 7], gap="medium")
    
    with col_mem:
        render_memory_sidebar()
        
    with col_chat:
        # 채팅창 외관 (컨테이너로 감싸기)
        with st.container(border=True):
            
            # 스크롤 영역 (고정 높이)
            chat_area = st.container(height=500)
            
            with chat_area:
                # 인사말
                if not st.session_state.messages:
                    st.markdown(f"<div class='chat-bubble-ai'>안녕하세요 {st.session_state.nickname}님! 헤드셋 추천을 도와드릴게요. 용도가 어떻게 되세요?</div>", unsafe_allow_html=True)
                
                # 대화 내용 렌더링
                for msg in st.session_state.messages:
                    if msg["role"] == "user":
                        st.markdown(f"<div class='chat-bubble-user'>{msg['content']}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='chat-bubble-ai'>{msg['content']}</div>", unsafe_allow_html=True)
                
                # [단계별 특수 UI 렌더링]
                
                # 요약 단계
                if st.session_state.stage == "summary":
                    st.info("💡 기준이 충분히 모였습니다. 추천을 진행할까요?")
                    if st.button("추천 보기", type="primary"):
                        st.session_state.recommended_products = make_recommendation() # 점수 기반 추천
                        st.session_state.stage = "comparison"
                        st.rerun()
                
                # 추천 단계
                if st.session_state.stage == "comparison":
                    st.divider()
                    render_carousel()
                    
                # 상세 단계
                if st.session_state.stage == "product_detail":
                    p = st.session_state.selected_product
                    st.divider()
                    c1, c2 = st.columns([1, 2])
                    with c1: st.image(p['img'])
                    with c2:
                        st.subheader(p['name'])
                        st.write(f"**{p['price']:,}원**")
                        st.write(", ".join(p['tags']))
                        
                        b1, b2 = st.columns(2)
                        if b1.button("목록으로", type="secondary"):
                            st.session_state.stage = "comparison"
                            st.rerun()
                        if b2.button("구매하기", type="primary"):
                            st.session_state.stage = "purchase_decision"
                            st.session_state.final_choice = p
                            st.rerun()
                            
                # 구매 완료
                if st.session_state.stage == "purchase_decision":
                    st.balloons()
                    st.success(f"🎉 {st.session_state.final_choice['name']} 구매 완료!")

            # 입력창 (채팅창 하단에 붙어있음)
            with st.form("chat_input", clear_on_submit=True):
                c1, c2 = st.columns([8.5, 1.5])
                user_input = c1.text_input("메시지", placeholder="입력하세요...", label_visibility="collapsed")
                submit = c2.form_submit_button("전송", type="primary", use_container_width=True)
                
                if submit and user_input:
                    # 유저 메시지 저장
                    st.session_state.messages.append({"role":"user", "content":user_input})
                    
                    # 1. 카테고리 이탈 방지
                    drift_words = ["스마트폰", "갤럭시", "아이폰"]
                    if any(w in user_input for w in drift_words):
                        st.session_state.messages.append({"role":"assistant", "content":"죄송해요, 저는 헤드셋만 추천해드려요."})
                        st.rerun()
                    
                    # 2. 부정 반응 체크
                    if is_negative_response(user_input):
                         st.session_state.messages.append({"role":"assistant", "content":"알겠습니다. 다른 중요한 점을 살펴볼게요."})
                         st.rerun()

                    # 3. 메모리 추출
                    mems = extract_memory_gpt(user_input, str(st.session_state.memory))
                    for m in mems: add_memory(m)
                    
                    # 4. 상태 자동 전환 (탐색 -> 요약)
                    if st.session_state.stage == "explore" and len(st.session_state.memory) >= 4:
                        st.session_state.stage = "summary"
                    
                    # 5. GPT 응답 (요약/추천 단계가 아닐때만)
                    if st.session_state.stage not in ["summary", "comparison", "product_detail"]:
                        reply = get_gpt_response(user_input)
                        st.session_state.messages.append({"role":"assistant", "content":reply})
                    
                    st.rerun()
