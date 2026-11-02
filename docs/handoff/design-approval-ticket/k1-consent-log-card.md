---
mode: handoff
status: draft（設計案・審査前・PO 実装承認前・実装未着手）
---

# 実装カード（SM-K1-V2）: K1 が同意の記録（ADR-1034）も数える

この文書は何か（専門用語なしの1行）: 毎週の許可の点検で、しんごさんの同意を取って足した許可も「記録に載っている」と数えられるように、点検の道具を直すための作業指示書。

親: [self-maintenance-design.md](self-maintenance-design.md) の §5-8（先に読むこと）・§8 の S5〜S7／ADR: [ADR-1011](../../adr/ADR-1011-permission-self-maintenance.md)・[ADR-1034](../../adr/ADR-1034-opus-permission-delegation-ledger.md)

## 着手の条件（3つそろうまで手を付けない）

1. このカードと §5-8 の設計審査が APPROVE（クラウドの審査）。
2. 文書 PR が main に入っている。
3. PO の実装承認がある（このカードを名指しした返事）。

## 実物の事実（2026-11-02、origin/main d97928fa7 で確認）

- `docs/handoff/design-approval-ticket/routine/sm_k1_k3.py:102-142` `replay`。第1版の再生。**変えない**。
- `docs/handoff/design-approval-ticket/routine/sm_k1_k3.py:145-155` `run_k1`。ここを第2版の比べ方に替える。
- `docs/handoff/design-approval-ticket/routine/sm_k1_k3.py:238-263` `main`。引数を1つ足す。
- `scripts/dev/consent-audit.py:457-459` `item_sha8`。要素の印の式の正本。
- `scripts/dev/consent-audit.py:513-540` `read_ledger(home)`。同意の記録を読み、鎖（prev_sha）を確かめる。読む場所は `perm_paths(home)["perm_ledger"]`（関数は :489、記録のパスは :493）。
- `scripts/dev/consent-audit.py:1160` に `if __name__ == "__main__":` がある。モジュールとして読んでも点検は走らない（実装者は読み込み時に他の副作用が無いことも確かめる。あれば止めて Opus に報告）。
- `docs/handoff/design-approval-ticket/routine/test_sm_tools.py:179-207` に K1 の既存の試験（一致・remove(sha256)・不一致）がある。

## 変更（触るファイルは4つだけ）

### 1. `docs/handoff/design-approval-ticket/routine/sm_k1_k3.py`

- 足す引数: `--consent-home DIR`（既定 `os.path.expanduser("~")`）。同意の記録は `read_ledger(<DIR>)` で読む。
- `consent-audit.py` の読み込み: 同じ checkout の `scripts/dev/consent-audit.py`（パスは `DEFAULT_HOOK_TEST` と同じく HERE から4つ上）を `importlib.util.spec_from_file_location` で読む。`item_sha8`・`read_ledger` の2つだけを使う。式を写して持たない。
- `run_k1` の手順（§5-8 の1〜6をそのまま実装）:
  1. `replayed, applied = replay(...)`（今と同じ）。
  2. `led = read_ledger(consent_home)`。`led["chain_ok"]` が偽、または `rows` に空の dict（読めなかった行）があれば `{"k1": "エラー", "error": "同意の記録の鎖が切れている"}`。
  3. R（replayed）と C（current）のキーの和集合を回す。両方が list のキーは `collections.Counter(item_sha8(x))` の差で増減を出す。片方だけ list、または list でない値は、`R.get(k) != C.get(k)` なら `unexplained` に `"<k>:value:-"` を1件足す。
  4. 増減した印ごとに §5-8 手順4の条件で判定する。行は `sub`・`result`・`op` が §5-8 手順4の「受ける組」に当たるものだけを数える（当たらない行は無いものとして扱う）。対応表は sm_k1_k3.py の中に辞書1つで置く: `{"allow": "user-automode-allow", "environment": "user-automode-env", "soft_deny": "user-automode-soft-deny"}`。`SM-` で始まる文と §5-2 の文（`design_statement(args.design)`）は説明をつけない。文を取り出すには、増えた要素は C、減った要素は R から同じ印の文を探す。
  5. 並びの判定: 説明がついた要素を C と R から除き、残りの印の列が違えば `order_differs: true`。
  6. 出力のキー: `k1`・`rows_applied`・`replayed_sha256`・`current_sha256`・`baseline_sha256`（今と同じ）、`consent_log_rows`・`consent_chain`・`explained_by_consent_log`（`"allow:add:33b870c3"` の形の一覧・昇順）・`unexplained`（同じ形・昇順）・`order_differs`。
- 冒頭の説明文（docstring）の K1 の段落を §5-8 に合わせて書き直す。終了コードの意味は変えない。
- 触らない: `replay`・`ledger_rows`・`read_outside`・K3 の全部（`protected_hashes`・`run_k3`・`save_hashes`）・`canonical_sha`。

