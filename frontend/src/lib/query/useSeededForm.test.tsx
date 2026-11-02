/** ADR-1054 段 3: useSeededForm だけの試験（Q3）。K5 と打ちかけを消さないことを、画面を通さずに確かめる。 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useSeededForm } from "./useSeededForm";

const auth = vi.hoisted(() => ({ user: { uid: "uid-A" } as { uid: string } | null }));
vi.mock("../../contexts/AuthContext", () => ({ useAuth: () => ({ user: auth.user, loading: false }) }));

type D = { name: string };
const toForm = (d: D) => ({ name: d.name });
const empty = { name: "" };
const hook = (data: D | undefined) =>
  renderHook((p: { data: D | undefined }) => useSeededForm("bot/7", p.data, toForm, empty), { initialProps: { data } });

afterEach(() => {
  auth.user = { uid: "uid-A" };
});

describe("useSeededForm (Q3)", () => {
  it("K5: after A edited, user B never sees A's form and gets B's data", () => {
    const view = hook({ name: "A-data" });
    expect(view.result.current.form).toEqual({ name: "A-data" });
    act(() => view.result.current.setForm({ name: "A-typed" }));
    expect(view.result.current.form).toEqual({ name: "A-typed" });
    auth.user = { uid: "uid-B" };
    view.rerender({ data: undefined });
    expect(view.result.current.ready).toBe(false);
    expect(view.result.current.form).toEqual(empty);
    view.rerender({ data: { name: "B-data" } });
    expect(view.result.current.ready).toBe(true);
    expect(view.result.current.form).toEqual({ name: "B-data" });
  });

  it("reseeds from a refetched copy only while untouched", () => {
    const view = hook({ name: "v1" });
    view.rerender({ data: { name: "v2" } });
    expect(view.result.current.form).toEqual({ name: "v2" });
    act(() => view.result.current.setForm((p) => ({ ...p, name: "typed" })));
    view.rerender({ data: { name: "v3" } });
    expect(view.result.current.form).toEqual({ name: "typed" });
  });

  it("is empty and not ready before the first copy arrives", () => {
    const view = hook(undefined);
    expect(view.result.current.ready).toBe(false);
    expect(view.result.current.form).toEqual(empty);
  });
});
