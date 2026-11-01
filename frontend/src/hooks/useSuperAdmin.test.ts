import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useSuperAdmin } from "./useSuperAdmin";
import { usePermissions } from "./usePermissions";
import { queryClient } from "../lib/query/apiQuery";

// 試験の中で利用者を変えるため、今の人を差し替えられるようにする（ADR-1054 K5）
const auth = vi.hoisted(() => ({ user: { uid: "user-a" } as { uid: string } | null }));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => auth,
}));

vi.mock("../lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

import { api } from "../lib/api";
const mockGet = vi.mocked(api.get);

afterEach(() => {
  vi.clearAllMocks();
  auth.user = { uid: "user-a" };
  // 前の試験の写しが次の試験に残らないようにする（ADR-1054）
  queryClient.clear();
});

describe("useSuperAdmin", () => {
  it("initial state: loading=true, isSuperAdmin=false", () => {
    mockGet.mockResolvedValueOnce({ permissions: [], is_super_admin: true });
    const { result } = renderHook(() => useSuperAdmin());

    expect(result.current.loading).toBe(true);
    expect(result.current.isSuperAdmin).toBe(false);
  });

  it("is_super_admin true: isSuperAdmin becomes true and loading becomes false", async () => {
    mockGet.mockResolvedValueOnce({ permissions: [], is_super_admin: true });

    const { result } = renderHook(() => useSuperAdmin());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isSuperAdmin).toBe(true);
  });

  it("is_super_admin false: isSuperAdmin stays false and loading becomes false", async () => {
    mockGet.mockResolvedValueOnce({ permissions: [], is_super_admin: false });

    const { result } = renderHook(() => useSuperAdmin());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isSuperAdmin).toBe(false);
  });

  it("on API failure: isSuperAdmin is false and loading becomes false", async () => {
    mockGet.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useSuperAdmin());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isSuperAdmin).toBe(false);
  });

  it("calls the /me/permissions endpoint", async () => {
    mockGet.mockResolvedValueOnce({ permissions: [], is_super_admin: false });

    renderHook(() => useSuperAdmin());
    await waitFor(() => expect(mockGet).toHaveBeenCalledOnce());

    expect(mockGet).toHaveBeenCalledWith("/me/permissions");
  });

  it("shares one /me/permissions call with usePermissions on the same screen", async () => {
    mockGet.mockResolvedValueOnce({ permissions: ["read:customers"], is_super_admin: true });

    const { result } = renderHook(() => ({ s: useSuperAdmin(), p: usePermissions() }));
    await waitFor(() => expect(result.current.s.loading).toBe(false));

    expect(result.current.s.isSuperAdmin).toBe(true);
    expect(result.current.p.hasPermission("read:customers")).toBe(true);
    expect(mockGet).toHaveBeenCalledOnce();
  });

  it("reopening shows the previous result on the first render (ADR-1054 K1)", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: [], is_super_admin: true })
      .mockResolvedValueOnce({ permissions: [], is_super_admin: true });

    const first = renderHook(() => useSuperAdmin());
    await waitFor(() => expect(first.result.current.loading).toBe(false));
    first.unmount();

    const second = renderHook(() => useSuperAdmin());
    expect(second.result.current.loading).toBe(false);
    expect(second.result.current.isSuperAdmin).toBe(true);

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it("after the user changes, the previous user's result is never returned (ADR-1054 K5)", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: [], is_super_admin: true })
      .mockReturnValueOnce(new Promise(() => {}));

    const { result, rerender } = renderHook(() => useSuperAdmin());
    await waitFor(() => expect(result.current.isSuperAdmin).toBe(true));

    auth.user = { uid: "user-b" };
    rerender();

    expect(result.current.isSuperAdmin).toBe(false);
    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });
});
