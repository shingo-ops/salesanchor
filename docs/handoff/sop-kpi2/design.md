# Phase 3 設計 — sop-kpi2（SOPコンプライアンス保証機構）

**対象ADR**: ADR-121  
**recon**: docs/handoff/sop-kpi2/recon.md  
**日付**: 2026-06-09  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 事例1: WHO手術チェックリスト（Gawande 2009）→ チェックリストが存在するだけでは不十分。強制運用（ゲート）がないと実施率が下がり効果ゼロになる例あり。我々への応用: CI ゲートで**機械的に強制**し、個人の自律に依存しない。
- 事例2: トヨタ生産方式のアンドン（ライン停止権限の現場委譲）→ 「問題を見つけたら止める」を仕組み化。我々への応用: process-artifacts gate が fail を返すことで「止める」役割を担い、成果物不備のまま進むことを構造的に防ぐ。
- 事例3: Lean/Kaizen 改善活動の持続率（約30%しか定着しない）→ 根本原因は「仕組みでなく個人の意識に依存」。我々への応用: SOP を `docs/STANDARD-WORKFLOW.md` に一元化し、CI で強制することで「守る人次第」から脱却する。

---

## 0. 全体（一言）
PRに「申告書」を付け、点検プログラムが「成果物が揃って・本物か」を機械照合。**危ない変更の特例は人の承認でのみ**。緊急の後追い宿題は**自動起票＋自動期限監視**。

---

## 1. パスの区分（自動判定・客観）
| 区分 | パス | 扱い |
|---|---|---|
| 書類・メタデータ | `docs/` `*.md` `CLAUDE.md` `AGENTS.md` `.codex/` `.github/`(workflows以外) | **自動スキップ(pass)** |
| 危ない | `migrations/` `.github/workflows/deploy.yml` `scripts/`本番系(`*migrat*`・`*deploy*`・`aeon-dispatch.sh` 等) | 本検査 or **人の承認**特例のみ |
| 実コード(その他) | `frontend/src/` `frontend/public/` `backend/app/` `backend/tests/` `lp/src/` その他`scripts/`・`workflows/` | 本検査 or **自己申告**免除 |
| 未知のパス | 上記のどれにも無い | 安全側＝**本検査** |

- 全変更ファイルが「書類」区分のみ → 自動スキップ。1つでも「危ない／実コード」を含む → 該当の扱い。
- `scripts/`本番系リストは短く保ち、**governanceが新規本番スクリプトを監視**（リスト漏れ防止）。← 唯一の小さな判断（必要なら後で調整可）。

---

## 2. 申告書（PRテンプレ追加・`## チェックリスト` の先頭）
```
### 標準ワークフロー確認
- [ ] 免除（自律クラフト：バグ修正/CI/リファクタ）※低リスクのみ
- 対象ADR: ADR-____
- recon: docs/handoff/<仕事名>/recon.md
- 設計: ____
- （危ない変更の特例時）モード: 些細 / 緊急 ＋ 承認者: ____
```

---

## 3. テンプレ（成果物の型）
- **recon.md**（`docs/handoff/<仕事名>/recon.md`）：仕事名・日付・対象ADR・**file:line引用表**・不明点リスト。
- **設計doc**：対象ADR・recon.mdパス（相互参照）・**受け入れ基準表（各行に検証方法）**・**「外部・過去事例の参照と我々への応用」欄（必須・記入。小規模は「該当なし＋理由」可、空欄不可）**・弊害/計画/継続。

---

## 4. 点検プログラム（process-artifacts gate・常時実行）
- モデル：`check-claude-size.yml`（常時実行・内部分岐）。**node**。ジョブ名＝Ruleset登録名と一致。
1. パス判定（§1）。
2. **書類のみ** → pass。
3. **実コード（その他）**：
   - 免除宣言あり → pass＋免除ログ。
   - else **本検査**：ADR参照／recon実在＋**file:line実在照合**／設計実在＋**各受入基準に検証リンク**＋相互参照／**「外部・過去事例と応用」欄が記入済み（空欄不可）**／**不明ゼロ**。欠ければ fail。
