# card: 便2-2c2b 直し2 海外用の書類に日本の会社の住所を英語の順で載せる（ADR-1061）

- 状態: 草案。PO 2026-11-28「1」（海外用の書類では都道府県を英語名にして英語の順で並べる。作るのはクラウドの係）。電話の形（§D3）と実装の開始は PO の答え待ち。PO の実装の承認が出るまでクラウドに渡さない。
- きっかけ: 2026-11-28 に本番で国内用を入れた。海外用に英語の番地を入れると、見積書に「〒444-2141 愛知県Okazaki8-312 Ryokuyoudai, Kuwabara」と出る（recon.md §15）。
- 設計: docs/handoff/viewer-contract-stage/design.md §3-4e。
- 担当: クラウドの Sonnet。§1 の2ファイルだけを直す。本番・secrets・DB には触らない。PR は作らない（Opus が作る）。
- 基準: origin/main `045abb209`。行番号がずれていたら「変更前」の文字列で場所を探す。件数が §0-3 と合わなければ BLOCKED。
- 危険便か: いいえ（migrations/・deploy.yml・本番 scripts/ に触らない。表・列・入力の決まりは変えない）。
- 本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと

- D1 変えるのは書類に載せる文字の組み立てだけ。backend/app/services/issuer.py の format_issuer_address・get_issuer と、新しい format_issuer_phone の3つ。issuer_rules.py・表・移行・画面・invoice_renderer.py・invoices.py は触らない。
- D2 住所: format_issuer_address に省ける引数 `english: bool = False` を足す。国が JP で english が真のときだけ「番地, 建物, 市区町村, 都道府県名 郵便番号（3桁-4桁）, 国名」の順にする。english が偽の JP と、JP 以外は、今の組み立てを1文字も変えない。
- D3 電話: format_issuer_phone(phone, country_code, dial_code, *, international) を足す。international が真・国が JP・dial_code がある・電話が "0" で始まる、のすべてのときだけ `f"{dial_code} {phone[1:]}"` を返す。それ以外は保存した値のまま（空は ""）。
- D4 get_issuer は SELECT に `pr.name_en AS prefecture_name_en` と `co.dial_code AS country_dial_code` を足す。region が "overseas" のときだけ english・international を真にし、都道府県名は name_en を渡す。"domestic" は今のまま name_ja を渡す。
- D5 旧来の表から読む道（行が無いとき・:102〜:114）は変えない。
- D6 試験の国名・都道府県名・国番号は試験に書かず、seed と国の表から読む（test_issuer.py 冒頭の決まり）。並べ方の単体試験は今の試験と同じく "P"・"Countryname" のような置き字を使う。

## 0. カード発行前チェック

| # | 確かめたこと | 結果 |
|---|---|---|
| 1 | 設計の節（§3-4e）と PO の答えを指している | ○ |
| 2 | 触るファイルを §1 に全部並べた（2） | ○ |
| 3 | 直すファイルの「変更前」の文字列を 045abb209 で数えた（§0-3） | ○ |
| 4 | 危険パス（migrations/・deploy.yml・本番 scripts/）を含まない | ○ |
| 5 | 対象外（入力の決まり・表・画面・PDF の描き方・呼び出し元・旧来の表の道）を書いた | ○ |
| 6 | 画面の文字の変更なし（t() の対象なし） | ○ |
| 7 | 新しい置き場所を作らない（name_en・dial_code は既存の public の表） | ○ |
| 8 | 試験のコマンドは今のリポジトリにある（pytest） | ○ |
| 9 | 停止の条件を §4 に書いた | ○ |
| 10 | 報告の形を §5 に書いた | ○ |

## 0-2. 読んだ節

- docs/ai-agents/executor-checklist.md の 00-common・03-file・10-executor。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md（1手順1コマンド・出力に上限・プレースホルダなし・commit と push は git log で確かめる）・11-lint.md。照合: 手順はすべて `cd` で始まる（L01）・`gh pr create` なし（L08）・`rm ` なし（L11）・`gh run view` なし（L21）・`--admin` `--auto` なし（L18）・`sleep` なし。

## 受領確認

最初の返事の1行目と2行目に次を書く。

```
RECEIVED viewer-contract-bin2-2c2b-fix2 HEAD=（git rev-parse HEAD の40文字）
本報告はカード 便2-2c2b 直し2 海外用の書類に日本の会社の住所を英語の順で載せる の実行結果である
```

## 0-3. 実装前点検

手順2で数える。1つでも違えば停止する（BLOCKED）。

| # | ファイル | 数える文字列 | 期待 |
|---|---|---|---|
| P1 | backend/app/services/issuer.py | 行数（wc -l） | 114 |
| P2 | backend/tests/test_issuer.py | 行数（wc -l） | 352 |
| P3 | backend/app/services/issuer.py | `pr.name_ja AS prefecture_name, co.name AS country_name` | 1 |
| P4 | backend/app/services/issuer.py | `"address": format_issuer_address(row, row["prefecture_name"], row["country_name"]),` | 1 |
| P5 | backend/app/services/issuer.py | `"phone": row["phone"] or "",` | 1 |
| P6 | backend 全体 | `format_issuer_phone` | 0 |

