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

## ファイル構成

```
labs/scenario1-no-mcp/
├── agent.py          ★ エージェントループ。試験範囲（ドメイン1）はここ
├── tools.py          ★ ツールの説明書(DEFS)と実体(IMPL)。試験範囲
├── README.md / コード解説.md
├── infra/            自社DB。試験範囲外（Claude からは見えない）
│   ├── db.py
│   └── shop.db       ← 自動生成・git 管理外
├── replay/           やりとりの記録・再生ツール（学習用の観察装置）
│   ├── trace_run.py
│   ├── trace_view.py
│   └── trace_view.template.html
└── traces/           記録の出力先・git 管理外
```

**読むべきは直下の2本だけ。** `agent.py`（ループ）と `tools.py`（ツール定義）が公式サンプル問題1の舞台で、
`infra/` と `replay/` は「本物らしさ」と「観察」のための足場。コマンドは**すべてラボ直下から実行する**。

---

## 舞台設定（`tools.py`）

ツール名は公式シナリオ1と同じ4本。データは自社DB（`infra/db.py` → SQLite の `infra/shop.db`）に分離してあり、
`tools.py` は `db.py` のクエリ関数だけを呼ぶ。`python3 infra/db.py` で DB を作り直して中身を表示できる（`shop.db` は git 管理外）。

```
agent.py ──④呼ぶ──> tools.py ──> infra/db.py ──SQL──> shop.db   ← ここまで全部自分のコード
agent.py ──①渡す──> Anthropic API（Claude）──②返る──> agent.py   ← API はここだけ
```

| 顧客 | ID | 注文 | 金額 |
|---|---|---|---|
| 田中太郎 | C-8831 | O-42 ランニングシューズ | 12,800円 |
| **田中花子（本当の依頼主）** | **C-2044** | **O-77 スニーカー** | **9,800円** |
| 田中健 | C-7195 | O-91 サンダル | 4,200円 |
| 佐藤健一（Few-shot の例に使う） | C-5510 | O-13 レインコート | 5,600円 |

顧客・注文・返金に加えて、**シナリオの設定も DB 側にある**（`infra/db.py`）。

| 設定 | 意味 | どこで使われるか |
|---|---|---|
| `REQUESTER_EMAIL` | 実際に依頼してきた顧客 | 誤返金の採点（`agent.py` / `trace_run.py`） |
| `REQUESTED_ORDER` | その顧客が返品したい注文 | 依頼文の商品名 |
| `FEWSHOT_EMAIL` | Few-shot の例に出す顧客 | 選択肢 C の会話例 |

依頼文・Few-shot・見本ログの台本は、この3つを起点に組み立てている。
**顧客ID・注文番号・商品名・金額をコードに直書きしていない**ので、`db.py` の初期データを差し替えれば全部追随する。

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

## やりとりを記録して再生する（API キー不要の見本あり）

`agent.py` のループには手を入れず、外側から「①渡す・②返る・④呼ぶ・SQL・⑤戻る」を JSON に記録し、
1ステップずつ再生できる HTML を書き出す。

```bash
python3 replay/trace_run.py --sample --guard none                      # 見本ログ（Claude の応答だけ台本。関数と DB は本物）
python3 replay/trace_run.py --sample --guard programmatic
uv run --with anthropic replay/trace_run.py --guard none               # 実走ログ（要 ANTHROPIC_API_KEY）
python3 replay/trace_view.py traces/A.json traces/B.json -o cmp.html   # 複数本を切り替えて見比べる
```

- 出力先は `traces/<日時>-<sample|live>-<guard>.json` と同名の `.html`（git 管理外）
- 見本2本をまとめたものが `../../_zukai/04_trace-replay.html`
- 仕組み：`replay/trace_run.py` が client を包んで `create()` の出入りを、`tools.IMPL` を包んで関数呼び出しを、
  `db.on_query()` で SQL を記録する。依頼されたのに関数が呼ばれなかった `tool_use` を「A 関門でブロック」と判定する

---

## 見える化サポートチャット（お客さん役で打ち込む → 裏側が矢印で流れる）

```bash
uv run --managed-python --python 3.12 --with anthropic replay/chat_server.py   # → http://127.0.0.1:8765
```

- 左：お客さん役のチャット。右：フロント／バックエンド／Claude API／DB の4レーンに、①送る→②tool_use→③実行（SQL）→④tool_result が起きた順に1本ずつ出る
- 矢印・箱をクリックすると、その瞬間の実 JSON。下の帯には「いま messages に何件積まれ、毎回まるごと送っているか」が出る
- 上のボタンで 対策なし／B（プロンプト）／A（コードの関門）を切り替え（会話と DB は初期化）。A では本人確認前の `lookup_order` が赤い ⛔ で止まる
- チェックボックスで、メールの書き写しミス対策を3段階で試せる：**構造化エラー**（見つからない時に検索値とヒントを Claude に返す。直すかは Claude 次第）／**メール照合**（お客さんの発言に無いメールでの検索をコードが止める）／**フォーム本人確認**（メールは入力欄からコードが直接照合。Claude は書き写さず、照会・返金の対象はコードが確認済みの人に固定）
- 「1本ずつ進める」で Space キーごとに1ステップ。費用は右上に概算表示（1会話 $0.01 前後）
- 1往復ごとに `traces/<日時>-live-chatui-<guard>.json` と再生用 `.html` を上書き保存
- API キーは環境変数か、リポジトリ直下の `.env.local` から読む

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
