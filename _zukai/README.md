# _zukai

図解の置き場。ブラウザで開く（standalone HTML・外部依存なし・ライト/ダーク対応）。

- [01_agent-overview.html](01_agent-overview.html) — **エージェントの全体像**。①所有権の境界（Claude は DB を触らない）②ステートレスで履歴が毎周伸びる ③`stop_reason` によるループの終わり方 ④⑤ドメイン対応と未実装リスト
- [02_scenario1.html](02_scenario1.html) — **シナリオ1の解剖**（`labs/scenario1-no-mcp/` の中身）。①何がどこにあるか（`DEFS` と `IMPL` の分離）②事故が起きる瞬間（正しい経路 vs 事故の経路）③MCP を足すと何が変わるか ④コード上の差分表
- [03_scenario1-code-map.html](03_scenario1-code-map.html) — **シナリオ1のコード地図**。①Anthropic の仕様で固定の名前（オレンジ）と自分で決めた名前（青緑）の色分け ②API の境界と渡す・返る・呼ぶの往復（①〜⑦）③`DEFS` と `IMPL` の役割 ④境界を越える JSON ⑤返ってきたものの処理手順。`agent.py` / `tools.py` 内の 🟧🟦 コメントと対応
- [04_trace-replay.html](04_trace-replay.html) — **やりとり再生**。`labs/scenario1-no-mcp/trace_run.py` の記録を1ステップずつ再生（自社DB / 自分の関数 / 自分のコード / Anthropic API の4列）。見本ログ2本（対策なし・A）を切り替えて比較。実走ログは `trace_run.py` で生成
- [05_domain1-terms.html](05_domain1-terms.html) — **ドメイン1 用語リファレンス**（エージェント設計27%）。`stop_reason` 全値とループ制御／リクエスト・レスポンスの固定フィールド／content ブロック／ツール定義と `tool_choice`／ツールの3分類と Anthropic 定義ツールの宣言／往復の規則と落とし穴／オーケストレーション用語／頻出のひっかけ／英日対照
- [06_basics.html](06_basics.html) — **前提知識の基礎**。JSON／配列と単一値の区別／HTTP とステータスコード／Python の最低限／ステートレス／JSON Schema／トークンと上限／SDK とは／用語ミニ辞書。05 を読む前の土台
