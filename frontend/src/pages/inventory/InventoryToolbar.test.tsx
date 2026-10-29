/**
 * InventoryToolbar.test.tsx — design: docs/handoff/inventory-series-sort-panel/design.md ⑤ E15。
 *
 * InventoryToolbar.tsx が持つ2つの純粋な部品を単体で確かめる:
 *   K4) `inventoryChoiceRow`（パネルの行。design.md 4-3）: すでに選ばれている行をもう一度押しても
 *      `pick` が呼ばれる（＝親で「閉じる」まで実行される）こと。ネイティブ radio の `change` は
 *      値が変わったときしか起きないため、`onClick` が無いと赤くなる（下の注記を参照）。
 *   H3) `buildTypeOptions`（種別の選択肢。design.md 4-3・審査 H3）: `tcgTypes` が空（マスタ取得失敗）
 *      でも `MAIN_TCG_CODES` の3件が必ず出ること（今までのタブと同じ保証・退行防止）。
 *
 * 空振り防止（design.md ⑤ E15）: 「K4」のテストで `inventoryChoiceRow` の `onClick` を一時的に
 * 外して実行し、このテストが赤くなることを1回確かめた（E7/K4 の退行を実際に捕まえられることの裏取り）。
 * 確認後 `onClick` を戻し、全件緑に戻してある（確認結果は実装報告に記録）。
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { buildTypeOptions, inventoryChoiceRow } from './InventoryToolbar';

afterEach(() => {
  cleanup();
});

describe('inventoryChoiceRow (design.md 4-3)', () => {
  it('K4: clicking an already-selected row still calls pick (K4 — re-clicking the active row must close the panel)', () => {
    const pick = vi.fn();
    render(
      <>
        {inventoryChoiceRow({
          name: 'test-choice',
          value: 'already-selected',
          checked: true,
          testId: 'test-option-already-selected',
          label: 'Already selected',
          pick,
        })}
      </>,
    );
    fireEvent.click(screen.getByTestId('test-option-already-selected'));
    expect(pick).toHaveBeenCalledTimes(1);
  });

  it('calling pick twice (onChange + onClick firing together) is harmless — row renders a single radio input', () => {
    const pick = vi.fn();
    render(
      <>
        {inventoryChoiceRow({
          name: 'test-choice',
          value: 'v',
          checked: false,
          testId: 'test-option-v',
          label: 'V',
          pick,
        })}
      </>,
    );
    const input = screen.getByTestId('test-option-v');
    expect(input.getAttribute('type')).toBe('radio');
    expect(input.getAttribute('name')).toBe('test-choice');
    fireEvent.click(input);
    fireEvent.change(input);
    expect(pick.mock.calls.length).toBeGreaterThanOrEqual(1);
  });
});

describe('buildTypeOptions (design.md 4-3 / review-opus.md H3)', () => {
  const MAIN_TCG_CODES = ['pokemon_booster_box', 'one_piece', 'dragon_ball'] as const;

  it('H3: even when tcgTypes master data failed to load (empty array), the 3 main codes still appear as options', () => {
    const options = buildTypeOptions(MAIN_TCG_CODES, [], 'All');
    expect(options.map((o) => o.code)).toEqual(['all', 'pokemon_booster_box', 'one_piece', 'dragon_ball']);
    // マスタが無いときは code がそのまま表示名になる（今のタブのラベルと同じ規則・審査 H4）
    expect(options.find((o) => o.code === 'pokemon_booster_box')?.name).toBe('pokemon_booster_box');
    expect(options[0]).toEqual({ code: 'all', name: 'All' });
  });

  // 見本名は ASCII（ADR-027: src 配下は日本語の文字列リテラル禁止）。本番の表示名は tcgTypes の name_ja がそのまま入る
  it('fills in display names from tcgTypes when available, and appends extra (non-main) codes after the main 3', () => {
    const options = buildTypeOptions(
      MAIN_TCG_CODES,
      [
        { code: 'pokemon_booster_box', name_ja: 'Pokemon' },
        { code: 'one_piece', name_ja: 'OnePiece' },
        { code: 'dragon_ball', name_ja: 'DragonBall' },
        { code: 'hololive', name_ja: 'Hololive' },
      ],
      'ALL',
    );
    expect(options).toEqual([
      { code: 'all', name: 'ALL' },
      { code: 'pokemon_booster_box', name: 'Pokemon' },
      { code: 'one_piece', name: 'OnePiece' },
      { code: 'dragon_ball', name: 'DragonBall' },
      { code: 'hololive', name: 'Hololive' },
    ]);
  });
});
