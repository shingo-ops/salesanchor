/**
 * デザインプレビュー — 共有ユーティリティ
 * セクションヘッダー・トークン読み取り行（内部使用）
 */

/** セクションタイトル + 説明文 */
export function SectionHeader({ title, desc }: { title: string; desc?: string }) {
  return (
    <div className="dp-section-header">
      <h3 className="dp-section-title">{title}</h3>
      {desc != null && <p className="dp-section-desc">{desc}</p>}
    </div>
  );
}

/** CSS トークンの実測値を読み出して表示する行 */
export function TokenRow({
  token,
  desc,
  expected,
}: {
  token: string;
  desc: string;
  expected: string;
}) {
  const actual =
    typeof getComputedStyle === "function"
      ? getComputedStyle(document.documentElement).getPropertyValue(token).trim()
      : "--";

  return (
    <tr>
      <td className="dp-token-name"><code>{token}</code></td>
      <td>{desc}</td>
      <td className="dp-token-expected">{expected}</td>
      <td className="dp-token-actual">{actual || "--"}</td>
    </tr>
  );
}
