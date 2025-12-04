# =========================================================
# 자연어 메모리 정제
# =========================================================
def naturalize_memory(text):
    text = text.strip()
    replace_map = {
        "깔끔": "깔끔한 디자인을 선호하고 있어요.",
        "미니멀": "미니멀한 디자인을 선호하고 있어요.",
        "레트로": "레트로 스타일을 선호하고 있어요.",
        "블랙": "색상은 블랙 계열을 선호하고 있어요.",
        "화이트": "색상은 화이트 계열을 선호하고 있어요.",
    }
    for k, v in replace_map.items():
        if k in text:
            return v
    return text

# =========================================================
# 최우선 기준 추출
# =========================================================
def detect_priority(mems):
    for m in mems:
        if "(가장 중요)" in m:
            base = m.replace("(가장 중요)", "").strip()
            return base
    return None

# =========================================================
# 메모리 변경 함수들
# =========================================================
def add_memory(text):
    text = naturalize_memory(text)
    ss = st.session_state

    # 중복 질문 방지
    for m in ss.memory:
        if text in m or m in text:
            return

    ss.memory.append(text)

    # priority 표시가 있으면 기존 priority 제거
    if "(가장 중요)" in text:
        ss.memory = [m.replace("(가장 중요)", "") for m in ss.memory]
        ss.memory[-1] = text

def delete_memory(idx):
    ss = st.session_state
    if 0 <= idx < len(ss.memory):
        del ss.memory[idx]

def update_memory(idx, text):
    ss = st.session_state
    if "(가장 중요)" in text:
        ss.memory = [m.replace("(가장 중요)", "") for m in ss.memory]
    ss.memory[idx] = text

# =========================================================
# 메모리 요약
# =========================================================
def build_summary_from_memory(name, mems):
    if not mems:
        return f"{name}님, 아직 명확한 기준이 정해지지 않았어요!"

    lines = [f"• {m.replace('(가장 중요)', '').strip()}" for m in mems]

    prio = detect_priority(mems)

    header = f"[@{name}님의 메모리 요약_지금 나의 쇼핑 기준은?]\n\n"
    body = "지금까지 확인된 기준은 다음과 같아요:\n\n" + "\n".join(lines)

    if prio:
        body += f"\n\n그중에서도 가장 중요한 기준은 **‘{prio}’**이에요."

    tail = (
        "\n\n좌측 **쇼핑 메모리 패널에서 언제든 수정할 수 있어요.**\n"
        "기준을 바꾸면 추천 후보도 달라집니다!\n"
        "준비되셨다면 아래 버튼을 눌러 추천을 받아보세요 👇"
    )
    return header + body + tail

# =========================================================
# 추천 로직
# =========================================================
def make_recommendation():
    mems = st.session_state.memory

    # 단순 필터링 방식
    scored = []
    for p in PRODUCTS:
        score = 0
        for m in mems:
            if "음질" in m and "음질" in p["tags"]:
                score += 1
            if "노이즈" in m and "노이즈" in p["tags"]:
                score += 1
            if "착용감" in m and "착용감" in p["tags"]:
                score += 1
            if "디자인" in m and "디자인" in p["tags"]:
                score += 1
            if "예산" in m and p["price"] <= extract_budget(mems):
                score += 1
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]

# =========================================================
# personalized reason
# =========================================================
def generate_personalized_reason(product, mems, name):
    key = []
    for m in mems:
        if "음질" in m: key.append("음질")
        if "노이즈" in m: key.append("노이즈캔슬링")
        if "착용감" in m: key.append("착용감")
        if "디자인" in m: key.append("디자인")
    key = list(dict.fromkeys(key))[:2]

    if key:
        intro = f"{name}님께서 중요하게 보신 **{', '.join(key)}** 기준을 중심으로 살펴봤을 때, "
    else:
        intro = f"{name}님의 전반적인 기준을 고려하면, "

    reason = []

    if "음질" in product["tags"]:
        reason.append("음질 평가가 매우 좋아요.")
    if "노이즈캔슬링" in product["tags"]:
        reason.append("노이즈캔슬링 성능이 우수해요.")
    if "착용감" in product["tags"]:
        reason.append("착용감이 편안하다는 리뷰가 많아요.")

    if not reason:
        reason.append("전반적인 품질과 만족도가 높아요.")

    return intro + " ".join(reason)
