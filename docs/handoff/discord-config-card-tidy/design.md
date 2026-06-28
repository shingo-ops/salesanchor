# design — Discord設定ページ Card整理（見やすさ改善）

**仕事名**: discord-config-card-tidy
**日付**: 2026-06-28
**対象ADR**: ADR-067
**recon**: docs/handoff/discord-config-card-tidy/recon.md

---

## 概要
/admin/discord-config の設定項目が仕切りの無い縦並びで、グループ境界と各保存ボタンの所属が判別しづらい。標準金型 Card（variant=container）で論理3グループを箱化し、各箱に見出し（h3）を付ける presentational 変更。入力欄・ラベル・説明・保存ロジックは変更しない。色・余白は ADR-067（CSS変数・トークン）に従いトークン経由のみ。

## 設計方針（変更前→変更後）
| 項目 | 内容 |
|------|------|
| 箱化 | `<section>`×3 → `<Card variant="container" className="space-y-*">`×3（DiscordConfigPage.tsx:254/284/379） |
| 見出し | Guild ID に新規 `<h3>`（i18n discordConfig.guildSectionTitle）。自動セットアップ・チケットは既存 `<p>`→`<h3>`（文言キー不変） |
| 仕切り削除 | `<hr>`（DiscordConfigPage.tsx:377）は箱が代替するため削除 |
| 触りやすさ | ウェルカム textarea rows 3→6 |
| import | Card 追加（components/Card.tsx:27、className対応 components/Card.tsx:34） |
| i18n | ja/en に guildSectionTitle 追加（キー欠落ゲート対策で両方必須） |
| 不変範囲 | state・各handler・検証・API・各入力欄ラベル/説明・内部小箱（ロール名/ボタン設置）は1文字も変更しない |

## 受け入れ基準
| 基準 | 検証方法 |
|------|----------|
| 枠線の箱が3つ表示される | 画面目視（Guild ID/自動セットアップ/チケットが箱で分離） |
| 各箱の左上に見出しがある | 画面目視（サーバー接続／自動セットアップ／チケット機能設定） |
| 各入力欄にラベル＋説明がある | 画面目視（既存維持） |
| 保存ボタンが各箱の中にある | 画面目視（Guild IDの箱・チケットの箱それぞれに保存） |
| 変更ファイルは3つのみ（コード分） | git diff --stat = DiscordConfigPage.tsx / ja.json / en.json |
| 入力欄の中身は無変更 | git diff に各 input/label/hint が現れない |
| CI 全緑 | GitHub Actions |

## 外部・過去事例の参照と我々への応用
| 事例 | 概要 | 我々への応用 |
|------|------|--------------|
| 自社 PR #1919（ui-consistency-a） | 集計枠 fieldset/section → Card 統一（SalesPage/CommissionsPage） | 同じ「素のグルーピング→Card variant=container」変換を踏襲。CommissionsPage.tsx:135 を実装の手本にした |
| docs/CC_UI_GOVERNANCE.md:9 | 生タグより既存金型を優先 | 生 `<section>` を標準 Card に置換する本変更はガバナンス順守 |
| 標準コンテナ部品の再利用（デザインシステム一般） | レイアウトを個別手組みせず共通部品へ集約 | Card 集約で将来の余白統一（Task 1E）に自動追従でき、ページ個別調整が不要 |

## Task 1E との非干渉
docs/handoff/mobile-responsive/recon.md:118 のとおり Card「Preview専用」コメントは技術的依存なし。Task 1E は受け入れ基準未定義・進行中PR無しで停止状態のため、本変更が割り込む計画は存在しない。Card 余白の最終統一が将来決まれば Card 側で一括変更され本ページも自動追従する。
