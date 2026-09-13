# recon指示書：取引フロー As-Is（KGI K1〜K10 基準・ゼロベース）

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

> **この文書は何か（素人向け1行説明）**：承認済みのゴール（KGI 10本）を物差しに、今のシステムとデータがどこまでできていて何が足りないかを「読むだけ」で数える調査の指示書。

- **親文書**: `docs/specs/transaction-flow/README.md`（設計仕様書・KGI承認 2026-07-02）
- **KGI（この recon 自体の成功条件）**: R1〜R7 の全項目が「生出力（file:line / psql表）」で埋まり、K1〜K10 それぞれについて「現状で満たす／満たさない／存在しない」が Planner が○×判定できる状態。空欄・要約・推測はゼロ。無い物は「なし」。
- **出力先**: 生出力を貼るのが第一義。整理は Planner が行う。

---

## 0. 厳守ルール

- **読み取り専用**。SELECT と `\d` 系のみ。UPDATE/INSERT/DELETE/ALTER/DROP/CREATE/TRUNCATE 禁止。git は read のみ（rebase/commit/push 禁止）。
- **要約禁止・生出力のみ**。コマンドを echo してから出力全文を貼る。所感・解釈・「〜と思われます」禁止。
- 各 Part 冒頭で `date -u`（FRESH-RUN）。
- **出力はファイルに書いてから cat する**（画面コピーの折りたたみ防止。今回の必須方式）。
- Part B の psql は**例外なく** `docker compose exec -T -e PGOPTIONS="-c default_transaction_read_only=on" postgres psql -U jarvis -d jarvis_db` の形（`-e` を落とすと安全装置が効かない）。冒頭 B-0 で `SHOW transaction_read_only;` が `on` であることを確認し、on でなければ中止・報告。
- tenant_004（本番）と tenant_006（QA/DEMO）は**別計上**。
- エラーが出たら**全文を貼る**（エラー自体が発見）。列が無ければ「なし」。

---

# Part A — リポジトリ（origin/main 基準・file:line）

冒頭:
```
cd <リポジトリroot> && git fetch origin && date -u && git rev-parse origin/main
```
以下の各出力は `> /tmp/recon_a.txt` に追記し、最後に `cat /tmp/recon_a.txt` で全文を貼る。

### R1（K1/K2）背骨のFKと「作れなさ」
1. `grep -n "CREATE TABLE" backend/app/services/tenant.py` → leads/deals/companies/orders/contacts/conversation_logs の行番号特定 → 各ブロックを `sed -n 'START,ENDp'` で本文（**lead_id 等のFK・NOT NULL の有無**まで）。
2. 生成経路：`grep -n "def create" backend/app/routers/deals.py backend/app/routers/companies.py backend/app/routers/orders.py` → 各 create 関数の本文を sed で表示し、**lead_id が必須引数か・省略できるか**を file:line で。
3. 会話ログ生成経路：`grep -n "lead_id" backend/app/services/conv_log_writer.py backend/app/routers/conv_logs.py` → lead 無しで書ける経路の有無。

### R2（K3）ファネル6軸の在り処
`grep -n "initiative\|channel_type\|country\|company_size\|store_type\|scale\|business_type" backend/app/services/tenant.py migrations/*.sql | head -60`
→ 6軸（initiative／流入元／国／規模／店舗形態／取扱商材）それぞれについて「**列が有る（型・マスタ参照か自由文字列か）／無い**」を判定できる行を貼る。無い軸は「なし」と明記。

### R3（K4）商談の結果・理由
`grep -n "close_reason\|closed_at\|won\|lost\|status" backend/app/services/tenant.py | grep -i deal`
→ deal の結果（成約/失注）と理由の列・マスタ（close_reasons）の実在を file:line で。

### R4（K6）顧客カルテ画面の現状
`grep -rln "累計\|受注回数\|最終取引\|company detail\|CompanyDetail" frontend/src | head` → 該当画面ファイルを特定し、**表示6要素のうち何が有るか／集計値に手入力欄が有るか**を該当行で。

