# 作業指示書: 注記マスタの一覧が 500 で開かない不具合の直し（第 2 版）

- 状態: 設計案作成済み。第 1 版はクラウドの審査役（Claude Opus）が REVISE（指摘 1〜5）。第 2 版で 1〜4 を直し、5 は §7 に記録
- 対象 ADR: ADR-1054（段 3 の 1 回目 batch3a の受入 B5 を止めている不具合）。match_type `STATE_LITERAL` の設計は docs/handoff/tcg-product-master-growth/design-keyword.md:472-482
- 実装役: クラウドの Sonnet。この指示書に書いた変更だけをする

## 0. 何が起きているか（観測事実）

1. 本番の画面の測定（prod-ui-check run 41377463601・2026-11-02 11:37 JST）で `/management-center/note-master` の行は API 2 件・5xx 1 件・戻った時 0.20 秒。変更前の run 41371097056（10:14 JST）でも同じ 5xx 1 件・0.20 秒。
2. 一覧の API は `backend/app/routers/note_master.py:137-152`。取った全行を `TcgNoteMasterResponse(**dict(row))` に通す。1 行でも検査に落ちると一覧全体が 500 になる。
3. 検査は `backend/app/schemas/central_masters.py:626-630`（作る時と返す時）と `:651-655`（直す時）。許す値は `("LITERAL", "REGEX", "DEFAULT")` の 3 つだけ。
4. 本番 DB（読み取り専用の道 ADR-1024・2026-11-02 11:53 JST）: `public.tcg_note_master` の `tenant_id IS NULL OR tenant_id = 1` は 99 行。そのうち 1 行（id 148・共用・伝票剥がし跡あり・priority 1）の match_type が `STATE_LITERAL`。共用の行なので、全テナントの 1 ページ目に入る。
5. `STATE_LITERAL` は設計どおりの値（design-keyword.md:472-482）。解析は `backend/app/services/tcg_analyzer_svc.py:1164-1167` で使う。`migrations/20260910_200000_tcg_condition_note_delivery_t004.sql:37` は `tenant_004.tcg_note_master` へ入れた。`public` の id 148 がどの道で入ったかはまだ確かめていない（直しには関係しない）。検査だけが直されていなかった。
6. 手元で本線の `central_masters.py` を読み込み、この行と同じ値を `TcgNoteMasterResponse` に通した。`LITERAL` は通り、`STATE_LITERAL` は `ValidationError: match_type must be LITERAL, REGEX, or DEFAULT` で落ちた。
7. 画面側 `frontend/src/pages/note-master/NoteMasterPage.tsx:85` と運営者の画面 `frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:81` の選び肢も 3 つだけ。`ja.json` / `en.json` の `ruleManagement.matchType` に `STATE_LITERAL` の言葉が無い（`frontend/src/locales/ja.json:5423-5429`・`en.json:5423-5429`）。

8. 運営者の一覧 `backend/app/routers/super_admin_note_master.py:143-150` も同じ `TcgNoteMasterResponse` に全行を通す。共用の行 id 148 が入るので、同じく 500 になる。
9. CSV の取り込み `_parse_note_master`（`note_master.py:68-108`・`super_admin_note_master.py:59-99`）は match_type を検査しない。列が無いか空なら `""` のまま DB に入る（`note_master.py:101`・`super_admin_note_master.py:92`）。DB に match_type の制約は無い（審査役が確認）。このため取り込みで同じ 500 がまた起きうる。作る時の型の初めの値は `"LITERAL"`（`central_masters.py:620`）。

## 1. 変えるファイル（これ以外は触らない）

| # | ファイル | 変更 |
|---|---|---|
| 1 | backend/app/schemas/central_masters.py | 注記マスタの match_type の許す値に `STATE_LITERAL` を足す |
| 2 | frontend/src/pages/note-master/NoteMasterPage.tsx | 選び肢に `STATE_LITERAL` を足す |
| 3 | frontend/src/locales/ja.json | 言葉を 1 つ足す |
| 4 | frontend/src/locales/en.json | 言葉を 1 つ足す |
| 5 | backend/tests/test_note_master_match_type.py（新規） | 検査の試験 |
| 6 | frontend/src/pages/super-admin/components/NoteMasterPanel.tsx | 選び肢に `STATE_LITERAL` を足す |
| 7 | backend/app/routers/note_master.py | CSV の取り込みで match_type を検査する |
| 8 | backend/app/routers/super_admin_note_master.py | 同上 |

触らない: DB・migrations・解析（tcg_analyzer_svc.py）・router 2 本の CSV 以外の場所・`tcg_status_values.py`（状態マスタの値の表で、注記マスタとは別の物）・deploy.yml・本番 scripts。

## 2. 変更の中身

### #1 central_masters.py

`class TcgNoteMasterBase` の直前（`# tcg_note_master` の区切り線の下）に定数を 1 つ置く。

```python
# 注記マスタの照合の種類。STATE_LITERAL は備考に加えて状態の欄も読む（design-keyword.md:472）
NOTE_MATCH_TYPES = ("LITERAL", "REGEX", "DEFAULT", "STATE_LITERAL")
```

`TcgNoteMasterBase.validate_match_type`（変更前 :627-630）:

```python
    def validate_match_type(cls, v: str) -> str:
        if v not in NOTE_MATCH_TYPES:
            raise ValueError(f"match_type must be one of {list(NOTE_MATCH_TYPES)}")
        return v
```

`TcgNoteMasterUpdate.validate_match_type`（変更前 :652-655）:

