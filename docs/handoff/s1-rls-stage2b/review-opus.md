---
mode: handoff
---
# Opus 審査記録 — S1 段階②b（仕入先台帳 public.suppliers の RLS）

> この文書は何か：設計書が実装に渡せる出来かを、同じ AI（Opus）が審査した記録です。独立した第二者のレビューではありません。

**日付**: 2026-10-16　**対象**: [design.md](design.md)、[recon.md](recon.md)、ADR-1018、ADR-145

**判定: APPROVE**

| 観点 | 結果 | 根拠 |
|---|---|---|
| 既存 ADR との整合 | 適合（ADR-1018 段階②「文脈を張らずに書く経路を先に直す」を同じ PR で実施。ポリシーは ADR-145 products と同文） | design §2-1 |
| 実物との整合 | 適合（書込経路を HTTP・CLI・CI・Celery の 4 系統で全列挙。Celery の書込 0 件。毎日の自動登録は端末取込 POST /tcg/line-devices/import と突合で確定） | recon §2・§3 |
| 本番データとの整合 | 適合（288 行すべて共通行。各社スキーマに suppliers は無い。DDL のみで行を変えない） | recon §1 |
| 利用者に見える変化 | なし（会社画面は自社行のみ読むので 0 件のまま。共通行は誰でも読める） | design §1 |
| 受入条件の検証可能性 | 適合（CI 試験・本番 SQL・取込ジョブ件数で○×判定可） | design §4 |
| 審査中に直した点 | ① CLI 入口（line_import_admin.run）で外側にも operator を張る案を取り下げ、「書込のある関数の中だけで張る」に統一（内側の reset で外側が崩れるのを防ぐ）② 端末取込の経路が 2b 初回調査の nginx 検索語（tcg/line-import）で漏れていたため、再調査（2b2）で確定させた | design §2-2 #5、recon §3 |

## 未解決事項

- 反映後に新しい仕入先の自動登録が起きるかは取込の内容次第。起きなければ「未観測」と記録し、CI 試験④を代替根拠とする。
- fx_rate_updater（Celery）の is_operator が接続に残る件は本便の対象外（別件として記録）。