4. **危ない変更**：
   - 自己申告免除は**不可**。
   - **承認確認**：PR Reviews API（`gh api repos/.../pulls/{番号}/reviews`）で**認可された人間（shingo-ops／開発パートナー）の APPROVED** があるか。
     - 些細モード＋承認 → pass（軽い扱い・ログ）。
     - 緊急モード＋承認 → pass＋**宿題待ち自動起票**（`gh issue create`・`sop-followup`ラベル・重複防止）＋期限記録。
     - 承認なし → 本検査（実コードと同じ）を要求。
5. fail時：**欠けている物と直し方**を明示出力。

---

## 5. 自動期限監視（scheduled workflow）
`weekly-stale-pr` の cron パターン流用。`sop-followup` ラベルの open issue をチェックし、**期限超過を自動警告・エスカレーション**。

---

## 6. ダッシュボード（定着・軽く自動）
ゲート通過／免除／危ない特例／宿題待ち の件数を**自動集計表示**。点検は「これを数分見る」だけ。

---

## 7. この設計自身の受け入れ基準（標準を自分にも適用）
| 基準 | 検証方法 |
|---|---|
| 偽の file:line（存在しない行）を含む recon は fail | 偽参照テストケース → fail確認 |
| 「外部・過去事例と応用」欄が空欄の設計は fail | 空欄テストケース → fail確認 |
| 検証リンク無しの受入基準を含む設計は fail | 空基準テストケース → fail確認 |
| 危ない変更で承認なしは本検査を要求（特例で素通りしない） | 未承認high-riskテスト → 本検査要求を確認 |
| 緊急承認PRは pass＋宿題待ち起票 | 緊急テスト → pass＋issue生成確認 |
| 書類のみPRは自動スキップ | docs-onlyテスト → pass確認 |

---

## 8. 建てる順番（非必須で作って検証 → 必須化）
1. テンプレ（recon.md・設計doc・PR）。
2. 点検プログラム（§4）＋テスト（§7）。**まだ必須にしない**。
3. 自動起票＋期限監視（§5）＋ダッシュボード（§6）。
4. 非必須で実運用テスト・緑を確認。
5. **KPI1＝必須化**（Ruleset変更・不可逆・PO承認）。← 最後のスイッチ。

---

## 8-B. gate 精度改善バックログ（ADR-133 実運用で判明した既知バグ）

### Bug-1: `/\n##/` が `\n###` にも一致 → 外部事例セクション内容が空判定される

**発見経緯**: ADR-133 PR（#1970）で `## 3. 外部・過去事例の参照と我々への応用` の直後に `### サブ見出し` があったところ、`validateDesignDoc` が section content を長さ 0 と判定し FAIL した。

**根本原因**: `check-process-artifacts.js` の next-section 検索 `/\n##/` が H3 (`###`) にも一致する。`afterHeading.match(/\n##/)` が `\n###` の位置でマッチし、section content が `\n` のみになる。

**暫定回避策**: セクション見出し直下に `###` でなく平文（1行以上）を置く。ADR-133 ではこの方法で通過済み。

**恒久修正案**: `/\n##/` → `/\n## /`（スペース付き）または `/\n##[^#]/`（三連シャープを除外）に変更する。修正行: `scripts/check-process-artifacts.js` の `afterHeading.match(/\n##/)` 部分。

---

### Bug-2: `file:line` 引用でディレクトリパスが EISDIR クラッシュを起こす

**発見経緯**: ADR-133 PR の recon.md に `` `frontend:8080` `` が含まれていたため、`validateFileCitations` が `frontend/` ディレクトリを `readFileSync` しようとして EISDIR 例外が uncaught のまま CI をクラッシュさせた。

**根本原因**: `existsSync(fullPath)` はディレクトリに対しても `true` を返す。その後 `readFileSync(fullPath, 'utf8')` がディレクトリに対して EISDIR をスローするが、try-catch がないため unhandled exception になる。

**恒久修正案**: `existsSync` の後に `statSync(fullPath).isDirectory()` チェックを追加し、ディレクトリなら `errors.push('ディレクトリパス')` として continue する。修正行: `scripts/check-process-artifacts.js` の `validateFileCitations` 関数内 `existsSync` ブロック（現行 line 117-119 付近）。

---

## 9. 不明ゼロ確認
- 承認primitive：PR Reviews API（§7 recon 確定）。
- 自動起票/期限：既存パターン（§7 recon 確定）。
- パス区分：§1で確定（`scripts/`本番系リストのみ運用で維持）。
→ **推測ゼロ。PO承認 → Generator へハンドオフ可。**
