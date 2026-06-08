/**
 * §11 モーダル — サイズ × コンテンツ
 */
import { useState } from "react";
import { Modal, type ModalSize } from "../../../components/Modal";
import { Button }                from "../../../components/Button";
import { SectionHeader }         from "./_shared";

const SIZES: { size: ModalSize; label: string; desc: string }[] = [
  { size: "sm", label: "小 (sm)",  desc: "max-width: 420px — 確認・アラート" },
  { size: "md", label: "中 (md)",  desc: "max-width: 600px — 標準フォーム" },
  { size: "lg", label: "大 (lg)",  desc: "max-width: 800px — 詳細・テーブル" },
];

type OpenState = ModalSize | "footer" | null;

export function ModalSection() {
  const [open, setOpen] = useState<OpenState>(null);

  return (
    <>
      <section className="dp-section">
        <SectionHeader
          title="11. モーダル (Modal / Dialog)"
          desc="サイズ sm / md / lg。Esc / 背景クリックで閉じる。フォーカストラップ有り。"
        />

        {/* サイズデモ */}
        <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
          {SIZES.map(({ size, label }) => (
            <Button key={size} variant="secondary" onClick={() => setOpen(size)}>
              {label} を開く
            </Button>
          ))}
          <Button variant="outline" onClick={() => setOpen("footer")}>
            フッタ付き を開く
          </Button>
        </div>

        {/* sm */}
        <Modal
          open={open === "sm"}
          onClose={() => setOpen(null)}
          size="sm"
          title="小サイズ モーダル (sm)"
        >
          <p style={{ margin: 0 }}>max-width: 420px — 確認・簡易アラート向けのコンパクトサイズです。</p>
        </Modal>

        {/* md */}
        <Modal
          open={open === "md"}
          onClose={() => setOpen(null)}
          size="md"
          title="中サイズ モーダル (md)"
        >
          <p style={{ margin: "0 0 var(--space-3)" }}>max-width: 600px — 標準フォームや中程度のコンテンツに使用します。</p>
          <p style={{ margin: 0 }}>本体エリアは縦スクロール対応です。コンテンツが多い場合はここがスクロールします。</p>
        </Modal>

        {/* lg */}
        <Modal
          open={open === "lg"}
          onClose={() => setOpen(null)}
          size="lg"
          title="大サイズ モーダル (lg)"
        >
          <p style={{ margin: "0 0 var(--space-3)" }}>max-width: 800px — 詳細情報・テーブル表示など広いコンテンツに使用します。</p>
          <p style={{ margin: 0 }}>モバイルでは幅 100% のボトムシート形式になります。</p>
        </Modal>

        {/* フッタ付き */}
        <Modal
          open={open === "footer"}
          onClose={() => setOpen(null)}
          size="md"
          title="フッタ付きモーダル"
          footer={
            <>
              <Button variant="secondary" onClick={() => setOpen(null)}>キャンセル</Button>
              <Button variant="primary"   onClick={() => setOpen(null)}>保存</Button>
            </>
          }
        >
          <p style={{ margin: 0 }}>footer prop にアクションボタンを渡すと、ダイアログ下部に標準レイアウトで表示されます。</p>
        </Modal>
      </section>

      {/* トークン一覧 */}
      <section className="dp-section">
        <SectionHeader title="11b. モーダルトークン" />
        <table className="dp-token-table">
          <thead>
            <tr>
              <th>トークン</th>
              <th>説明</th>
              <th>値</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["--modal-max-w-sm", "sm 最大幅", "420px"],
              ["--modal-max-w-md", "md 最大幅", "600px"],
              ["--modal-max-w-lg", "lg 最大幅", "800px"],
              ["--z-backdrop",     "背景レイヤー",  "298"],
              ["--z-modal",        "ダイアログ",    "400"],
              ["--shadow-modal",   "影",            "var(--shadow-modal)"],
              ["--radius-lg",      "角丸",          "8px"],
            ].map(([token, desc, val]) => (
              <tr key={token}>
                <td><code>{token}</code></td>
                <td>{desc}</td>
                <td>{val}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