```python
    def validate_match_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in NOTE_MATCH_TYPES:
            raise ValueError(f"match_type must be one of {list(NOTE_MATCH_TYPES)}")
        return v
```

ほかの行は変えない。

### #2 NoteMasterPage.tsx:85

```tsx
const MATCH_TYPE_VALUES = ["LITERAL", "REGEX", "DEFAULT", "STATE_LITERAL"];
```

### #6 NoteMasterPanel.tsx:81

```tsx
const MATCH_TYPE_VALUES = ["LITERAL", "REGEX", "DEFAULT", "STATE_LITERAL"];
```

:88 と :193 はこの並びを使うだけなので変えない。:193 の札は `t()` の言葉（#3・#4）で出る。

### #7・#8 CSV の取り込み（2 本とも同じ直し）

`from app.schemas.central_masters import (` の並びに `NOTE_MATCH_TYPES,` を足す（`note_master.py:36`・`super_admin_note_master.py:27`）。

`_parse_note_master` の priority の検査の後ろ・`rows.append({` の前に足す:

```python
        match_type = (raw_row.get("match_type") or "").strip() or "LITERAL"
        if match_type not in NOTE_MATCH_TYPES:
            errors.append(f"L{line_num}: invalid match_type '{match_type}' (must be one of {list(NOTE_MATCH_TYPES)})")
            continue
```

`rows.append` の中の `"match_type": (raw_row.get("match_type") or "").strip() or "",` を `"match_type": match_type,` に変える。空の時は作る時の型の初めの値 `"LITERAL"`（`central_masters.py:620`）にそろえる。

### #3・#4 言葉

`ruleManagement.matchType` の中、`"RELEASE"` の後ろに 1 つ足す（ほかの場所の同じ名前の鍵は触らない）。

- ja.json: `"STATE_LITERAL": "完全一致（状態の欄も見る）"`
- en.json: `"STATE_LITERAL": "Literal (memo and state)"`

### #5 試験（新規）

`backend/tests/test_note_master_match_type.py`。DB を使わない。

- T1: `TcgNoteMasterResponse` に match_type `STATE_LITERAL` の行（id 148 と同じ形）を通すと通る。
- T2: `TcgNoteMasterCreate` と `TcgNoteMasterUpdate` が `STATE_LITERAL` を受ける。
- T3: `LITERAL`・`REGEX`・`DEFAULT` は今までどおり通る。
- T4: `BOGUS` は 3 つの型すべてで `ValidationError`。`TcgNoteMasterUpdate(match_type=None)` は通る。
- T5: 2 本の router の `_parse_note_master` それぞれで、match_type が `STATE_LITERAL` の行は rows に入る。空の行と列が無い CSV は `"LITERAL"` になる。`BOGUS` の行は errors に `L2: invalid match_type 'BOGUS'` で始まる文が入り、rows に入らない。

## 3. 想定の分かれ道（実装役は迷ったら止まって報告する）

- `central_masters.py` の該当行が上の行番号と違う → 中身が同じなら進める。中身が違えば止まる。
- `ruleManagement.matchType` が ja/en で 1 か所ずつでない → 止まる。
- 既存の試験が `"match_type must be LITERAL, REGEX, or DEFAULT"` の文を当てにしている → 止まって報告する（文を変えるため）。
- `_parse_note_master` の中身が 2 本で §0-9 の行番号の中身と違う → 止まる。
- 既存の試験が CSV の取り込みで match_type が `""` のまま入ることを当てにしている → 止まって報告する。

## 4. 実装役の確かめ

- `cd backend && python -m pytest tests/test_note_master_match_type.py -q`
- `cd backend && python -m pytest tests -q -k "note or central_master or tcg_keyword"`
- `cd frontend && npx tsc --noEmit && npx eslint src/pages/note-master/NoteMasterPage.tsx src/pages/super-admin/components/NoteMasterPanel.tsx`
- ja.json と en.json の鍵の数が同じ（CI の i18n 検査）
- `git diff --stat origin/main` が #1〜#8 とこの指示書・台帳だけ

## 5. 受入（マージ後）

| 基準 | 確かめ方 |
|---|---|
| N1 試験 T1〜T5 が通る | CI の backend の試験 |
| N1b 運営者の一覧も直る | 運営者の一覧（`super_admin_note_master.py:150`）は T1 と同じ `TcgNoteMasterResponse` を使うので T1 で確かめる。本番の測定には運営者の画面が入っていないので、本番では測らない |
| N2 本番の測定で `/management-center/note-master` の 5xx が 0 件 | prod-ui-check の結果表 |
| N3 同じ行の戻った時が 0.1 秒以下・最初が 2 秒以下 | 同上 |
| N4 ほかの画面の 5xx の合計と 2 秒を超える画面の数が、run 41377463601 より増えない | 同上 |
| N5 本番への反映が成功 | deploy の実行結果 |

## 6. 戻し方

この PR を revert する。DB は変えないので、戻すのは検査と選び肢と言葉と CSV の検査だけ。

## 7. 今回は直さないこと（記録）

- 審査役の指摘 5: 発送の時期と発送の除外の区分（`tcg_analyzer_svc.py:1278`・`:1280`）では状態の欄を渡していない。このため、そこでは `STATE_LITERAL` が `LITERAL` と同じ動きになる。id 148 の区分は「跡痕系」で、この 2 つの区分ではない（本番の読み取り 2026-11-02 12:08 JST）。今回の 500 には関係しない。解析の動きを変えるので、別の便で扱う。
