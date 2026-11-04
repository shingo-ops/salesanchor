# impl-report-3: NoticeBell / NoticeRow の stories 追加

結果: 完了（BLOCKED なし）

## 足したファイル

- `frontend/src/components/NoticeRow.stories.tsx`（Unread / Read の2つ。文言は `t("notices.kind.discord_outside_ticket_post")` 経由）
- `frontend/src/components/NoticeBell.stories.tsx`（WithUnread / AllRead / Empty / OverNinetyNine の4つ。`api.get`・`api.post` を story の間だけ差し替えるモック。ChannelTypeCombobox.stories.tsx と同じ型）

読んで真似た既存: ChannelTypeCombobox.stories.tsx（API モック）、AppUpdateNotice.stories.tsx / Callout.stories.tsx（meta の形）。
EXEMPT には足していない。部品の本体（NoticeBell.tsx / NoticeRow.tsx / CSS）は変えていない。色の直値なし。

## 命令ごとの結果

| 命令 | 結果 |
|---|---|
| `npm run check:stories` | 通過（全 65 コンポーネントに stories あり・失敗 0） |
| `npx tsc --noEmit -p .` | 初回は 4 件失敗（`src/api/generated/schema` が未生成の既存要因。NoticeBell 関連の指摘は 0）。`npm run generate:api-types` で生成後に再実行 → 通過（エラー 0） |
| `npm run lint` | 通過（エラー 0・警告 59、既存ファイルの警告のみ。今回の2ファイルへの指摘なし） |
| `npm run check:all` | 通過（24 本すべて exit code 0・失敗 0） |

注: `src/api/generated/schema.d.ts` は生成物で未追跡のため commit していない。Storybook 本体の起動確認は未実施（未確認）。
