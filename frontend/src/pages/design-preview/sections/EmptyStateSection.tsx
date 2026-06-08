/**
 * §12 空状態 (EmptyState) — サイズ × コンテンツ構成
 */
import { EmptyState }     from "../../../components/EmptyState";
import { Button }         from "../../../components/Button";
import { Card }           from "../../../components/Card";
import { PAGE_ICONS, NAV_ICONS } from "../../../constants/icons";
import { ICON }           from "../../../constants/iconSizes";
import { SectionHeader }  from "./_shared";

export function EmptyStateSection() {
  return (
    <>
      {/* §12a: default サイズ */}
      <section className="dp-section">
        <SectionHeader
          title="12a. 空状態 — default（全画面・大きめ）"
          desc="アイコン ICON.xl(48px) / 見出し font-md / 説明 font-sm / padding 48px。リスト・ページ全体の空状態に。"
        />

        {/* アイコン + 見出し + 説明 + アクション */}
        <div style={{ border: "1px dashed var(--border)", borderRadius: "var(--radius-lg)" }}>
          <EmptyState
            icon={<PAGE_ICONS.inboxEmptyOutline size={ICON.xl} />}
            title="受信箱は空です"
            description="新しいメッセージが届くとここに表示されます。チャンネルを追加して会話を開始しましょう。"
            action={<Button variant="secondary">チャンネルを追加</Button>}
          />
        </div>

        {/* アイコン + 見出し + 説明（アクションなし） */}
        <div style={{ border: "1px dashed var(--border)", borderRadius: "var(--radius-lg)", marginTop: "var(--space-4)" }}>
          <EmptyState
            icon={<NAV_ICONS.leads size={ICON.xl} />}
            title="リードがありません"
            description="登録されているリードはまだありません。"
          />
        </div>

        {/* 見出しのみ（最小構成） */}
        <div style={{ border: "1px dashed var(--border)", borderRadius: "var(--radius-lg)", marginTop: "var(--space-4)" }}>
          <EmptyState title="データがありません" />
        </div>
      </section>

      {/* §12b: compact サイズ */}
      <section className="dp-section">
        <SectionHeader
          title="12b. 空状態 — compact（テーブル・カード内）"
          desc="アイコン ICON.lg(24px) / 見出し font-sm / 説明 font-xs / padding 24px。DataTable emptyState prop やカード内に。"
        />

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
          {/* 検索結果なし */}
          <Card variant="container">
            <EmptyState
              size="compact"
              icon={<NAV_ICONS.search size={ICON.lg} />}
              title="検索結果なし"
              description="条件を変えてお試しください。"
            />
          </Card>

          {/* フィルター結果なし + アクション */}
          <Card variant="container">
            <EmptyState
              size="compact"
              icon={<NAV_ICONS.filter size={ICON.lg} />}
              title="該当するリードがありません"
              action={<Button variant="ghost" size="sm">フィルターをリセット</Button>}
            />
          </Card>

          {/* ファイルなし */}
          <Card variant="container">
            <EmptyState
              size="compact"
              icon={<NAV_ICONS.fileText size={ICON.lg} />}
              title="ファイルがありません"
              description="添付ファイルはまだありません。"
            />
          </Card>

          {/* テキストのみ */}
          <Card variant="container">
            <EmptyState
              size="compact"
              title="データがありません"
            />
          </Card>
        </div>
      </section>

      {/* §12c: DataTable との連携例 */}
      <section className="dp-section">
        <SectionHeader
          title="12c. DataTable emptyState prop との連携"
          desc="DataTable の emptyState prop に <EmptyState size='compact'> を渡す想定パターン。"
        />
        <pre style={{
          background: "var(--bg-subtle)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)",
          padding: "var(--space-4)",
          fontSize: "var(--font-xs)",
          overflowX: "auto",
          margin: 0,
        }}>
{`<DataTable
  columns={columns}
  data={[]}
  emptyState={
    <EmptyState
      size="compact"
      icon={<NAV_ICONS.leads size={ICON.lg} />}
      title="リードがありません"
      description="新しいリードを追加してください。"
      action={<Button variant="primary" size="sm">リードを追加</Button>}
    />
  }
/>`}
        </pre>
      </section>
    </>
  );
}
