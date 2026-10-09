# ay2b-eslint

base HEAD fb036a2388c2。コマンド: cd frontend && npx eslint --max-warnings=0 -f json <対象 .tsx 47 本>（ay2b-target-rel.txt）。対象 = 移管対象（確定+祖先未確定）と商品編集 G06 を含む .tsx（非テキストのみのファイルは除く）。生出力: ay2b-eslint-raw.json、終了コード: ay2b-eslint-exit.txt（exit=1、stderr: ESLint found too many warnings (maximum: 0).）。

結果: ファイル 47 本、errors 0、warnings 63。警告ありのファイル 1 本。

| ファイル | warnings | errors | ルール内訳 | 確定の移管対象を含むか |
|---|---|---|---|---|
| frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx | 63 | 0 | local/no-japanese-literal:62, (unused-directive):1 | いいえ（祖先未確定のみ） |

警告なし: 46 本。

警告の全行:

### frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx
- 71:21 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 175:96 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 180:17 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 181:12 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 182:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 189:11 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 191:12 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 195:33 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 196:33 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 197:33 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 198:33 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 199:42 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 203:42 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 207:42 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 211:42 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 215:42 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 219:42 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 225:17 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 226:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 227:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 228:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 229:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 230:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 230:37 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 231:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 231:51 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 232:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 232:49 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 247:18 warn (none) — Unused eslint-disable directive (no problems were reported from 'local/no-japanese-literal').
- 247:87 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 252:46 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 259:40 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 259:49 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 266:38 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 266:47 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 309:23 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 312:23 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 324:17 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 325:12 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 326:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 333:11 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 334:10 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 334:49 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 334:64 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 336:38 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 341:25 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 347:24 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 347:33 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 351:33 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 361:40 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 367:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 368:16 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 373:41 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 373:50 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 387:11 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 388:10 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 389:10 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 389:50 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 390:10 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 391:14 warn local/no-japanese-literal — i18n: JSX直書き日本語禁止。{t("key")} を使ってください（ADR-027）
- 526:48 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 528:36 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
- 529:62 warn local/no-japanese-literal — i18n: 文字列リテラル日本語禁止。t("key") を使ってください（ADR-027）
