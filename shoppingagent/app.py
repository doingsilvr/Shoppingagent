# =========================================================
# 채팅 UI (우측 패널)
# =========================================================
def chat_interface():

    # -------------------------------------------------------
    # 🔵 상단 단계 진행바
    # -------------------------------------------------------
    st.markdown(
        """
        <div class='progress-container'>
            <div class='progress-step {s1}'>1. 선호 조건 탐색</div>
            <div class='progress-step {s2}'>2. 선호도 요약</div>
            <div class='progress-step {s3}'>3. AI 추천</div>
        </div>
        """.format(
            s1="active" if st.session_state.stage == "explore" else "",
            s2="active" if st.session_state.stage == "summary" else "",
            s3="active" if st.session_state.stage == "comparison" else ""
        ),
        unsafe_allow_html=True
    )

    # -------------------------------------------------------
    # 🟣 상단 타이틀 박스
    # -------------------------------------------------------
    st.markdown(
        """
        <div class='title-card'>
            <h2 style='margin:0;'>🎧 AI 쇼핑 에이전트와 대화하기</h2>
            <p style='margin:4px 0 0; font-size:14px; color:#555;'>
                대화를 통해 기준을 정리하고, 그 기준에 맞는 헤드셋 추천을 받아보는 실험입니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------------------------------
    # 좌측 메모리 / 우측 대화창 레이아웃
    # -------------------------------------------------------
    col_mem, col_chat = st.columns([0.38, 0.62], gap="medium")

    # -------------------------------------------------------
    # 🔔 메모리 알림 (5초 후 자동 제거)
    # -------------------------------------------------------
    if st.session_state.notification_message:
        st.info(st.session_state.notification_message, icon="📝")

        st.markdown(
            """
            <script>
            setTimeout(function() {
                const alerts = parent.document.querySelectorAll('.stAlert');
                alerts.forEach(a => a.style.display='none');
            }, 5000);
            </script>
            """,
            unsafe_allow_html=True
        )

    st.session_state.notification_message = ""

    # -------------------------------------------------------
    # 🧠 좌측 — 메모리 패널
    # -------------------------------------------------------
    with col_mem:
        st.markdown("<div class='memory-panel-fixed'>", unsafe_allow_html=True)
        top_memory_panel()
        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------
    # 💬 우측 — 대화창
    # -------------------------------------------------------
    with col_chat:

        # 대화창 제목
        st.markdown("#### 💬 대화창")

        # 초기 웰컴 메시지
        if not st.session_state.messages and st.session_state.nickname:
            ai_say(
                f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요.\n"
                "대화를 통해 고객님의 중요 정보들을 기억하며 블루투스 헤드셋을 함께 찾아볼게요.\n"
                "우선, 어떤 용도로 사용하실 예정인가요?"
            )

        # -------------------------------------------------------
        # 🔵 말풍선 영역 (스크롤 박스)
        # -------------------------------------------------------
        st.markdown("<div class='chat-display-area'>", unsafe_allow_html=True)

        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(
                    f"<div class='chat-bubble-user'>{msg['content']}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='chat-bubble-ai'>{msg['content']}</div>",
                    unsafe_allow_html=True
                )

        st.markdown("</div>", unsafe_allow_html=True)

        # -------------------------------------------------------
        # ⭐ Summary 단계
        # -------------------------------------------------------
        if st.session_state.stage == "summary":

            summary_message_exists = any(
                ("@" in m["content"]) and ("메모리 요약" in m["content"])
                for m in st.session_state.messages
                if m["role"] == "assistant"
            )

            if not summary_message_exists or st.session_state.just_updated_memory:
                summary_step()
                st.session_state.just_updated_memory = False
                st.rerun()

            if st.button("🔍 이 기준으로 추천 받기", key="summary_btn"):
                if extract_budget(st.session_state.memory) is None:
                    ai_say(
                        "아직 예산을 여쭤보지 못했어요. 추천을 시작하기 전에 "
                        "대략적인 가격대(예: 30만원 이내)를 말씀해주시겠어요?"
                    )
                    st.session_state.stage = "explore"
                else:
                    st.session_state.stage = "comparison"
                    comparison_step()

                st.rerun()

        # -------------------------------------------------------
        # ⭐ AI 추천 단계
        # -------------------------------------------------------
        if st.session_state.stage == "comparison":
            if not any(
                "🎯 추천 제품 3가지" in m["content"]
                for m in st.session_state.messages
                if m["role"] == "assistant"
            ):
                comparison_step()

        # -------------------------------------------------------
        # ⭐ 사용자 입력 폼
        # -------------------------------------------------------
        with st.form(key="chat_form", clear_on_submit=True):
            user_input_area = st.text_area(
                "메시지를 입력하세요.",
                key="main_text_area",
                placeholder="헤드셋에 대해 궁금한 점이나 원하는 기준을 자유롭게 말씀해주세요.",
                label_visibility="collapsed"
            )
            submit_button = st.form_submit_button("전송")

        if submit_button and user_input_area:
            user_say(user_input_area)
            handle_user_input(user_input_area)
