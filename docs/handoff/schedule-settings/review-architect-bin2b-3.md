# 審査報告 便2b 設計（第3回）

本報告は design-bin2b.md 第3版（5f9ecaf77）の設計審査である。

- 審査役: クラウドの Architect（コードは直さない）。審査日 2026-11-25
- 対象: `docs/handoff/schedule-settings/design-bin2b.md` 第3版（枝 `release/schedule-settings-bin2b`）。作業場所で `git log -1 --oneline` が `5f9ecaf77` であることを確認し、`git rev-parse HEAD` と `origin/release/schedule-settings-bin2b` が同じ `5f9ecaf771a978fd07f037aaa65ada097507ca65` であることも確認した
- 実物の基準: 行番号は、この作業場所（`5f9ecaf77`）の実物。`origin/main` は fetch 済み（先頭 `09900b564`）
- 前回: `review-architect-bin2b-2.md`（第2版 `63e6edc3a`・REVISE・R1〜R2・S1〜S6）、第1回 `review-architect-bin2b-1.md`
- 本番の値（F8・F9・F15・F21）は、この審査では本番を読んでいないため「未確認」（設計担当の記録として受け取る）

## 1 前回指摘の照合

| # | 判定 | 第3版の直し方と、実物での照合 |
|---|---|---|
| 第2回 R1（直すときの決まりの食い違い） | ○ 直った | §3-3 L141-152 に 6 行の表を置き、`validate_team_ids` が今の共有・決める共有・`team_ids` の 3 つから `None`（通す・書かない）／昇順の list／422 を返す形に直した（L153）。B4（L50）・B11（L52）・§4-2（L184）・§5（L203-204）を表と突き合わせた結果は下の「2 表と各所の突き合わせ」。実物の画面は `canChangeVisibility` なら毎回 `calendar_type` を送る（`SchedulePageImpl.tsx:1024-1025`）ので、§4-2 L184 の「`calendar_type` は今と同じ値のまま送ってよい」は実物と合う。「今の形」の語は消えた |
| 第2回 R2（B8 ①） | ○ 直った | ①は `git grep -n '"shared", "personal")' -- backend/app`（閉じ括弧まで）。実物で今 2 件（`backend/app/routers/calendar.py:542`・`:633`）に当たり、定義 `("shared", "personal", "team")` は `"personal")` ではなく `"personal", "team")` なので当たらない。実装後 0 件で合格にできる。②`^SHARE_VALUES\b`・`^CATEGORY_SHARE_VALUES\b` は今 0 件で、実装後ちょうど 2 件にできる形。③`_VALID_CATEGORY_SHARES` は今 `calendar.py:167`・`:171` の 2 件で、消せば 0 件。④`"self" \| "all"` は今 `frontend/src/features/schedule/useCalendarCategories.ts:9` の 1 件で、実装後は `CalendarShare` の定義 1 件にできる（`ScheduleItem.calendarType` の注も L56 にある） |
| 第2回 S1（`:1234`） | ○ | §3-3 L137。実物 `calendar_service.py:1234` が `_commit`（今回 sed で確認） |
| 第2回 S2（文字↔数） | ○ | §4-2 L185 に 1 行。`useCalendarTeams` のそばに 1 組 |
| 第2回 S3（`defaultTeamIds`） | ○ | §4-3 L191 |
| 第2回 S4（B8 ④の注） | ○ | B8 ④（L56）に注が入った |
| 第2回 S5（F21 の根拠） | ○ | F21（L41）に `calendar_service.py:422` と「Google 取り込み由来に限られる」が入った |
| 第2回 S6（Google の回） | ○ | §3-3 L140。実物 `_apply_app_instance_from_google` への分岐が `calendar_service.py:1753-1755` にある（今回確認）。試験は B3「例外の行」 |
| 第1回 R1〜R7・S1〜S12 | ○（前回確認のまま） | 第2版から該当箇所は動いていない。第1回の R1（「この予定だけ」）は第2回 R1 と同じ根で、今回 ○ |

## 2 表と各所の突き合わせ（新しい照合）

表（§3-3 L143-150）の 6 行を、B4・B11・§4-2・§5 と突き合わせた。

