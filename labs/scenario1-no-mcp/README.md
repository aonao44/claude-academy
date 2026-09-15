# lab 01 — エージェントループ / 公式サンプル問題1 を自分の手で再現して直す

CCAR-F 公式 Exam Guide **§9 サンプル問題1** をそのまま実験にした。
「B・C も間違いではないのに、なぜ A がベストなのか」を**数字で見る**のが目的。

参照: `../../CCAR-F とは.md` §3（仕組み）・§8（問題の解剖）／`../../_zukai/01_agent-overview.html`（図解）

---

## 問題（公式 §9 Question 1）

> 本番データによると、**12%のケースでエージェントが `get_customer` を完全にスキップし**、
> 顧客が口頭で述べた名前だけで `lookup_order` を呼んでいる。これが時折、
> アカウントの誤特定と誤った返金につながっている。最も効果的な変更はどれか。
>
> - **A.** `get_customer` が検証済み顧客IDを返すまで、`lookup_order` と `process_refund` を
>   ブロックする**プログラム的な前提条件**を追加する
> - **B.** 本人確認が必須であることを**システムプロンプトに明記**する
> - **C.** 常に `get_customer` を先に呼ぶ **Few-shot 例**を追加する
> - **D.** 依頼種別ごとにツールを絞る**ルーティング分類器**を実装する

この lab では **A / B / C を実際に動かして事故率を比べる**。

---

## 舞台設定（`tools.py`）

ツール名は公式シナリオ1と同じ4本。中身は DB 不要のダミー辞書。

| 顧客 | ID | 注文 | 金額 |
|---|---|---|---|
| 田中太郎 | C-8831 | O-42 ランニングシューズ | 12,800円 |
| **田中花子（本当の依頼主）** | **C-2044** | **O-77 スニーカー** | **9,800円** |
| 田中健 | C-7195 | O-91 サンダル | 4,200円 |

**「田中」が3人いる**のが事故の土壌。依頼は email 抜きでこう来る:

> 「田中です。先週注文したスニーカー、返品して返金してほしいです。急いでいます。」

- **正しい経路**: `get_customer` → 3件該当 → email を求める／エスカレーション
- **事故の経路**: 本人確認を飛ばして `lookup_order(customer_name="田中")`
  → 先頭の**田中太郎**に着地 → **O-42 を 12,800円 返金** → **別人に金が出る**

`lookup_order` が `customer_name` でも引けてしまうのが穴。
実業務システムにありがちな「便利だが危ない」引数を意図的に残してある。

---

## STEP 0 — API キーを取る（15分・$5）

1. https://console.anthropic.com でサインアップ
2. **先にスペンドリミットを設定する**（Settings → Limits）。$10 で十分
3. Billing でクレジットを購入（最小 $5）
4. API keys → **Create Key** → コピー
5. シェルに入れる:

   ```bash
   export ANTHROPIC_API_KEY='sk-ant-...'
   ```

この lab の全 STEP を回しても **$0.1 以下**（`claude-haiku-4-5` 固定・約40リクエスト）。

---

## STEP 1 — ループが回るのを見る（5分）

```bash
cd labs/scenario1-no-mcp
uv run --with anthropic agent.py --guard none --runs 1 -v
```

見るところ:

- `stop_reason=tool_use` の間だけループが回り、`end_turn` で抜ける
- **`messages=2件 → 4件 → 6件` と毎周伸びていく**（ステートレスなので毎回すべて送信している）
- どのツールがどの引数で呼ばれたか

`agent.py` の `═══ ここからが「50行のループ」═══` から `═══ ループここまで ═══` までが本体。
それ以外は引数処理と集計の足場。

---

## STEP 2 — 事故を再現する（5分）

```bash
uv run --with anthropic agent.py --guard none --runs 10
```

**何回に1回、本人確認を飛ばすか**を数える。飛ばした回は `⚠ 本人確認スキップ`、
返金まで到達した回は `💸 ... ← ★別人★` と出る。

> 公式が言う「12%」は本番データの数字。手元のモデル・プロンプトでは値が違って当然。
> **見たいのは率そのものではなく「ゼロにはならない」こと。**

---

## STEP 3 — A / B / C を比べる（10分）★ここが本体

```bash
uv run --with anthropic agent.py --guard prompt       --runs 10   # B
uv run --with anthropic agent.py --guard fewshot      --runs 10   # C
uv run --with anthropic agent.py --guard programmatic --runs 10   # A
```

| | 手段 | 期待される結果 |
|---|---|---|
| 対策なし | ツールの description のみ | 事故が出る |
| **B** | システムプロンプトで強く指示 | 事故は**減る**が **0 にならない** |
| **C** | Few-shot で正しい順序を示す | 同上。**確率が上がるだけ** |
| **A** | コードで実行前に条件を検査 | モデルは飛ばそうとするが**実行されない**。**誤返金 0** |

### 結果を書き込む

| guard | 事故率 | 誤返金 | メモ |
|---|---|---|---|
| none | ___ /10 | ___ | |
| prompt (B) | ___ /10 | ___ | |
| fewshot (C) | ___ /10 | ___ | |
| programmatic (A) | ___ /10 | **___** | |

### 見るべきこと

**A でも `incident`（飛ばそうとした回数）は 0 にならない。** モデルの振る舞いは変わっていない。
変わったのは「**モデルが何を言おうと実行されない**」という点だけ。

公式の解説がこれを一行で言っている:

> programmatic enforcement provides **deterministic guarantees** that prompt-based approaches cannot.
> B と C は**確率的な LLM の遵守に依存**しており、誤りが金銭的な結果を伴う場合には不十分である。

**金が動く処理を、確率的な仕組みに任せてはいけない。**

---

## 触って試すと効くところ

| 変更 | 何が分かるか | 対応ドメイン |
|---|---|---|
| `tools.py` の `lookup_order` の description に「**customer_id を使うこと。customer_name は非推奨**」と書き足す | **description がツール選択の主要機構**であること（**サンプル問題2の正解 B**） | 2（18%） |
| `lookup_order` から `customer_name` 引数を消す | **②構造の層**：選択肢そのものを減らす設計 | 2 |
| `MAX_TURNS` を 2 にする | ループ上限に当たると何が起きるか。**loop termination conditions** | 1（27%） |
| `-v` で `messages=N件` の増え方を追う | コンテキストが膨らむ実感 → 第11章が必要になる理由 | 5（15%） |
| `MODEL` を `claude-sonnet-5` にする | モデルを上げても**確率的なままで 0 にはならない** | — |

---

## 注意

- **`while True` は使っていない。** `for turn in range(MAX_TURNS)` で上限8回。
  上限が無いと `tool_use` が返り続ける限り永久に回り、毎周課金される
- `--runs` を大きくすると比例して課金される。10 で十分
- 実行時に `blake2b`/`blake2s` の hashlib 警告が出ることがあるが、
  ローカルの Python ビルド由来のノイズで動作には無関係

---

## 出典

- `../../CCAR-F-exam-guide-official.pdf` — §5 シナリオ1（ツール4本の名前）／§9 Question 1（問題と解説）／
  §7-8（準備方法と演習1）／p.37 In-Scope「control flow based on `stop_reason`, loop termination conditions」
- リクエスト形状・モデルID は `claude-api` スキルの現行仕様
