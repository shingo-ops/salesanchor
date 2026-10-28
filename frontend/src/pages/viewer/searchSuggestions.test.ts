/* eslint-disable local/no-japanese-literal -- テスト: 検索の正規化・商品名の並びを検証する（ADR-027・precedent: viewerFilter.test.ts） */
/**
 * searchSuggestions.test.ts — design.md ⑤ Acceptance Criteria U1〜U5 を固定する単体テスト
 * （docs/handoff/viewer-search-suggestions/design.md）
 */
import { describe, expect, it } from "vitest";
import { buildSuggestions } from "./searchSuggestions";
import type { ViewerRow } from "./types";

const mk = (o: Partial<ViewerRow>): ViewerRow => ({
  posted_at: "", mark: "", japanese_title: "", english_title: "", condition: "", unit_price: "", quantity: "",
  note_ja: "", status: "", release_date: "", series: "", provider: "", search_keywords: "", ship_ja: "", offer_type: null, ...o,
});

describe("buildSuggestions", () => {
  it("U1: draft が空のとき候補は0件", () => {
    const rows = [mk({ japanese_title: "ピカチュウ" })];
    expect(buildSuggestions(rows, "")).toEqual([]);
    expect(buildSuggestions(rows, "   ")).toEqual([]);
  });

  it("U2: 先頭一致が、途中一致より先に並ぶ（件数が同じでも、名前の昇順より先頭一致が勝つ）", () => {
    const rows = [
      mk({ japanese_title: "アカード" }), // 途中一致。名前の昇順ではこちらが先（「ア」<「カ」）
      mk({ japanese_title: "カードB" }), // 先頭一致
    ];
    expect(buildSuggestions(rows, "カード")).toEqual(["カードB", "アカード"]);
  });

  it("U3: 同じ表示名は1件にまとまる・最大10件", () => {
    const sameName = Array.from({ length: 3 }, () => mk({ japanese_title: "ピカチュウ box" }));
    expect(buildSuggestions(sameName, "ピカチュウ")).toEqual(["ピカチュウ box"]);

    const many = Array.from({ length: 12 }, (_, i) => mk({ japanese_title: `ピカチュウ${i}` }));
    expect(buildSuggestions(many, "ピカチュウ")).toHaveLength(10);
  });

  it("U4: ひらがなで打ってもカタカナの商品名に当たる（正規化の確認）", () => {
    const rows = [mk({ japanese_title: "ピカチュウ" })];
    expect(buildSuggestions(rows, "ぴかちゅう")).toEqual(["ピカチュウ"]);
  });

  it("U5: 候補は必ず1件以上の行に当たる語だけを返す（matchesQuery と一致）", () => {
    // シリーズ名・提供者名だけに含まれる語では候補が出ない（matchesQuery の対象外のため）
    const rows = [mk({ japanese_title: "ピカチュウ", series: "ポケモン", provider: "ProviderXYZ" })];
    expect(buildSuggestions(rows, "ポケモン")).toEqual([]);
    expect(buildSuggestions(rows, "ProviderXYZ")).toEqual([]);
    // 一方、対象の4つ（日本語名・英語名・型番・検索ワード）に含まれる語は当たる
    expect(buildSuggestions(rows, "ピカチュウ")).toEqual(["ピカチュウ"]);
  });

  it("件数は並べ替えの材料にする（件数の多い順）。画面に出す文字列には件数を含めない", () => {
    const rows = [
      mk({ japanese_title: "ピカチュウA" }),
      mk({ japanese_title: "ピカチュウB" }),
      mk({ japanese_title: "ピカチュウB" }),
    ];
    expect(buildSuggestions(rows, "ピカチュウ")).toEqual(["ピカチュウB", "ピカチュウA"]);
  });

  it("表示名は japanese_title →（空なら）english_title →（空なら）mark", () => {
    expect(buildSuggestions([mk({ english_title: "pikachu", mark: "M1" })], "pikachu")).toEqual(["pikachu"]);
    expect(buildSuggestions([mk({ mark: "M1", search_keywords: "box" })], "box")).toEqual(["M1"]);
  });
});
