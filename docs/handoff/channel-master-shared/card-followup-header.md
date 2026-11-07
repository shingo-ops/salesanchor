# 実装カード: channel_masters.py 冒頭の説明を実物に合わせる（PR-B 審査の軽微な指摘 a）

- 設計: docs/handoff/channel-master-shared/design.md（PO 承認 2026-11-06）・recon.md
- 元の指摘: PR #5230 の審査役（Opus）軽微 (a)「channel_masters.py 冒頭の説明と conv_logs.py の INSERT/UPDATE の食い違い」
- PO の実施承認: 2026-11-07「1,2を順番に」（直前の選択肢 1＝この説明書きの直し）
- 区分: コメントだけ。動きは変えない。migrations/・deploy.yml・scripts/ を含まない

## 1. 実物（origin/main 931be583e で確認）

- `backend/app/services/channel_masters.py:1` が `from __future__ import annotations`。説明の文字列は :3-11 にある。`from __future__` の後ろにあるため、Python はこの文字列をファイルの説明（`__doc__`）として扱わない（Python の決まり: ファイルの説明は最初の文でなければならない。`from __future__` の前に置けるのは説明・コメント・空行だけ）。
- 説明 :9 は「名簿の表を読み書きする SQL はこのファイルだけに置く（他のファイルは関数を呼ぶ）。」と書く。実物では、このファイルの外に名簿の表へ触る SQL が3か所ある。
  - `backend/app/routers/conv_logs.py:485` create_channel_master の INSERT（会社専用の行を足す）
  - `backend/app/routers/conv_logs.py:574` deactivate_channel_master の UPDATE（会社専用の行を無効にする）
  - `backend/app/services/lang_judge.py:34` 除外条件の NOT EXISTS（読むだけ）
- 3か所とも表名は定数 `channel_masters.CHANNEL_MASTERS_TABLE` を使う（直書きなし）。`git grep -n "CHANNEL_MASTERS_TABLE\|CHANNEL_SETTINGS_TABLE" origin/main -- backend` で確認。

## 2. 変更（このファイルの :1-11 だけ）

変更前（:1-11）:

```python
from __future__ import annotations

"""channel_masters の共通定義と、名簿（全社1つの表）の読み口。

名簿は全社で1つの表（下の CHANNEL_MASTERS_TABLE）。tenant_id が NULL の行は共用（運営が管理）、
値がある行はその会社専用。会社ごとの「隠す」設定は
別の表（CHANNEL_SETTINGS_TABLE）に1行で持つ。

名簿の表を読み書きする SQL はこのファイルだけに置く（他のファイルは関数を呼ぶ）。
表名の文字列も、下の定数2つにだけ書く。
"""
```

変更後:

```python
"""channel_masters の共通定義と、名簿（全社1つの表）の読み口。

名簿は全社で1つの表（下の CHANNEL_MASTERS_TABLE）。tenant_id が NULL の行は共用（運営が管理）、
値がある行はその会社専用。会社ごとの「隠す」設定は
別の表（CHANNEL_SETTINGS_TABLE）に1行で持つ。

表名の文字列は、下の定数2つにだけ書く。他のファイルは表名を直書きせず、この定数を使う。
名簿を読む SQL と「隠す」設定を書く SQL は、このファイルに置く。
このファイルの外で名簿の表に触る SQL は次の3か所だけ（増やすときはここに書き足す）:
- backend/app/routers/conv_logs.py create_channel_master: 会社専用の行を足す（INSERT）
- backend/app/routers/conv_logs.py deactivate_channel_master: 会社専用の行を無効にする（UPDATE）
- backend/app/services/lang_judge.py: 書き写さない連絡手段を除く条件（読むだけ）
"""

from __future__ import annotations
```

触らない範囲: :12 以降（import・定数・関数）すべて。ほかのファイルすべて。

## 3. 確かめ方

| 基準 | 検証方法 |
|---|---|
| 説明がファイルの説明として読める | `cd backend && python3 -c "import ast,sys; t=ast.parse(open('app/services/channel_masters.py').read()); print(ast.get_docstring(t).splitlines()[0])"` が「channel_masters の共通定義と、名簿（全社1つの表）の読み口。」を出す |
| 動きが変わらない | `git diff HEAD~1 --stat` が channel_masters.py の1ファイルだけ。`git diff HEAD~1` の変更が :1-15 の範囲だけ |
| 説明の3か所が実物と合う | `git grep -n "CHANNEL_MASTERS_TABLE" -- backend/app` の channel_masters.py 以外の行が conv_logs.py 2行・lang_judge.py 2行（import と SQL）だけ |
| CI | PR の必須チェックが緑 |

## 4. 想定分岐

- :1-11 が上の「変更前」と1字でも違う → BLOCKED:（本線が先に進んだ。Opus が照合し直す）
- ruff などの検査が「from __future__ が先頭に無い」と止める → 説明の文字列の前に置くのは Python の決まりで許されている。止まったら直さず BLOCKED: で出力を返す

## 5. 戻し方

この PR を revert する。コメントだけなので本番の動きへの影響は無い。

## 受領確認

実装役は最初に「card-followup-header.md を受領: channel_masters.py :1-11 の説明だけを置き換える」と返す。
