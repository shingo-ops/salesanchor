import { render } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../firebase", () => ({
  auth: { currentUser: { getIdToken: () => Promise.resolve("tok") } },
}));

import { RealtimeProvider } from "./RealtimeProvider";

describe("RealtimeProvider", () => {
  const signals: AbortSignal[] = [];
  beforeEach(() => {
    signals.length = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init: RequestInit) => {
        signals.push(init.signal as AbortSignal);
        return new Promise<Response>(() => undefined);
      })
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("aborts the in-flight stream request on unmount", async () => {
    const { unmount } = render(
      <RealtimeProvider>
        <div />
      </RealtimeProvider>
    );
    await vi.waitFor(() => expect(signals.length).toBe(1));
    expect(signals[0].aborted).toBe(false);
    unmount();
    expect(signals[0].aborted).toBe(true);
  });

  it("under StrictMode, the first (discarded) connection is aborted", async () => {
    render(
      <StrictMode>
        <RealtimeProvider>
          <div />
        </RealtimeProvider>
      </StrictMode>
    );
    await vi.waitFor(() => expect(signals.length).toBeGreaterThanOrEqual(1));
    const live = signals.filter((s) => !s.aborted);
    expect(live.length).toBe(1);
  });
});
