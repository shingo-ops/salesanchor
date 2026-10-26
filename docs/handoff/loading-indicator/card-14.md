# 実装カード 段階3 便6b — 生 button 9 か所を金型 Button へ移し「丸＋元の言葉」にする

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO 承認: 方針 2026-10-23「1」、設計 2026-10-24「1」（design.md 3-3 便6「生 `<button>` 9 件を金型 Button へ」）、便6 着手 2026-10-25「1」
- 起点: 便6a 合流後の最新 origin/main。ブランチ `release/loading-button-bin6b`
- 根拠: /tmp/CC報告ファイル/loading-button-bin6/recon/rows.md・button-compare.md（origin/main c233ec8f6 時点の実物）
- 対象ADR: ADR-144（生 button 禁止・金型を使う）・ADR-067・ADR-027
- 弊害（design.md 3-2「見た目が変わるため単独で確かめる」）: 9 か所の見た目が金型の見た目に変わる。この便だけで合流し、本番の配信 JS で確かめる

## 1. 対象と移し先（行は c233ec8f6 時点）
| # | ファイル:行 | 今 | 移し先 | 中身 |
|---|---|---|---|---|
| 1 | components/GoogleCalendarStatusBar.tsx:144 | インライン style の赤塗り | `<Button variant="secondary" size="sm" loading={reconnecting} disabled={reconnecting} onClick={handleReconnect}>` | `{t("schedule.statusReconnect")}` |
| 2 | features/tcg-analysis-review/ItemComparison.tsx:112（1つ目） | 素の見た目・`disabled={true}` | `<Button type="button" variant="secondary" size="sm" loading={correctionState === 'saving'} disabled={true} onClick={onCorrectionSave}>` | `{t('tcgAnalysisReview.saveCorrected')}` |
| 3 | 同 :112（2つ目） | 同上 | `<Button type="button" variant="secondary" size="sm" loading={noteState === 'saving'} disabled={true} onClick={onNoteSave}>` | `{t('tcgAnalysisReview.saveMemo')}` |
| 4 | features/tcg-distribution/DistributionPreview.tsx:128 | dist-btn--primary | `<Button type="button" variant="primary" size="sm" loading={running} disabled={running \|\| preview.output_count === 0} onClick=… aria-label=…>` | アイコン＋`{t("distributionTarget.preview.runAll")}` |
| 5 | features/tcg-distribution/DistributionTargetForm.tsx:256 | dist-btn--primary | `variant="primary" size="sm" loading={saving} disabled={saving}` | `{t("common.save")}` |
| 6 | features/tcg-distribution/DistributionTargetList.tsx:179 | dist-btn--primary | `variant="primary" size="sm" loading={running === target.id} disabled={running === target.id}`、title・aria-label はそのまま | アイコン＋`{t("distributionTarget.list.runBtn")}` |
| 7 | pages/admin/ChannelMastersPage.tsx:141 | 素の見た目 | `variant="primary" size="md" loading={saving}`、disabled・aria-label はそのまま | `{t("channelMasters.add")}` |
| 8 | pages/inbox/ManualRecordSection.tsx:197 | クラスはあるが CSS 定義なし | `variant="primary" size="md" loading={saving}`、disabled・aria-label はそのまま | `{t("inbox.manualRecord.save")}` |
| 9 | pages/inbox/OutboundTranslationPreview.tsx:178 | outbound-translation-send-btn | `variant="primary" size="md" loading={confirming}`、disabled はそのまま | `{t("translation.outbound.confirmSend")}` |

- 共通: type・onClick・disabled・aria-label・title・data-testid は元のまま移す（元に type が無ければ足さない。ただし form の中にあるなら元の挙動を保つため元のまま）。className と style は金型が禁止しているので外す。アイコンの子要素はそのまま残す
- 移し先の決め方（Opus 判断）: 塗りの色が var(--accent) のもの（4〜6・9）は primary。padding 4px/12px のもの（1・4〜6）は sm。見た目の定義が無い追加・保存（7・8）は主たる操作なので primary md。常に押せない仮置き（2・3）と、赤い帯の上の再接続（1）は目立ちすぎない secondary sm（金型に赤塗りの variant は無い。danger は「消す」操作の意味なので使わない）
- import は各ファイルから components の Button への相対パス（同じ階層の既存 import の書き方に合わせる）

## 2. 余白
- #1 は元の style に `marginLeft: var(--space-3)` がある。親要素が flex で gap を持つか実物で確かめる。gap があればそのまま。無ければ Button.tsx の `layoutClassName` の決まり（Button.tsx のコメント・docs/CC_UI_GOVERNANCE.md）に従い、そのファイルの既存 CSS にクラスを1つ足して `margin-left: var(--space-3)` を書く。CSS ファイルが無い・決まりが読めない → NEEDS_DECISION:
- それ以外の余白は変えない

## 3. 使われなくなる CSS
- dist-btn・dist-btn--primary・outbound-translation-send-btn・manual-record-save-btn は、src 全体で他に使う箇所が残るか `git grep` で数えて報告する。CSS は消さない（便7 で整理）

## 4. 押せる・押せないの変化
- 9 か所とも disabled に読み込みの条件が入っている（2・3 は常に true）。変化なし。実物で違えば報告

## 5. 試験
- 変更するファイルを描く試験を `frontend/src` 全体から探し、一覧を impl/tests-found.txt に保存して全部を実行する
- 既知の期待の直し: GoogleCalendarStatusBar.test.tsx:103 が `textContent` に 'common.saving' を期待している。期待を「元の言葉 'schedule.statusReconnect' のまま・aria-busy="true"」に直す。disabled の確認（:102）は残す
- 生 button の役割・名前で探している試験（getByRole('button', { name }) など）は金型でも同じ名前になるはず。落ちたら直さず、落ちた行と理由を報告して BLOCKED:
- 全体の `npx vitest run -c vitest.unit.config.ts` を1回（tsc・eslint と同時に走らせない）。落ちたファイルは単独・`--testTimeout=30000` で再実行
- tests-e2e は触らない。`git grep -n "dist-btn\|outbound-translation-send-btn\|manual-record-save-btn" -- frontend/tests-e2e frontend/src` の結果を報告する（クラス名で探す試験があれば BLOCKED:）

## 6. 触らない範囲
- §1 以外の行、辞書、CSS の削除、scripts/、金型（Button.tsx・Button.css）

## 7. 文書
- 本カードを docs/handoff/loading-indicator/card-14.md として同じ PR に入れる
- 台帳 .claude-pipeline/active-work.d/release-loading-button-bin6b.md

## 8. 検証（生出力を /tmp/CC報告ファイル/loading-button-bin6b/impl/ へ）
| 基準 | 検証方法 |
|---|---|
| 対象が消える | targets.cjs を frontend/src で再実行し 0 件 |
| 生 button が減る | `git grep -c "<button" -- <対象8ファイル>` の前後。対象の要素が無くなる |
| 丸＋元の言葉 | tests-found.txt の試験と全体の unit 試験が pass |
| 型・lint・i18n・UI | tsc 0・eslint（変更ファイル --max-warnings=0）0・check-i18n-missing-keys.js exit 0・scripts/check-ui-governance.js exit 0 |
| 範囲 | `git diff origin/main...HEAD --name-only` が対象 8 ファイル＋直した試験＋§2 で足した CSS＋§7 の文書・台帳だけ |
