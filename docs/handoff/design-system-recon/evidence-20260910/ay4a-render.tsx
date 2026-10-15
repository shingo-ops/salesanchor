// AY-4a 実測用: DataTable を renderToStaticMarkup した HTML を JSON で出す（手書きしない）。
// "@dt" は esbuild の alias で「前（origin/main）」「後（作業ツリー）」の DataTable.tsx を指す。
import { renderToStaticMarkup } from "react-dom/server";
import { DataTable } from "@dt";

// useIsMobile が window.matchMedia を読むため、デスクトップ幅（matches=false）の最小スタブを置く
(globalThis as any).window = { matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }) };

const DATA = [
  { id: "1", name: "a" },
  { id: "2", name: "b" },
];
const html = (selected: string[]) =>
  renderToStaticMarkup(
    <DataTable
      columns={[{ key: "name", header: "Name" }]}
      data={DATA}
      rowKey={(r: { id: string }) => r.id}
      selectable
      selectedKeys={new Set(selected)}
      onSelectChange={() => {}}
    />,
  );
process.stdout.write(JSON.stringify({ none: html([]), all: html(["1", "2"]), some: html(["1"]) }));
