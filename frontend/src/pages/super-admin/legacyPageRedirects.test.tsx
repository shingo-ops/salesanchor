import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, expect, it } from "vitest";

// AY-2g: the three Routes below mirror src/App.tsx:297, :310 and :326 (as of this change).
// Keep them identical to App.tsx.
const TARGETS = {
  productMaster: "/super-admin/analysis-rules?section=product-master",
  accuracy: "/super-admin/analysis-rules?section=accuracy-management",
  supplierMaster: "/super-admin/analysis-rules?section=supplier-master",
} as const;

function Where() {
  const location = useLocation();
  return <output data-testid="where">{location.pathname + location.search}</output>;
}

afterEach(() => cleanup());

it.each([
  ["/super-admin/tcg-product-master", TARGETS.productMaster],
  ["/super-admin/tcg-supplier-quality", TARGETS.accuracy],
  ["/super-admin/supplier-master", TARGETS.supplierMaster],
])("redirects %s to %s", (from, to) => {
  render(
    <MemoryRouter initialEntries={[from]}>
      <Routes>
        <Route path="/super-admin/tcg-product-master" element={<Navigate to={TARGETS.productMaster} replace />} />
        <Route path="/super-admin/tcg-supplier-quality" element={<Navigate to={TARGETS.accuracy} replace />} />
        <Route path="/super-admin/supplier-master" element={<Navigate to={TARGETS.supplierMaster} replace />} />
        <Route path="/super-admin/analysis-rules" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByTestId("where").textContent).toBe(to);
});
