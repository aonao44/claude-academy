"""ツールの実体 ── ただの自分が書いた関数。Claude とは何の関係もない。

名前は公式 Exam Guide §5 シナリオ1 と同じ4本:
    get_customer / lookup_order / process_refund / escalate_to_human
"""

# ── ダミーの「自社DB」 ───────────────────────────────────────────
# 「田中」が3人いるのが事故の土壌。名前だけでは一意に決まらない。
CUSTOMERS = {
    "C-8831": {"name": "田中太郎", "email": "taro.tanaka@example.com"},
    "C-2044": {"name": "田中花子", "email": "hanako.tanaka@example.com"},
    "C-7195": {"name": "田中健",   "email": "ken.tanaka@example.com"},
}
ORDERS = {
    "O-42": {"customer_id": "C-8831", "item": "ランニングシューズ", "amount": 12800},
    "O-77": {"customer_id": "C-2044", "item": "スニーカー",         "amount": 9800},
    "O-91": {"customer_id": "C-7195", "item": "サンダル",           "amount": 4200},
}


def get_customer(email: str | None = None, name: str | None = None) -> dict:
    """本人確認。email なら一意に確定する。name だけだと確定できない。"""
    if email:
        for cid, c in CUSTOMERS.items():
            if c["email"] == email:
                return {"customer_id": cid, **c, "verified": True}
        return {"error": "該当する顧客がいません", "verified": False}
    if name:
        hits = [{"customer_id": cid, **c} for cid, c in CUSTOMERS.items() if name in c["name"]]
        if len(hits) == 1:
            return {**hits[0], "verified": True}
        return {"error": f"「{name}」に一致する顧客が{len(hits)}件。email が必要です",
                "candidates": len(hits), "verified": False}
    return {"error": "email または name が必要です", "verified": False}


def lookup_order(customer_id: str | None = None, customer_name: str | None = None) -> dict:
    """注文を引く。

    ★ここが穴★ customer_name でも引けてしまうので、本人確認を飛ばせる。
    実際の業務システムにありがちな「便利だが危ない」引数。
    """
    if customer_id:
        hits = [{"order_id": oid, **o} for oid, o in ORDERS.items() if o["customer_id"] == customer_id]
        return {"orders": hits, "resolved_by": "customer_id"}
    if customer_name:
        # 名前で顧客を推測 → 複数該当しても先頭を返してしまう（誤特定の発生源）
        cands = [cid for cid, c in CUSTOMERS.items() if customer_name in c["name"]]
        if not cands:
            return {"error": "該当なし"}
        guessed = cands[0]
        hits = [{"order_id": oid, **o} for oid, o in ORDERS.items() if o["customer_id"] == guessed]
        return {"orders": hits, "resolved_by": "customer_name(推測)", "guessed_customer_id": guessed,
                "ambiguous": len(cands) > 1}
    return {"error": "customer_id または customer_name が必要です"}


def process_refund(order_id: str) -> dict:
    """返金を実行する。★金が動く★"""
    o = ORDERS.get(order_id)
    if not o:
        return {"error": f"注文 {order_id} が見つかりません"}
    return {"refunded": True, "order_id": order_id,
            "amount": o["amount"], "to_customer_id": o["customer_id"]}


def escalate_to_human(reason: str) -> dict:
    """人間のオペレーターに引き継ぐ。"""
    return {"escalated": True, "reason": reason}


IMPL = {"get_customer": get_customer, "lookup_order": lookup_order,
        "process_refund": process_refund, "escalate_to_human": escalate_to_human}


# ── Claude に渡す「説明書」。関数そのものではない ────────────────
DEFS = [
    {
        "name": "get_customer",
        "description": "顧客を本人確認する。email を渡すと顧客を一意に確定できる。name だけでは同姓の顧客が複数いる場合に確定できない。",
        "input_schema": {"type": "object",
                         "properties": {"email": {"type": "string"}, "name": {"type": "string"}}},
    },
    {
        "name": "lookup_order",
        "description": "顧客の注文履歴を取得する。customer_id または customer_name を受け付ける。",
        "input_schema": {"type": "object",
                         "properties": {"customer_id": {"type": "string"},
                                        "customer_name": {"type": "string"}}},
    },
    {
        "name": "process_refund",
        "description": "指定した注文の返金を実行する。実際に金銭が移動する。",
        "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}},
                         "required": ["order_id"]},
    },
    {
        "name": "escalate_to_human",
        "description": "自力で解決できない場合に人間のオペレーターへ引き継ぐ。",
        "input_schema": {"type": "object", "properties": {"reason": {"type": "string"}},
                         "required": ["reason"]},
    },
]
