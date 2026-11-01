import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
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

describe("usePermissions", () => {
  it("initial state: loading=true, empty permissions, error=null", () => {
    mockGet.mockResolvedValueOnce({ permissions: [] });
    const { result } = renderHook(() => usePermissions());

    expect(result.current.loading).toBe(true);
    expect(result.current.permissions.size).toBe(0);
    expect(result.current.error).toBeNull();
  });

  it("on API success: permissions are stored in a Set and loading becomes false", async () => {
    mockGet.mockResolvedValueOnce({
      permissions: ["read:customers", "write:orders"],
    });

    const { result } = renderHook(() => usePermissions());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.permissions.has("read:customers")).toBe(true);
    expect(result.current.permissions.has("write:orders")).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("on API failure: error is set and loading becomes false", async () => {
    mockGet.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => usePermissions());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe("Network error");
    expect(result.current.permissions.size).toBe(0);
  });

  it("hasPermission returns true for a held permission", async () => {
    mockGet.mockResolvedValueOnce({
      permissions: ["read:customers", "write:orders"],
    });

    const { result } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.hasPermission("read:customers")).toBe(true);
    expect(result.current.hasPermission("write:orders")).toBe(true);
  });

  it("hasPermission returns false for a permission not held", async () => {
    mockGet.mockResolvedValueOnce({ permissions: ["read:customers"] });

    const { result } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.hasPermission("admin:superadmin")).toBe(false);
  });

  it("hasAny returns true when at least one permission is held", async () => {
    mockGet.mockResolvedValueOnce({ permissions: ["write:orders"] });

    const { result } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(
      result.current.hasAny("read:customers", "write:orders"),
    ).toBe(true);
  });

  it("hasAny returns false when none of the permissions are held", async () => {
    mockGet.mockResolvedValueOnce({ permissions: ["write:orders"] });

    const { result } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(
      result.current.hasAny("read:customers", "admin:superadmin"),
    ).toBe(false);
  });

  it("reload triggers a second API call and updates permissions", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: ["read:customers"] })
      .mockResolvedValueOnce({ permissions: ["read:customers", "write:orders"] });

    const { result } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.permissions.has("write:orders")).toBe(false);

    await act(async () => {
      await result.current.reload();
    });

    expect(mockGet).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(result.current.permissions.has("write:orders")).toBe(true));
  });

  it("calls the /me/permissions endpoint", async () => {
    mockGet.mockResolvedValueOnce({ permissions: [] });

    renderHook(() => usePermissions());
    await waitFor(() => expect(mockGet).toHaveBeenCalledOnce());

    expect(mockGet).toHaveBeenCalledWith("/me/permissions");
  });

  it("two consumers on the same screen share one /me/permissions call", async () => {
    mockGet.mockResolvedValueOnce({ permissions: ["read:customers"] });

    const { result } = renderHook(() => ({ a: usePermissions(), b: usePermissions() }));
    await waitFor(() => expect(result.current.b.loading).toBe(false));

    expect(result.current.a.hasPermission("read:customers")).toBe(true);
    expect(result.current.b.hasPermission("read:customers")).toBe(true);
    expect(mockGet).toHaveBeenCalledOnce();
  });

  it("reopening shows the previous permissions on the first render (ADR-1054 K1)", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: ["write:orders"] })
      .mockResolvedValueOnce({ permissions: ["write:orders"] });

    const first = renderHook(() => usePermissions());
    await waitFor(() => expect(first.result.current.loading).toBe(false));
    first.unmount();

    const second = renderHook(() => usePermissions());
    expect(second.result.current.loading).toBe(false);
    expect(second.result.current.hasPermission("write:orders")).toBe(true);

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it("after the user changes, the previous user's permissions are never returned (ADR-1054 K5)", async () => {
    mockGet
      .mockResolvedValueOnce({ permissions: ["admin:a-only"] })
      .mockReturnValueOnce(new Promise(() => {}));

    const { result, rerender } = renderHook(() => usePermissions());
    await waitFor(() => expect(result.current.hasPermission("admin:a-only")).toBe(true));

    auth.user = { uid: "user-b" };
    rerender();

    expect(result.current.hasPermission("admin:a-only")).toBe(false);
    expect(result.current.permissions.size).toBe(0);
    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });
});
