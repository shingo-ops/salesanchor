# 本番サーバーでの組み立てをやめる（build-on-github）

> この文書は何か: アプリの箱を本番サーバーで作るのをやめ、GitHub で作って会社の非公開の倉庫にしまい、本番は指紋の合う完成品を受け取って並べるだけにする仕組みの表紙。

親: [docs/specs/README.md](../README.md)

## 概要

今は本番への入れ替えのたびに、本番サーバー（prod1）の上で 5 つの箱（backend・frontend・gemini-egress・gha-exporter・secretary-agent）を組み立てている。組み立てを GitHub に移し、完成品を組織 GEN-RYU-System の非公開の倉庫（ghcr.io）にしまう。本番は指紋（sha256）で受け取って並べるだけにする。

## 境界

- 対象: 本番で組み立てている 5 つの箱の組み立て場所・しまい場所・受け取り方。
- 対象外: 置き場（shingo-ops/salesanchor）の公開をやめる件、秘書の ChatGPT 化そのもの（ADR-1058）、管理室サーバー prod2、組み立てずに取ってくる箱（nginx・certbot・redis・postgres）。
- 越えない線: 鍵・組織の画面の設定は PO が行う。倉庫の完成品を公開にしない（公開は取り消せない）。

## 案内

| 文書 | 中身 |
|---|---|
| [ideal-state.md](./ideal-state.md) | あるべき姿（PO の言葉の正本） |
| [kgi.md](./kgi.md) | 目標 K1〜K8（PO 承認済み） |
| [recon.md](../../handoff/build-on-github/recon.md) | 現在地 |
| [design.md](../../handoff/build-on-github/design.md) | 設計（便0〜便4） |
| [external-cases-dockerd.md](../../handoff/build-on-github/external-cases-dockerd.md) | 箱を動かす係の入れ直しの外部事例 |
| [adr-draft.md](../../handoff/build-on-github/adr-draft.md) | ADR 案 |
| [card-bin1.md](../../handoff/build-on-github/card-bin1.md) | 便1 の実装カード |

## ステータス

| 日付 | 状態 |
|---|---|
| 2026-11-04 | KGI K1〜K8 PO 承認。recon・design（審査 APPROVE）。PO の決定 4 件。便1 カード作成。実装未着手 |
