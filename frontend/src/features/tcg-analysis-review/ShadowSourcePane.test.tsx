import { cleanup, render } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import "../../i18n";
import { ShadowSourcePane } from "./ShadowSourcePane";

afterEach(() => cleanup());

const RAW = "a\nb\nc\nd";
const attr = (line: number) =>
  document.querySelector(`[data-line-number="${line}"]`)?.getAttribute("data-range") ?? null;

it("numbers every line of the source text", () => {
  render(<ShadowSourcePane rawText={RAW} />);
  expect(document.querySelectorAll("[data-line-number]").length).toBe(4);
  expect(document.querySelector('[data-line-number="4"] .shadow-source-line-no')?.textContent).toBe("4");
});

it("marks the block range and the heading range separately", () => {
  render(
    <ShadowSourcePane rawText={RAW} blockRange={{ start: 3, end: 4 }} headingRange={{ start: 2, end: 2 }} />,
  );
  expect([attr(1), attr(2), attr(3), attr(4)]).toEqual([null, "heading", "block", "block"]);
});

it("prefers the block color on lines shared with the heading range", () => {
  render(<ShadowSourcePane rawText={RAW} blockRange={{ start: 2, end: 3 }} headingRange={{ start: 1, end: 2 }} />);
  expect([attr(1), attr(2), attr(3)]).toEqual(["heading", "block", "block"]);
});

it("marks nothing when the ranges are missing or null", () => {
  render(<ShadowSourcePane rawText={RAW} blockRange={{ start: null, end: null }} headingRange={null} />);
  expect([attr(1), attr(2), attr(3), attr(4)]).toEqual([null, null, null, null]);
});

const legendText = () => document.querySelector(".shadow-source-legend")?.textContent ?? "";

it("shows only the legend items whose range is given", () => {
  render(<ShadowSourcePane rawText={RAW} blockRange={{ start: 1, end: 2 }} />);
  expect(document.querySelectorAll(".shadow-source-legend-item").length).toBe(1);
  expect(document.querySelector(".shadow-source-legend-item--block")).not.toBeNull();
  expect(document.querySelector(".shadow-source-legend-item--heading")).toBeNull();
  expect(legendText()).not.toBe("");
});

it("shows both legend items when both ranges are given", () => {
  render(<ShadowSourcePane rawText={RAW} blockRange={{ start: 1, end: 2 }} headingRange={{ start: 3, end: 3 }} />);
  expect(document.querySelectorAll(".shadow-source-legend-item").length).toBe(2);
});

it("hides the legend but keeps the block highlight when showLegend is false", () => {
  render(<ShadowSourcePane rawText={RAW} blockRange={{ start: 3, end: 4 }} showLegend={false} />);
  expect(document.querySelector(".shadow-source-legend")).toBeNull();
  expect([attr(1), attr(2), attr(3), attr(4)]).toEqual([null, null, "block", "block"]);
});