### 2. `docs/handoff/design-approval-ticket/routine/test_sm_tools.py`

- 既存の (c)・(f) の K1 の呼び出しすべてに `--consent-home <空の一時フォルダ>` を足す。判定の期待値は変えない（S7）。
- 足す試験（(g) として。同意の記録は `<一時フォルダ>/.claude/logs/permission-changes.jsonl` に、`prev_sha` を正しくつないだ行で作る。つなぎ方は `consent-audit.py` の `ledger_line_sha` を読み込んで使う）:

| # | 入力 | 期待 |
|---|---|---|
| T1 | C に R に無い文 X が1件。記録に `user-automode-allow`・`add`・`sub=record`・`recorded` の X の行 | 一致・`explained_by_consent_log` に X・exit 0 |
| T2 | T1 の記録が `held` の行だけ | 不一致・`unexplained` に `allow:add:<X の印>`・exit 1 |
| T3 | T1 の記録の後ろに同じ X の `remove`・`applied` の行 | 不一致 |
| T4 | 増えた文が `SM-` で始まり、記録に add の行がある | 不一致 |
| T5 | 同じ文 X が C に2件増え、記録に add の行がある | 不一致 |
| T6 | R にある文 Y が C に無い。記録に `user-automode-allow`・`remove`・`applied` の Y の行 | 一致 |
| T7 | T1 の記録の2行目の `prev_sha` を書き換える | エラー・exit 1 |
| T8 | T1 に加えて、C の allow の並びを R と入れ替える | 一致・`order_differs: true` |
| T9 | `hard_deny` に1件増え、記録に何かの target の add の行がある | 不一致（対応表に無いキー） |
| T10 | allow に X が増え、記録の行が `sub=apply`・`result=applied`・`add` だけ | 不一致（allow の add は record だけ受ける） |
| T11 | environment に E が増え、記録の行が `user-automode-env`・`sub=apply`・`result=applied`・`add` だけ | 不一致 |
| T12 | environment に E が増え、記録の行が `user-automode-env`・`sub=record`・`result=recorded`・`add` | 一致 |
| T13 | allow に §5-2 の文が増え、記録に `sub=record`・`recorded`・`add` の行がある | 不一致 |
| T14 | `--consent-home` の下に記録のファイルが無い・差も無い | 一致・`consent_log_rows` が 0 |
| T15 | 記録に JSON として読めない行が1行混じる | エラー・exit 1 |

### 3. `docs/handoff/design-approval-ticket/routine/ROUTINE.md`

- 手順9の文に「K1 は同意の記録も数える（設計 §5-8）。不一致のときは `unexplained` の値（`キー:op:印`）を報告書に写す。全文は書かない」を足す。
- 5行報告の3行目を「K1(一致／不一致 N 件)・K3(同じ／変化あり)」にする。

### 4. `docs/handoff/design-approval-ticket/self-maintenance-design.md`

- 実装後に S5〜S7 の結果を §8 の下に追記する（数と日時だけ）。

agent-console に登録した定期実行の指示文は変えない（呼ぶコマンドが同じため）。

## 確かめ（実装者が実行し、生の出力をファイルに残す）

1. `bash docs/handoff/design-approval-ticket/routine/test_sm_tools.sh` が全部合格。
2. 本物の記録で `python3 -I docs/handoff/design-approval-ticket/routine/sm_k1_k3.py --k1` を1回走らせ（読み取りだけ）、`unexplained` が3件・`explained_by_consent_log` が4件であること（S5）。違えば止めて Opus に報告する（推測で直さない）。クラウドでは本物の記録が無いので、この確かめは Opus が Mac で行う。
3. `--k3 --save` は走らせない。

## 想定される分かれ道

- `consent-audit.py` の読み込みで副作用（ファイルの作成・ネットワーク）が見つかった → 止めて Opus に報告。式を写して逃げない。
- 既存の (c)・(f) の試験が `--consent-home` を足して判定が変わった → 止めて報告（S7 を満たさない）。
- 本物の記録で S5 の数が違う → 止めて報告。週次保守の記録が増えた可能性があるため、Opus が数え直して設計の数を直す。

## 戻し方

- この PR を revert する。道具は repo の中だけで、設定・フック・記録のファイルは書かない。

## 触らない範囲

- `~/.claude/settings.json`・同意の記録・台帳・基準の写し・`~/.claude/logs` の下のすべて（読むだけ）。
- `scripts/dev/consent-audit.py`・`scripts/dev/perm-change.py`（読み込むだけで変えない）。
- K3 の対象（.backup・__pycache__ などの雑音の扱い）はこのカードでは変えない。
