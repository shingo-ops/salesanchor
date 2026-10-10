import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, expect, it } from "vitest";
import { LEGACY_SUPER_ADMIN_REDIRECTS } from "./legacyPageRedirects";

// AY-2g: App.tsx は LEGACY_SUPER_ADMIN_REDIRECTS を map して Route にしている。
// ここでも同じ形で描画するので、対応表を変えれば (a) の期待値の直書きと食い違って落ちる。
function Where() {
  const location = useLocation();
  return <output data-testid="where">{location.pathname + location.search}</output>;
}

afterEach(() => cleanup());

it("(a) the redirect table is exactly the four expected pairs", () => {
  expect(LEGACY_SUPER_ADMIN_REDIRECTS.map(r => ({ ...r }))).toEqual([
    { from: "/super-admin/tcg-product-master", to: "/super-admin/analysis-rules?section=product-master" },
    { from: "/super-admin/tcg-supplier-quality", to: "/super-admin/analysis-rules?section=accuracy-management" },
    { from: "/super-admin/supplier-master", to: "/super-admin/analysis-rules?section=supplier-master" },
    { from: "/super-admin/tcg-parallel-report", to: "/super-admin/analysis-rules" },
  ]);
});

it.each(LEGACY_SUPER_ADMIN_REDIRECTS.map(r => [r.from, r.to] as const))("(b) %s moves to %s", (from, to) => {
  render(
    <MemoryRouter initialEntries={[from]}>
      <Routes>
        {LEGACY_SUPER_ADMIN_REDIRECTS.map(r => <Route key={r.from} path={r.from} element={<Navigate to={r.to} replace />} />)}
        <Route path="/super-admin/tcg-product-master/import" element={<output data-testid="where">import</output>} />
        <Route path="/super-admin/analysis-rules" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByTestId("where").textContent).toBe(to);
});
