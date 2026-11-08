"""見える化サポートチャット ── お客さん役で打ち込むと、裏側の4レーンに矢印が1本ずつ流れる。

  （ラボ直下 labs/scenario1-no-mcp/ から実行する。要 ANTHROPIC_API_KEY。無ければ ../../.env.local を読む）
  uv run --managed-python --python 3.12 --with anthropic replay/chat_server.py
  → http://127.0.0.1:8765 を開く

■ 4レーン
  フロント（ブラウザ） / バックエンド（このファイルのループ） / Claude API / DB（infra/shop.db）

■ ループの中身は agent.py・live.py と同じ
  ① create() で messages と tools を送る → ② stop_reason と content が返る
  → tool_use なら ③ tools.IMPL の自分の関数を実行（SQL が DB に飛ぶ）→ ④ tool_result を messages に積んで ① へ
  → end_turn なら最後の text をお客さんに表示して、次の入力を待つ

■ 画面へ送る方法
  POST /api/send のレスポンスを1行1イベントの JSON（NDJSON）で少しずつ書き出す。ブラウザは fetch で読みながら描く。
  会話が1往復終わるたびに traces/<日時>-live-chatui.json と .html（再生画面）を上書きで残す。
"""
import argparse, datetime, json, os, pathlib, re, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent      # replay/
ROOT = HERE.parent                                  # ラボ直下
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
TRACE_DIR = ROOT / "traces"
PAGE = HERE / "chat.html"

# claude-haiku-4-5 の料金（USD / 100万トークン）。画面の費用メーターの概算に使う
PRICE_IN, PRICE_OUT = 1.0, 5.0
GUARDS = {"none": "対策なし", "prompt": "B: システムプロンプトでお願い", "programmatic": "A: コードの関門"}


def load_env_file():
    """ANTHROPIC_API_KEY が環境変数に無ければ、リポジトリ直下の .env.local から読む（値は表示しない）。"""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    path = ROOT.parent.parent / ".env.local"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.removeprefix("export ").split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.ASCII)   # ASCII：「…comです」の「です」まで拾わない


def customer_emails(messages):
    """お客さん本人が打った文（role:user の文字列）に出てきたメールアドレスを全部拾う。"""
    return {e for m in messages if m["role"] == "user" and isinstance(m["content"], str)
            for e in EMAIL_RE.findall(m["content"])}


def roles(messages):
    """messages の並びを短く表す（live.py と同じ）。"""
    out = []
    for m in messages:
        c = m["content"]
        if isinstance(c, str):
            out.append(m["role"])
        else:
            kinds = {(b["type"] if isinstance(b, dict) else b.type) for b in c}
            out.append(f"{m['role']}({'+'.join(sorted(kinds))})")
    return out


