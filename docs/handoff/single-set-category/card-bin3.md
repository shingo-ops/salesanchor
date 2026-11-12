# 実装カード 便3: 13 商品の行を解析し直す道具（試走と書き込みの台本・PO が `!` で流す）

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

> What this document is, in one line:
> Build a one-off rerun tool for the 13 products moved to シングルセット系: it reruns the v102 system stage (no Gemini) per supplier, oldest post first, inside a transaction that is always rolled back (dryrun), and in commit mode writes only suppliers whose trial matches the reviewed expected.json.

- 親: `docs/handoff/single-set-category/design.md` §5 便3 手順 3〜6・§2 KGI 1〜3・§8 K5・K6
- 手本: `docs/handoff/single-set-category/data/bin3/ref/rejudge_pika30.py`（2026-11-11 に 1 商品で本番の試走と書き込みに使った台本。sha256 先頭 `df1e1752275e843ed7bf`）
- PO の承認: 便3 の付け替え 2026-11-12「1」、やり直しの準備 2026-11-13「1」。このカードの実装は、カードを PO に見せて「1」を受けてから渡す
- 基準: origin/main 4892f2c6a。行番号はこの版で Opus が読んで確かめた
- ブランチ: `release/single-set-category-bin3-rejudge-card`（このカードと同じ枝）。既にある枝を checkout して、その上に commit する
- 読んだ決まり: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・10-executor.md
  - 照合: 手順のコマンドは cd で始める・1手順1コマンド・出力に head／tail を付ける・sleep で待たない・gh run view を使わない・プレースホルダを置かない
- 受領確認: 着手の前に、§0 を満たしたかを1行で返してから始める
- 起票: Opus が手元で行う。担当は push までとする（PR は作らない）
- 本番で流すのは PO だけ。担当も Opus も本番に触らない

## カード発行前の照合（design-partner.md §5.5）

| 項目 | 結果 |
|---|---|
| 1 記号を壊さない（パス・名前はバッククォート） | ○ |
| 2 下書き禁止 | ○ PR は作らない（push まで。PR は Opus が ready で作る） |
| 3 報告の宛先 | ○ 最後の発言に生出力を全文 |
| 4 1便1目的 | ○ 道具 1 本と試験 1 本だけ（流すのは PO・本番の書き込みは別の手順） |
| 5 既存ブランチは起点明示 | ○ `origin/release/single-set-category-bin3-rejudge-card` を checkout |
| 6 書式は実例で | ○ commit 文を下に丸ごと書いた |
| 7 合格基準を出力まで縛る | ○ 下の「合格の形」 |
| 8 件数と名前を対で | ○ 落ちた検査は名前を出す |
| 9 出力に上限 | ○ ruff は `tail`、diff は `--stat` |
| 10 報告の3点 | ○ 下の「報告」 |
| 11 行番号を停止条件にしない | ○ 手本の直しは関数の名前と文字で指定 |
| 12 停止は2段 | ○ 下の「止まる条件」 |
| 13 委任文の4点 | ○ sleep 禁止・Write/Edit で書く・PR は作らない（validate は Opus）・止められたら言い換えない |

## なぜ

13 商品は区分をシングルセット系へ付け替えた（2026-11-13 08:09 本番）。けれども、付け替えの前に解析した行は Sealed box や Error のまま残る。2026-11-13 の読み取りで、13 商品の現行の行は 50 行。うち 34 行が single の群でない（Sealed box 26・Error 8）。この行を持つ投稿を、本番と同じ関数でシステム段だけ解析し直す（Gemini は呼ばない）。前の投稿の行を〆と価格の引き継ぎが読むので、仕入元ごとに古い順に流す。

## 禁止

- 本番に触らない。ssh・scp・docker を使わない
- 手本のファイル（`data/bin3/ref/rejudge_pika30.py`）を変えない
- `backend/app/` の中を変えない。既存の試験ファイルを変えない
- 下の「変えるファイル」の 2 本のほかを足さない・変えない
- 試験の期待値が合わないとき、期待値を書き換えない。止まって NEEDS_DECISION: で返す
- PR を作らない・マージしない。force-push しない
- sleep で待たない。ファイルは Write／Edit で書く（ヒアドキュメントで書かない）
- フックや自動判定に止められたら、言い換えて再試行しない。止まった手順・最後のコマンド・理由の原文を返して終える

## 0. 着手条件（満たさなければ止まって BLOCKED: で返す）

origin/main の次の行が、表の「基準の中身」を含むこと。1 つでも違えば BLOCKED: で差を返す。

