# Recon: design-site 視認性・理解容易性 最高品質化

**調査日**: 2026-06-13 / 追加調査: 2026-06-14
**担当**: Generator（Claude Code）
**正本指示書**: 本 handoff 内 `design.md`

---

## ADR 検索結果

```bash
git grep -i "design-site" docs/adr/ docs/handoff/ | head -80
git grep -i "顧客マスタ" docs/adr/ docs/handoff/ | head -80
git grep -i "テナントポリシー" docs/adr/ docs/handoff/ | head -80
git grep -i "RLS" docs/adr/ docs/handoff/ | head -80
```

確認済み ADR:

| ADR | 内容 | 本件との関係 |
|---|---|---|
| `docs/adr/ADR-134-design-site-delivery.md` | design-site 配信方式（Basic 認証・静的配信） | 配信変更なし・対象外 |
| `docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md` | 全 SA 共通原則・KGI/KPI 正本 | 文言変更なし・図解の視認性のみ |
| `docs/adr/ADR-096-sa-customer-master-crm-data-model.md` | SA-02 顧客マスタ正本 | SA-02 図の文言根拠 |
| `docs/adr/ADR-106-sa-multitenant-policy.md` | SA-12 マルチテナントポリシー正本 | SA-12 状態表示の文言根拠 |
| `docs/handoff/design-site/design.md` | 設計図書サイト設計方針（素の HTML+CSS・SVG 直埋め・ビルドツールなし） | 本件も方針継続 |

---

## 現在地の事実確認（file:line）

| 観点 | file:line | 確認事実 |
|---|---|---|
| 共通コンテナ幅 | `docs/design-site/style.css:84-88` | `.page-container { max-width: 900px }` — 図解ページに対して狭い |
| 図ラッパ定義 | `docs/design-site/style.css:151-165` | `.architecture-diagram` — `overflow-x:auto`、SVG に `max-width:100%; height:auto` |
| トップ コンテナ | `docs/design-site/index.html:26` | `<div class="page-container">` — wide クラスなし |
| トップ 図ラッパ | `docs/design-site/index.html:93` | `<div style="overflow-x:auto">` — インライン style、共通クラス未使用 |
| トップ SVG | `docs/design-site/index.html:94-144` | `viewBox="0 0 1000 520"` `min-width:900px` — 下流 4 ノードが横に並び 900px 幅では詰まる |
| SA-02 コンテナ | `docs/design-site/sa-02.html:26` | `<div class="page-container">` — wide クラスなし |
| SA-02 図ラッパ | `docs/design-site/sa-02.html:97` | `<div class="architecture-diagram">` — wide クラスなし |
| SA-02 SVG | `docs/design-site/sa-02.html:98-181` | `viewBox="0 0 680 300"` — 情報量（7 ノード + 矢印 + 注記）に対してキャンバスが小さい |
| SA-02 注記 | `docs/design-site/sa-02.html:178-180` | `text` 要素 3 本で「顧客IDで参照のみ（コピーしない）」を表示。破線矢印の上に重なりやすい座標 |
| SA-12 コンテナ | `docs/design-site/sa-12.html:26` | `<div class="page-container">` — wide クラスなし |
| SA-12 未決表示 | `docs/design-site/sa-12.html:243-245` | `.decision-undecided` — 1 行長文。状態・理由・次アクションが分離されていない |
| SA-12 KGI未設定 | `docs/design-site/sa-12.html:256-260` | `.kgi-unset` — 1 ブロック長文。意味階層が見えにくい |

---

## ギャップまとめ

| # | ギャップ | 根拠 |
|---|---|---|
| G1 | コンテナ幅 900px で図が詰まる | `style.css:85` |
| G2 | トップ図ラッパがインライン style で共通クラス未使用 | `index.html:93` |
| G3 | SA-02 SVG が `680×300` で情報量に対して小さい | `sa-02.html:98` |
| G4 | SA-02 注記が矢印と重なりやすい座標にある | `sa-02.html:178-180` |
| G5 | SA-12 の未決・KGI未設定が長文 1 ブロックで意味階層が見えない | `sa-12.html:243-260` |

---

## 追加recon: 全SVG図の横断点検（2026-06-14）

| ページ | 図タイトル | file:line | 現状 | 改善方針 |
|---|---|---|---|---|
| SA-01 | 仕組みの図解 — SSOT原則のイメージ | `docs/design-site/sa-01.html:93-141` | `viewBox 640×240`、page-container未拡張 | `--wide`+`--wide` 付与、`viewBox 980×380` に拡張 |
| SA-02 | 仕組みの図解 — データの流れ | PR #2109変更済み | `viewBox 1160×560`、注記カード化済み | 最終目視対象 |
| SA-03 | 仕組みの図解 — トークン検証フロー | `docs/design-site/sa-03.html:92-151` | `viewBox 680×230`、page-container/diagram未拡張、サーバー検証ノード窮屈 | `--wide`+`--wide`、`viewBox 1180×430` |
| SA-04 | 仕組みの図解 — ID 保存 → テンプレ → リンク生成 | `docs/design-site/sa-04.html:94-140` | `viewBox 680×220`、テンプレ表 180px 幅に長文が詰まる | `--wide`+`--wide`、`viewBox 1160×420` |
| SA-05 | 仕組みの図解 — A/B 区分と 2 段階引当 | `docs/design-site/sa-05.html:93-149` | `viewBox 680×240`、A在庫2段階説明が横に詰まる | `--wide`+`--wide`、`viewBox 1180×500` |
| SA-06 | 仕組みの図解 — 解析パイプライン | `docs/design-site/sa-06.html:94-158` | `viewBox 680×220`、AI解析ノードが 145px 幅で窮屈 | `--wide`+`--wide`、`viewBox 1320×540` |
| SA-07 | 仕組みの図解 — 見積・請求の生成フロー | `docs/design-site/sa-07.html:93-147` | `viewBox 680×220`、見積書ノード 145px で1行に長文 | `--wide`+`--wide`、`viewBox 1180×460` |
| SA-12 | 仕組みの図解 — エンジン＋ポリシー注入モデル | `docs/design-site/sa-12.html:94-153` | `viewBox 680×230`、page-container--wide済み、diagram未拡張 | `architecture-diagram--wide` 追加、`viewBox 1160×420` |

---

## 停止条件チェック

- [x] 対象ファイルの構造が本書と一致（確認済み）
- [x] 対象図が別 PR で変更されていない（origin/main 確認済み）
- [x] 意味を変えない変更のみ
- [x] CSS 変更は modifier クラス追加のみ（全ページへの副作用なし）