## 1. 触るファイル

| ファイル | 種類 | 何をするか |
|---|---|---|
| backend/app/services/issuer.py | 直す | D1〜D5 |
| backend/tests/test_issuer.py | 直す | §2-2 の試験を足す |

ほかのファイルは触らない。

## 2. 変更

### 2-1. issuer.py

変更前（:30〜:41）:

```python
def format_issuer_address(row: Mapping[str, Any], prefecture_name: str | None, country_name: str | None) -> str:
    """発行元の住所を 1 行にする。日本は〒・都道府県から、海外は通りから国へ。"""
    city = row.get("city") or ""
    address1 = row.get("address1") or ""
    address2 = row.get("address2") or ""
    if row.get("country_code") == "JP":
        postal = row.get("postal_code") or ""
        head = f"〒{postal[:3]}-{postal[3:]} " if postal else ""
        line = f"{head}{prefecture_name or ''}{city}{address1}"
        return f"{line} {address2}" if address2 else line
    tail = f"{row.get('state_region') or ''} {row.get('postal_code') or ''}".strip()
    return ", ".join(p for p in [address1, address2, city, tail, country_name or ""] if p)
```

変更後:

```python
def format_issuer_address(
    row: Mapping[str, Any], prefecture_name: str | None, country_name: str | None, *, english: bool = False
) -> str:
    """発行元の住所を 1 行にする。日本は〒・都道府県から、海外は通りから国へ。
    english=True の日本（海外用の書類。design.md §3-4e）は、通りから国への英語の順にする。"""
    city = row.get("city") or ""
    address1 = row.get("address1") or ""
    address2 = row.get("address2") or ""
    if row.get("country_code") == "JP" and not english:
        postal = row.get("postal_code") or ""
        head = f"〒{postal[:3]}-{postal[3:]} " if postal else ""
        line = f"{head}{prefecture_name or ''}{city}{address1}"
        return f"{line} {address2}" if address2 else line
    if row.get("country_code") == "JP":
        postal = row.get("postal_code") or ""
        postal_text = f"{postal[:3]}-{postal[3:]}" if postal else ""
        tail = f"{prefecture_name or ''} {postal_text}".strip()
    else:
        tail = f"{row.get('state_region') or ''} {row.get('postal_code') or ''}".strip()
    return ", ".join(p for p in [address1, address2, city, tail, country_name or ""] if p)


def format_issuer_phone(
    phone: str | None, country_code: str | None, dial_code: str | None, *, international: bool
) -> str:
    """発行元の電話を書類の形にする。海外用の書類の日本の番号は先頭の 0 を外して国番号を付ける（design.md §3-4e）。"""
    if not phone:
        return ""
    if international and country_code == "JP" and dial_code and phone.startswith("0"):
        return f"{dial_code} {phone[1:]}"
    return phone
```

変更前（:81）:

```python
                   pr.name_ja AS prefecture_name, co.name AS country_name
```

変更後:

```python
                   pr.name_ja AS prefecture_name, pr.name_en AS prefecture_name_en,
                   co.name AS country_name, co.dial_code AS country_dial_code
```

変更前（:92〜:96）:

```python
    if row:
        return {
            "name": row["company_name"],
            "address": format_issuer_address(row, row["prefecture_name"], row["country_name"]),
            "phone": row["phone"] or "",
```

変更後:

```python
    if row:
        english = region == "overseas"
        prefecture_name = row["prefecture_name_en"] if english else row["prefecture_name"]
        return {
            "name": row["company_name"],
            "address": format_issuer_address(row, prefecture_name, row["country_name"], english=english),
            "phone": format_issuer_phone(row["phone"], row["country_code"], row["country_dial_code"],
                                         international=english),
```

`from app.services.issuer import ...` の行（test_issuer.py:20）に `format_issuer_phone` を足す。

### 2-2. test_issuer.py に足す試験

| # | 名前 | 確かめること |
|---|---|---|
| T1 | test_format_issuer_address_jp_english | `{"country_code": "JP", "postal_code": "4442141", "city": "C", "address1": "A1", "address2": None}` に `("P", "Countryname", english=True)` → `"A1, C, P 444-2141, Countryname"`。address2 を `"B2"` にすると `"A1, B2, C, P 444-2141, Countryname"` |
| T2 | test_format_issuer_address_jp_default_unchanged | 同じ行を english を渡さずに → `"〒444-2141 PCA1"`（今の形のまま） |
| T3 | test_format_issuer_phone | `("09060727767", "JP", "+81", international=True)` → `"+81 9060727767"`。international=False → `"09060727767"`。`("+14155550100", "US", "+1", international=True)` → そのまま。`(None, "JP", "+81", international=True)` → `""`。dial_code が None → そのまま |
| T4 | test_get_issuer_overseas_jp_uses_english_order | seed（_PREF_SEED）の 23 の行を prefectures に INSERT OR IGNORE（既存の test_get_issuer_reads_region_row_with_prefecture_and_registration と同じ書き方）。国の表から JP の name と dial_code を読む。overseas の行を country_code="JP"・prefecture_code="23"・postal_code="4442141" で入れる（_insert_issuer を使う。市区町村は "CityA"・番地は "Street1"・電話は "0312345678"）。`issuer["address"] == f"Street1, CityA, {name_en} 444-2141, {country_name}"`・`issuer["phone"] == f"{dial} 312345678"`。見積書の PDF（render_quote_pdf）の文字に住所と `f"TEL: {dial} 312345678"` が入る |
| T5 | 既存の test_get_issuer_reads_region_row_with_prefecture_and_registration に1行足す | `assert issuer["phone"] == "0312345678"`（国内用の電話は変わらない） |