| 場所 | 基準の中身 |
|---|---|
| `backend/app/services/line_analysis_v102_svc.py:123` | `REASON_EXTRACT_EXCEPTION = "extract_exception"` |
| `backend/app/services/line_analysis_v102_svc.py:130` | `REASON_SEPARATOR = ","` |
| `backend/app/services/line_analysis_v102_svc.py:138` | `CONDITION_BASIS_SOLDOUT_REF = "SOLDOUT_REF"` |
| `backend/app/services/line_analysis_v102_svc.py:168` | `def is_v102_prompt_version(` |
| `backend/app/services/line_analysis_v102_svc.py:1594` | `def run_v102_analysis(session: Session, extraction_job_id: str) -> dict:` |
| `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:33` | `CONDITION_BASIS_SOLDOUT_INHERIT = "SOLDOUT_INHERIT"` |
| `backend/app/tasks/tcg_extraction.py:97` | `def _get_sync_session() -> Session:` |

## 1. 手順（この順）

手順1 枝を取る（失敗したら BLOCKED:）
    cd "$(git rev-parse --show-toplevel)" && git fetch origin release/single-set-category-bin3-rejudge-card
    cd "$(git rev-parse --show-toplevel)" && git checkout -B release/single-set-category-bin3-rejudge-card origin/release/single-set-category-bin3-rejudge-card
    cd "$(git rev-parse --show-toplevel)" && git config user.name shingo-cc
    cd "$(git rev-parse --show-toplevel)" && git log -1 --oneline

手順2 §0 の表の行を読む
    cd "$(git rev-parse --show-toplevel)" && sed -n '123p;130p;138p;168p;1594p' backend/app/services/line_analysis_v102_svc.py
    cd "$(git rev-parse --show-toplevel)" && sed -n '33p' backend/app/services/gemini_raw_copy_v102_soldout_ref.py
    cd "$(git rev-parse --show-toplevel)" && sed -n '97p' backend/app/tasks/tcg_extraction.py

手順3 手本を新しいファイルに写す
    cd "$(git rev-parse --show-toplevel)" && cp docs/handoff/single-set-category/data/bin3/ref/rejudge_pika30.py docs/handoff/single-set-category/data/bin3/rejudge_single_set.py

手順4 写したファイルに §2 の直しを Edit で 1 つずつ当てる

手順5 §3 の新しい試験ファイルを Write で丸ごと書く

手順6 構文と書式の確かめ（失敗したら直してから進む。§2・§3 の外を直す必要が出たら NEEDS_DECISION:）
    cd "$(git rev-parse --show-toplevel)" && python3 -m py_compile docs/handoff/single-set-category/data/bin3/rejudge_single_set.py backend/tests/test_single_set_rejudge_tool.py
    cd "$(git rev-parse --show-toplevel)/backend" && ruff check ../docs/handoff/single-set-category/data/bin3/rejudge_single_set.py tests/test_single_set_rejudge_tool.py 2>&1 | tail -20

手順7 §4 の検索を流す（出力は報告に入れる）

手順8 commit する（§6 の文を Write で `/tmp/bin3-tool-commit-msg.txt` に書いてから）
    cd "$(git rev-parse --show-toplevel)" && git add docs/handoff/single-set-category/data/bin3/rejudge_single_set.py backend/tests/test_single_set_rejudge_tool.py
    cd "$(git rev-parse --show-toplevel)" && git commit -F /tmp/bin3-tool-commit-msg.txt

手順9 push する（単独で）
    cd "$(git rev-parse --show-toplevel)" && git push -u origin release/single-set-category-bin3-rejudge-card

手順10 push を確かめる
    cd "$(git rev-parse --show-toplevel)" && git log --oneline -3
    cd "$(git rev-parse --show-toplevel)" && git rev-parse HEAD origin/release/single-set-category-bin3-rejudge-card
    cd "$(git rev-parse --show-toplevel)" && git diff origin/main...HEAD --stat | tail -10

## 2. 直し（`docs/handoff/single-set-category/data/bin3/rejudge_single_set.py`）

手本の動き（仕入元ごとに 1 つの取引で流す・`s.commit = s.flush` に差し替える・最後に必ず ROLLBACK・元に戻ったかを `back != before` で確かめる・commit モードは expected.json と全件同じ仕入元だけ書く・書く前を SNAP_PATH に足す・書いた後に読み戻して試走と比べる）は変えない。直すのは次の 12 点だけ。

