/**
 * §1 デザイントークン確認
 * CSS 変数の実測値を自動取得して期待値と照合する。
 */
import { SectionHeader, TokenRow } from "./_shared";

const TOKEN_SUMMARY = [
  { token: "--comp-btn-radius",           desc: "ボタン角丸",               expected: "6px (radius-md)"    },
  { token: "--comp-card-radius",          desc: "カード角丸",               expected: "8px (radius-lg)"    },
  { token: "--comp-card-padding",         desc: "カード余白 PC/タブレット",  expected: "24px (space-6)"     },
  { token: "--comp-card-padding-compact", desc: "カード余白 モバイル",      expected: "16px (space-4)"     },
  { token: "--comp-card-gap",             desc: "カード間ギャップ",          expected: "24px (space-6)"     },
  { token: "--comp-input-radius",         desc: "入力コントロール角丸",      expected: "6px (radius-md)"    },
  { token: "--comp-input-height-sm",      desc: "入力 sm 最小高",           expected: "28px"               },
  { token: "--comp-input-height-mobile",  desc: "入力 モバイルタッチ最小高", expected: "44px (WCAG 2.5.5)"  },
  { token: "--comp-badge-height-sm",      desc: "バッジ sm 最小高",         expected: "20px"               },
  { token: "--comp-badge-height-md",      desc: "バッジ md 最小高",         expected: "24px"               },
  { token: "--comp-table-row-h-compact",  desc: "テーブル行高 compact",     expected: "32px"               },
  { token: "--comp-table-row-h-default",  desc: "テーブル行高 default",     expected: "44px"               },
  { token: "--comp-table-row-h-relaxed",  desc: "テーブル行高 relaxed",     expected: "56px"               },
  { token: "--comp-tab-h-sm",             desc: "タブ高さ sm",              expected: "28px"               },
  { token: "--comp-tab-h-md",             desc: "タブ高さ md",              expected: "36px (height-tab-item)" },
  { token: "--comp-tab-underline-w",      desc: "アクティブ下線幅",          expected: "2px"                },
  { token: "--comp-tab-pill-radius",      desc: "ピルタブ角丸",              expected: "6px (radius-md)"    },
];

export function TokenSection() {
  return (
    <section className="dp-section">
      <SectionHeader
        title="1. デザイントークン確認"
        desc="CSS 変数の実測値を自動取得して期待値と照合します。"
      />
      <table className="dp-token-table">
        <thead>
          <tr>
            <th>トークン</th>
            <th>説明</th>
            <th>期待値</th>
            <th>実測値</th>
          </tr>
        </thead>
        <tbody>
          {TOKEN_SUMMARY.map(({ token, desc, expected }) => (
            <TokenRow key={token} token={token} desc={desc} expected={expected} />
          ))}
        </tbody>
      </table>
    </section>
  );
}
