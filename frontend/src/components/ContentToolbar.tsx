import "./ContentToolbar.css";

interface ContentToolbarProps {
  /** 左スロット: フィルタ・検索・タブ切替 */
  left?: React.ReactNode;
  /** 右スロット: 実行ボタン（Button金型 primary 1個＋secondary。ghost設定系はヘッダーへ） */
  right?: React.ReactNode;
}

/**
 * 操作台（ContentToolbar・page-header-v2 改訂5・第3の金型）
 * design: docs/specs/design-system/component-ssot/page-header-v2/design.md §2.5
 * 1本の横棒で 左=フィルタ / 右=実行ボタン を同一X軸に揃える。
 * 親ページ: ヘッダー直下に置く / 子ページ: 子タイトル行と同一X軸に置く。
 * 高さ・余白は本部品が独占（ページ側の手書きmargin/paddingは禁止）。
 */
export function ContentToolbar({ left, right }: ContentToolbarProps) {
  return (
    <div className="content-toolbar">
      <div className="content-toolbar__left">{left}</div>
      <div className="content-toolbar__right">{right}</div>
    </div>
  );
}
