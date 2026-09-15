# _zukai

図解の置き場。ブラウザで開く（standalone HTML・外部依存なし・ライト/ダーク対応）。

- [01_agent-overview.html](01_agent-overview.html) — **エージェントの全体像**。①所有権の境界（Claude は DB を触らない）②ステートレスで履歴が毎周伸びる ③`stop_reason` によるループの終わり方 ④⑤ドメイン対応と未実装リスト
- [02_scenario1.html](02_scenario1.html) — **シナリオ1の解剖**（`labs/scenario1-no-mcp/` の中身）。①何がどこにあるか（`DEFS` と `IMPL` の分離）②事故が起きる瞬間（正しい経路 vs 事故の経路）③MCP を足すと何が変わるか ④コード上の差分表
