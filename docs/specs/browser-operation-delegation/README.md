# ブラウザ操作の Opus への委任（browser-operation-delegation）

**この文書は何か（専門用語なしの1行）**: しんごさんの Chrome の画面操作を、どこまで AI（Opus）に任せるかを決めた仕様書の表紙。

## 概要

Claude in Chrome（しんごさんのログイン済みの Chrome を AI が操作する道具）で、自社アプリの画面の確かめと、外の会社の管理画面の設定を Opus が行う。支払いなど、しんごさんだけが行う操作は機械の見張りで止める。

## 境界

- 対象: 自社アプリの画面の確かめ、外の管理画面（Meta・Google Workspace・Cloudflare・Firebase など）の読み取りと設定。
- 対象外: スマホの実機の確かめ、夜間の自動実行（Mac と Chrome が開いている間しか動かない）、クラウドの担当からの画面操作。

## 状態

あるべき姿 = PO 発言転記 2026-11-22。KGI は PO 承認済み（2026-11-23「1」）。recon・design は設計審査済み（同一 AI の自己審査）。ADR-1085 は Draft。便1の実装は PO の実装承認と実装カードの後。

## 子文書

- [ideal-state.md](ideal-state.md) — PO の言葉（正本）
- [kgi.md](kgi.md) — 物差し
- [../../handoff/browser-operation-delegation/recon.md](../../handoff/browser-operation-delegation/recon.md) — 現在地
- [../../handoff/browser-operation-delegation/design.md](../../handoff/browser-operation-delegation/design.md) — 設計
- [../../adr/ADR-1085-browser-operation-delegation.md](../../adr/ADR-1085-browser-operation-delegation.md) — 決定
