# recon — line-analysis-tuning-log

**仕事名**: line-analysis-tuning-log  
**日付**: 2026-10-07  
**対象ADR**: ADR-100（grep 済み。LINE解析の取り込み・解析の親 ADR）。関連: ADR-1004・ADR-085・ADR-154（Gemini の使用量台帳・仕入元のプロンプト・TCG 移行。いずれも調整記録の置き場所を定めていない）  
**担当**: 設計担当（Opus）→ 実装担当（Sonnet）

---

- この文書は何か（1行）: LINE解析 Gemini の調整記録を置く場所を決める前に、既存の置き場所と決まりを事実だけ記録したもの。評価・提案は書かない。
- 設計仕様書（あるべき姿）: 新規作成（`docs/specs/line-analysis-tuning/README.md`）。理由は design.md に記載。
- 社外秘: 仕入元の名前・投稿の原文・判定の一覧は書かない。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `docs/STANDARD-WORKFLOW.md:32` | 設計仕様書の一覧（索引）は docs/specs/README.md と定めている |
| `docs/STANDARD-WORKFLOW.md:71` | 新規テーマ（索引に類似が無い）は設計仕様書＋子文書一式が必要 |
| `docs/STANDARD-WORKFLOW.md:72` | 既存の延長・修正は既存テーマの履歴・進捗表に追記する |
| `docs/STANDARD-WORKFLOW.md:80` | recon は file:line 引用と既存 ADR 検索の結果を明記する |
| `docs/ai-agents/design-partner.md:110` | 新テーマ着手時はまず索引で似たあるべき姿を探す |
| `docs/ai-agents/design-partner.md:111` | 在れば新規作成せず既存へ追記 |
| `docs/ai-agents/design-partner.md:112` | 無ければ新規作成可。ただし「なぜ既存で足りないか」を1行明記し、索引に1行登録する |
| `docs/ai-agents/design-partner.md:113` | 索引を唯一の入口とする（置き場の SSOT） |
| `docs/ai-agents/design-partner.md:254` | 定点観測（track-record）の未記帳行は次の便に相乗りして記帳する |
| `docs/specs/README.md:73` | 索引の既存の最終行。書式は「領域｜リンク｜状態」の3列 |
| `docs/specs/agent-complete-design/track-record.md:9` | 記帳ルール（1便1行・起因ラベル・未記帳は次の便に相乗り）の先例 |
| `docs/specs/ledger-guard/track-record.md:3` | 表紙リンク行と「記録（1便1行）」表の先例 |
| `docs/handoff/line-accuracy-pages/accuracy-evidence.md:1` | 精度の記録の先例（1回の測定の証拠。版をまたぐ履歴ではない） |

## 調べた事実

1. 索引 `docs/specs/README.md` に LINE 解析（Gemini の指示書・精度）の行は無い（grep で "LINE" を含む行は、完売ルールの認識合わせ・GO 記録の2行だけ）。
2. 版ごとの設計書が `docs/handoff/gemini-v8`・`docs/handoff/gemini-v9`・`docs/handoff/gemini-v10`・`docs/handoff/gemini-v101`・`docs/handoff/gemini-v102`・`docs/handoff/gemini-prompt-d`・`docs/handoff/gemini-prompt-e` など、PR 単位に分かれて散らばっている。版をまたいだ精度の推移・PO の判断の一覧を持つ文書は無い。
3. 精度の記録の先例は `docs/handoff/line-accuracy-pages/accuracy-evidence.md`（2026-10-01、1回分の測定）。
4. ADR 検索: `git grep -il gemini -- docs/adr` で ADR-014・075・080・085・100・1004・110・154 などが該当。調整記録（版ごとの精度・PO の判断・事故）の置き場所を定める ADR は無い。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 索引に似たあるべき姿が在るか | docs/specs/README.md を grep | 解消済み（無い） |
| 2 | 既存 ADR に置き場所の定めが在るか | git grep docs/adr | 解消済み（無い） |

**未解決ゼロ確認**: 全て解消済み