2-1 冒頭の説明文（docstring）を、この便の説明に書き換える。中身: 13 商品をシングルセット系へ付け替えた後、その商品の行を持つ投稿をシステム段だけ解析し直す。目当ての合格は「商品はそのまま・単位 Set・状態の群 single・bundle_size なし」。PO 2026-11-13「1」。手本の 466062 と「30周年」の語は残さない。

2-2 定数。`PID = 466062` と `SET_CATEGORY = 4` を消し、次を置く。
```python
PIDS = (465992, 466031, 466062, 466088, 466165, 466166, 466167, 466168, 466169, 466170, 466171, 466172, 466173)
SINGLE_SET_CATEGORY = 15  # PC_SINGLE_SET（便2 で本番に入れた区分）
SOLDOUT_BASES = (svc.CONDITION_BASIS_SOLDOUT_REF, "SOLDOUT_INHERIT")  # 〆が前の行の状態を写した印（design.md §2 KGI 1）
EXCL_PATH = os.environ.get("EXCL_PATH", "/m/excluded.json")
LOCK_TIMEOUT = "1s"  # ADR-1037。PO の台本が PGOPTIONS で付ける。付いていなければ止まる
```

2-3 `DISCOVER` の内側の条件 `WHERE ar.product_id = :pid AND ar.condition_canonical = 'Single'` を `WHERE ar.product_id = ANY(:pids)` にする（置き換え済みの行も含める＝design.md §5 便3 手順 3）。`discover` の中の `q(s, DISCOVER, pid=PID)` を `q(s, DISCOVER, pids=list(PIDS))` にする。

2-4 `ROWS` に 2 列を足す。`ar.ship_en` の後ろに `, ar.bundle_size::text AS bundle_size, lc.value_group` を足し、`LEFT JOIN public.analysis_results ar ON ar.extraction_item_id = ei.id` の後ろに `LEFT JOIN public.line_conditions lc ON lc.id = ar.condition_id` を足す（状態の群は `public.line_conditions.value_group`。`public.conditions` はその写しの view＝`migrations/20260922_080000_rename_line_analysis_tables.sql:83`）。

2-5 `STRICT` の最後に `"bundle_size"` を足す。`value_group` は足さない（condition_id から決まるので二重になる）。

2-6 外す理由を関数に出す。`discover` の中の `why` を作る 3 行を、次の関数に移し、`discover` からはこれを呼ぶ。
```python
def exclusion_reasons(r):
    why = []
    if r["corr"]: why.append(f"人の手直し {r['corr']} 件")
    if not svc.is_v102_prompt_version(r["prompt_version"]): why.append("v102 でない")
    if r["status"] != "done": why.append(f"status={r['status']}")
    return why
```
`discover` の戻り値の 2 つ目（外した投稿）を、id の一覧から `[{"job": r["job"], "ch": r["ch"], "received_at": str(r["received_at"]), "why": why} ...]` に変える（K5 の数え方がこの一覧を使う）。

2-7 目当ての行の判定を関数に出す。
```python
def classify_target(t, a):
    """t=前の行・a=後の行（無ければ None）。戻り値 (判定, 後の形)。判定は OK / NG / SOLDOUT。"""
    if a is None:
        return "NG", "行が無い"
    key = f"{a['product_id']}/{a['unit_canonical']}/{a['condition_canonical']}/{a['value_group']}/bundle={a['bundle_size']}/cur={a['is_current']}"
    if a["product_id"] != t["product_id"]:
        return "NG", key
    if a["condition_basis"] in SOLDOUT_BASES:
        return "SOLDOUT", key
    if a["unit_canonical"] == "Set" and a["value_group"] == "single" and a["bundle_size"] is None:
        return "OK", key
    return "NG", key
```

2-8 `judge_channel` の目当ての行を、`r["product_id"] == PID and r["condition_canonical"] == "Single"` から `r["product_id"] in PIDS` に替える。`good` と `key` を作る所は `classify_target(t, a)` を呼ぶ形にし、tally のキーは `(判定, 後の形)`、出力の印は `[TARGET-OK]`・`[TARGET-NG]`・`[TARGET-SOLDOUT]` の 3 つにする。印の行には前の形（`unit_canonical`/`condition_canonical`/`value_group`/`bundle_size`/`condition_basis`/`is_current`）と `p`・`q` を出す。`out["jobs"][ej]` に `"targets": [{"item": 行の id, "before": 前の形, "after": 後の形, "label": 判定}]` を足す（changes.json に入り、commit の照合にも入る）。

2-9 ロック待ちの上限。`main` の最初（`_get_sync_session()` の直後）で `SHOW lock_timeout` を読み、`[PRE] lock_timeout=値` を出す。`LOCK_TIMEOUT` と違えば `stop("lock_timeout が 1s でない（PGOPTIONS が付いていない）")`。