class Chat:
    """1会話ぶんの状態。ブラウザ1枚・自分1人で使う前提なので、サーバー全体で1つだけ持つ。"""

    def __init__(self, guard, structured=False, verify_email=False, form_verify=False):
        self.verify_email = verify_email   # メール照合：実行の前にコードがお客さんの発言と照合する
        self.form_verify = form_verify     # フォーム本人確認：email は入力欄で受け取り、Claude に書き写させない
        self.session_customer = None       # フォームで確認できた顧客（バックエンドだけが持つ）
        import agent, tools, trace_run
        tools.STRUCTURED_ERRORS = structured   # ウ：エラーに searched_email などを入れるか
        self.structured = structured
        from infra import db
        self.guard = guard
        self.messages = []
        self.verified_id = None
        self.called, self.refunds = [], []
        self.usage = {"input_tokens": 0, "output_tokens": 0}
        self.rec = trace_run.Recorder()
        self.started = datetime.datetime.now()
        self.system = agent.PROMPT_GUARD if guard == "prompt" else agent.BASE_SYSTEM
        db.reset()                      # 毎回まっさらな DB から
        self.truth = db.requester_id()

    def current_system(self):
        """毎回の ① で送る system。フォーム本人確認では、確認結果をバックエンドが書き足す（Claude は書き写さない）。"""
        if not self.form_verify:
            return self.system
        c = self.session_customer
        if c:
            return self.system + (f"\n\n【本人確認済み】この顧客は画面のフォームで本人確認が済んでいます："
                                  f"{c['name']} 様（customer_id {c['customer_id']}）。"
                                  "get_customer で確認し直す必要はありません。")
        return self.system + ("\n\n本人確認は画面のフォームで行います。メールアドレスをチャットで聞かず、"
                              "画面上部のフォームから本人確認するよう案内してください。")

    def verify(self, email, emit):
        """フォームから届いた email で、バックエンドのコードが直接本人確認する。Claude は一切通らない。"""
        import tools
        emit({"kind": "user", "from": "front", "to": "back", "title": "フォームから email を送る（Claude は通らない）",
              "json": {"email": email}})
        emit({"kind": "call", "lane": "back", "title": f"🔒 コードが直接実行：get_customer(email=\"{email}\")",
              "json": {"name": "get_customer", "input": {"email": email}, "by": "backend code (not Claude)"}})
        _db_emit[0] = emit
        try:
            out = tools.IMPL["get_customer"](email=email)
        finally:
            _db_emit[0] = None
        ok = bool(out.get("verified"))
        if ok:
            self.session_customer, self.verified_id = out, out["customer_id"]
        emit({"kind": "return", "lane": "back", "json": out,
              "title": f"🔒 本人確認{'OK：' + out['name'] + '（' + out['customer_id'] + '）をバックエンドが保持' if ok else '失敗'}"})
        emit({"kind": "verified", "from": "back", "to": "front", "ok": ok,
              "title": "本人確認の結果を画面に返す", "text": f"{out['name']} 様として確認しました" if ok else "該当する顧客がいません",
              "json": out})
        emit({"kind": "done", "cost": self.cost(), "usage": self.usage, "called": self.called,
              "refunds": len(self.refunds), "wrong_refunds": 0, "trace": ""})

    def cost(self):
        return (self.usage["input_tokens"] * PRICE_IN + self.usage["output_tokens"] * PRICE_OUT) / 1e6

    def send(self, text, emit):
        """お客さんの1発言を受けて、Claude の番が終わるまでループを回す。emit(dict) で画面へ流す。"""
        import agent, tools, trace_run
        client = trace_run.RecordingClient(_anthropic_client(), self.rec)

        emit({"kind": "user", "from": "front", "to": "back", "title": f"お客さんの発言を送る",
              "text": text, "json": {"role": "user", "content": text}})
        self.messages.append({"role": "user", "content": text})

        for _ in range(agent.MAX_TURNS):
            emit({"kind": "request", "from": "back", "to": "api",
                  "title": f"① 送る：messages {len(self.messages)}件 ＋ tools {len(tools.DEFS)}つ",
                  "roles": roles(self.messages),
                  "json": {"model": agent.MODEL, "max_tokens": agent.MAX_TOKENS, "system": self.current_system(),
                           "tools": tools.DEFS, "messages": trace_run.plain(self.messages)}})
            res = client.messages.create(model=agent.MODEL, max_tokens=agent.MAX_TOKENS,
                                         system=self.current_system(), tools=tools.DEFS, messages=self.messages)
            self.usage["input_tokens"] += res.usage.input_tokens
            self.usage["output_tokens"] += res.usage.output_tokens
            self.messages.append({"role": "assistant", "content": res.content})
            uses = [b for b in res.content if b.type == "tool_use"]
            emit({"kind": "response", "from": "api", "to": "back",
                  "title": f"② 返る：stop_reason = \"{res.stop_reason}\"",
                  "stop_reason": res.stop_reason,
                  "tool_uses": [{"name": b.name, "input": b.input} for b in uses],
                  "texts": [b.text for b in res.content if b.type == "text"],
                  "json": trace_run.plain(res), "cost": self.cost()})

            if res.stop_reason != "tool_use":
                reply = "".join(b.text for b in res.content if b.type == "text").strip()
                emit({"kind": "reply", "from": "back", "to": "front",
                      "title": "⑤ end_turn：最後の text をお客さんに表示", "text": reply,
                      "json": {"stop_reason": res.stop_reason, "text": reply}})
                break

            results = []
            for b in uses:
                self.called.append(b.name)
                if b.name in agent.VERIFY_REQUIRED and self.verified_id is None and self.guard == "programmatic":
                    r = {"type": "tool_result", "tool_use_id": b.id, "is_error": True,
                         "content": json.dumps({"error": "本人確認が未完了です。先に get_customer を email 付きで呼んでください。"},
                                               ensure_ascii=False)}
                    results.append(r)
                    emit({"kind": "blocked", "lane": "back",
                          "title": f"⛔ 関門：本人確認前の {b.name} をコードが止めた（関数は呼ばれない）",
                          "json": {"tool_use": {"name": b.name, "input": b.input}, "tool_result": r}})
                    continue

                # ━━ メール照合の関門：Claude が頼んだ email が、お客さんの発言に本当にあるかをコードで確かめる ━━
                #   モデルが何を書こうと、発言にない値では関数を実行しない（モデルの性能に依存しない）
                said = customer_emails(self.messages)
                if (self.verify_email and b.name == "get_customer" and b.input.get("email")
                        and b.input["email"] not in said):
                    r = {"type": "tool_result", "tool_use_id": b.id, "is_error": True,
                         "content": json.dumps({"error": "email が顧客の発言と一致しません。顧客の発言にある値をそのまま使ってください",
                                                "requested_email": b.input["email"],
                                                "emails_in_customer_messages": sorted(said)}, ensure_ascii=False)}
                    results.append(r)
                    emit({"kind": "blocked", "lane": "back",
                          "title": f"⛔ メール照合：{b.input['email']} はお客さんの発言にない → 実行しない",
                          "json": {"tool_use": {"name": b.name, "input": b.input},
                                   "お客さんの発言にあった email": sorted(said), "tool_result": r}})
                    continue

                # ━━ フォーム本人確認：誰のデータを触るかは、Claude の引数ではなくバックエンドが保持する顧客で決める ━━
                inp = dict(b.input)
                if self.form_verify:
                    blocked = None
                    c = self.session_customer
                    if b.name in ("get_customer", *agent.VERIFY_REQUIRED) and c is None:
                        blocked = "フォームでの本人確認がまだです。お客様に画面上部のフォームで確認するよう案内してください"
                    elif b.name == "get_customer":
                        inp = {"email": c["email"]}
                    elif b.name == "lookup_order":
                        inp = {"customer_id": c["customer_id"]}
                    elif b.name == "process_refund":
                        from infra import db
                        o = db.get_order(inp.get("order_id", ""))
                        if not o or o["customer_id"] != c["customer_id"]:
                            blocked = f"注文 {inp.get('order_id')} は本人確認済みのお客様の注文ではありません"
                    if blocked:
                        r = {"type": "tool_result", "tool_use_id": b.id, "is_error": True,
                             "content": json.dumps({"error": blocked}, ensure_ascii=False)}
                        results.append(r)
                        emit({"kind": "blocked", "lane": "back", "title": f"⛔ フォーム本人確認：{b.name} を止めた（{blocked[:24]}…）",
                              "json": {"tool_use": {"name": b.name, "input": b.input}, "tool_result": r}})
                        continue
                    if inp != b.input:
                        emit({"kind": "override", "lane": "back",
                              "title": f"🔒 引数をコードが差し替え：{json.dumps(b.input, ensure_ascii=False)} → {json.dumps(inp, ensure_ascii=False)}",
                              "json": {"Claude が頼んだ引数": b.input, "実際に使う引数（バックエンドが保持する顧客）": inp}})

                emit({"kind": "call", "lane": "back",
                      "title": f"③ 実行：tools.IMPL[\"{b.name}\"](**{json.dumps(inp, ensure_ascii=False)})",
                      "json": {"name": b.name, "input": inp, "tool_use_id": b.id}})
                self.rec.called_this_turn.append(b.name)
                self.rec.add("call", name=b.name, input=inp)
                _db_emit[0] = emit
                try:
                    out = tools.IMPL[b.name](**inp)
                except TypeError as e:
                    out = {"error": f"引数が不正です: {e}"}
                finally:
                    _db_emit[0] = None
                if self.form_verify and inp != b.input and isinstance(out, dict):
                    # 差し替えた事実を Claude にも伝える。伝えないと「頼んだ相手のデータ」だと思い込んで説明してしまう
                    c = self.session_customer
                    out = {**out, "note": f"引数 {json.dumps(b.input, ensure_ascii=False)} は使っていません。"
                                          f"これは本人確認済みの {c['name']} 様（{c['customer_id']}）のデータです。"
                                          "他のお客様の情報はお見せできません。"}
                self.rec.add("return", name=b.name, output=out)
                if b.name == "process_refund" and out.get("refunded"):
                    self.refunds.append(out)
                if b.name == "get_customer" and out.get("verified"):
                    self.verified_id = out["customer_id"]
                title = ("↩ 戻り値：★構造化エラー（searched_email = " + out["searched_email"] + "）"
                         if out.get("errorCategory") else "↩ 戻り値（ただの dict）")
                emit({"kind": "return", "lane": "back", "title": title, "json": out, "structured": bool(out.get("errorCategory")),
                      "refund": out if b.name == "process_refund" and out.get("refunded") else None,
                      "wrong": bool(out.get("refunded")) and out.get("to_customer_id") != self.truth})
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": json.dumps(out, ensure_ascii=False)})

            self.messages.append({"role": "user", "content": results})
            emit({"kind": "tool_result", "lane": "back",
                  "title": f"④ tool_result {len(results)}件を messages に積む（次の①で一緒に送る）",
                  "json": {"role": "user", "content": results}})
        else:
            emit({"kind": "reply", "from": "back", "to": "front",
                  "title": "⚠ ターン上限に到達（未完了で打ち切り）", "text": "（ターン上限で打ち切りました）",
                  "json": {"max_turns": agent.MAX_TURNS}})

        path = self.save()
        wrong = sum(r["to_customer_id"] != self.truth for r in self.refunds)
        emit({"kind": "done", "cost": self.cost(), "usage": self.usage, "called": self.called,
              "refunds": len(self.refunds), "wrong_refunds": wrong,
              "trace": str(path.relative_to(ROOT))})

    def save(self):
        """ここまでの会話を traces/ に書き出す（trace_view で1ステップずつ再生できる形）。"""
        import agent, trace_view
        from infra import db
        events = [dict(e) for e in self.rec.events]
        last = next((e for e in reversed(events) if e["kind"] == "response"), {"body": {}})
        events.append({"kind": "end", "turn": self.rec.turn, "ms": events[-1]["ms"] if events else 0,
                       "stop_reason": last["body"].get("stop_reason"), "db": db.dump(),
                       "summary": {"incident": False, "called": self.called, "refunds": self.refunds,
                                   "wrong_refunds": sum(r["to_customer_id"] != self.truth for r in self.refunds)}})
        for i, e in enumerate(events, 1):
            e["seq"] = i
        trace = {"meta": {"mode": "live", "guard": f"chatui-{self.guard}", "model": agent.MODEL,
                          "started_at": self.started.isoformat(timespec="seconds"),
                          "user_msg": self.messages[0]["content"] if self.messages else "",
                          "true_customer_id": self.truth},
                 "events": events}
        TRACE_DIR.mkdir(exist_ok=True)
        path = TRACE_DIR / f"{self.started:%Y%m%d-%H%M%S}-live-chatui-{self.guard}{'-structured' if self.structured else ''}{'-verify' if self.verify_email else ''}{'-form' if self.form_verify else ''}.json"
        path.write_text(json.dumps(trace, ensure_ascii=False, indent=2))
        trace_view.render([trace], path.with_suffix(".html"))
        return path