### R5（K7/K8/K9）受注6事実・進行段階・成約
1. `sed -n` で orders / quotes / invoices / purchase_orders / purchase_order_items / order_financials / order_shipping_details の CREATE ブロック全文（tenant.py の該当行）。
2. `grep -n "payment_method\|currency\|status" backend/app/services/tenant.py | grep -iE "order|invoice|purchase"` → 決済方法・通貨・ステータス列の在り処と、**status が手動入力か**（routers で PATCH/PUT に status があるか：`grep -n "status" backend/app/routers/orders.py | head -20`）。

### R6（K10）派生値の書込経路
`grep -n "total\|cumulative\|profit\|count" backend/app/services/tenant.py | grep -iE "compan|lead|order_financials" | head -30`
→ 集計・利益系の**保存列**の有無。有れば、routers でその列に書き込むエンドポイントを grep（＝手入力経路の実在）。

---

# Part B — 本番DB（既承認の無制限経路・強制読み取り専用）

prod1 で以下を **1つのスクリプトとして /tmp に書き出し → cat** する（前回成功した方式）:

```
ssh prod1 'cd /home/ubuntu/salesanchor && {
  echo "=== date ==="; date -u
  PSQL () { docker compose exec -T -e PGOPTIONS="-c default_transaction_read_only=on" postgres psql -U jarvis -d jarvis_db -c "$1"; }
  echo "=== B0 readonly ==="; PSQL "SHOW transaction_read_only;"
  for t in tenant_004 tenant_006; do
    echo "=== R1 背骨NULL率 ($t) ==="
    PSQL "SELECT '\''deals.lead_id'\'' col,COUNT(*) total,COUNT(lead_id) nn FROM $t.deals UNION ALL SELECT '\''companies.lead_id'\'',COUNT(*),COUNT(lead_id) FROM $t.companies UNION ALL SELECT '\''orders.deal_id'\'',COUNT(*),COUNT(deal_id) FROM $t.orders UNION ALL SELECT '\''conv.lead_id'\'',COUNT(*),COUNT(lead_id) FROM $t.conversation_logs;"
    echo "=== R2 6軸の実データ充足 ($t) ==="
    PSQL "\d $t.leads"
    echo "=== R5 orders/invoices 実列 ($t) ==="
    PSQL "\d $t.orders"
    PSQL "\d $t.invoices"
    echo "=== R5 決済・通貨の充足 ($t) ==="
    PSQL "SELECT COUNT(*) total, COUNT(payment_method) pm, COUNT(currency) cur FROM $t.invoices;" 
    echo "=== R6 派生値保存列の行数 ($t) ==="
    PSQL "SELECT COUNT(*) FROM $t.order_financials;"
  done
} > /tmp/recon_b.txt 2>&1; echo WROTE; wc -l /tmp/recon_b.txt'
ssh prod1 'cat /tmp/recon_b.txt'
```
※ 列名が実在しない場合はエラー全文が /tmp に残る＝それが発見。書き換えず貼る。

---

## 合格条件（Planner照合用KPI）

| # | 項目 | ○の条件 |
|---|---|---|
| R1 | 背骨FK＋生成経路＋NULL率 | 4子種すべてに file:line＋数値。lead無しで作れる経路の有無が確定 |
| R2 | ファネル6軸 | 6軸それぞれ「有（型）／なし」が確定 |
| R3 | 商談の結果・理由 | 列・マスタの実在が file:line で確定 |
| R4 | カルテ画面 | 表示要素の有無＋手入力欄の有無が file:line で確定 |
| R5 | 6事実×7属性・段階・成約 | 実列一覧＋status の手動/自動が確定 |
| R6 | 派生値書込経路 | 保存列と書込エンドポイントの有無が確定 |
| R7 | 全体 | 生出力のみ・FRESH-RUN・エラー全文・無い物は「なし」 |
