# 実装カード — 数字だけの値を金額の一部に当てない

> この文書は何か：照合の共有関数 `has_word_boundary` に、数字だけの値のときだけ「金額の形の位置では当たらない」条件を足す作業指示書です。直すのは `backend/app/services/extraction_judgement_svc.py` の1関数と、試験の追加だけです。

- 設計: docs/handoff/line-match-price-digit-boundary/design.md（2章が変更の正本。変えてはいけない）
- 事実確認: docs/handoff/line-match-price-digit-boundary/recon.md（origin/main 91310d6db で確認済み）
- 対象ADR: ADR-154・ADR-135・ADR-136
- 状態: 実行してよい（§0 の GO の記録を参照）
- 危険便: いいえ（`migrations/`・`deploy.yml`・`scripts/` を触らない）
- 担当: 実装 Sonnet／コード審査・GO 記録・マージ・反映確認 Opus

## 0. カード発行前チェック

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | 報告の宛先・生出力の扱いを明記 | ○（§10） |
| 3 | 1便1目的 | ○（金額の形に当てないことだけ） |
| 4 | 既存ブランチへの追記ではない | ○（release/line-match-price-digit-boundary は本件専用） |
| 5 | 変更前後のコードを実物どおりに書いた | ○（§4） |
| 6 | 触らない範囲を明記 | ○（§1） |
| 7 | 停止条件・報告3点・受領確認・終端合図 | ○（§7・§10） |
| 8 | 社外秘（仕入元の ID・名前・投稿原文）を試験にも本文にも入れない | ○（§8） |

GO の記録（Opus が記入）: POの委任に基づくClaude Opus発行（2026-10-16 JST 夕方）。根拠: PO の実装承認（「数字の区切りの決まりをプログラムに入れてよいですか」への PO 原文「y」）。実装 PR の番号は起票後に PR 本文の `### GO記録` に書く

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 |
|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない |
| guards/04-worktree.md | worktree は `scripts/new-worktree.sh` で作成済み |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイルは同一行カンマ区切り |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 金額の数字に当てない（line-match-price-digit-boundary）の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `backend/app/services/extraction_judgement_svc.py` の `has_word_boundary`（62〜67行）を §4-2 のとおりに変え、その直前に定数2つを足す
2. `backend/tests/test_extraction_judgement_svc.py` の `TestMatchProductShortBoundary`（542行〜）に試験を足す

入れない（触らない）:
- `has_left_word_boundary`（70〜75行）、`_needs_boundary`（57〜59行）、`_strict_code_hits`、`_value_hits`
- followup・soldout_ref・gap_lines・product_first の各ファイル
- マスタ・`migrations/`・`.github/workflows/`・`scripts/`
- 再解析（Opus が別に行う）

## 2. 前提の事実（recon.md の引用）

| # | 事実 | 根拠 |
|---|---|---|
| 1 | 境界の判定は `has_word_boundary` 1か所 | `backend/app/services/extraction_judgement_svc.py:62-67` |
| 2 | 呼び出しは `_value_hits` の1か所 | `backend/app/services/extraction_judgement_svc.py:214` |
| 3 | 既存の 151 の試験 | `backend/tests/test_extraction_judgement_svc.py:568`・`:583`・`:609` |

## 3. 触るファイル（これ以外は触らない）

| ファイル | 内容 |
|---|---|
| `backend/app/services/extraction_judgement_svc.py` | 定数2つ・`has_word_boundary` の本体 |
| `backend/tests/test_extraction_judgement_svc.py` | 試験の追加（既存試験は変えない） |
| `docs/handoff/line-match-price-digit-boundary/recon.md`・`design.md`・`card-implement.md` | 既にある。§11 の報告欄だけ追記してよい |

## 4. 作り方

### 4-1. 変更前（実物どおり。62〜67行）

```python
def has_word_boundary(folded_text: str, value: str) -> bool:
    """fold_for_match 済みの文字列の中に、前後が英字・数字でない（または端の）value があるか。"""
    needle = fold_for_match(value).strip()
    if not needle:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", folded_text) is not None
```

