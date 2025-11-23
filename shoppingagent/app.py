def generate_personalized_reason(product, mems, nickname):
    mem_str = " ".join([naturalize_memory(m) for m in mems])

    preferred_color_match = re.search(r"색상은\s*([^계열]+)\s*계열", mem_str)
    if not preferred_color_match:
        preferred_color_match = re.search(r"색상은\s*([^을를])\s*(을|를)\s*선호", mem_str)

    preferred_color_raw = preferred_color_match.group(1).strip().replace("/", "") if preferred_color_match else None
    preferred_color = preferred_color_raw.lower() if preferred_color_raw else None

    preferred_style_match = re.search(r"디자인은\s*['\"]?([^']+?)['\"]?\s*스타일을 선호", mem_str)
    preferred_style = preferred_style_match.group(1).strip() if preferred_style_match else None

    preferred_usage = None
    if any("산책" in m for m in mems):
        preferred_usage = "산책/가벼움/편안함"
    elif any("출퇴근" in m for m in mems):
        preferred_usage = "출퇴근/가벼움/편안함"
    elif any("운동" in m for m in mems) or any("러닝" in m for m in mems):
        preferred_usage = "운동/가벼움/착용감"

    product_colors_lower = [c.lower() for c in product["color"]]

    if preferred_color and any(c in preferred_color for c in product_colors_lower):
        matched_color = next((c for c in product["color"] if c.lower() in preferred_color), product["color"][0])

        if preferred_style:
            return (
                f"**{matched_color} 색상**이 {nickname}님의 **'{preferred_style}'** 스타일에 잘 어울릴 거예요. "
                f"특히 이 제품은 **{product['review_one']}** 평을 받고 있어요."
            )
        elif any(tag in product["tags"] for tag in ["디자인", "고급"]):
            return (
                f"**{matched_color} 색상**이 준비되어 있고 **디자인** 면에서도 호평을 받는 제품이에요. "
                "시각적 만족도가 높으실 거예요."
            )

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

    previously_recommended_names = [p["name"] for p in st.session_state.recommended_products]

    def score(c):
        s = c["rating"]

        if budget:
            if c["price"] > budget * 1.5:
                return -1000

            if priority == "가격/예산":
                if c["price"] <= budget:
                    s += 4.0
                elif c["price"] <= budget * 1.2:
                    s += 1.0
                else:
                    s -= 3.0
            else:
                if c["price"] <= budget:
                    s += 2.0
                elif c["price"] <= budget * 1.2:
                    s += 0.5
                else:
                    s -= 2.0

        mandatory_pass = True
        for m in mems:
            if "(가장 중요)" in m:
                mem_stripped = m.replace("(가장 중요)", "").strip()
                is_feature_met = False

                if "예산" in mem_stripped:
                    continue

                if "노이즈캔슬링" in mem_stripped and any(tag in c["tags"] for tag in ["노이즈캔슬링", "최상급 노캔", "ANC"]):
                    is_feature_met = True
                elif ("가벼움" in mem_stripped or "착용감" in mem_stripped) and any(
                    tag in c["tags"] for tag in ["가벼움", "경량", "편안함"]
                ):
                    is_feature_met = True
                elif ("음질" in mem_stripped or "사운드" in mem_stripped) and any(
                    tag in c["tags"] for tag in ["균형 음질", "스튜디오", "밸런스", "자연스러운 사운드"]
                ):
                    is_feature_met = True
                elif ("배터리" in mem_stripped) and "배터리" in c["tags"]:
                    is_feature_met = True
                elif ("디자인" in mem_stripped or "스타일" in mem_stripped) and any(
                    tag in c["tags"] for tag in ["디자인", "고급", "프리미엄"]
                ):
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

        if "노이즈캔슬링" in mem and "노이즈캔슬링" in " ".join(c["tags"]):
            s += 1.5
        if ("가벼움" in mem or "가벼운" in mem or "휴대성" in mem) and (
            ("가벼움" in " ".join(c["tags"])) or ("경량" in " ".join(c["tags"]))
        ):
            s += 2.0
        if ("디자인" in mem or "스타일" in mem) and ("디자인" in " ".join(c["tags"])):
            s += 1.0
        if "음질" in mem and ("균형" in " ".join(c["tags"]) or "사운드" in " ".join(c["tags"])):
            s += 0.8

        if "브랜드 감성" in mem and c["brand"] in ["Apple", "Bose", "Sony"]:
            s += 3.0
        if "전문적인 사운드 튜닝" in mem and c["brand"] in ["Sennheiser", "Audio-Technica"]:
            s += 2.5

        s += max(0, 10 - c["rank"])

        if c["name"] in previously_recommended_names:
            if is_reroll:
                s -= 10.0
            else:
                s -= 5.0

        return s

    cands = CATALOG[:]
    cands.sort(key=score, reverse=True)

    current_recs = cands[:3]
    st.session_state.current_recommendation = current_recs

    for p in current_recs:
        if p["name"] not in previously_recommended_names:
            st.session_state.recommended_products.append(p)

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

