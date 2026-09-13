# recon — i18n 欠落64キー追加

## 調査日時
2026-06-26

## 調査対象
`frontend/src/locales/ja.json` と `frontend/src/locales/en.json` に存在しない翻訳キーの全件洗い出し。

## Stage 0 — SHA固定
base: `d8b10184e1e61d9c29af7487fa461e9cce5e7377` (origin/main)

## Stage 1 — i18n設定確認

`frontend/src/i18n.ts:30-48` にて確認:
- keySeparator: `.`（デフォルト）
- namespace: `translation` シングル構成
- resources: `frontend/src/locales/ja.json:14-15` / `frontend/src/locales/en.json:14-15` を static import

## Stage 2 — 突合スクリプト結果

```
raw_t_hits 3299 | dropped_test/story 137 | dropped_non-keyshape 142 | clean_used_keys 1609
ja_defined 2750
TRUE_MISSING count 64
```

## Stage 3 — 欠落キー一覧（64件）

### badges（11件）
呼び出し元: `frontend/src/pages/badges/BadgesPage.tsx:76`

- `badges.badgeCount` — `frontend/src/pages/badges/BadgesPage.tsx:76`
- `badges.badgeList` — `frontend/src/pages/badges/BadgesPage.tsx:90`
- `badges.badgeName` — `frontend/src/pages/badges/BadgesPage.tsx:58`
- `badges.criteria` — `frontend/src/pages/badges/BadgesPage.tsx:61`
- `badges.icon` — `frontend/src/pages/badges/BadgesPage.tsx:59`
- `badges.leaderboard` — `frontend/src/pages/badges/BadgesPage.tsx:74`
- `badges.newBadge` — `frontend/src/pages/badges/BadgesPage.tsx:45`
- `badges.noBadges` — `frontend/src/pages/badges/BadgesPage.tsx:100`
- `badges.points` — `frontend/src/pages/badges/BadgesPage.tsx:63`
- `badges.rank` — `frontend/src/pages/badges/BadgesPage.tsx:76`
- `badges.user` — `frontend/src/pages/badges/BadgesPage.tsx:76`

### buddy（15件）
呼び出し元: `frontend/src/pages/buddy/BuddyPage.tsx:75`

- `buddy.coachId` — `frontend/src/pages/buddy/BuddyPage.tsx:75`
- `buddy.coachUserId` — `frontend/src/pages/buddy/BuddyPage.tsx:62`
- `buddy.end` — `frontend/src/pages/buddy/BuddyPage.tsx:83`
- `buddy.ended` — `frontend/src/pages/buddy/BuddyPage.tsx:81`
- `buddy.feedbackTitle` — `frontend/src/pages/buddy/BuddyPage.tsx:89`
- `buddy.menteeId` — `frontend/src/pages/buddy/BuddyPage.tsx:75`
- `buddy.menteeUserId` — `frontend/src/pages/buddy/BuddyPage.tsx:63`
- `buddy.newPair` — `frontend/src/pages/buddy/BuddyPage.tsx:50`
- `buddy.noFeedbacks` — `frontend/src/pages/buddy/BuddyPage.tsx:101`
- `buddy.noPairs` — `frontend/src/pages/buddy/BuddyPage.tsx:86`
- `buddy.pairId` — `frontend/src/pages/buddy/BuddyPage.tsx:91`
- `buddy.pairsTitle` — `frontend/src/pages/buddy/BuddyPage.tsx:73`
- `buddy.postedAt` — `frontend/src/pages/buddy/BuddyPage.tsx:91`
- `buddy.reason` — `frontend/src/pages/buddy/BuddyPage.tsx:91`
- `buddy.startedAt` — `frontend/src/pages/buddy/BuddyPage.tsx:75`

### goals（33件）
呼び出し元: `frontend/src/pages/goal-setting/GoalSettingPage.tsx:316`

- `goals.aiLabel` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:316`
- `goals.advisorEyebrow` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:317`
- `goals.advisorTitle` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:323`
- `goals.advisorLead` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:324`
- `goals.advisorMonthlyLabel` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:329`
- `goals.advisorMonthlyPlaceholder` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:341`
- `goals.advisorTypeLabel` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:343`
- `goals.advisorTypeRevenue` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:350`
- `goals.advisorTypeWins` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:358`
- `goals.advisorGenerate` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:368`
- `goals.advisorScopeMine` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:371`
- `goals.advisorInsufficient` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:377`
- `goals.advisorShiftNotSubmitted` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:382`
- `goals.advisorPlanTitle` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:391`
- `goals.advisorPlanNote` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:393`
- `goals.advisorLeads` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:398`
- `goals.advisorDeals` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:405`
- `goals.advisorWins` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:412`
- `goals.advisorEvidenceLabel` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:426`
- `goals.advisorWaiting` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:428`
- `goals.advisorUnitPrice` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:434`
- `goals.advisorWinRate` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:438`
- `goals.advisorDealRate` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:442`
- `goals.advisorWorkingDays` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:446`
- `goals.advisorWorkingDaysValue` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:449`
- `goals.advisorShowReasoning` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:459`
- `goals.advisorDecisionNote` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:461`
- `goals.advisorStep1` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:463`
- `goals.advisorStep2` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:465`
- `goals.advisorStep3` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:471`
- `goals.advisorMonthlyRequired` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:483`
- `goals.advisorWeeklyRequired` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:483`
- `goals.advisorGeneratedAt` — `frontend/src/pages/goal-setting/GoalSettingPage.tsx:487`

### leads（5件）
呼び出し元: `frontend/src/pages/leads/LeadsPage.tsx:304`

- `leads.channelType` — `frontend/src/pages/leads/LeadsPage.tsx:304`
- `leads.channelTypePlaceholder` — `frontend/src/pages/leads/LeadsPage.tsx:309`
- `leads.initiative` — `frontend/src/pages/leads/LeadsPage.tsx:312`
- `leads.initiative_inbound` — `frontend/src/pages/leads/LeadsPage.tsx:315`
- `leads.initiative_outbound` — `frontend/src/pages/leads/LeadsPage.tsx:316`

## Stage 4 — 住所違い判定
全63件 NOWHERE（真の欠落）。1件（badges.rank）は `leads.rank` が EXISTS_ELSEWHERE だが意味的に別物。住所違いは0件。

## Stage 5 — ja/en 対称性
- ja_defined 2750 / en_defined 2750 / ASYMMETRY 0（完全同期）
