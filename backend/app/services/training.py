import re
import unicodedata

ROLES = [
    {"id": "lin", "name": "林悦", "title": "企业人事专员"},
    {"id": "chen", "name": "陈浩", "title": "项目招聘顾问"},
    {"id": "wang", "name": "王宇", "title": "校园朋友"},
]

TOPICS = {
    "mandate": (
        "授权",
        "委托",
        "招聘主体",
        "签约",
        "哪家单位",
        "哪家公司",
        "用人单位",
        "谁负责",
        "招聘关系",
        "主体",
    ),
    "scope": (
        "资料",
        "证件",
        "身份证",
        "银行卡",
        "收集",
        "隐私",
        "保存",
        "用途",
        "接收方",
        "个人信息",
    ),
    "source": (
        "群里",
        "群消息",
        "转述",
        "亲自",
        "来源",
        "核实过",
        "官方渠道",
        "证据",
        "出处",
        "原始",
    ),
}
REPLIES = {
    "lin": {
        "mandate": "我负责的是云栖工坊（虚构）的校招。职位说明、面试邀请和拟签约单位都标注同一主体；我只能确认自己负责的岗位。",
        "scope": "聊岗位和预约面谈只需要一个称呼。现在不需要提交身份资料；你可以只用“候选人甲”。",
        "source": "我的信息来自本企业的岗位说明。你可以核对说明中的招聘主体和面试通知落款，我不能替别的项目作证。",
        "job": "这是面向应届生的运营助理岗，日常工作有活动记录和数据整理。流程是了解岗位、业务面谈、书面确认。",
        "register": "先了解岗位即可。我们在面谈后提供正式的书面流程，现在不用填写材料。",
        "other": "我是林悦，负责云栖工坊的校招。你想先了解工作内容，还是这次招聘的流程？",
    },
    "chen": {
        "mandate": "我负责项目对接，目前手头只有岗位摘要，没有用人单位给我的书面授权。招聘主体和签约单位这两项我现在无法确认。",
        "scope": "我手上的预登记说明没有写清资料交给谁、为什么需要、保存多久。这几项我还不能给出依据；先不要提交任何资料。",
        "source": "这个机会来自项目对接的信息摘要。我手里暂时没有可供独立核验的正式公告。",
        "job": "项目在了解运营支持岗位的候选人意向，工作偏资料整理和日常沟通。我现在能介绍的是岗位摘要。",
        "register": "摘要里提到了候选人预登记，但我只有这份简要说明。你希望先核对其中哪一项？",
        "other": "我是这次机会的项目对接人陈浩。岗位内容、招聘关系或流程，你想先聊哪部分？",
    },
    "wang": {
        "mandate": "我只在校园群看见过介绍，不认识用人单位的人，也没看到他们的委托材料。",
        "scope": "我没看过正式的资料说明，不知道谁会收到这些信息。我不想把猜测当成事实告诉你。",
        "source": "我是在校园群里看到转发的，没有亲自核实。别人转过这条消息，不等于岗位已经得到确认。",
        "job": "群里转发时写的是运营相关，我没去面试过。你要是想确认岗位细节，得问直接负责的人。",
        "register": "我没走过预登记，不能说明它是不是必要流程。",
        "other": "嗨，我是王宇。之前在校园群里见过类似的招聘消息，你是想问我是从哪儿知道的吗？",
    },
}
CLUES = {
    ("chen", "mandate"): "mandate",
    ("chen", "scope"): "scope",
    ("chen", "source"): "source",
    ("wang", "source"): "source",
    ("wang", "mandate"): "source",
}
LABELS = {"mandate": "招聘主体与授权", "scope": "资料收集边界", "source": "消息来源"}


def is_sensitive(text: str) -> bool:
    value = unicodedata.normalize("NFKC", text)
    compact = re.sub(r"[\s()\-]", "", value)
    return bool(
        re.search(r"(?<!\d)(?:1[3-9]\d{9}|\d{15,19}[Xx]?)(?!\d)", compact)
        or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value)
        or re.search(
            r"(?:住址|家庭地址|我住在)\s*[:：为是]?\s*[^，。！？?]{2,40}(?:号|室|单元|栋)",
            value,
        )
    )