_client = None
_db_emit = [None]          # ツール実行中だけ、SQL を画面へ流す先を入れておく
LOCK = threading.Lock()    # 会話は1本ずつ処理する
STATE = {"chat": None}


def _anthropic_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def _on_sql(sql, params, rows):
    emit = _db_emit[0]
    if emit is None:
        return
    sql = " ".join(sql.split())
    STATE["chat"].rec.add("sql", sql=sql, params=params, rows=rows)
    emit({"kind": "sql", "from": "back", "to": "db", "title": f"SQL：{sql[:70]}{'…' if len(sql) > 70 else ''}",
          "json": {"sql": sql, "params": params}})
    emit({"kind": "rows", "from": "db", "to": "back", "title": f"rows {len(rows)}件", "json": rows})


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = PAGE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/info":
            import agent
            from infra import db
            self._json({"user_msg": agent.USER_MSG, "requester_email": db.requester()["email"], "family_name": db.requester()["family_name"],
                        "model": agent.MODEL, "guards": GUARDS,
                        "guard": STATE["chat"].guard if STATE["chat"] else "none"})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/reset":
            body = self._body()
            guard = body.get("guard", "none")
            if guard not in GUARDS:
                return self._json({"error": f"guard は {list(GUARDS)} のどれか"}, 400)
            with LOCK:
                STATE["chat"] = Chat(guard, bool(body.get("structured")), bool(body.get("verify_email")),
                                     bool(body.get("form_verify")))
            return self._json({"ok": True, "guard": guard, "structured": STATE["chat"].structured})
        if self.path not in ("/api/send", "/api/verify"):
            return self.send_error(404)

        body = self._body()
        text = (body.get("text") or body.get("email") or "").strip()
        if not text:
            return self._json({"error": "入力が空です"}, 400)
        if not LOCK.acquire(blocking=False):
            return self._json({"error": "前の発言を処理中です"}, 409)
        try:
            if STATE["chat"] is None:
                STATE["chat"] = Chat("none")
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            def emit(ev):
                self.wfile.write((json.dumps(ev, ensure_ascii=False, default=str) + "\n").encode())
                self.wfile.flush()

            try:
                if self.path == "/api/verify":
                    STATE["chat"].verify(text, emit)
                else:
                    STATE["chat"].send(text, emit)
            except Exception as e:      # API エラーなども画面に出す
                emit({"kind": "error", "title": f"エラー：{type(e).__name__}", "json": {"error": str(e)}})
        finally:
            LOCK.release()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    load_env_file()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY が未設定です（環境変数か リポジトリ直下の .env.local に入れてください）。")
    from infra import db
    db.on_query(_on_sql)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"見える化サポートチャット： http://127.0.0.1:{a.port}   （Ctrl+C で終了）")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
