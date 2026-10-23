# review-opus: 在庫のスマホ対応 便0（測るだけ）

> この文書は何か（1行）: 便0 の設計と実装を、設計担当（Opus・メインセッション）が反証を探す立場で確かめた記録。

**日付**: 2026-10-21
**対象**: ブランチ `release/inventory-mobile-baseline` の3コミット（`bfecce141` / `3fa7d08d7` / `223e79c81`）
**設計**: `docs/handoff/inventory-mobile-responsive/design.md`
**recon**: `docs/handoff/inventory-mobile-responsive/recon.md`
**区分**: B-3（テストと、正本でない `docs/` のみ。ADR-1015 §15）
**判定**: **APPROVE**（下の「残る穴」を記録した上で）

## 1. 自分の手で確かめたこと（報告の受け売りではない）

| 確認 | 実行したこと | 結果 |
|---|---|---|
| 見た目を変えていない | `git diff --stat origin/main...HEAD -- frontend/src` | **出力0行**（`frontend/src` は1行も変わっていない） |
| CI で収集される | `cd frontend && E2E_NO_WEBSERVER=1 npx playwright test --list --project=vl-mobile-390 --project=vl-tablet-768 --project=vl-desktop-1280` | `inventory` を含む行が **21件**（7テスト×3 project）。新規の「原文3件・タブ有り」も3 project すべてに出る |
| 型検査 | `cd frontend && npx tsc --noEmit` | **exit 0** |
| 既存検査の意味を変えていない | `inventory-helpers.ts:71` の `rawTexts ?? 1`、既存 spec の呼び出し（`inventory-raw-text-mobile.spec.ts:25,47,99`）が 375/375/1440 のまま | 既定値が従来と同じ1件。**原文ボタンの A1〜A4・A6 の条件は不変** |
| 計測の成立を assert しているか | `inventory-mobile-baseline.spec.ts:145`（カード1枚以上）、`:162-163`（開いたパネルを `--open` で1件に絞る） | あり。「0件のはみ出し」と「測れていない」が区別できる |

## 2. recon の引用を抜き取り検証した（2件の誤りを破棄）

下請け調査の報告をそのまま採らず、`recon.md` に載せる行は全件実ファイルで開いた。結果、報告のうち**2件が実ファイルと一致しなかったため破棄**した（`recon.md` §7 に記録）。

- 「`frontend/src/styles/mobile-shell.css:22-25`」→ そのパスにファイルは無い（実際は `frontend/src/mobile-shell.css:22-26`）
- 「`frontend/src/components/Drawer.tsx:88` が余白指定」→ 実際はフォーカストラップのコード。余白は `frontend/src/components/Drawer.css:85-89`

**教訓（記録に残す理由）**: 下請けの報告は一次情報ではない。設計に載せる前に必ず現物で突き合わせる。

## 3. 反証を探した点と結論

| # | 疑った点 | 調べ方 | 結論 |
|---|---|---|---|
| R1 | 「CI で走る」は本当か（PR #4602 で同じ思い込みが外れた） | `--list` で3 project の収集を実測 | 収集される。走ることは CI 初回で確定させる（A2） |
| R2 | モック集約で既存検査が緩まないか | `rawTexts` の既定値と既存 spec の引数を確認 | 緩んでいない（§1） |
| R3 | 「測るだけ」なので赤くならず、壊れても気づかないのではないか | assert の有無を確認 | 計測成立の assert があるため、測れなくなれば赤になる |
| R4 | タブ列を測れていないのでは | `frontend/src/features/inventory/InventoryRowDrawer.tsx:161-169`（原文2件以上で `itemTabs`）を読み、原文3件の計測を追加指示 | 追加済み。**実際に `tabs.found` が true になるかは CI で確定**（この端末では走らせられない） |
| R5 | 幅 360 を spec 側で上書きすると project の意味が崩れるのでは | spec 冒頭コメントと design 4-2・⑩ に理由を明記したか確認 | 明記済み |

## 4. 残る穴（隠さず記録する）

1. **この端末では spec を実行できない**（`npx playwright install chromium` が `ubuntu26.04-arm64` 非対応）。したがって `INVENTORY_BASELINE` / `INVENTORY_DRAWER_BASELINE` / `INVENTORY_DRAWER_TABS_BASELINE` の**中身は未確認**。CI のログが一次情報になる。
2. **「解析｜原文」の切替タブは未測定**（`InventoryRowDrawer.tsx:207-217`・super admin のときだけ出る）。認証モックの作り替えが必要で便の範囲外。design ⑫ の継続に残す。
3. **実機（SC-51G）の実測は未了**。ADB のペア設定が切れており（走査で候補ポート1件に `adb connect` → `Connection refused`）、PO からペア設定コードを受領するまで測れない。過去記録の 360 CSS px を根拠に 360 を測っている。
4. 同じ計測が3 project で3回走る（`vl-tablet-768` / `vl-desktop-1280` でも 360/390 を測る）。無駄だが実害は無く、project 名に依存した `skip` を入れると将来 project 名が変わったときに**黙って測らなくなる**ため、あえて入れていない。

## 5. 次の便に渡す条件

CI のログで数値が出たら、**その数値を根拠に**（推測でなく）次を設計する: 上部操作台のスマホ版（受信箱の形に寄せる）／カードのラベルと値の幅配分／詳細パネル内の折り返しと余白。合否を出す検査の閾値も、実測値を見てから決める。