2-10 解析の失敗印を投稿ごとに見る。`run_v102_analysis` は中で失敗すると `session.rollback()` する（`backend/app/services/line_analysis_v102_svc.py` の `run_v102_analysis` の `except Exception:` の所）。試走中にこれが起きると、同じ仕入元の前の投稿の試走まで消える。そこで、`trial` の中で `run_v102_analysis` を呼ぶたびに、その投稿の `extraction_jobs.review_reasons` を読み、`svc.REASON_SEPARATOR` で分けた中に `svc.REASON_EXTRACT_EXCEPTION` があれば、その仕入元の試走をそこで止める（`finally` の ROLLBACK と `s.commit` の戻しは今のまま通す）。戻り値は `None, None, "仕入元 {ch[:8]} の投稿 {ej[:8]} で extract_exception が付いた"`。commit モードの本実行でも、呼ぶたびに同じものを読み、あれば `stop(...)` で全体を止める。

2-11 例外で全体を落とさない（dryrun だけ）。`main` の仕入元の繰り返しで、`trial` と `judge_channel` を `try:` で包む。`except Exception as e:` では `s.rollback()` を呼び、`[NG] 仕入元 {ch[:8]} 例外 {type(e).__name__}: {str(e)[:300]}` を出し、その仕入元を飛ばした仕入元に入れて次へ進む。commit モードでは包まずに今のまま落とす（`stop` と同じく、書いた投稿の数を出してから終える）。

2-12 書いた後の不一致で全体を止める（commit モード）。手本は `[NG-WRITE]` の後も次の仕入元へ進む。これを、`[NG-WRITE]` を出したらすぐ `stop("仕入元 {ch[:8]} の読み戻しが試走と違う。ここで止めた")` にする。dryrun の終わりでは、changes.json と別に `EXCL_PATH` へ外した投稿の一覧（2-6 の形）を書き、`[excluded] 外した投稿 N 件を保存 パス` を出す。

## 3. 新しい試験（`backend/tests/test_single_set_rejudge_tool.py`・丸ごと）

```python
"""便3 の解析し直しの道具の判定だけを確かめる（DB には触らない）。道具: docs/handoff/single-set-category/data/bin3/rejudge_single_set.py"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_TOOL = _REPO / "docs" / "handoff" / "single-set-category" / "data" / "bin3" / "rejudge_single_set.py"


def _tool():
    spec = importlib.util.spec_from_file_location("rejudge_single_set", _TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # `if __name__ == "__main__"` のため main は走らない
    return module


def _row(**kw):
    base = {"product_id": 466062, "unit_canonical": "Set", "condition_canonical": "Single", "value_group": "single",
            "bundle_size": None, "condition_basis": "R7:単品既定", "is_current": True}
    return {**base, **kw}


def test_constants():
    t = _tool()
    assert len(t.PIDS) == 13 and len(set(t.PIDS)) == 13
    assert t.SINGLE_SET_CATEGORY == 15
    assert t.STRICT[-1] == "bundle_size" and "value_group" not in t.STRICT
    assert set(t.SOLDOUT_BASES) == {"SOLDOUT_REF", "SOLDOUT_INHERIT"}
    assert t.LOCK_TIMEOUT == "1s"


def test_exclusion_reasons():
    t = _tool()
    ok = {"corr": 0, "prompt_version": "v102:abc", "status": "done"}
    assert t.exclusion_reasons(ok) == []
    assert len(t.exclusion_reasons({**ok, "corr": 2})) == 1
    assert t.exclusion_reasons({**ok, "prompt_version": "v101:abc"}) == ["v102 でない"]
    assert t.exclusion_reasons({**ok, "status": "failed"}) == ["status=failed"]


def test_classify_ok():
    t = _tool()
    assert t.classify_target(_row(unit_canonical="Piece"), _row())[0] == "OK"


def test_classify_ng_cases():
    t = _tool()
    before = _row(condition_canonical="Sealed box", value_group="box")
    assert t.classify_target(before, None) == ("NG", "行が無い")
    assert t.classify_target(before, _row(unit_canonical="Piece"))[0] == "NG"
    assert t.classify_target(before, _row(unit_canonical=None))[0] == "NG"
    assert t.classify_target(before, _row(bundle_size="12"))[0] == "NG"
    assert t.classify_target(before, _row(condition_canonical="Sealed box", value_group="box"))[0] == "NG"
    assert t.classify_target(before, _row(condition_canonical="Error", value_group=None))[0] == "NG"
    assert t.classify_target(before, _row(product_id=1))[0] == "NG"


def test_classify_soldout_is_separate():
    t = _tool()
    for basis in ("SOLDOUT_REF", "SOLDOUT_INHERIT"):
        after = _row(condition_canonical="Sealed box", value_group="box", condition_basis=basis)
        assert t.classify_target(_row(), after)[0] == "SOLDOUT"


def test_classify_key_shows_shape():
    t = _tool()
    label, key = t.classify_target(_row(), _row(bundle_size="5", is_current=False))
    assert label == "NG" and key == "466062/Set/Single/single/bundle=5/cur=False"
```

