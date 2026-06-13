# Design: design-site 視認性・理解容易性 最高品質化

**作成**: Planner / Architect
**実装**: Generator（Claude Code）
**正本指示書**: 本ファイルおよび `recon.md`
**参照 recon**: `docs/handoff/design-site-visual-fit/recon.md`

---

## KGI

| KGI | 内容 |
|---|---|
| KGI-1 見切れゼロ | 主要図が 1440px/1280px で途中切れしない |
| KGI-2 はみ出しゼロ | 図形内テキストがボックス外に出ない |
| KGI-3 重なりゼロ | 図形・矢印・注記・ラベルが重ならない |
| KGI-4 100%表示で読める | ブラウザズーム 100%・通常 PC で図と表が読める |
| KGI-5 内容理解が速い | 非技術者が流れを説明できる |

---

## 変更対象・方針

### style.css — modifier クラス追加

追加位置: `docs/design-site/style.css:88`（`.page-container` 定義直後）

- `.page-container--wide { max-width: 1120px }` — SA-02/SA-12 用
- `.page-container--map { max-width: 1280px }` — トップページ用
- `.architecture-diagram--wide` — 図ラッパ拡張・横スクロール設計

既存 `.page-container`・`.architecture-diagram` は変更しない。

### index.html — コンテナ・図ラッパ・SVG

| 変更 | 対象 | 内容 |
|---|---|---|
| コンテナ | `index.html:26` | `page-container` → `page-container page-container--map` |
| 図ラッパ | `index.html:93` | `style="overflow-x:auto"` → `class="architecture-diagram architecture-diagram--wide"` |
| SVG | `index.html:94-144` | `viewBox="0 0 1180 660"` に拡大、ノード間隔・余白を広げる |

### sa-02.html — コンテナ・図ラッパ・SVG

| 変更 | 対象 | 内容 |
|---|---|---|
| コンテナ | `sa-02.html:26` | `page-container` → `page-container page-container--wide` |
| 図ラッパ | `sa-02.html:97` | `architecture-diagram` → `architecture-diagram architecture-diagram--wide` |
| SVG | `sa-02.html:98-181` | `viewBox="0 0 1160 560"` に再構成。注記を独立カードに退避 |

### sa-12.html — コンテナ・図ラッパ・SVG・状態カード化

| 変更 | 対象 | 内容 |
|---|---|---|
| コンテナ | `sa-12.html:26` | `page-container` → `page-container page-container--wide` |
| 図ラッパ | `sa-12.html:94` | `architecture-diagram` → `architecture-diagram architecture-diagram--wide` |
| SVG | `sa-12.html:95-153` | `viewBox="0 0 1160 420"` に拡大、6ノード全体余白確保 |
| 未決表示 | `sa-12.html:243-245` | `decision-undecided` 1行 → `state-card` で状態/理由/次アクション分離 |
| KGI未設定 | `sa-12.html:256-260` | `kgi-unset` 長文 → `state-card` で状態/理由/タイミング/候補分離 |

### sa-01.html — コンテナ・図ラッパ・SVG

| 変更 | 対象 | 内容 |
|---|---|---|
| コンテナ | `sa-01.html:26` | `page-container` → `page-container page-container--wide` |
| 図ラッパ | `sa-01.html:93` | `architecture-diagram` → `architecture-diagram architecture-diagram--wide` |
| SVG | `sa-01.html:94-141` | `viewBox="0 0 980 380"` に拡大（旧 640×240）、NG/OK両セクション余白拡張 |

### sa-03.html — コンテナ・図ラッパ・SVG

| 変更 | 対象 | 内容 |
|---|---|---|
| コンテナ | `sa-03.html:26` | `page-container` → `page-container page-container--wide` |
| 図ラッパ | `sa-03.html:92` | `architecture-diagram` → `architecture-diagram architecture-diagram--wide` |
| SVG | `sa-03.html:93-151` | `viewBox="0 0 1180 430"` に拡大（旧 680×230）、4ステップ＋失敗パス |

### sa-04.html — コンテナ・図ラッパ・SVG

| 変更 | 対象 | 内容 |
|---|---|---|
| コンテナ | `sa-04.html:26` | `page-container` → `page-container page-container--wide` |
| 図ラッパ | `sa-04.html:94` | `architecture-diagram` → `architecture-diagram architecture-diagram--wide` |
| SVG | `sa-04.html:95-140` | `viewBox="0 0 1160 420"` に拡大（旧 680×220）、テンプレ表180px→320px幅 |

### sa-05.html — コンテナ・図ラッパ・SVG

| 変更 | 対象 | 内容 |
|---|---|---|
| コンテナ | `sa-05.html:26` | `page-container` → `page-container page-container--wide` |
| 図ラッパ | `sa-05.html:93` | `architecture-diagram` → `architecture-diagram architecture-diagram--wide` |
| SVG | `sa-05.html:94-149` | `viewBox="0 0 1180 500"` に拡大（旧 680×240）、A在庫2段階説明余白確保 |

### sa-06.html — コンテナ・図ラッパ・SVG

| 変更 | 対象 | 内容 |
|---|---|---|
| コンテナ | `sa-06.html:26` | `page-container` → `page-container page-container--wide` |
| 図ラッパ | `sa-06.html:94` | `architecture-diagram` → `architecture-diagram architecture-diagram--wide` |
| SVG | `sa-06.html:95-158` | `viewBox="0 0 1320 540"` に拡大（旧 680×220）、AI解析ノード330px幅 |

### sa-07.html — コンテナ・図ラッパ・SVG

| 変更 | 対象 | 内容 |
|---|---|---|
| コンテナ | `sa-07.html:26` | `page-container` → `page-container page-container--wide` |
| 図ラッパ | `sa-07.html:93` | `architecture-diagram` → `architecture-diagram architecture-diagram--wide` |
| SVG | `sa-07.html:94-147` | `viewBox="0 0 1180 460"` に拡大（旧 680×220）、見積書/請求書ノード幅280px |

---

## 設計原則

1. 図は「説明の主役」— 図だけで大筋が理解できること
2. 余白をケチらない — 見切れ・はみ出し・重なりは余白不足から起きる
3. 図形内文言は改行込みで設計する
4. 1440px/1280px では横スクロールなし、1024px 以下は横スクロール保険
5. 内容は変えない（文意変更禁止）

---

## 受け入れ基準

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | トップ全体図が見切れない | 1440px/1280px/1024px でブラウザ確認 |
| A2 | SA-01〜07・SA-12 全図でテキストはみ出しなし | スクリーンショット目視 |
| A3 | 全図で重なり（ノード/矢印/注記/ラベル）なし | スクリーンショット目視 |
| A4 | SA-02 注記が矢印と重ならない | スクリーンショット目視 |
| A5 | SA-12 状態表示が構造化されている | ブラウザ確認 |
| A6 | 既存文言・ADR リンクが残存 | diff 確認 |
| A7 | `deploy.yml`/`migration`/`nginx` に変更なし | `git diff --name-only` |
| A8 | CI 緑 | GitHub Actions |

---

## 外部事例・根拠

本件は小規模静的 HTML/SVG の視認性改善。新ライブラリ不要。
一般的なドキュメントサイトの原則を適用:
- viewBox を情報量に合わせる
- 文章幅と図幅を分ける
- 状態表示は長文でなくラベル付き行に分ける
