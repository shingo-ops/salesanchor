# 実装カード 便3: アプリで説明・場所を空にしたら Google でも消す

- 設計: docs/handoff/calendar-two-way-sync/design.md §11（正）。ADR-1059 改訂 2026-11-23。
- PO の決定: 2026-11-23「1. 空にできるようにする」。実装・合流・反映まで委任済み。
- 枝: release/calendar-clear-text-fields（origin/main 3763e55c7 起点）。
- 触るファイルは 2 本だけ: `frontend/src/pages/schedule/SchedulePageImpl.tsx`・`frontend/src/pages/schedule/SchedulePageImpl.test.tsx`。ほかは触らない（裏側・文言・ja.json/en.json も触らない）。

## 0. 着手前の実物点検（違ったら止めて BLOCKED: で返す）

1. `frontend/src/pages/schedule/SchedulePageImpl.tsx:1033-1034` が次の 2 行であること。
   ```ts
           description: draft.description || undefined,
           location: draft.location || undefined,
   ```
2. `frontend/src/pages/schedule/SchedulePageImpl.tsx:1045` が次の 1 行であること。
   ```ts
         const editing = popover?.mode === "edit" && popover.item ? popover.item : null;
   ```
3. `frontend/src/pages/schedule/SchedulePageImpl.test.tsx:174` が `describe("SchedulePage share-with-staff toggle", () => {` であること。

## 1. `frontend/src/pages/schedule/SchedulePageImpl.tsx`

1045 行目のすぐ下に足す（1033-1034 行目は変えない）。

変更前:
```ts
      const editing = popover?.mode === "edit" && popover.item ? popover.item : null;
      // 繰り返しは今の値と違うときだけ送る（作るときは「繰り返さない」以外のとき・§12.6.1 G4）
```
変更後:
```ts
      const editing = popover?.mode === "edit" && popover.item ? popover.item : null;
      // 直すとき、元にあった説明・場所を空にしたら "" を送って消す（Google でも消える・ADR-1059 改訂 2026-11-23）
      if (editing && !draft.description && editing.description) {
        body.description = "";
      }
      if (editing && !draft.location && editing.location) {
        body.location = "";
      }
      // 繰り返しは今の値と違うときだけ送る（作るときは「繰り返さない」以外のとき・§12.6.1 G4）
```

## 2. `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`

`describe("SchedulePage share-with-staff toggle", ...)` の閉じ `});` のすぐ下に、新しい describe を 1 つ足す。中の操作は同じファイルの「shows the toggle when editing own event and sends calendar_type」の書き方（`view()`・`findByText`・`editEvent` ボタン・`editorDialog()`・`common.save`）をそのまま使う。

```ts
describe("SchedulePage clearing description and location (design §11)", () => {
  it("K18: sends empty strings when an existing description and location are cleared", async () => {
    answers.events = [apiEvent({ description: "Old note", location: "Room A" })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    fireEvent.change(within(dialog).getByLabelText(i18n.t("schedule.eventDescription")), { target: { value: "" } });
    fireEvent.change(within(dialog).getByLabelText(i18n.t("schedule.eventLocation")), { target: { value: "" } });
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(body.description).toBe("");
    expect(body.location).toBe("");
  });

  it("K18: keeps sending the text when it is not cleared", async () => {
    answers.events = [apiEvent({ description: "Old note", location: "Room A" })];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    expect(body.description).toBe("Old note");
    expect(body.location).toBe("Room A");
  });

  it("K19: does not send them when the event had none", async () => {
    answers.events = [apiEvent({})];
    view();
    fireEvent.click(await screen.findByText("Own Event"));
    fireEvent.click((await screen.findAllByRole("button", { name: i18n.t("schedule.editEvent") }))[0]);
    const dialog = await editorDialog();
    fireEvent.click(within(dialog).getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    const body = vi.mocked(api.patch).mock.calls[0][1] as Record<string, unknown>;
    const sent = JSON.parse(JSON.stringify(body)) as Record<string, unknown>;
    expect(sent).not.toHaveProperty("description");
    expect(sent).not.toHaveProperty("location");
  });

  it("K19: does not send them when creating", async () => {
    view();
    fireEvent.click(await screen.findByRole("button", { name: i18n.t("schedule.create") }));
    fireEvent.change(await screen.findByLabelText(i18n.t("schedule.eventTitle")), { target: { value: "New" } });
    fireEvent.click(screen.getByRole("button", { name: i18n.t("common.save") }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    const body = vi.mocked(api.post).mock.calls[0][1] as Record<string, unknown>;
    const sent = JSON.parse(JSON.stringify(body)) as Record<string, unknown>;
    expect(sent).not.toHaveProperty("description");
    expect(sent).not.toHaveProperty("location");
  });
});
```

## 3. 想定される分岐（迷ったら止めて NEEDS_DECISION: で返す）

- `answers`・`apiEvent`・`view`・`editorDialog` が describe の外から使えないとき: 同じファイルの使い方を写す。それでも書けなければ止める。
- 試験の名前の取り方（`getByLabelText` が 2 つ当たる等）で落ちるとき: `within(dialog)` の中で取る。見つからなければ止める（画面の部品は変えない）。
- 「作るとき」の試験で保存ボタンが見つからないとき: 同じファイルの「shows the toggle on create, default on, and sends personal when switched off」の書き方に合わせる。

- K19 の判定について（2026-11-23 改訂）: 本体の作る式（1033-1034 行の `|| undefined`）は空のとき undefined の値のキーを残す。送るときは `frontend/src/lib/api.ts:294,301` の `JSON.stringify` でそのキーが落ちる。そのため試験は「実際に送る文に入らない」ことを `JSON.parse(JSON.stringify(body))` で確かめる（1回目は `"description" in body` で書き、本体が undefined のキーを残すため落ちた）。本体の式は変えない。
- `npx tsc --noEmit -p .` が `api/generated/schema` が無いという誤りと、その影響の `SoldOutResultsPanel.tsx` の型の誤りだけを出すとき: この型ファイルは CI が tsc の前に作る（`.github/workflows/frontend-check.yml:29`）。今回の 2 ファイルに誤りが無ければ続けてよい。2 ファイルに誤りが出たら止める。

## 4. 確かめ（手元の Mac では試験を回さない。クラウドで回す）

- `cd frontend && npx vitest run src/pages/schedule/SchedulePageImpl.test.tsx`（全件通る・新しい 4 件を含む）
- `cd frontend && npx tsc --noEmit -p .` と `npx eslint src/pages/schedule/SchedulePageImpl.tsx src/pages/schedule/SchedulePageImpl.test.tsx`
- 生の出力をそのまま返す。
