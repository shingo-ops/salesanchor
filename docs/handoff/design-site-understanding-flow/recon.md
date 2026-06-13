# Recon: design-site 理解導線追加

**調査日**: 2026-06-14
**担当**: Generator（Claude Code）
**正本指示書**: 本 handoff 内 `design.md`

---

## ADR 検索結果

確認済み ADR:

| ADR | 内容 | 本件との関係 |
|---|---|---|
| `docs/adr/ADR-134-design-site-delivery.md` | design-site 配信方式 | 配信変更なし |
| `docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md` | 全SA共通原則 | SA-01の基準説明に参照 |

---

## 現状確認

| 観点 | file:line | 事実 |
|---|---|---|
| トップ page-subtitle | `docs/design-site/index.html:28-31` | ADR優先注意書きあり。読む順番の案内なし |
| トップ ①4原則カード | `docs/design-site/index.html:33-88` | 4原則カードあり・SA-01リンクあり |
| トップ ②全体図 | `docs/design-site/index.html:90-188` | 図あり・「最終的に実現すること」の概要説明なし |
| トップ 全体図説明文 | `docs/design-site/index.html:186-187` | 図の下に説明文あり。「図の読み方」1文なし |
| 各SA page-subtitle | `docs/design-site/sa-*.html:32-35` | 全ページ32行目に `page-subtitle` あり |
| 各SA 一言でいうと | `docs/design-site/sa-*.html:37-` | 全ページ「一言でいうと」セクションあり |
| 各SA 「このページで分かること」 | 全ページ | なし（追加対象） |
| 各SA 図の下の読み方 | 全ページ | なし（追加対象） |
| SA-01 バッジ | `docs/design-site/sa-01.html:29` | `badge--cross`（横断適用） |
| SA-02 バッジ | `docs/design-site/sa-02.html:29` | `badge--wip`（進行中 80%） |
| SA-03 バッジ | `docs/design-site/sa-03.html:29` | `badge--wip`（④ 実装中 60%） |
| SA-04 バッジ | `docs/design-site/sa-04.html:29` | `badge--wip`（④ 実装中 35%） |
| SA-05 バッジ | `docs/design-site/sa-05.html:29` | `badge--todo`（未着手） ← status-explain 対象 |
| SA-06 バッジ | `docs/design-site/sa-06.html:29` | `badge--todo`（未着手） ← status-explain 対象 |
| SA-07 バッジ | `docs/design-site/sa-07.html:29` | `badge--todo`（未着手） ← status-explain 対象 |
| SA-12 バッジ | `docs/design-site/sa-12.html:29` | `badge--todo`（未着手） ← status-explain 対象 |
| 用語ミニ辞典 | 全SAページ `⑤` セクション | 用語辞典あり（追加補足はここに集約済み） |
| architecture-diagram 末尾 | SA-01:156, SA-02:186, SA-03:154, SA-04:141, SA-05:159, SA-06:169, SA-07:149, SA-12:156 | `</div>` 直後に `<p>` 説明文（SA-05のみ `<p>` なし） |
| SSOT 補足 | SA-01:41-42 | 「一言でいうと」内にあり |
| style.css 末尾 | `docs/design-site/style.css:599-608` | `@media (max-width:600px)` レスポンシブブロック |

---

## ギャップまとめ

| # | ギャップ | 追加内容 |
|---|---|---|
| G1 | 読む順番の案内がない | `reader-guide`（トップ） |
| G2 | 全体の目的説明がない | `最終的に実現すること` セクション（トップ） |
| G3 | 全体図の読み方がない | `diagram-reading`（トップ図直後） |
| G4 | 各SA「何が分かるか」がない | `understanding-points`（全SAページ） |
| G5 | 未着手ページで実装済み誤解リスク | `status-explain`（SA-05/06/07/12） |
| G6 | 各SA図の読み方がない | `diagram-reading`（全SA図直後） |

---

## 停止条件チェック

- [x] 対象ファイルの構造が本書と一致（確認済み）
- [x] migration / deploy.yml / nginx / backend 変更なし
- [x] 意味を変えない変更のみ（追加のみ）
- [x] CSS 変更は新クラス追加のみ（全ページへの副作用なし）