def recommend_products(name, mems, is_reroll=False):
    products = filter_products(mems, is_reroll)
    budget = extract_budget(mems)

    concise_criteria = []
    for m in mems:
        reason_text = naturalize_memory(m).replace("(가장 중요) ", "").rstrip(".")
        if "예산은 약" in reason_text:
            concise_criteria.append(reason_text.replace("예산은 약", "예산").replace("로 생각하고 있어요", ""))
        elif "중요시" in reason_text or "중요하게 생각하고 있어요" in reason_text:
            concise_criteria.append(reason_text.replace(" 중요시 여겨요", "").replace(" 중요하게 생각하고 있어요", ""))
        else:
            concise_criteria.append(reason_text.replace("이에요", "").replace("고 있어요", ""))

    concise_criteria = [r.strip() for r in concise_criteria if r.strip()]
    concise_criteria = list(dict.fromkeys(concise_criteria))

    header = "🎯 추천 제품 3가지\n\n"

    blocks = []
    for i, c in enumerate(products):
        is_over_budget = budget and c["price"] > budget
        personalized_reason_line = generate_personalized_reason(c, mems, name)

        if is_over_budget:
            reason = (
                f"추천 이유: ⚠️ **예산({budget//10000}만 원)을 초과하지만,** "
                f"**{name}님**의 **다른 기준({', '.join(concise_criteria)})**에 **매우 뛰어나** 추천드려요. "
                f"특히 **{personalized_reason_line}**"
            )
        else:
            reason = (
                f"추천 이유: **{name}님**의 **모든 기준({', '.join(concise_criteria)})**에 부합하며, "
                f"특히 **{personalized_reason_line}**"
            )

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

    tail = (
        "\n\n궁금한 제품을 골라 번호로 물어보시거나, 기준을 바꾸면 추천도 함께 바뀝니다. "
        "새로운 추천을 원하시면 '다시 추천해줘'라고 말해주세요."
    )
    return header + "\n\n---\n\n".join(blocks) + "\n\n" + tail

# =========================================================
# 상세 정보 프롬프트 / GPT 호출
# =========================================================
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
        f"답변은 **줄글이 아닌** '**-**' 또는 '**•**'와 같은 기호나 **번호**를 사용하여 핵심 정보별로 **단락을 나누어** 작성하고, "
        f"**이모티콘**을 적절히 활용하여 가독성을 높여야 합니다."
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
            prompt_content = (
                f"현재 메모리: {memory_text}\n사용자 발화: {user_input}\n"
                f"이전에 선택된 상품이 없습니다. 일반적인 대화를 이어가주세요."
            )
            st.session_state.stage = "explore"
    else:
        stage_hint = ""
        is_design_in_memory = any("디자인/스타일" in m or "디자인은" in m for m in st.session_state.memory)
        is_color_in_memory = any("색상" in m for m in st.session_state.memory)

        is_usage_in_memory = any(
            k in memory_text for k in ["용도로", "운동", "게임", "출퇴근", "여행", "음악 감상"]
        )

        if st.session_state.stage == "explore":
            if is_usage_in_memory and len(st.session_state.memory) >= 2:
                stage_hint += (
                    "[필수 가이드: 사용 용도/상황('출퇴근 용도' 등)은 이미 파악되었습니다. "
                    "절대 용도/상황을 재차 묻지 말고, 다음 단계인 기능(배터리, 착용감, 통화품질 등)에 대한 질문으로 전환하세요.]"
                )

            if is_design_in_memory and not is_color_in_memory:
                stage_hint += (
                    "디자인 기준이 파악되었으므로, 다음 질문은 선호하는 색상이나 "
                    "구체적인 스타일(레트로, 미니멀 등)에 대한 질문으로 전환되도록 유도하세요. "
                )

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

