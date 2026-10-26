# 実装カード 段階3 便1 — 金型 Button・HeaderButton を「丸＋元の言葉」に固定し 15 か所を揃える

- 状態: Opus 作成・自己審査済み（同一AIの審査）。PO の方針 2026-10-23「1」（押すと丸と元の言葉が並ぶ・部品1か所で全部変わる）。実装の開始は PO が設計を見て承認したあと
- 起点: origin/main 50d7f52da。ブランチ `release/loading-button-mold`、worktree /Users/tanizawashingo/worktrees/salesanchor/release-loading-button-mold
- 根拠: /tmp/CC報告ファイル/loading-button-recon/（targets.tsv・excluded.tsv・buttons.txt・tests.txt）、design.md 段階3、recon.md 段階3 C10
- 対象ADR: ADR-144・ADR-067・ADR-027・ADR-069

## 1. 金型
- frontend/src/components/Button.tsx: props から `loadingText` を削除。69 行 `{loading ? (loadingText ?? children) : children}` → `{children}`。Spinner（68行）・disabled||loading（62行）・aria-busy（63行）はそのまま
- frontend/src/components/HeaderButton.tsx: テキスト用の props に `loading?: boolean` を足し、Button へ `loading={loading}` で渡す。icon 用には足さない
- 金型の試験: Button.test.tsx:87,98-106 の loadingText の期待を「押下中も children のまま」に直す。HeaderButton.test.tsx に loading=true で role=status（Spinner）・aria-busy=true・disabled を確かめる試験を1本足す。stories に loadingText があれば外す

## 2. loadingText を外す 8 か所（属性を消すだけ。loading はそのまま）
AvatarUpload.tsx:99、RuleDrawer.tsx:292・308、RuleTestPanel.tsx:365・389、ScheduleSettingsPage.tsx:187・241、AnalysisDashboardPanel.tsx:821
- AnalysisDashboardPanel.tsx は本店の作業場所に他人の未保存変更がある。worktree の origin/main 版だけを触る

## 3. loading と三項を併用している 7 か所（三項だけ外し元のキーを残す）
FedExRateModal.tsx:207、ReviewValueFixForm.tsx:117、viewer の LoginView:94・PasswordChangeView:105・PasswordResetView:166・191・SignupView:146
- 形: `{busy ? t(A) : t(B)}` → `{t(B)}`。loading={…} が既にあることを行ごとに確かめる。無ければ BLOCKED:

## 4. 触らない範囲
- 残りの targets 119 件（便2〜6）、AsyncCombobox の loadingText 3 件、辞書（使われなくなるキーも消さない。便7）、CSS、scripts/
- 対象ファイルのもともとの lint 警告で止まったら直さず BLOCKED:

## 5. 文書
- 本カードを docs/handoff/loading-indicator/card-8.md として同じ PR に入れる（design.md 段階3・recon.md 段階3 も同じ PR）
- 台帳 .claude-pipeline/active-work.d/release-loading-button-mold.md（前便と同じ形）

## 6. 検証（生出力を /tmp/CC報告ファイル/loading-button-bin1/impl/ へ）
| 基準 | 検証方法 |
|---|---|
| loadingText が Button 系から消える | `git grep -n loadingText -- frontend/src` が AsyncCombobox 関連の3件と AsyncCombobox 本体だけ |
| 15 か所が丸＋元の言葉 | 対象ファイルの試験で押下中の文字が元の言葉。押下中の文字を見ている試験が落ちたら直さず BLOCKED:（Opus が期待を判断） |
| 押せなくなる変化の有無 | 15 か所それぞれで、disabled の条件に busy 変数が入っているかを一覧にして報告（入っていない箇所は「押下中に押せなくなる」差分） |
| 型・lint・i18n・UI | tsc 0・eslint（変更ファイル --max-warnings=0）0・check-i18n-missing-keys.js exit 0・check-ui-governance.js exit 0・Storybook build 緑 |
| 範囲 | `git diff origin/main...HEAD --name-only` が §1〜§3 のファイル＋§5 の文書・台帳だけ |

## 7. 想定分岐
- loadingText を使う箇所が 8 以外にも見つかった → 止まって一覧を報告
- vitest が負荷で時間切れ → 単独・`--testTimeout=30000` で切り分け、両方の生出力を残す
- schema.d.ts が無い → `npm run generate:api-types` を先に
- 行がずれた → 文面が一致すれば進め新旧の行を報告。不一致なら止まる
