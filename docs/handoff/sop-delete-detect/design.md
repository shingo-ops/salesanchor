# Design: 既存行の削除検知（削除ファイル宣言 vs 実diff）

- **ステータス**: Draft（①KGI承認済み / ②recon確定済み / ③設計＝本書）
- **日付**: 2026-06-24
- **正本**: `docs/STANDARD-WORKFLOW.md`（矛盾時は正本優先）
- **参照 recon**: `docs/handoff/sop-delete-detect/recon.md`
- **関連**: PR #2544（③指差呼称＝触るファイル照合・本設計はその拡張）、PR #2521（①共用許可制）、PR #2554（④自己保護）
- **関連ADR**: 該当なし（process-artifacts gate 拡張）

> local-only注意: 本doc・recon・実装は「コミット＋CI緑」で初めて成果物。

---

## 0. 一行サマリ

PRが「削除するファイル」を宣言し、宣言に無いファイルから既存行を削除していたら（`git diff --numstat` の削除行数>0）process-artifacts gate を赤にする。#2453（schedule.cssから107行を無自覚に削除）の直接対策。③の触るファイル照合の拡張で、PR番号2600以上で義務化（猶予）、自動生成ファイルは除外。

---

## ①KGI（PO承認済み）

**KGI（観測可能な事象）:**
```
PR番号2600以上のPRが、「削除するファイル」に宣言していないファイルから
既存行を削除していたら（git diff --numstat の削除行数>0、除外対象を除く）、
process-artifacts gate が赤になる。
対象は「ファイル内の行削除」も「ファイル丸ごと削除(git rm)」も両方。
PR番号2600未満はスキップ（猶予）。
```

**KPI（数値）:**

| KPI | 測定 | 目標 |
|---|---|---|
| PR≥2600で宣言外ファイルから削除しpassしたPR数 | CIログ | 0件 |
| 削除を正しく宣言したPRの誤爆ブロック数 | PR確認 | 0件 |
| 除外対象(lock/snapshot/active-work)の削除による誤爆数 | PR確認 | 0件 |
| planted violation（宣言外から削除→赤）の実証 | 手動PR | 1回・赤確認 |

**○×最終確認:** PR≥2600で「Aを削除」宣言のPRが、宣言外のBから行を削除 → CI赤を目視。

---

## ②recon サマリ（file:line / 要 recon.md 確定）

### 削除行の取得（生命線・確認済み）

- `git diff --numstat "${base}...${head}"` で「追加行数 削除行数 ファイルパス」が取得可能（実行確認済み）。
- CIでは既存の `git diff --name-only`（`scripts/check-process-artifacts.js:530`）と同じ BASE_SHA/HEAD_SHA を使って実行できる。**yml変更・追加env不要**。
- ファイル丸ごと削除（git rm相当）は「削除行のみ・追加0」で現れ、ファイル名は --name-only と同形式。→ 行削除・ファイル削除の両方を numstat の削除行数>0 で捕捉できる。

### 宣言の追加（③の拡張）

- `parseSOPDeclaration` の現戻り値に `touchFiles`（PR #2544で追加）がある。同型で `deleteFiles: string[]` を別フィールドとして追加する（「触る」と「削除」は別宣言・別照合＝エラーメッセージを分離できる）。
- PRテンプレ `.github/PULL_REQUEST_TEMPLATE.md:32` に「触るファイル:」行あり。「削除するファイル:」は :32 直後（:33の前）に挿入が自然。

### 既存の照合・除外（③で実装済み・流用）