| 場所 | 判定 | 突き合わせ |
|---|---|---|
| B4（L50） | ○ | 「作るときと今が `team` 以外を `team` にするときの欠け・空は 422」＝表の行 3・4。「今が `team` で `team_ids` を送らないのは通し、対応は今のまま」＝行 1。「`team` で空を明示・無い id・使っていない id・int4 の範囲外は 422」＝行 3 と `validate_team_ids`（L153）。「`team` 以外で空でない 422」＝行 6。「重なりは 1 つにまとめる」＝L153。表と矛盾しない |
| B11（L52） | ○ | ①`calendar_type: "team"`・`team_ids` なし → 行 1（`validate_team_ids` が `None`）で通り、`check_recurrence_request` の `calendar_type` 判定（`calendar_service.py:858-859`・同じ値なら通る）も通るので 200。②今と同じ `team_ids` → 行 2 で通り、L139 の「元の行の対応と同じなら通す」で 200。③違う `team_ids` か違う `calendar_type` → 422 `recurrence_this_not_allowed`（`calendar_type` は実物 `:858-859`、`team_ids` は L139 の新しい判定）。§4-2 L184「画面は `team_ids` を送らない・`calendar_type` は同じ値で送ってよい」は①と同じ送り方で、逆向きの記述は残っていない |
| §4-2（L184）と §4-1（L176） | ○ | §4-1「送るとき `team` なら `team_ids` も送る」は一般則、§4-2 は「この予定だけ」の例外で、並べて読んで矛盾しない |
| §5（L203-204） | ○ | L203「表の 6 行を 1 つずつ」＝表。L204 B11「`team_ids` を送らず 200・同じ `team_ids` で 200・違う `team_ids` で 422」＝B11 ①②③のうち `team_ids` の部分（S1 参照） |
| 表の抜け | ○ | 今の共有 2 値 × 決める共有 2 値 × `team_ids` の 3 状態（無し・空・空でない）を 6 行がふさぐ。「今が `team` 以外・`calendar_type` を送らない・`team_ids` が空でない」は決める共有が `team` 以外なので行 6 に入る。「今が `team`・`calendar_type: shared`・`team_ids` なし」は行 5（空で呼んで対応を消す）。実装を誤らせる穴は無い |
| `validate_team_ids` の `None` | ○ | L153 の返り値の説明と表の行 1 が一致。呼び手は `None` なら `set_event_teams` を呼ばない。L135 の「送った中に `calendar_type` か `team_ids` があれば呼ぶ」とも整合 |
| 「この予定だけ」と順序 | ○ | 受け口で `validate_team_ids`（`try` の前）→ `check_recurrence_request` の順。「違う `team_ids`・正しい id」は前者を通って後者で `recurrence_this_not_allowed`。無効な id を送った場合は前者の `invalid_team_ids` が先に出るが、B11 ③の「違う `team_ids`」は正しい id の話として読める |

## 3 新しい矛盾の探索

- 表（L143-150）・L153・L135-139 の呼ぶ決まり・B4・B11・B5・§4-2・§5 の間に、実装を誤らせる食い違いは見つからなかった。
- B8 の 4 つの `git grep` は、実装前は今の値（①②③④の今の件数は上のとおり）、実装後は設計どおりの件数にできる形で、測れる。
- 実物の行番号（`calendar_service.py:858-860`・`:1234`・`:1753-1755`、`SchedulePageImpl.tsx:1024-1025`・`:1083-1087`、`ScheduleDraftFields.tsx:151`）は設計の記述と合う。
- 本番の値（F8・F9・F15・F21）は未確認のまま。

## 4 指摘

### 必須

なし。

### 推奨

| # | 指摘 |
|---|---|
| S1 | §5 L204 の B11 の並びは「違う `team_ids` で 422」だけで、B11 ③のもう一方（違う `calendar_type` で 422）が書かれていない。実装役は B11 の本文で足りるが、試験を 3 通り（①②③）と数えるなら、③の中に両方入れると取りこぼさない |
| S2 | B4 の「裏側の試験（7 通り）」の 7 の中身が、§5 L203（表 6 行・作るときの欠けと空・int4 の範囲外・重なり）と数えて同じになるかは書かれていない。通り数の語を外すか中身を並べると、試験の足りなさを後で数えやすい |
| S3 | 表の行 5 の「送らない」は、`team` 以外で `team_ids: []` を明示した場合を明記しない（L153 の `team` 以外で空でない → 422 から、空は通して空で呼ぶ読みになる）。実装役が迷うなら行 5 に「送らない、または空」と足す |

## 5 結論

- 第2回の必須 R1・R2 は、実物と表・B4・B11・§4-2・§5 を突き合わせて直っていると確認した。
- S1〜S6 は全部入っており、実物の行番号も合う。
- 新しい必須の直しは無い。上の推奨 S1〜S3 は実装を誤らせるものではなく、実装役への補足の範囲。
- 本番の値（F8・F9・F15・F21）は **未確認**（設計担当の記録として受け取る）。

判定: APPROVE
