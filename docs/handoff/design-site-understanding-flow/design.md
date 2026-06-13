# Design: design-site 理解導線追加

**作成**: Generator（Claude Code）
**実装**: Generator（Claude Code）
**参照 recon**: `docs/handoff/design-site-understanding-flow/recon.md`

参照ADR:
- ADR-134: design-site 配信方式（nginx Basic認証・静的HTML配信）
- ADR-095: SAシリーズ共通4原則（追加のみ・ADR本文変更禁止・docs-only・正本整合）

---

## KGI

| KGI | 内容 |
|---|---|
| KGI-1 トップ5秒理解 | 読む順番・全体の目的を冒頭で伝える |
| KGI-2 各SA 1分理解 | 「このページで分かること」3点で目的明示 |
| KGI-3 専門語で詰まらない | 図の読み方・用語補足（初出1回のみ） |
| KGI-4 未着手/進行中の誤解ゼロ | status-explain で設計方針ページと明記 |
| KGI-5 正本との整合維持 | ADR本文・文意変更なし・追加のみ |

---

## 変更対象・方針

### style.css — 理解導線用クラス追加

追加位置: `docs/design-site/style.css:599`（レスポンシブブロック直前）

| クラス | 用途 |
|---|---|
| `.reader-guide` | トップ「この設計図書の読み方」カード |
| `.reader-guide__title` | タイトル行 |
| `.understanding-points` | 各SA「このページで分かること」カード |
| `.understanding-points__title` | タイトル行 |
| `.diagram-reading` | 各図の下の読み方1文（左ボーダー） |
| `.status-explain` | 未着手/進行中ページの状態説明 |

既存スタイルは変更しない。

### index.html

| 追加 | 位置 | 内容 |
|---|---|---|
| reader-guide | `index.html:32` 直後 | 3ステップの読み方案内 |
| 最終的に実現すること | `<!-- ②全体図 -->` 直前 | 全体目的の1段落説明 |
| diagram-reading | 全体図SVG `</div>` 直後 | 図の読み方1文 |

### 各SAページ（sa-01〜07、sa-12）

| 追加 | 位置 | 内容 |
|---|---|---|
| understanding-points | `page-subtitle </p>` 直後 | 「このページで分かること」3点 |
| status-explain | SA-05/06/07/12 のみ | 未着手ページの誤解防止説明 |
| diagram-reading | `architecture-diagram </div>` 直後 | 「読み方:」1文（用語初出補足含む） |

---

## 設計原則

1. 追加のみ — 既存の図・ADRリンク・正本注意書きは削除しない
2. 各追加ブロックは短く — 説明を増やしすぎない
3. 専門語は消さず初出1回だけ括弧補足する
4. 未着手ページはバッジ確認（badge--todo）で対象を判断
5. docs-only 変更のみ — migration/deploy.yml/nginx は触れない

---

## 受け入れ基準

| # | 基準 | 検証方法 |
|---|---|---|
| A1 | トップページに「この設計図書の読み方」がある | `git grep "この設計図書の読み方"` |
| A2 | トップページに「最終的に実現すること」がある | `git grep "最終的に実現すること"` |
| A3 | 各SAページに「このページで分かること」が3点表示 | `git grep "このページで分かること"` |
| A4 | 各図の下に「図の読み方」が1文表示 | `git grep "読み方:"` |
| A5 | SA-05/06/07/12 に状態説明がある | `git grep "このページは設計方針を説明するページです"` |
| A6 | 既存の図・ADRリンク・正本注意書きが消えていない | diff 確認 |
| A7 | migration / deploy.yml / nginx / backend 変更なし | `git diff --name-only` |
| A8 | CI 緑 | GitHub Actions |

---

## 外部・過去事例の参照と我々への応用

### 外部事例
本件は静的HTMLドキュメントサイトの「理解支援」追加。
非技術者向けドキュメントの標準原則（Nielsen Norman Group「Progressive Disclosure」等）:
- 冒頭に目的・読む順番を明示する（認知負荷軽減）
- 各セクションに「このセクションで分かること」を入れる（スキャナビリティ向上）
- 図には読み方の1文を添える（グラフィカルリテラシー補助）
- 未完成ページは明示的に状態を示す（期待値管理）

### 我々への応用
- `reader-guide`: トップページ冒頭に3ステップ読み方案内 → 初見でも迷わず読み進められる
- `understanding-points`: 各SAページに「このページで分かること」3点 → 読む目的を先に把握
- `diagram-reading`: 各図の直下に読み方1文 → 専門語の初出補足を1か所に集約
- `status-explain`: 未着手SA（05/06/07/12）に状態説明 → 「設計方針を説明するページ」と明示して誤解防止
