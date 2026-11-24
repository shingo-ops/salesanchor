/* eslint-disable local/no-japanese-literal -- 試験の題名（画面の文字ではない） */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { COUNTRIES, type CountryEntry } from "../../constants/countries";
import { CountryCombobox } from "./CountryCombobox";

afterEach(() => cleanup());

const dialOnly = (c: CountryEntry) => c.dial;
const dialAndName = (c: CountryEntry) => `${c.dial} ${c.name}`;
const filterDial = (c: CountryEntry, q: string) => c.dial.includes(q) || c.name.toLowerCase().includes(q);

describe("公開フォームの国番号の欄（K2）", () => {
  it("COUNTRIES の全件で、欄に出る字は番号だけ（+ と数字のみ・4文字以内）", () => {
    expect(COUNTRIES.length).toBeGreaterThan(0);
    for (const c of COUNTRIES) {
      expect(dialOnly(c)).toMatch(/^\+\d{1,4}$/);
    }
  });

  it("「+1」を選ぶと欄が「+1」になり、onChange には番号が渡る", () => {
    const onChange = vi.fn();
    render(
      <CountryCombobox
        id="dial"
        entries={COUNTRIES}
        value=""
        onChange={onChange}
        displayFn={dialOnly}
        optionLabelFn={dialAndName}
        filterFn={filterDial}
      />,
    );
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.focus(input);
    const row = screen.getAllByText(/^\+1 /)[0];
    fireEvent.mouseDown(row);
    expect(onChange).toHaveBeenCalledWith("+1");
  });

  it("選んだ後、value が「+1」なら欄は「+1」と出る", () => {
    render(
      <CountryCombobox
        id="dial"
        entries={COUNTRIES}
        value="+1"
        onChange={() => {}}
        displayFn={dialOnly}
        optionLabelFn={dialAndName}
        filterFn={filterDial}
      />,
    );
    expect((screen.getByRole("textbox") as HTMLInputElement).value).toBe("+1");
  });

  it("一覧の行は optionLabelFn の字（番号＋国名）を出す。省けば displayFn", () => {
    const { rerender } = render(
      <CountryCombobox
        id="dial"
        entries={COUNTRIES}
        value=""
        onChange={() => {}}
        displayFn={dialOnly}
        optionLabelFn={dialAndName}
        filterFn={filterDial}
      />,
    );
    fireEvent.focus(screen.getByRole("textbox"));
    expect(screen.getByText("+81 Japan")).toBeTruthy();
    rerender(
      <CountryCombobox
        id="dial"
        entries={COUNTRIES}
        value=""
        onChange={() => {}}
        displayFn={dialOnly}
        filterFn={filterDial}
      />,
    );
    expect(screen.queryByText("+81 Japan")).toBeNull();
    expect(screen.getAllByText("+81").length).toBeGreaterThan(0);
  });
});