- ③で `GRACE_THRESHOLD_PR = 2600`、`EXCLUDE_PATTERNS`（package-lock / -snapshots/*.png / active-work.md）、`printFailure`（exit1）が実装済み。本設計はこれらを流用する。

---

## ③設計（技術How・Generatorは判断ゼロ）

`scripts/check-process-artifacts.js` ＋ `.github/PULL_REQUEST_TEMPLATE.md`。

### 変更1: PRテンプレート（:32「触るファイル」行の直後）
```
- 削除するファイル: <!-- 既存行を削除/ファイル削除する対象をリポジトリ相対パスで列挙。PR番号2600以上で必須。なければ「なし」 -->
```

### 変更2: `parseSOPDeclaration` に `deleteFiles` 抽出
`touchFiles` と同型のパターンで「削除するファイル:」行を抽出。コメント/プレースホルダ/「なし」除去 → 配列化 → `declaration.deleteFiles` として返す。

### 変更3: 照合ロジック（③の触るファイル照合ブロックの直後に追加）
```
（PR番号 ≥ 2600 のとき）
1. const numstat = git diff --numstat "${base}...${head}" を実行
2. 削除行数>0 のファイル一覧 deletedFiles を抽出
3. EXCLUDE_PATTERNS（③と同じ）に該当するものを除外
4. 残った deletedFiles のうち declaration.deleteFiles に無いものを検出
   - あれば printFailure（「宣言外のファイルXから行を削除しています」）
PR < 2600 → このブロックを通らない（猶予）
```
※ `git diff --numstat` の実行は既存の git diff 呼び出し（`scripts/check-process-artifacts.js:530`）と同じ方式。

### 触らない範囲
- ③の触るファイル照合・①共用許可制・④自己保護・GO記録チェック・classifyFile は変更しない。
- yml は変更しない。

### KPI（=KGI検証）
- planted violation（PR≥2600で宣言外から削除）→ 赤
- 削除を正しく宣言 → 緑
- 除外対象のみ削除を宣言せず → 緑（誤爆なし）
- PR<2600 → スキップ

### 弊害対策
- **誤爆**: ③と同じ除外リストで自動生成系（lock/snapshot/active-work）を対象外。
- **「なし」宣言**: 削除が無いPRは「削除するファイル: なし」で明示。空欄と「なし」を同等に扱う（削除が実際に無ければ緑）。
- **猶予の正しさ**: PR<2600の作りかけは止めない。
- **本PR自身**: PR<2600で作成し、自分自身を新チェック対象外にする（猶予内）。`scripts/`変更＝GO必須。
- **numstatのパス形式**: リポジトリ相対パス。宣言も相対パスで書く前提をテンプレコメントに明記。

### 計画（段階）
- **P1（本書）**: 変更1〜3を1PR、PR<2600で作成、GO必須。
- **P2（実証）**: マージ後、PR≥2600相当の planted violation で赤を確認。

### 継続・再発防止（＋外部・過去事例）
- **直接の対象事故**: #2453（`f5ea8ec7`）が schedule.css から高さ・sticky定義を含む107行を**無自覚に削除**→今日のレイアウト崩壊の根。本チェックは「削除を意識的な宣言事項にする」ことで、この無自覚削除を機械的に止める。
- **外部事例**:
  - **policy-as-code（予防的コントロール）**: 違反時にパイプライン停止が検知のみより有効。本設計の「赤で止める」がこれ。
  - **手術安全チェックリスト**: 着手前の項目確認で重大事故が減るが、遵守維持が鍵。だから宣言（チェック）＋numstat照合（機械）の二段にする。
  - **Knight Capital**: 「死んだコードの残置・取りこぼし」が$440M損失の一因。削除の可視化は、逆に「消すべきものを消したか／消すべきでないものを消していないか」を宣言で意識化する。

---

## 関所・承認（process-artifacts gate）
- `scripts/check-process-artifacts.js` 変更 = `scripts/`配下 = **危険な変更 → PO の GO 記録必須**（GO原文 `GO #<PR>` literal）。
- recon を `recon.md` としてコミット＋CI緑にし、本design と相互参照。
- 本PRは PR番号<2600 で作成し、自分自身を新チェック対象外にする（猶予内）。

### GO記録（PR本文へ転記）
```
### GO記録
- GO発行者: Shingo（shingo-ops）
- 日時: 2026-06-24 HH:MM JST
- GO原文: GO #<PR番号>
- バックアップ確認: 該当なし（scripts/のみ・git管理下で復元可・DB非接触）
```

## 受け入れ基準

| 基準 | 検証方法 |
|------|------|
| PR≥2600で宣言外ファイルから削除→赤 | planted violation で目視（○=赤） |
| 削除を正しく宣言したPR→緑 | 実証PRで確認 |
| 除外対象のみ削除を宣言せず→緑（誤爆なし） | lock更新等のPRで確認 |
| PR<2600→スキップ（既存作りかけを止めない） | 既存PRで確認 |
| ファイル丸ごと削除(git rm)も検知 | git rm を含む実証で確認 |
| 差分が2ファイル（テンプレ＋scripts）＋handoff | `git diff --stat` |
| CI全緑（GO記録あり） | CI |
