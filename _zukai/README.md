# _zukai

図解の置き場。ブラウザで開く（standalone HTML・外部依存なし・ライト/ダーク対応）。

- [01_agent-overview.html](01_agent-overview.html) — **エージェントの全体像**。①所有権の境界（Claude は DB を触らない）②ステートレスで履歴が毎周伸びる ③`stop_reason` によるループの終わり方 ④⑤ドメイン対応と未実装リスト
- [02_scenario1.html](02_scenario1.html) — **シナリオ1の解剖**（`labs/scenario1-no-mcp/` の中身）。①何がどこにあるか（`DEFS` と `IMPL` の分離）②事故が起きる瞬間（正しい経路 vs 事故の経路）③MCP を足すと何が変わるか ④コード上の差分表
- [03_scenario1-code-map.html](03_scenario1-code-map.html) — **シナリオ1のコード地図**。①Anthropic の仕様で固定の名前（オレンジ）と自分で決めた名前（青緑）の色分け ②API の境界と渡す・返る・呼ぶの往復（①〜⑦）③`DEFS` と `IMPL` の役割 ④境界を越える JSON ⑤返ってきたものの処理手順。`agent.py` / `tools.py` 内の 🟧🟦 コメントと対応
- [04_trace-replay.html](04_trace-replay.html) — **やりとり再生**。`labs/scenario1-no-mcp/trace_run.py` の記録を1ステップずつ再生（自社DB / 自分の関数 / 自分のコード / Anthropic API の4列）。見本ログ2本（対策なし・A）を切り替えて比較。実走ログは `trace_run.py` で生成
- [05_domain1-terms.html](05_domain1-terms.html) — **ドメイン1 用語リファレンス**（エージェント設計27%）。`stop_reason` 全値とループ制御／リクエスト・レスポンスの固定フィールド／content ブロック／ツール定義と `tool_choice`／ツールの3分類と Anthropic 定義ツールの宣言／往復の規則と落とし穴／オーケストレーション用語／頻出のひっかけ／英日対照
- [06_basics.html](06_basics.html) — **前提知識の基礎**。JSON／配列と単一値の区別／HTTP とステータスコード／Python の最低限／ステートレス／JSON Schema／トークンと上限／SDK とは／用語ミニ辞書。05 を読む前の土台
- [07_q7-narrow-decomposition.html](07_q7-narrow-decomposition.html) — **公式サンプル Q7 の図解**（シナリオ3・Task Statement 1.2）。①長い問題文を状況・証拠・症状・設問に分けて英日対照 ②テーマ→コーディネーター→サブエージェント→レポートの流れで分野が消えた場所 ③選択肢 A〜D を図の上に置いて消去 ④直し方（指示の修正／反復改善ループ）
- [08_agent-sdk-picture.html](08_agent-sdk-picture.html) — **Agent SDK のサポートエージェント**。①あなたのサーバー（アプリ・Agent SDK・MCP サーバー）と Anthropic API の位置関係 ②返金1件の流れ（アプリ／SDK／Claude の分担） ③失敗の返し方（"Operation failed." と構造化エラーの比較、問題 1.6） ④用語の整理
- [09_mcp-flow.html](09_mcp-flow.html) — **MCP はこう走る**（Gmail を例に）。①会話は2本（Claude⇄クライアントの Messages API／クライアント⇄MCP サーバーの MCP）②起動時の tools/list から最終回答までの時系列（①〜⑫）③クライアント役とサーバーの置き場（claude.ai／Claude Code／Agent SDK）④練習用コード（no-mcp）との関係
- [10_tool-choice.html](10_tool-choice.html) — **tool_choice の見え方**（シナリオ6・問題 6.1/6.2）。①白紙の用紙（tools）→記入済みの用紙（tool_use）の1往復 ②auto / any / 名前指定で許される返し方 ③請求書・契約書・領収書が届いたときの結果比較 ④使い分けの早見表
- [11_api-map.html](11_api-map.html) — **API 呼び出しの全体マップ**（シナリオ6）。リクエスト（model / system / messages / tools → 用紙 → input_schema → properties・required / tool_choice）とレスポンス（stop_reason / content → text・tool_use → name・input）の入れ子図。送る側と返る側の名前の対応、プロンプトで直す vs 構造で直す（6.1〜6.3 の比較）、全部入りのコード
- [12_agent-loop.html](12_agent-loop.html) — **エージェントループの全体図**（シナリオ1・stop_reason でループを続けるか終えるかの問題）。①グラレコの全体イメージ ②4者（フロント／バックエンド／Claude API／DB）の位置関係 ③「返品したい」から「返金完了」までの時系列図（関門の位置つき） ④毎周 messages を送り直す様子 ⑤1・2周目の実際のデータ ⑥判断しているコード3行 ⑦誤答 A・C・D がどこで壊れるか
- [13_live-run-replay.html](13_live-run-replay.html) — **本物の API で動かした記録の再生画面**（2026-11-01、`labs/scenario1-no-mcp/replay/live.py --auto-reply`）。聞き返し → tool_use 2つ同時（本人確認と名前だけの注文検索）→ 別人の注文を提示、までを1ステップずつ再生。解説は 12 の 8 番
