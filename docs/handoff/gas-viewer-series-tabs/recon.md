# recon: 顧客向け在庫一覧GAS — Seriesタブ追加・スマホで提供者を表示

- 日付: 2026-10-05
- 設計: Opus／調査・実装: Sonnet（Haiku 不使用）
- 対象: リポジトリ外の GAS webアプリ。本番と配信テスト用の2つ
- 社外秘: 仕入元データの値（提供者名・商品行）はこの文書に書かない

## 既存 ADR の確認
- ADR-067（デザイントークン強制）: トークンを唯一の正本とする（docs/adr/ADR-067-design-token-enforcement.md:17）。CI の検査対象は frontend 配下（同 :81-116）
- ADR-144（UIガバナンス）: CI ゲートの対象は frontend/src/pages 配下の tsx（docs/adr/ADR-144-ui-component-governance.md:43）
- 上の2つとも、GAS を対象にするとも対象外にするとも明記していない
  - PO 判断（2026-10-05）:「このGASのタブや色はデザインシステムに従わせる」

## 現在地（変更前）
- 本番 GAS は scriptId `1hc-Wn3g…`、公開デプロイは `AKfycbyS…`（版11）
  - これがお客様に渡している URL であることを PO が確認した（2026-10-05）
  - 本番の版11 とリモート HEAD に差はない（`diff -r` が空）
- 配信テスト用 GAS は scriptId `1Tb-84Fj39…`、テスト用デプロイは `AKfycbxnn…`（版13）
  - 本番のリモート HEAD とファイル単位で完全に一致する（`diff -q` が3ファイルとも0件）
- サーバー側（Code.js）の動き
  - 「在庫集計」シートの列を、ヘッダー名で探して取り出す（`indexOf`）
  - 許可リスト11列に Series は入っていなかった
- 画面側（index.html）の動き
  - スマホ（640px 以下）はカード表示
  - 提供者の列には `mobileHidden: true` が付いていて、CSS `td.mobile-hidden{display:none}` で隠れていた
  - 色の直書きは28種類・105箇所。`:root` のトークン定義はなかった
- Series の正本
  - SA の配信処理が書き込んでいる。対象: `backend/app/services/tcg_distribution_svc.py:56-69`（DIST_HEADERS の12列）、`:221-226`（`public.type_master.name_ja` を products.work_id 経由で取る）、`:487-488`（全面置き換え）
  - `type_master` は中分類マスタ（`migrations/20260921_060000_create_product_kinds.sql:5`）
  - GAS 側はシートを読むだけ
- トークンの正本
  - `frontend/src/tokens.css`・`frontend/src/index.css`（origin/main a34381937）
- タブの金型
  - `frontend/src/components/Tabs.tsx`・`Tabs.css`（variant underline／size md）
- 手順書: `docs/handoff/dist-deploy-guard/gas-deploy-runbook.md`
  - 版が古い（@5 のまま）
  - テスト用 GAS の記載がない
- コードの保管場所とされる `shingo-ops/tcg-client-viewer`
  - shingo-cc から見えない（`Repository not found`）
  - ローカルの `src/index.html` は586行で、本番の1323行と食い違っている

## 未確認
- 本番シートのヘッダー行そのもの（シートが非公開で、HTTP 401 になる）
  - 反映後の本番画面で、タブ11個が出たことを確認した