### 4-2. 変更後

```python
# 数字だけの値は、金額の一部（1,151 / @151 / ¥151 / 151,000 / 151円）では境界ありとしない
_PRICE_LEFT_GUARD = r"(?<![0-9][,.])(?<![@¥$])"
_PRICE_RIGHT_GUARD = r"(?![,.][0-9])(?!円)"


def has_word_boundary(folded_text: str, value: str) -> bool:
    """fold_for_match 済みの文字列の中に、前後が英字・数字でない（または端の）value があるか。

    value が数字だけのときは、金額の一部になっている出現も除く。
    """
    needle = fold_for_match(value).strip()
    if not needle:
        return False
    left, right = r"(?<![a-z0-9])", r"(?![a-z0-9])"
    if needle.isdigit():
        left, right = left + _PRICE_LEFT_GUARD, right + _PRICE_RIGHT_GUARD
    return re.search(left + re.escape(needle) + right, folded_text) is not None
```

### 4-3. 試験（`TestMatchProductShortBoundary` に足す。既存の `_product`・照合の呼び方は 568〜590行の型に合わせる）

1. product_code="151" が次のどれにも当たらない: 「@151,000円」「＠151，000円」「1,151」「¥151」「￥151」「$151」「151円」「151.5」「0.151」
2. product_code="151" が次には当たる: 「151 カートン @151,000円」（区切られた151が別にある）・「SV2a 151」・「151/2BOX」
3. 検索ワード「151」（トークン）でも 1. と同じく当たらない（既存の検索ワード試験の型を使う）
4. 英字を含む値 product_code="sv2a" は、「¥sv2a」で今と同じ結果（変更の対象外であることの固定）

## 5. 確かめ方（担当が実行し、出力をファイルに保存してパスを報告する）

1. `cd /Users/tanizawashingo/worktrees/salesanchor/release-line-match-price-digit-boundary/backend` の後、`python -m pytest tests/test_extraction_judgement_svc.py tests/test_gemini_raw_copy_v102_score_select.py -q` と `python -m pytest tests -q -k "v102 or judgement or extraction"`（出力は /tmp/CC報告ファイル/price-digit-impl/pytest.txt に保存）
2. `git diff --name-only origin/main` に §3 の表にないファイルが無い
3. ruff（リポジトリの既存設定）で触ったファイルに違反が無い

## 6. 分岐ごとの対処

| 分岐 | 対処 |
|---|---|
| 既存の試験が落ちた | 直さずに停止して、落ちた試験名と出力を報告 |
| 追加試験 2. の「151 カートン @151,000円」が当たらない | `re.search` が最初の出現だけで判定していないか確認。直せなければ停止 |
| ruff が既存の違反を出す | 触った行以外は直さない。報告に書く |

## 7. 停止条件

次のいずれかで作業を止めて Opus に報告する（言い換えて再試行しない）:
- 設計 2章と食い違う実装が必要になった
- §1 の「入れない」に触る必要が出た
- フック・分類器・CI に止められた
- 試験の結果が想定と合わない

## 8. 社外秘

試験データ・PR 本文・コミットメッセージに、実在の仕入元の ID・名前・投稿原文を入れない。試験の文は架空のもの（上の例のような短い文）にする。

## 9. 戻し方

この PR を revert する。DB の変更はない。

## 10. PR と報告

- 作業場所は上記 worktree（既にある）。`./scripts/dev/executor-preflight.sh` を最初に実行する
- commit の末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- 作成前に `gh auth status` で `shingo-cc` 名義を確かめる
- PR は `scripts/gh-pr-create-safe.sh` で `--base main` に作る。本文は `.github/pull_request_template.md` 起点。`### 標準ワークフロー確認` に recon・design・このカード・ADR を書き、「触るファイル:」を同一行・カンマ区切りで全列挙する。本文の末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる
- マージは Opus が行う。担当はマージしない。sleep しない。CI の完了を待たず PR の URL を報告する
- 報告の1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか。事実だけを書く

## 11. 報告欄（担当が追記）

（未記入）

END OF CARD