def analyze(role_id: str, text: str, phase: str) -> dict:
    hits = [
        topic for topic, words in TOPICS.items() if any(word in text for word in words)
    ]
    doubtful = any(
        word in text
        for word in (
            "未核实",
            "未经",
            "没核实",
            "没有核实",
            "不能证明",
            "不代表",
            "不等于",
            "不清楚",
            "不明确",
            "不透明",
            "说不清",
            "不必要",
            "超出",
            "超范围",
            "不一致",
            "缺少",
            "没有授权",
        )
    )
    asks = any(
        word in text
        for word in (
            "？",
            "?",
            "请问",
            "请说明",
            "请提供",
            "我想核实",
            "希望核对",
            "我要核对",
            "能否",
            "是不是",
            "为什么",
            "怎么核实",
            "谁负责",
            "哪家",
        )
    )
    recognized = hits if doubtful else []
    actions = [f"verify:{p}" for p in hits] if asks else []
    if recognized and any(
        w in text
        for w in (
            "只是",
            "原文",
            "对比",
            "因为",
            "不能证明",
            "不等于",
            "不代表",
            "不足以",
        )
    ):
        actions.append("weigh_source")
    topic = (
        hits[0]
        if hits
        else (
            "register"
            if "预登记" in text
            else "job"
            if any(w in text for w in ("岗位", "工作", "流程", "面试", "实习", "薪资"))
            else "other"
        )
    )
    if role_id == "wang" and "source" in hits:
        topic = "source"
    clue = CLUES.get((role_id, topic))
    target = (
        4
        if any(a.startswith("verify:") for a in actions)
        else 3
        if recognized or clue
        else 2
        if topic == "register"
        else 1
        if topic == "job"
        else 0
    )
    return {
        "reply": REPLIES[role_id][topic],
        "next_phase": f"S{max(int(phase[1]), target)}",
        "actions": actions,
        "recognized": recognized,
        "disclosed": [clue] if clue else [],
    }


def make_report(turns: list[dict], decision: dict | None) -> dict:
    seen = {c for t in turns if t["presented"] for c in t["disclosed"]}
    identified = {c for t in turns for c in t["recognized"]}
    checks = {a[7:] for t in turns for a in t["actions"] if a.startswith("verify:")}
    weighed = [t for t in turns if "weigh_source" in t["actions"]]
    reason = (decision or {}).get("reason") or ""
    reason_topics = {
        k for k, words in TOPICS.items() if any(w in reason for w in words)
    }

    def evidence(rows):
        return [
            {
                "message_id": t["message_id"],
                "role_id": t["role_id"],
                "excerpt": t["text"],
            }
            for t in rows[:4]
        ]

    def dimension(key, label, weight, score, explanation, rows):
        return {
            "key": key,
            "label": label,
            "weight": weight,
            "score": score,
            "explanation": explanation,
            "evidence": evidence(rows),
        }

    def names(items):
        return "、".join(LABELS[k] for k in LABELS if k in items)

    opportunities = seen | identified
    risk_score = (
        round(100 * len(identified) / len(opportunities)) if opportunities else None
    )
    dimensions = [
        dimension(
            "risk",
            "风险识别",
            25,
            risk_score,
            ("你明确指出了：" + names(identified) + "。")
            if identified
            else "没有找到你明确指出疑点的原话。"
            if seen
            else "尚无已呈现的风险线索或主动识别记录。",
            [t for t in turns if t["recognized"]],
        ),
        dimension(
            "verify",
            "主动核实",
            30,
            min(100, 50 * len(checks)) if turns else None,
            ("你主动核实了：" + names(checks) + "。重复提问只计一次。")
            if checks
            else "没有观察到针对主体、资料或来源的核实问题。",
            [t for t in turns if any(a.startswith("verify:") for a in t["actions"])],
        ),
        dimension(
            "decision",
            "决策合理性",
            25,
            (
                min(100, 60 * len(reason_topics & (checks | identified | seen)))
                if reason and turns
                else None
            ),
            (
                "判断有书面理由；本项看理由是否引用训练中核实或指出的事项，不按选择本身加分。"
            )
            if reason
            else "没有提交决策理由，无法据此评价判断过程。",
            [
                t
                for t in turns
                if reason
                and (
                    set(t["recognized"])
                    | {a[7:] for a in t["actions"] if a.startswith("verify:")}
                )
                & reason_topics
            ],
        ),
        dimension(
            "analysis",
            "证据分析",
            20,
            (100 if weighed else 0) if opportunities or weighed else None,
            "你区分了陈述和证据，并解释了信息的局限。"
            if weighed
            else "尚未观察到对来源可靠性或证据局限的明确比较。",
            weighed,
        ),
    ]
    if reason:
        dimensions[2]["evidence"].append(
            {"message_id": None, "role_id": None, "excerpt": reason}
        )
    scores = [d["score"] for d in dimensions]
    total = (
        None
        if None in scores
        else round(sum(d["score"] * d["weight"] / 100 for d in dimensions))
    )
    return {
        "dimensions": dimensions,
        "total": total,
        "decision": decision,
        "rubric_version": "demo-0.1",
        "strengths": (["主动追问了" + names(checks) + "。"] if checks else [])
        + (["用自己的话明确指出了疑点。"] if identified else []),
        "suggestions": (
            []
            if "mandate" in checks
            else ["向发布方询问用人单位和书面授权，而不只问岗位待遇。"]
        )
        + (
            []
            if weighed
            else ["在作决定前，用一句话区分“对方声称的”和“你已经核实的”。"]
        )
        or ["下次可以换一种决策，并比较支撑理由是否仍然成立。"],
    }