# =========================================================
# 대화/메시지 유틸
# =========================================================
def ai_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})

def user_say(text: str):
    st.session_state.messages.append({"role": "user", "content": text})

# =========================================================
# 유저 입력 처리
# =========================================================
def handle_user_input(user_input: str):
    mems = memory_sentences_from_user_text(user_input)
    if mems:
        for m in mems:
            add_memory(m, announce=True)

    # 상품 상세 보기 선택
    product_re = re.search(r"([1-3]|첫\s*번|두\s*번|세\s*번).*(궁금|골라|선택)", user_input)
    if product_re and st.session_state.stage == "comparison":
        match = product_re.group(1).lower()
        if "첫" in match or "1" in match:
            idx = 0
        elif "두" in match or "2" in match:
            idx = 1
        elif "세" in match or "3" in match:
            idx = 2
        else:
            idx = -1

        if 0 <= idx < len(st.session_state.current_recommendation):
            st.session_state.current_recommendation = [st.session_state.current_recommendation[idx]]
            st.session_state.stage = "product_detail"
            reply = gpt_reply(user_input)
            ai_say(reply)
            return
        else:
            ai_say("죄송해요, 해당 번호의 제품은 추천 목록에 없습니다. 1번부터 3번 중 다시 선택해 주시겠어요?")
            return

    # 다시 추천
    if any(k in user_input for k in ["다시 추천", "다른 상품"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say(
                "추천을 다시 받기 전에 **예산/가격대**를 먼저 알려주시겠어요? "
                "'몇 만 원 이내'로 생각하고 계신지 말씀해주시면 됩니다."
            )
            st.session_state.stage = "explore"
            return

        st.session_state.stage = "comparison"
        comparison_step(is_reroll=True)
        return

    # 기준 충분히 모였는데 예산 없음 → 예산 먼저
    if (
        st.session_state.stage == "explore"
        and len(st.session_state.memory) >= 3
        and extract_budget(st.session_state.memory) is None
    ):
        ai_say(
            "잠깐 멈추고 **예산/가격대**를 먼저 여쭤봐도 될까요? "
            "대략 '**몇 만 원 이내**'로 생각하고 계신지 알려주시면 딱 맞는 제품을 찾아드릴 수 있어요."
        )
        return

    # 기준 & 예산 모두 있음 → 요약 단계로
    if (
        st.session_state.stage == "explore"
        and len(st.session_state.memory) >= 4
        and extract_budget(st.session_state.memory) is not None
    ):
        st.session_state.stage = "summary"
        summary_step()
        return

    # 명시적으로 추천 요청
    if any(k in user_input for k in ["추천해줘", "추천 해줘", "추천좀", "추천", "골라줘"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say(
                "잠시만요! 추천으로 넘어가기 전에 **예산/가격대**를 먼저 여쭤봐도 될까요? "
                "대략 '몇 만 원 이내'로 생각하고 계신지 알려주시면 딱 맞는 제품을 찾아드릴 수 있어요."
            )
            st.session_state.stage = "explore"
            return
        else:
            st.session_state.stage = "summary"
            summary_step()
            return

    # 대화 종료 시도
    if any(k in user_input for k in ["없어", "그만", "끝", "충분"]):
        if extract_budget(st.session_state.memory) is None:
            ai_say(
                "추천을 받기 전에 **예산/가격대**만 확인하고 싶어요! "
                "대략 '몇 만 원 이내'로 생각하시나요?"
            )
            st.session_state.stage = "explore"
            return
        else:
            st.session_state.stage = "summary"
            summary_step()
            return

    # 단계별 일반 처리
    if st.session_state.stage in ["explore", "product_detail"]:
        reply = gpt_reply(user_input)
        ai_say(reply)
        return

    if st.session_state.stage == "summary":
        ai_say("정리된 기준을 한 번 확인해보시고, 아래 버튼을 눌러 추천을 받아보셔도 좋아요 🙂")
        return

    if st.session_state.stage == "comparison":
        reply = gpt_reply(user_input)
        ai_say(reply)
        return

# =========================================================
# 요약/비교 스텝
# =========================================================
def summary_step():
    st.session_state.summary_text = generate_summary(st.session_state.nickname, st.session_state.memory)
    ai_say(st.session_state.summary_text)

def comparison_step(is_reroll=False):
    rec = recommend_products(st.session_state.nickname, st.session_state.memory, is_reroll)
    ai_say(rec)

# =========================================================
# 메모리 제어창 (좌측 패널)
# =========================================================
def top_memory_panel():
    st.markdown("### 🧠 나의 쇼핑 기준")
    st.caption("AI가 파악한 기준이 현재 구매 상황과 다를 경우, 아래에서 직접 수정하거나 삭제할 수 있어요.")

    with st.container():
        if len(st.session_state.memory) == 0:
            st.caption("아직 파악된 정보가 없습니다. 대화 중에 기준이 차곡차곡 쌓일 거예요.")
        else:
            for i, item in enumerate(st.session_state.memory):
                cols = st.columns([6, 1])
                with cols[0]:
                    display_text = naturalize_memory(item)
                    key = f"mem_edit_{i}"
                    new_val = st.text_input(
                        f"메모리 {i+1}",
                        display_text,
                        key=key,
                        label_visibility="collapsed",
                    )

                    if new_val != display_text:
                        updated_mem_text = new_val.strip().replace("(가장 중요) ", "").replace(".", "")
                        if "이내로 생각하고 있어요" in new_val:
                            updated_mem_text = updated_mem_text
                        elif "디자인/스타일" in new_val:
                            updated_mem_text = "디자인/스타일을 중요시하다"
                        else:
                            updated_mem_text = updated_mem_text + "다"

                        if "(가장 중요)" in new_val:
                            updated_mem_text = "(가장 중요) " + updated_mem_text

                        update_memory(i, updated_mem_text)

                with cols[1]:
                    if st.button("삭제", key=f"del_{i}"):
                        delete_memory(i)

        st.markdown("---")
        st.markdown("##### ➕ 새로운 기준 추가")
        new_mem = st.text_input(
            "새 메모리 추가",
            placeholder="예: 운동용으로 가벼운 제품이 필요해요 / 15만원 이내로 생각해요",
            label_visibility="collapsed",
        )
        if st.button("추가"):
            if new_mem.strip():
                add_memory(new_mem.strip(), announce=True)

# =========================================================
# 채팅 UI (우측 패널)
# =========================================================
def chat_interface():
    st.markdown("### 🎧 AI 쇼핑 에이전트와 대화하기")
    st.caption("대화를 통해 기준을 정리하고, 그 기준에 맞는 헤드셋 추천을 받아보는 실험입니다.")

    col_mem, col_chat = st.columns([0.36, 0.64], gap="medium")

    with col_mem:
        top_memory_panel()

        if st.session_state.notification_message:
            st.info(st.session_state.notification_message, icon="📝")
            st.session_state.notification_message = ""

    with col_chat:
        st.markdown("#### 💬 대화창")

        # 처음 진입 시, 웰컴 메시지를 상단에 바로 찍기
        if not st.session_state.messages and st.session_state.nickname:
            ai_say(
                f"안녕하세요 {st.session_state.nickname}님! 😊 저는 당신의 AI 쇼핑 도우미예요.\n"
                "대화를 통해 기준을 기억하며 블루투스 헤드셋을 함께 찾아볼게요.\n"
                "우선, 어떤 용도로 사용하실 예정인가요?"
            )

        # 기존 메시지 위에서부터 순서대로 출력
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            elif msg["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
            elif msg["role"] == "system_notification":
                st.info(msg["content"], icon="📝")

        # 요약 단계일 때: 버튼 제공
        if st.session_state.stage == "summary":
            summary_message_exists = any(
                ("메모리 요약" in m["content"]) for m in st.session_state.messages if m["role"] == "assistant"
            )

            if not summary_message_exists or st.session_state.just_updated_memory:
                summary_step()
                st.session_state.just_updated_memory = False

            with st.chat_message("assistant"):
                if st.button("🔍 이 기준으로 추천 받기"):
                    if extract_budget(st.session_state.memory) is None:
                        ai_say(
                            "아직 예산을 여쭤보지 못했어요. 추천을 시작하기 전에 "
                            "**대략적인 가격대(예: 30만원 이내)**를 말씀해주시겠어요?"
                        )
                        st.session_state.stage = "explore"
                    else:
                        st.session_state.stage = "comparison"
                        comparison_step()

        if st.session_state.stage == "comparison":
            if not any(
                "🎯 추천 제품 3가지" in m["content"] for m in st.session_state.messages if m["role"] == "assistant"
            ):
                comparison_step()

        user_input = st.chat_input("메시지를 입력하세요.")
        if user_input:
            user_say(user_input)
            handle_user_input(user_input)

# =========================================================
# 사전 정보 입력 페이지 (이름 + 취향 한 번에)
# =========================================================
def context_setting():
    st.markdown("### 🧾 실험 준비 (1/3단계)")
    st.caption("헤드셋 구매에 반영될 기본 정보와 평소 취향을 간단히 입력해 주세요.")

    st.markdown("---")

    # 이름 + 기본 정보 카드
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**① 닉네임**")
    st.caption("실험 중 호칭에 사용할 이름입니다. 실명일 필요는 없습니다.")
    nickname = st.text_input("닉네임 입력", placeholder="예: 홍길동", key="nickname_input")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**② 최근에 산 물건 한 가지**")
    st.caption("최근 3개월 동안 구매한 제품 중 하나를 떠올려 주세요. (카테고리 단위면 충분합니다)")
    purchase_list = st.text_input("최근 구매 품목", placeholder="예: 옷 / 신발 / 시계 / 태블릿 등", key="purchase_list_input")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**③ 그때 좋아했던 색상**")
    st.caption("해당 품목에서 특히 마음에 들었던 색상을 입력해 주세요. 이 취향이 헤드셋 추천에도 반영됩니다.")
    color_option = st.text_input("선호 색상", placeholder="예: 화이트 / 블랙 / 네이비 등", key="color_input")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("**④ 그 구매에서 가장 중요했던 기준**")
    st.caption("해당 품목을 살 때 무엇을 가장 중요하게 보셨나요?")
    priority_option = st.radio(
        "가장 중요했던 기준을 선택해 주세요.",
        ("디자인/스타일", "가격/가성비", "성능/품질", "브랜드 이미지"),
        index=None,
        key="priority_radio",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("헤드셋 쇼핑 시작하기 (3단계로 이동)"):
        if not nickname.strip() or not purchase_list.strip() or not priority_option or not color_option.strip():
            st.warning("모든 항목을 입력해 주세요.")
            return

        st.session_state.nickname = nickname.strip()

        color_mem = f"색상은 {color_option.strip()}을 선호해요."
        particle = get_eul_reul(priority_option)
        priority_mem = f"(가장 중요) {priority_option}{particle} 중요시 여겨요."

        add_memory(color_mem, announce=False)
        add_memory(priority_mem, announce=False)

        st.session_state.messages = []
        st.session_state.stage = "explore"
        st.session_state.page = "chat"

# =========================================================
# 라우팅
# =========================================================
if st.session_state.page == "context_setting":
    context_setting()
else:
    chat_interface()

