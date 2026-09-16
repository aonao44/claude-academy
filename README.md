# claude-academy

Claude 認定試験（Anthropic 公式）の取得と、転職先での実務に向けたインプットを回すプロジェクト。

**→ 何をすべきか・順番・URL は `学習プラン.md`。教材カタログは `教材.md`。ここは事実と未確認事項の置き場。**

## ゴール

**Claude Certified Architect: Foundations (CCAR-F) の合格。** その後 CCDV-F。

理由：
1. 出題範囲（エージェント設計27% / Claude Code 20% / プロンプト20% / MCP 18% / コンテキスト管理15%）が、
   自分の実務（サブエージェント運用・回帰テスト・フォールバック設計・AgentCore マルチエージェントPoC）とほぼ一致
2. **CCAO-F は Claude Partner Network の Tier 算定対象外**＝頭数にすらならないので取らない
3. **CCDV-F は CCAR-F の前提にならない**（CCDV-F 最大配点の Messages API 33.1% は CCAR-F の配点に入っていない）。
   CCAR-F は4資格中最も範囲が広く、**越えると CCDV-F / CCAR-P が楽になる**（4資格全取得者の推奨と一致）

## 背景

- 2027年春に FDE（Forward Deployed Engineer）として入社予定
- 入社予定先から「Claude 認定試験」「OpenAI 社の FDE 試験」の受験を要請された
- 入社予定先は Anthropic の認定パートナーを目指している
  → 受験させられる＝**CPN には加盟済みと考えるのが自然**（組織ドメインのメールがないと登録すらできない制度のため）

> 入社予定先の固有情報・自分の待遇・未確認事項はリポジトリに含めない（ローカルの `PRIVATE.md`）。

## 公式の入口（ログイン不要で閲覧できる）

**https://anthropic-partners.skilljar.com/claude-certified-architect-foundations-certification**

ここに「**Download the exam guide**」「**Register for the exam**」「準備コース7本」が全部ある。

## 試験の事実（2026年9月時点）

| 認定 | 対象 | 問題数/時間 | 費用 | Tier算定 |
|---|---|---|---|---|
| Associate: Foundations (CCAO-F) | 非エンジニア | 60問 / 120分 | $99 | **対象外** |
| Developer: Foundations (CCDV-F) | API でアプリ・エージェントを開発する人 | 53問 / 120分 | $125 | 対象 |
| **Architect: Foundations (CCAR-F)** | **Claude Code・エージェント・MCP を含む本番システムを設計する人** | **60問 / 120分** | **$125** | 対象 |
| Architect: Professional (CCAR-P) | 上級（前提資格は不要） | 63問 / 120分 | $175 | 対象 |

- 実施：**Pearson VUE**（オンライン監督 or テストセンター）
- 合格：1000点満点中 **720点**（100〜1,000のスケールドスコア）
- **seat time は約135分**（試験時間120分＋前後の手続き）
- 出題形式：**Multiple choice（4択1正解）＋ Multiple response（複数選択・個数は問題文に明記）**
- 有効期限：**12ヶ月**
- **更新**：期限前なら Partner Academy の**無料・オープンブックのオンライン更新アセスメントに合格**すれば12ヶ月延長。
  受講するだけでは延長されない。期限切れ後は本試験の再受験
- 再受験：不合格後 14日 → 30日 → 90日と待機が延長（12ヶ月で最大4回、都度満額）
- パートナー階層（Select / Preferred / Global Premier）で受験料50%割引あり
- **資格間に必須の前提試験はない**

### CCAR-F の出題構造（公式ページ＋Purcell 氏の問題集の前書きより）

**配点は公式ページで確定**（旧メモの「サードパーティ記事に基づく」は解消済み）：

| ドメイン | 配点 | 60問中 |
|---|---|---|
| Agentic Architecture & Orchestration | **27%** | 16問 |
| Claude Code Configuration & Workflows | **20%** | 12問 |
| Prompt Engineering & Structured Output | **20%** | 12問 |
| Tool Design & MCP Integration | **18%** | 11問 |
| Context Management & Reliability | **15%** | 9問 |

- **シナリオベース。6つのシナリオバンクから4つがランダム出題され、各シナリオ約15問**（4×15=60問）
- 6シナリオの題材：①カスタマーサポートエージェント（MCP tools, escalation）②Claude Code でのコード生成
  ③マルチエージェント研究システム（coordinator-subagent）④Claude Agent SDK での開発者生産性ツール
  ⑤CI/CD への Claude Code 統合 ⑥非構造データの構造化抽出
- **公式 Exam Guide にはサンプル問題が12問入っている**（CCDV-F版は3問）
- Domain 1 は概念でなく**実装レベル**：`stop_reason` の分岐、`PostToolUse` フック、`fork_session`、context 分離
- 出題の質：**「正解と明らかな誤りの間で選ぶのではなく、良い答えとベストな答えの間で選ぶ」**

### 詰まる可能性がある2点

