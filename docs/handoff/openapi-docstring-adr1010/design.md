# Phase 3 設計 — openapi-docstring-adr1010

**対象ADR**: ADR-1010  
**recon**: docs/handoff/openapi-docstring-adr1010/recon.md  
**日付**: 2026-10-13  
**担当**: Dev（設計者 Opus のカードどおり）

---

## 外部・過去事例の参照と我々への応用

- 該当なし：説明文1行の番号修正で、外部事例を参照する設計判断が無いため。

---

## 変更の前と後

| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| `backend/tools/export_openapi.py:1` | `"""FastAPI の OpenAPI スキーマを、サーバーを起動せずに書き出す（ADR-1005）。"""` | 同文の「ADR-1005」を「ADR-1010」に変更 |
| `docs/handoff/cross-dept-integrity-foundation/card-c1.md:24` | 上と同じ文（コードブロック内の写し） | 同上 |

触らない範囲: 上記2行の「ADR-1005」以外の文字、ADR-1005 本体、コードの動作。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 変更が2行だけで、「ADR-1005」→「ADR-1010」以外の差分が無い | `git diff origin/main...HEAD -- backend/tools/export_openapi.py docs/handoff/cross-dept-integrity-foundation/card-c1.md` で +/- が各1行ずつ |
| backend/ frontend/ に API 型契約を指す ADR-1005 が残らない | `git grep -n 'ADR-1005' -- backend/ frontend/` の出力が空 |
| スクリプトの構文が壊れていない | `python3 -c "import ast; ast.parse(open('backend/tools/export_openapi.py').read())"` が終了コード0 |

---

## 技術 How・KPI

- KPI: backend/ frontend/ 内の API 型契約を指す旧番号 0 件。
- 技術選択: 行置換のみ（docstring の文字列なので実行時の動作は変わらない）。

---

## 弊害・トレードオフ

- 過去の cross-dept-integrity-foundation 記録の1行を書き換える → 同記録は docstring の写しなので、docstring と揃えるほうが正しい。他の記録は触らない。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 2行の番号置換 | Generator |
| 2 | 構文検証・grep 検証 | Generator |
| 3 | PR 起票 | Generator |

---

## 維持の仕組み

- 番号の付け直し時に旧番号の残りを探すのは人手で守る（付け直し PR の作成時に `git grep` で旧番号を確認する）。
- 今回の再発防止の自動化は範囲外。

## 戻し方

- この PR を revert する（2行の文字列変更のみで、DB・設定・実行時の動作に影響しない）。

## 継続

- 完了後の監視: 不要。
- 次フェーズへの引き継ぎ: なし。
