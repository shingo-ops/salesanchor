# ADR-109: status の SSOT化（不変コード＋i18nラベル）

**Status**: Accepted
**日付**: 2026-06-04
**配置先**: `docs/adr/`
**関連**: ADR-108（受信箱カルテ表示再編）/ ADR-012（What/How 分離）/ ADR-025 / デザイントークン・SSOT方針

> このADRは What／Why／Scope のみを記す。実装手順・命名規則（How）は Generator に委ねる。
> 再現性は受け入れ条件で担保する。

---

## Why

- `status` は今、日本語文字列を「値そのもの」として保持し、DB・SQL・コードに直書きで散在している（18箇所）。改名のたびに全箇所を探して直す必要があり、単一の正（SSOT）になっていない。
- **既に弊害が出ている**: `LeadsPage.tsx` 107-114行の旧値マップ（移行前の "コンタクト中／提案中／案件化／保留"）が放置され、現行値（商談中／既存顧客／追客（短期）／追客（長期）／対象外）が翻訳されず日本語の raw 値で表示される既存バグがある。
- 「新規→リード」のような表示改名を、データ移行もコード探しもなしに、ラベル1ヵ所の変更で行える状態にしたい（デザイントークンの SSOT の考え方を status に適用）。

---

## What（決定）

1. `status` の**値を不変の内部コード**に置き換える（コード文字列の具体的命名は Generator に委ねる＝安定識別子）。7つの状態は現行どおり：リード（旧"新規"）／商談中／既存顧客／追客（短期）／追客（長期）／失注／対象外。

2. **表示ラベルは i18n（コード→ラベル）に一本化**する。以後の段階名変更はラベルの変更だけで完結し、データ・コードは変更不要にする。先頭段階のラベルは「リード」とする。

3. **既存の全 `leads` 行を新コードへ移行**する（1対1マッピングの安全migration、`deploy.yml` 経由）。DB DEFAULT も新コードへ ALTER する。

4. **`LeadsPage` の旧値マップを撤去**し、全7値をコード経由で正しく表示する（上記の既存バグ修正を含む）。

5. コード・SQL中の status 日本語リテラルを撤廃し、比較・代入を全てコード（enum）経由に統一する。

---

## Scope（変換対象）

| 対象 | ファイル | 内容 |
|------|---------|------|
| enum 定義 | `backend/app/schemas/lead.py` | LeadStatus enum を不変コードへ |
| バックエンド直書き | `backend/app/routers/leads.py` (257, 326-328, 515行) | 日本語リテラルをコードへ |
| バックエンド直書き | `backend/app/routers/leads.py` (534行) | audit log の初期値 |
| バックエンド直書き | `backend/app/routers/analytics.py` (254, 450行) | |
| バックエンド直書き | `backend/app/routers/dashboard.py` (109行) | |
| バックエンド直書き | `backend/app/services/discord_gateway/dm_writer.py` (100行) | 新規lead作成の初期値 |
| DB DEFAULT | `migrations/003_...` 新migration で ALTER DEFAULT | |
| テスト | `backend/tests/conftest.py` (314行) | |
| フロント | `frontend/src/pages/LeadsPage.tsx` (68, 107-114行) | 旧値マップ撤去 |
| フロント | `frontend/src/features/inbox/inbox.types.ts` (21-28行) | STATUS_TABS |
| フロント | `frontend/src/features/inbox/inbox.types.ts` (40行) | FOLLOWUP_EXCLUDED |
| フロント | `frontend/src/features/inbox/useInboxState.ts` (664, 719行) | |
| i18n | `frontend/locales/ja.json` / `en.json` | コード→ラベルの対応に整理 |

---

## Migration の扱い

- 新 migration ファイルで全テナントの `leads.status` を1対1でコードへ UPDATE
- DB DEFAULT を新コードへ ALTER
- `deploy.yml` 経由で develop→main マージ時に自動適用
- VPS への直接作業はしない

---

## Scope外

- **過去の audit log（DB）に記録済みの旧 status 文字列は書き換えない**（履歴の改変はしない）。新規記録分からコードを用いる。
- 段階の遷移ロジック（昇格・降格の自動化）＝別ADR。本ADRは「値の表現」だけを正常化する。
- カルテの表示再編＝ADR-108。

---

## 事業上の制約

- マルチテナント：移行は全テナントの `leads` に一括適用（`deploy.yml` 経由・手動作業なし）。
- 可逆性：コードは不変なのでラベル変更は可逆。値移行は1対1なので逆変換も定義可能。

---

## 受け入れ条件（観測可能な挙動）

- [ ] コード・SQL中に status の日本語リテラル（"新規"／"商談中"／"既存顧客"／"追客（短期）"／"追客（長期）"／"失注"／"対象外"）が残っていない（全文検索でゼロ）。比較・代入はすべてコード（enum）経由。
- [ ] 段階の表示ラベルは i18n から来る。ラベルを変更しても（例「リード」→別語）データ・コードは変更不要で反映される。
- [ ] `LeadsPage` で全7段階が正しいラベルで表示される（旧値マップ起因の raw 日本語表示が解消されている）。
- [ ] 既存の全 `leads` 行が新コードへ移行済みで、旧値（"新規" 等の日本語）の行が残っていない。DB DEFAULT が新コードになっている。
- [ ] Discord DM 受信時の新規 lead 作成が、初期段階＝「リード」相当のコードで作られる。
- [ ] 過去の audit log の旧値はそのまま保持されている（履歴として）。
- [ ] migration が `deploy.yml` 経由で自動適用される（手動VPS作業なし）。

---

## 未確定

なし（V3／V4 で変換面は確定）。コード文字列の具体的命名は Generator 判断。