ruff が行の長さ（120 字）で止めた行は、引数の切れ目で折る。中身の値・期待値は変えない。

## 4. 検索（出力を報告に入れる）

手順7 の命令
    cd "$(git rev-parse --show-toplevel)" && grep -n "PID\b\|SET_CATEGORY\|466062\|30周年" docs/handoff/single-set-category/data/bin3/rejudge_single_set.py | head -20
    cd "$(git rev-parse --show-toplevel)" && grep -n "PIDS\|SINGLE_SET_CATEGORY\|SOLDOUT_BASES\|EXCL_PATH\|LOCK_TIMEOUT\|bundle_size\|value_group\|exclusion_reasons\|classify_target\|REASON_EXTRACT_EXCEPTION\|NG-WRITE" docs/handoff/single-set-category/data/bin3/rejudge_single_set.py | head -60
    cd "$(git rev-parse --show-toplevel)" && git diff origin/main --stat | tail -10

期待: 1 つ目は `PIDS` の中の 466062 の 1 行だけ（`PID` 単独・`SET_CATEGORY` 単独・「30周年」は 0 行）。2 つ目は §2 で足した所。3 つ目は §5 の 2 本と、この枝に先にある Opus の 3 本（このカード・手本・台帳）だけ。

## 5. 変えるファイル（これ以外は変えない）

- `docs/handoff/single-set-category/data/bin3/rejudge_single_set.py`（新規・手本の写しから）
- `backend/tests/test_single_set_rejudge_tool.py`（新規）

触らない:
- `backend/app/` の全部（解析の本体は本番と同じものを呼ぶ）
- 手本 `docs/handoff/single-set-category/data/bin3/ref/rejudge_pika30.py`・このカード
- 既存の試験ファイル・migrations/・deploy.yml・scripts/・.github/・frontend/
- PO が流す台本（ssh と鍵を使う外側の台本）は Opus が別に作る。担当は作らない

## 6. commit の文

```text
docs(single-set): add bin 3 rerun tool for the 13 single-set products

- docs/handoff/single-set-category/data/bin3/rejudge_single_set.py: rerun the v102 system stage
  (no Gemini) per supplier, oldest first, in a transaction that is always rolled back (dryrun);
  commit mode writes only suppliers whose trial matches the reviewed expected.json
- target check: same product, unit Set, condition group single, no bundle_size; SOLDOUT_* reported apart
- bundle_size added to the compared fields; excluded jobs saved for K5; lock_timeout 1s required
- tests: backend/tests/test_single_set_rejudge_tool.py (judgement only, no DB)

Not run in production by this commit. The PO runs it with ! after review.
Design: docs/handoff/single-set-category/design.md section 5 bin 3

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

## 7. 合格の形

- 手順6: py_compile は何も出さずに終わる。ruff は `All checks passed!`
- 手順7: §4 の期待のとおり
- 手順10: HEAD と origin の枝が同じ sha。`--stat` に削除の行が無い（`-` だけの行が無い）

## 8. 止まる条件（2 段）

止まる（そこで終えて返す）:
- §0 の行が基準と違う → BLOCKED:
- §2 の「前」の文字が手本に見つからない → BLOCKED: で、見つからない文字を返す
- 試験の期待値を変えないと通らない・§5 の外を変える必要がある → NEEDS_DECISION:
- push が拒まれた・フックに止められた → BLOCKED: で原文を返す

記録して続ける（判定は Opus）:
- ruff の書式の指摘（直して続ける）・`--stat` の行数

## 9. 報告

最後の発言の 1 行目を「本報告はカード 便3 解析し直しの道具 の実行結果である」とし、次を生出力のまま全文で書く。
- 受領確認の 1 行
- 手順1・2・6・7・10 の出力
- 止まったときは「止まった手順の番号／最後に流したコマンド／止まった理由の原文」
- 末尾の 1 語は DONE または BLOCKED: または NEEDS_DECISION:

END OF CARD
