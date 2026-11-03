"""ツールの実体 ── ただの自分が書いた関数。Claude とは何の関係もない。

  agent.py ──④呼ぶ──> tools.py（ここ）──> infra/db.py ──SQL──> infra/shop.db

名前は公式 Exam Guide §5 シナリオ1 と同じ4本:
    get_customer / lookup_order / process_refund / escalate_to_human

■ コメント内の凡例
  🟧 = Anthropic の仕様で固定された名前 / 🟦 = 自分で決めた名前
  このファイルに 🟧 が出てくるのは、末尾の DEFS（Claude に渡す説明書）だけ。
  関数と IMPL は全部 🟦 で、API の境界を越えない。DB の読み書きは db.py に任せる。

■ agent.py との関係
  DEFS … agent.py ① の create(tools=...) で Claude に「渡す」。Claude が読むのはこれだけ
  IMPL … agent.py ④ で自分のコードが引いて「呼ぶ」。Claude は見ることも呼ぶこともできない
"""

from infra import db   # 🟦 自社DB（infra/db.py → shop.db）。Claude からは見えない

# ── 自社DB は db.py に分離した ─────────────────────────────────────
# ツール関数は DB を直接触らず、db.py のクエリ関数だけを呼ぶ。
#   agent.py ──④呼ぶ──> tools.py（ここ）──> infra/db.py ──SQL──> infra/shop.db
# 「田中」が3人いる初期データは infra/db.py の SEED_CUSTOMERS を参照。
db.ensure()

# 🟦 True にすると、email で見つからなかったときのエラーを「構造化」して返す（予想問題 1.6・1.7）。
#    実際に何で検索したか（searched_email）を見せて、Claude が自分の書き写しミスに気づけるようにする。
#    見える化チャット（replay/chat_server.py）の画面からオン／オフできる。
STRUCTURED_ERRORS = False


# 🟦 以下の関数名・引数名はすべて自分で決めたもの。
#    ただし引数名は DEFS の input_schema の properties と揃える。
#    agent.py ④ で b.input（dict）を **展開して渡すため（自分で決めた約束事で、API の仕様ではない）。
def get_customer(email: str | None = None, name: str | None = None) -> dict:
    """本人確認。email なら一意に確定する。name だけだと確定できない。"""
    if email:
        c = db.find_customer_by_email(email)
        if c:
            return {**c, "verified": True}
        if STRUCTURED_ERRORS:
            return {"error": "該当する顧客がいません", "verified": False,
                    "errorCategory": "not_found",     # 何が起きたか
                    "isRetryable": True,              # 正しい値で呼び直せば成功しうる
                    "searched_email": email,          # 実際にこの値で検索した
                    "hint": "顧客の発言にあるメールアドレスと searched_email を一字ずつ照合し、"
                            "違っていれば顧客に聞き返さず正しい値で呼び直すこと"}
        return {"error": "該当する顧客がいません", "verified": False}
    if name:
        hits = db.find_customers_by_name(name)
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
        return {"orders": db.orders_of(customer_id), "resolved_by": "customer_id"}
    if customer_name:
        # 名前で顧客を推測 → 複数該当しても先頭を返してしまう（誤特定の発生源）
        cands = db.find_customers_by_name(customer_name)
        if not cands:
            return {"error": "該当なし"}
        guessed = cands[0]["customer_id"]
        return {"orders": db.orders_of(guessed), "resolved_by": "customer_name(推測)",
                "guessed_customer_id": guessed, "ambiguous": len(cands) > 1}
    return {"error": "customer_id または customer_name が必要です"}


def process_refund(order_id: str) -> dict:
    """返金を実行する。★金が動く★（refunds テーブルに実際に1行書き込む）"""
    o = db.get_order(order_id)
    if not o:
        return {"error": f"注文 {order_id} が見つかりません"}
    refund_id = db.insert_refund(order_id, o["amount"], o["customer_id"])
    return {"refunded": True, "refund_id": refund_id, "order_id": order_id,
            "amount": o["amount"], "to_customer_id": o["customer_id"]}


def escalate_to_human(reason: str) -> dict:
    """人間のオペレーターに引き継ぐ。"""
    return {"escalated": True, "reason": reason}


# ━━ 実体：ツール名 → 関数 の辞書。全部 🟦。API の境界を越えない ━━
#   agent.py ④ の tools.IMPL[b.name] で使う。
#   キーは DEFS の "name" と同じ綴りにする（Claude が返す b.name の値がこのキーになるため）
IMPL = {"get_customer": get_customer, "lookup_order": lookup_order,
        "process_refund": process_refund, "escalate_to_human": escalate_to_human}


# ── Claude に渡す「説明書」。関数そのものではない ────────────────
# ━━ agent.py ① の create(tools=tools.DEFS) で、境界を越えて Claude に届く ━━
#   🟧 "name" / "description" / "input_schema" … ツール定義のキー（Anthropic の仕様）
#   🟧 "type" / "object" / "properties" / "string" / "required" … JSON Schema の書き方（これも固定）
#   🟦 ツール名・説明文・引数名（"get_customer", "email" など）… 中身は自分で決める
DEFS = [
    {
        "name": "get_customer",                     # 🟧 キー / 🟦 値（ツール名。IMPL のキーと揃える）
        "description": "顧客を本人確認する。email を渡すと顧客を一意に確定できる。name だけでは同姓の顧客が複数いる場合に確定できない。",  # 🟧 キー / 🟦 説明文（Claude がツール選択に使う）
        "input_schema": {"type": "object",          # 🟧 キー / 🟧 JSON Schema
                         # 🟦 "email" と "name" は引数名。この "name" は上のツール名キーとは無関係
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
