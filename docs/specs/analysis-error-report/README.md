# 解析の誤り報告から自律修正まで（analysis-error-report）

> この文書は何か: 在庫表で見つけた解析の誤りをボタンで報告すると、AI が原因を調べて直し、再解析で正解になったかを確かめて Discord に残す仕組みの表紙。

- あるべき姿（PO の言葉のみ）: [ideal-state.md](./ideal-state.md)
- KGI: [kgi.md](./kgi.md)（PO 承認済み 2026-10-17）
- 子文書: [recon.md](../../handoff/analysis-error-report/recon.md)・[design.md](../../handoff/analysis-error-report/design.md)
- 関係する仕様: [product-master/registration-rules.md](../product-master/registration-rules.md)（新商品の値の決め方）／[discord-ops-intake/README.md](../discord-ops-intake/README.md)（Discord を Mac で受ける既存の仕組み）／[ai-ops-247/README.md](../ai-ops-247/README.md)

## 境界
- 対象: 在庫表の行ドロワー（super admin の解析タブ）からの報告、Discord 通知、agent-console でのセッション自動起動、委任範囲での修正、再解析と機械照合、Discord への記録。
- 対象外: 閲覧ページ（ADR-1019）の利用者・スタッフからの報告（PO 2026-10-17「n」）。マージと本番反映の手順（今の GO 手順のまま）。

## 状態
あるべき姿 作成 2026-10-17・KGI PO 承認 2026-10-17・recon 済・design 自己審査 APPROVE 2026-10-17・実装未着手。