1. **試験は英語のみ。** 公式ページに `Language: English` と明記。日本語試験は未提供、提供時期も未発表
   - ただし**学習コース（Claude Academy）は日本語対応済み**（2026年8月公開）
   - 120分で60問＝1問2分。**英語の読解速度が合否を分ける**（受験記3件が一致）
2. **受験には Claude Partner Network 加盟組織のドメインメールが必須。** 個人 Gmail では登録不可
   - → **入社後、かつ入社予定先が加盟していることが前提**

### Claude Partner Network の Tier 要件（Services Track）

資格保有者数だけでは上がらない。**3要素の組み合わせ**で評価される。

| Tier | Active Certified Individuals | 本番導入した共同顧客 | 公開顧客事例 |
|---|---|---|---|
| Select | **10人以上** | 直近12ヶ月で2社以上 | 1件以上 |
| Preferred | 100人以上 | 15社以上 | 3件以上 |
| Global Premier | 1,000人以上 | 3地域以上で100社以上 | 15件以上 |

- **Active 判定には「有効な対象資格を持ち、かつ直近90日以内に Claude を利用している」が含まれる。**
  取って使わない人はカウントされない → Claude Code を日常的に使っている自分は自動的に満たす
- 入社予定先は公開顧客事例の要件を既に満たしており、**残っているのは認定者10人**。自分はその枠の1人

## 手元の資産（PDF はリポジトリに含まない）

**この3点は第三者の著作物なので、リポジトリには入れていない**（`.gitignore` 済み）。
各自で下記から取得し、リポジトリ直下にこのファイル名で置くと、本文中の参照が繋がる。

| ファイル名 | 正体 | 入手先 |
|---|---|---|
| `CCAR-F-exam-guide-official.pdf` | **公式 Exam Guide v1.0（39ページ）。範囲を定義している唯一の一次資料** | [認定ページ](https://anthropic-partners.skilljar.com/claude-certified-architect-foundations-certification) の「Download the exam guide」（ログイン不要） |
| `guide_ja.pdf` | paullarionov 氏の非公式日本語学習ガイド 92ページ。**配点は公式と完全一致**し、構成も公式ブループリント準拠。**公式ではない** | [paullarionov/claude-certified-architect](https://github.com/paullarionov/claude-certified-architect) の `pdf/guide_ja.pdf` |
| `CCAR-F.pdf` | Matthew Purcell 氏の予想問題集 60問（"Written following Exam Guide v1.0 (July 2026)"）。**公式ではない** | 著者の配布元から各自取得 |

**公式は英語のみ。** 日本語試験は未提供で、多言語版の公式資料は存在しない。

## OpenAI 側（参考・当面動かせない）

- 要請された「OpenAI の FDE 試験」は **OpenAI Partner Network 内の Forward Deployed Experts** とみられる
- **公式記述で確認**：複雑な企業導入に取り組むパートナー向けに、**創設パートナーの一部と試験運用中**。
  適格なパートナー実務者が OpenAI の Forward Deployed Engineering チームと連携できるようにするもの。
  参加者は OpenAI の技術・プレイブック・変革パターンに触れられる
  → **資格試験ではない。**「英語のみか」という問いはそもそも成立しない
- 別に**認定コンサルタント**の制度がある（2026年末までに30万人育成が目標、$1.5億ドル投資）。
  こちらは試験。**ティアは Select / Advanced / Elite の3段階**、
  **スペシャライゼーションは Codex / サイバーセキュリティ / エージェント**
- OpenAI Partner Network の公式パートナー一覧には日本勢も複数掲載されている
- **試験言語の記載は公開情報になし。** 詳細はパートナーポータル（要ログイン）の中
- **「相当難しい」の裏付けは存在しない**（フル試験が一般稼働していないため合格率も体験談もない）
- 今すぐ取れるのは **OpenAI Academy の無料コース**（academy.openai.com。**ただし英語のみ・UIに言語切替なし**）
  - 公式が「バッジ・修了証は資格ではない」と明記

## 未確認事項

入社予定先に確認すべき事項（加盟状況・費用負担・優先度・入社日など）は
ローカルの `PRIVATE.md` に置き、beads の `claude-academy-256` で追跡している。


## 次の一手

1. **`学習プラン.md` STEP 0** — 公式 Exam Guide を Skilljar から入手する（30分）
2. **STEP 1** — 公式サンプル問題12問 → Purcell v2（60問）を120分計って解き、**ドメイン別に自己採点**
3. 75%を切ったドメインのコースだけ受ける（STEP 2）
4. 未確認事項（`PRIVATE.md`）を入社予定先への議事メモに含めて送る

## 関連

手元の関連リポジトリ（RAG+eval のハンズオン、Bedrock AgentCore のマルチエージェント PoC、
LangGraph + Agentic RAG の PoC）との対応は `PRIVATE.md` に記載。

- `labs/scenario1-no-mcp/` — CCAR-F シナリオ1（カスタマーサポートエージェント）を MCP 抜きで実装
- `labs/scenario1-mcp/` — 同シナリオの MCP 版（未実装）
- `_zukai/` — エージェントの全体像とシナリオ1の解剖（図解 HTML）
