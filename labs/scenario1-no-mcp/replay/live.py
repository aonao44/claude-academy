"""本物の API で問い合わせを1件流し、ループの各ステップを起きた順にその場で表示する。

  （ラボ直下 labs/scenario1-no-mcp/ から実行する。要 ANTHROPIC_API_KEY）
  uv run --managed-python --python 3.12 --with anthropic replay/live.py --auto-reply

  --auto-reply    Claude が聞き返して end_turn になったら、お客さん役が本当のメールアドレスを答える
  --reply "文"    お客さん役の返事を自分で決める（複数回指定すると順番に使う）

  終わると traces/<日時>-live-chat.json と .html（1ステップずつ再生できる画面）を書き出す。

■ agent.py との違い
  agent.py は「依頼1通 → Claude の番が終わるまで」の1往復だけを回す。
  ここでは Claude が聞き返したとき（end_turn）に、お客さんの返事を messages に足して会話を続ける。
  ループの中身（create → tool_use なら実行して tool_result を返す）は agent.py と同じ。
"""
import argparse, datetime, json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent      # replay/
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
TRACE_DIR = ROOT / "traces"


def short(x, n=110):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def roles(messages):
    """messages の並びを「user / assistant(tool_use) / user(tool_result)」のように短く表す。"""
    out = []
    for m in messages:
        c = m["content"]
        if isinstance(c, str):
            out.append(m["role"])
        else:
            kinds = {(b["type"] if isinstance(b, dict) else b.type) for b in c}
            out.append(f"{m['role']}({'+'.join(sorted(kinds))})")
    return " / ".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto-reply", action="store_true")
    ap.add_argument("--reply", action="append", default=[])
    a = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY が未設定です。")

    import anthropic, agent, tools, trace_run, trace_view
    from infra import db

    rec = trace_run.Recorder()
    db.reset()
    truth = db.requester_id()
    replies = list(a.reply) + ([f"{db.requester()['email']} です"] if a.auto_reply else [])
    db.on_query(lambda sql, params, rows: (
        rec.add("sql", sql=" ".join(sql.split()), params=params, rows=rows),
        print(f"        🗄  DB: {short(' '.join(sql.split()), 90)}  {params}")))
    client = trace_run.RecordingClient(anthropic.Anthropic(), rec)

    print(f"\n👤 お客さん → バックエンド：「{agent.USER_MSG}」")
    messages = [{"role": "user", "content": agent.USER_MSG}]
    called, refunds, started = [], [], datetime.datetime.now()

    for turn in range(1, agent.MAX_TURNS + 1):
        print(f"\n━━━━━━━━━━ {turn}周目 ━━━━━━━━━━")
        print(f"① バックエンド → Claude：messages {len(messages)}件 ＋ tools {len(tools.DEFS)}つ を送る")
        print(f"     並び：{roles(messages)}")
        res = client.messages.create(model=agent.MODEL, max_tokens=agent.MAX_TOKENS,
                                     system=agent.BASE_SYSTEM, tools=tools.DEFS, messages=messages)
        messages.append({"role": "assistant", "content": res.content})
        print(f"② Claude → バックエンド：stop_reason = \"{res.stop_reason}\"")
        for b in res.content:
            if b.type == "text":
                print(f"     💬 text：「{short(b.text.strip(), 200)}」")
            elif b.type == "tool_use":
                print(f"     📝 tool_use：{b.name}({short(b.input)})   id={b.id}")

        if res.stop_reason != "tool_use":
            if replies:
                r = replies.pop(0)
                print(f"\n   → end_turn：Claude の番が終わった（聞き返し）。お客さんに表示して返事を待つ")
                print(f"👤 お客さん → バックエンド：「{r}」  （messages に user として足して続ける）")
                messages.append({"role": "user", "content": r})
                continue
            print(f"\n⏹  end_turn → ループを抜けて、最後の text をお客さんに表示して終わり")
            break

        results = []
        for b in res.content:
            if b.type != "tool_use":
                continue
            print(f"③ バックエンドが実行：tools.IMPL[\"{b.name}\"](**{short(b.input)})")
            called.append(b.name)
            rec.called_this_turn.append(b.name)
            rec.add("call", name=b.name, input=b.input)
            try:
                out = tools.IMPL[b.name](**b.input)
            except TypeError as e:
                out = {"error": f"引数が不正です: {e}"}
            rec.add("return", name=b.name, output=out)
            if b.name == "process_refund" and out.get("refunded"):
                refunds.append(out)
            print(f"     ↩ 戻り値：{short(out)}")
            results.append({"type": "tool_result", "tool_use_id": b.id,
                            "content": json.dumps(out, ensure_ascii=False)})
        messages.append({"role": "user", "content": results})
        print(f"④ tool_result {len(results)}件を messages に足す（tool_use_id で②と対応）→ 次の周で全部送り直す")
    else:
        print("\n⚠ ターン上限に到達（未完了で打ち切り）")

    wrong = sum(r["to_customer_id"] != truth for r in refunds)
    print(f"\n結果：呼ばれた順 {' → '.join(called) or '(なし)'}  ／ 返金 {len(refunds)}件（うち別人 {wrong}件）")

    last = next(e for e in reversed(rec.events) if e["kind"] == "response")
    rec.add("end", stop_reason=last["body"].get("stop_reason"), db=db.dump(),
            summary={"incident": False, "called": called, "refunds": refunds, "wrong_refunds": wrong})
    rec.finish()
    trace = {"meta": {"mode": "live", "guard": "chat", "model": agent.MODEL,
                      "started_at": started.isoformat(timespec="seconds"),
                      "user_msg": agent.USER_MSG, "true_customer_id": truth},
             "events": rec.events}
    TRACE_DIR.mkdir(exist_ok=True)
    json_path = TRACE_DIR / f"{started:%Y%m%d-%H%M%S}-live-chat.json"
    json_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2))
    html = trace_view.render([trace], json_path.with_suffix(".html"))
    print(f"再生画面：{html}")


if __name__ == "__main__":
    main()
