---
mode: handoff
---
# 審査 — S1 段階③便A 設計（Opus 自己審査・独立した第二者審査ではない）

**日付**: 2026-10-16　**対象**: [design.md](design.md)、[recon.md](recon.md)
**判定**: **APPROVE**（下の補足 3 点をカードに反映する条件付き）

## 確認したこと

| 観点 | 結果 | 根拠 |
|---|---|---|
| PO 決定との整合 | 合致 | 案 C（書込だけ RLS）。読取ポリシーは USING (true) で現状と同じ |
| 書込経路の網羅 | 合致 | W1〜W8。全リポジトリの参照一覧で tasks・scripts は 0 件（recon §3） |
| 文脈の順序 | W2 のみ不足 → 設計 2-2 で 1 行追加 | integrations.py:551→562 の間に張り直し無し。ADR-072 の既存規則に寄せる修正で、ADR と実装の食い違いを ADR 側へ寄せる最上位原則どおり |
| ON CONFLICT DO UPDATE | 問題なし | 自社行のみが衝突対象（tenant_id UNIQUE）。SELECT は true、UPDATE USING は自社一致 |
| 連鎖削除 | 未確認を試験⑥で実測 | 公式 docs は参照整合の処理は RLS 対象外とするが CASCADE の明記なし |
| 戻し方 | あり | design §3（DDL のみ。行データは不変） |
| 受入条件の検証可能性 | あり | design §4 の表 |
| SSOT・データ分散 | 問題なし | 表・列の追加なし。ポリシーのみ |

## 補足（カードに反映）

1. 試験⑤の「接続の入れ替わり」再現は、save_credentials を monkeypatch で包み、元の処理の後に `SET app.tenant_id = ''` を実行する形にする（register_webhook はモックで ok と webhook_id を返す）。
2. migration のファイル名は着手時に origin/main の migrations/ と run_all_migrations.sh 末尾を確認し、最新より後の時刻にする。
3. .github/workflows/migration-test.yml の変更が必要になった場合は、実装を止めて Opus へ報告する（PO 確認が要る CI 土台ファイルのため）。
