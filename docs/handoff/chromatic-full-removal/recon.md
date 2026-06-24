# recon — chromatic.yml 削除（main 残存分・後始末）

**仕事名**: remove-chromatic-yml-main
**日付**: 2026-06-25
**対象ADR**: ADR-073
**担当**: architect

---

## 概要

develop では PR #2569（chromatic-full-removal）で npm 依存・プラグイン・コメントを撤去済み。
main にのみ `.github/workflows/chromatic.yml` が残存していたため本 PR で削除。
develop→main リリース PR #2540 のコンフリクト解消待ちのため先行して単独削除 PR を起票。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `docs/adr/ADR-073-design-system-kgi-rubric.md:77` | 「ビジュアルリグレッションテスト（Chromatic等）（現フェーズでは手動確認で代替）」— Chromatic 不使用を肯定する根拠。残すべき行。 |
| `.github/workflows/deploy.yml:52` | `# 他ワークフロー（chromatic/e2e/frontend-check）と統一。` コメント行。develop 側 #2569 で除去済み。本 PR では触らない（deploy.yml のコンフリクト解消は #2540 の範囲）。 |
| `docs/handoff/chromatic-full-removal/design.md:1` | develop 側の撤去設計書（本 PR の正本）。 |

---

## 削除対象

| ファイル | 状況 |
|---|---|
| `.github/workflows/chromatic.yml` | main にのみ残存（develop には PR #2519 以前に削除済み）。本 PR で `git rm`。 |

---

## required status check 確認

ruleset id=15777895 の required 10件（2026-06-24 PUT後）に
`Chromatic Snapshot` / `UI Tests (Chromatic App)` は含まれていない。
required 除去作業は不要。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | required status checks に Chromatic が残っているか | `gh api repos/shingo-ops/salesanchor/rulesets/15777895` で確認 | ✅ 解消済み（含まれていない） |

**未解決ゼロ確認**: 全て解消済み

---

**正本設計**: `docs/handoff/chromatic-full-removal/design.md`