既存の試験は1つも消さない・変えない（T5 の1行を足すだけ）。

## 3. 手順

1. 場所を作る。clone のまま commit しない。new-worktree.sh の出力はパイプに通さない（guards/04-worktree.md）。クラウドでは `--claude` を付けない。最後に「Input must be provided」と出て終了コードが 1 でも、場所ができていれば進む。

```
cd ~ && git clone https://github.com/shingo-ops/salesanchor.git salesanchor
cd ~/salesanchor && bash scripts/new-worktree.sh release/viewer-contract-bin2-2c2b-fix2
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && git log --oneline -1 | tail -1
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && git merge-base --is-ancestor 045abb209 HEAD; echo "is-ancestor exit=$?"
```

期待: `is-ancestor exit=0`。以下の手順はすべてこの場所（~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2）で行う。場所が無ければ BLOCKED。

2. 点検する（§0-3）。

```
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && git rev-parse HEAD
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && ls docs/handoff/viewer-contract-stage/card-2-2c2b-fix2.md
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && wc -l backend/app/services/issuer.py backend/tests/test_issuer.py
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && grep -cF 'pr.name_ja AS prefecture_name, co.name AS country_name' backend/app/services/issuer.py
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && grep -cF '"address": format_issuer_address(row, row["prefecture_name"], row["country_name"]),' backend/app/services/issuer.py
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && grep -cF '"phone": row["phone"] or "",' backend/app/services/issuer.py
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && grep -rn 'format_issuer_phone' backend | wc -l
```

期待: 114・352・1・1・1・0。

3. §2 を当てる。Edit で1か所ずつ。

4. 試験。

```
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2/backend && python3 --version
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2/backend && pip install -q -r requirements.txt -r requirements-dev.txt 2>&1 | tail -3
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2/backend && python3 -m pytest tests/test_issuer.py -q 2>&1 | tail -15
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2/backend && python3 -m pytest tests/test_invoice_draft_shipping.py tests/test_invoices.py -q 2>&1 | tail -15
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2/backend && ruff check app/ 2>&1 | tail -10
```

期待: pytest は failed 0・error 0。ruff は違反なし。

5. 確かめる。

```
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && git status --short | tail -10
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && git diff | tail -200
```

期待: 変わったファイルは §1 の2つだけ。

6. 記録して送る（shingo-cc 名義）。

```
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && git add backend/app/services/issuer.py backend/tests/test_issuer.py
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && git -c user.name=shingo-cc -c user.email=shingo-cc@users.noreply.github.com commit -m "fix(backend): print Japanese issuer address in English order on overseas documents (ADR-1061 bin2-2c2b fix2)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && git push origin release/viewer-contract-bin2-2c2b-fix2 2>&1 | tail -3
cd ~/worktrees/salesanchor/release-viewer-contract-bin2-2c2b-fix2 && git log --oneline -2 | tail -2
```

## 4. 想定される分かれ道

次のときは、そこで停止して BLOCKED と報告する（直さない・言い換えない）。

- 手順1の is-ancestor が 0 でない。
- §0-3 の数が1つでも違う。
- §2 の「変更前」の文字列が見つからない、または2か所以上に当たる。
- pytest に failed か error がある（既存の試験が落ちたときも、直さずに生のまま報告する）。
- 試験の DB（SQLite）で `pr.name_en` か `co.dial_code` が無いと言われる。
- ruff が違反を出す。
- 直すために §1 の外のファイルを触る必要がある。
- push が失敗する。

直してよいのは、このカードの写し間違い（字下げ・閉じかっこ・カンマの抜け）だけ。直したら、どこをどう直したかを報告に書く。試験の skipped は止めずに数を書く。

## 5. 報告の形

最後の返事に、受領確認の2行、手順ごとの tail の生出力、手順5の diff の全文、停止したときは「どの手順で・何が出たか・何をしなかったか」の3点を書く。最後の行は `DONE` か `BLOCKED: 理由` のどちらか。

## 6. 受入

design.md §3-4e の表のとおり。本番の見積書の PDF は、反映のあと海外用を入れてから Opus が Chrome で見る。

## 7. 委任の定型

- sleep・ヒアドキュメントは使わない。PR は作らない。
- 見張り（hook）に止められたら、言い換えずに止められた文をそのまま報告する。
- §1 にないファイルは直さない。

END OF CARD
