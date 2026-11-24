# recon: 受信箱のカルテの見せ方を段階で切り替える

- 基準: origin/main `1ac87e46b`（2026-11-24 fetch 後・作業場所 `release/inbox-karte-stage-tabs` の起点）
- 読んだ人: Opus（手元で `git show origin/main:<path>` と作業場所のファイルを読んだ）

## 0. 既存 ADR の検索

- `git grep -n "karte" origin/main -- docs/adr/` と `docs/adr/FEATURE-INDEX.md` で探した。関わるのは次の 3 本。
  - `docs/adr/ADR-108-inbox-karte-panel-redesign.md:38` 「顧客タブは段階によらず同一レイアウト（フルスペック）。段階で変えるのは『既定で開くタブ』のみ」→ 今回の依頼と食い違う。ADR-1089 で改める。
  - `docs/adr/ADR-108-inbox-karte-panel-redesign.md:102-105` 受入条件（商談タブの項目・顧客タブの項目・同一レイアウト・既定タブ）。
  - `docs/adr/ADR-110-karte-reference-alignment.md`（Accepted）タブ順 商談 / 顧客 / 連絡先。
  - `docs/adr/ADR-109`（段階の内部の名前・`frontend/src/constants/leadStatus.ts:9-17`）。
- ADR-1088 は PR #5713（未マージ）が使っているため、新しい番号は ADR-1089（`gh pr list --search ADR-1089` 0 件・origin/main に無し）。

## 1. 今の作り（file:line）

### タブの並び
- `frontend/src/pages/inbox/InboxKartePanel.tsx:228-238` タブの並びが `["deal", "company", "contact"]` の直書き。段階で変わらない。

### 最初に開くタブ
- `frontend/src/pages/inbox/useInboxState.ts:655-663` 会話一覧の `lead_status` を読み、`["existing_customer", "follow_up_short", "follow_up_long"]`（`:658` の直書き）なら `company`、それ以外は `deal`。
- `frontend/src/pages/inbox/useInboxState.ts:266` `karteTab` の初期値は `"deal"`。

### タブの中身
- `frontend/src/pages/inbox/InboxKartePanel.tsx:464` `export function KarteTabContent`。呼び元は `frontend/src/pages/inbox/InboxKartePanel.tsx:241` と試験 `frontend/src/pages/inbox/InboxKartePanel.discordButtons.test.tsx:27,40`（`tab="contact"` だけ）の 2 か所（`git grep -n KarteTabContent origin/main -- frontend`）。
- 連絡先タブ `:477-552`（メール・電話番号・Discord・Messenger/Instagram の未連携の印・Discord のボタン）。今回は変えない。
- 顧客タブ `:554-615`: 見出し 基本（呼び名・国・顧客タイプ）／取引プロフィール（取り扱いタイトル・販売形態）／実績サマリー（`PerformanceSummary`・読むだけ）／引き継ぎ（CS・関係性メモ）。
- 商談タブ `:617-720`: 見出し 次のアクション（次回アクション・次回アクション日・返信速度）／見極め（温度感・課題・ニーズ・競合確認）／商談規模（想定規模・月間見込み金額・1件単価・月間頻度）／メモ（商談メモ）。
- 項目の名前は `frontend/src/locales/ja.json` の `leads.*`（例 `leads.nickname`＝呼び名、`leads.responseSpeed`＝返信速度）。見出しは `inbox.section*`。新しい文は要らない。

### 保存
- `frontend/src/pages/inbox/useInboxState.ts:549-560` 入力欄から離れると、カルテの全部の値（`cardForm`）を `PATCH /leads/{id}` で送る。画面に出さない項目も値は `cardForm` に残るため、出し分けで値は消えない。

### 段階の名前
- `frontend/src/constants/leadStatus.ts:9-17` `lead`・`negotiating`・`existing_customer`・`follow_up_short`・`follow_up_long`・`lost`・`out_of_scope`。
- カルテの段階の印は `leadDetail.status` から出している（`frontend/src/pages/inbox/InboxKartePanel.tsx:124`）。

## 2. 自動の試験

- `frontend/tests-e2e/karte-visual-gate.spec.ts`（CI「Karte Visual Gate」・`.github/workflows/karte-gate.yml`。frontend が変われば PR ごとに走る）。
  - `:126-138` タブが 3 つで 商談・顧客・連絡先 の順 → 段階ごとに変える。
  - `:167-176`・`:231-268`・`:270-288`・`:349-383` リード（`leadShinki`）で顧客タブを押す → リードに顧客タブが無くなるので、成約後の見本（`leadKisonkosaku`）に替える。
  - `:178-229` 「商談タブに呼び名・国などが出ない」→ リードでは出るようになるので、段階ごとの置き場所の試験に置き換える。
  - `:290-319` 最初に開くタブ・`:321-347` 連絡先タブ → 今のまま通る。
  - `:392-411` 基準画像 2 枚（`karte-lead-deal.png`・`karte-customer-company.png`）→ 中身が変わるため作り直す。作り直しは `.github/workflows/karte-gate.yml` の手動実行（`--update-snapshots`・ボットが枝へ commit）。
- 見本データの段階: `frontend/tests-e2e/fixtures/karte-lead-shinki-with-deal.json:4` `lead`／`frontend/tests-e2e/fixtures/karte-lead-shoudanchuu-with-deal.json:4` `negotiating`／`frontend/tests-e2e/fixtures/karte-lead-kisonkosaku-with-deal.json:4` `existing_customer`／`frontend/tests-e2e/fixtures/karte-lead-oikomi-with-deal.json:4` `follow_up_short`。
- `frontend/tests-e2e/karte-screenshot-compare.spec.ts` は手動実行のときだけ・`continue-on-error`。リードは商談タブ、既存顧客は顧客タブを押すだけなので、そのまま動く（`:90-110`）。

## 3. 未確認

- 本番で、失注・対象外の相手のカルテを開く人がどれだけいるか（数えていない）。今回は今の見せ方を残すので、設計には効かない。
