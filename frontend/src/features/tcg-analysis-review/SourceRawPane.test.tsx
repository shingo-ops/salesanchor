/* eslint-disable local/no-japanese-literal -- テスト: 日本語の表示が変更前と同じであることを検証する（ADR-027・precedent: InboxMessageThread.discordSendError.test.tsx） */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import i18n from "../../i18n";
import { SourceRawPane } from "./SourceRawPane";

const RAW = ["L1 Alpha Box", "L2 Beta Pack", "L3 Alpha Box"].join("\n");

const renderPane = () => render(<SourceRawPane sourceMessageId="sm-1" rawText={RAW} itemCount={3} />);
const search = (value: string) => fireEvent.change(document.querySelector(".source-search input") as HTMLInputElement, { target: { value } });

afterEach(async () => {
  cleanup();
  await i18n.changeLanguage("ja");
});

describe("SourceRawPane (ja)", () => {
  beforeEach(async () => { await i18n.changeLanguage("ja"); });

  it("shows the counts in Japanese exactly as before", () => {
    renderPane();
    expect(screen.getByText("原文 1件")).toBeTruthy();
    expect(screen.getByText("抽出商品 3件")).toBeTruthy();
    expect(screen.getByText("原文検索")).toBeTruthy();
    expect((document.querySelector(".source-search input") as HTMLInputElement).placeholder).toBe("L0006 または文字列");
    expect(document.querySelector(".raw")?.getAttribute("aria-label")).toBe("原文全文");
    expect(screen.getByRole("button", { name: "移動" })).toBeTruthy();
  });

  it("says there is no matching line when nothing matches", () => {
    renderPane();
    search("zzz");
    expect(screen.getByText("該当行がありません")).toBeTruthy();
  });

  it("shows previous / next only when several lines match", () => {
    renderPane();
    expect(screen.queryByRole("button", { name: "前へ" })).toBeNull();
    search("Beta");
    expect(screen.queryByRole("button", { name: "前へ" })).toBeNull();
    search("Alpha");
    expect(screen.getByRole("button", { name: "前へ" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "次へ" })).toBeTruthy();
  });

  it("uses the shared input and button classes", () => {
    renderPane();
    const input = document.querySelector(".source-search input") as HTMLInputElement;
    expect(input.className).toContain("comp-field__input");
    expect(input.className).toContain("comp-field__input--sm");
    search("Alpha");
    const buttons = Array.from(document.querySelectorAll(".source-search button"));
    expect(buttons.length).toBe(3);
    for (const button of buttons) {
      expect(button.className).toContain("comp-btn--secondary");
      expect(button.className).toContain("comp-btn--sm");
    }
  });
});

describe("SourceRawPane (en)", () => {
  beforeEach(async () => { await i18n.changeLanguage("en"); });

  it("shows the counts in English", () => {
    renderPane();
    expect(screen.getByText("1 source message")).toBeTruthy();
    expect(screen.getByText("3 extracted items")).toBeTruthy();
    expect(screen.getByText("Search source")).toBeTruthy();
    expect((document.querySelector(".source-search input") as HTMLInputElement).placeholder).toBe("L0006 or text");
    expect(document.querySelector(".raw")?.getAttribute("aria-label")).toBe("Full source text");
    expect(screen.getByRole("button", { name: "Go" })).toBeTruthy();
  });

  it("says there is no matching line, and offers previous / next for several matches", () => {
    renderPane();
    search("zzz");
    expect(screen.getByText("No matching lines")).toBeTruthy();
    search("Alpha");
    expect(screen.getByRole("button", { name: "Previous" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Next" })).toBeTruthy();
  });

  it("leaves no Japanese in the pane chrome", () => {
    const { container } = renderPane();
    search("Alpha");
    const aside = container.querySelector(".source-raw") as HTMLElement;
    const attrs = Array.from(aside.querySelectorAll("[aria-label],[placeholder]")).map((e) => `${e.getAttribute("aria-label") ?? ""}${e.getAttribute("placeholder") ?? ""}`);
    expect(`${aside.textContent}${attrs.join("")}`).not.toMatch(/[぀-ヿ一-鿿]/);
  });
});
