# impl-report-5（in-app-notice-bell）

状態: DONE（DB の試験は CI で確認）

## 手順
- `origin/release/in-app-notice-bell`（b4a3f11a9）に合わせ、`origin/main` を取り込み（衝突なし。取り込みは docs の2ファイルのみ）。

## 作業A: 分類の行（design §5-改訂3）
- `migrations/20261024_100300_create_ai_cloud_views.sql`: `tenant_*` の `unparsed_lines` の次（並び順の位置）に `user_notices`（`actor_name`・`channel_name`・`kind`・`link_url`、`mask`）の1行を追加。冒頭の行数 1064 → 1068。
- 行数は main 取り込み後のファイルを、ARRAY の要素まで数えて 1064 と確認してから +4。
- `backend/tests/ops/test_ai_cloud_views.py`: 冪等の確かめの行数 1064 → 1068。
- `scripts/migration-guard/reference-allowlist.tsv`: sha256 を `sha256sum` の値（9a83f78d…918f）に更新し、理由欄の末尾に「 / in-app-notice-bell design §5-改訂3（分類4行追加）」。
- `migration-guard.yml` は触っていない。

## 作業B: DesktopShell / MobileShell の試験が落ちる原因
- 連なり: `DesktopShell.tsx`・`MobileShell.tsx` → `NoticeBell.tsx` → `lib/api.ts`（26行目 `import i18n from "../i18n"`）→ `src/i18n.ts`（`initReactI18next` を使う）。試験の `vi.mock("react-i18next")` は `useTranslation` だけを返すため「No initReactI18next export is defined」で落ちる。
- 2つ目: `NoticeBell.tsx` が `constants/icons` の `BellOutline` を使うが、両試験の `vi.mock("../constants/icons")` に無く、同じ形で落ちる（initReactI18next を直した後に判明）。
- 直し方（試験の側のみ。製品コードは不変）: 前例 `src/pages/leads/LeadFormFields.test.tsx` に合わせ、react-i18next の mock に `initReactI18next: { type: "3rdParty", init: vi.fn() }` を追加。icons の mock に `BellOutline: Icon` を追加。対象は `DesktopShell.test.tsx`・`MobileShell.test.tsx`。

## 確かめの結果
- `npx vitest run --project unit src/components`: 62 ファイル全通過、833 テスト通過、失敗 0。（`--project` なしだと storybook の browser 側が playwright の browser 不足で起動できないため unit 側で実行）
- `npm run check:all`: exit 0（lint は warning 59・error 0）。
- `python3 scripts/check-migration-value-writes.py repo`: 通過（348 ファイル走査、値の書き込みを持つ 15 ファイル = 許可一覧 15 行）。
- 流せなかったもの: `backend/tests/ops/test_ai_cloud_views.py` と `scripts/tests/test_migration_value_writes.py`（この環境に pytest・使い捨ての PostgreSQL が無い）。CI で確認が必要。
