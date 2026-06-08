/**
 * DesignPreviewPage -- コンポーネント標準 目視確認ページ（Task 1C / 2C）
 * dev-only preview: 日本語表記を許可（eslint.config.js の overrides 参照）
 *
 * アクセス: /design-preview（ログイン後 URL 直打ち・ナビ未掲載）
 */

import { useState } from "react";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { TextField } from "../../components/TextField";
import { Select } from "../../components/Select";
import { Textarea } from "../../components/Textarea";
import { Badge } from "../../components/Badge";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn, SortDir } from "../../components/DataTable";
import { X, PAGE_ICONS } from "../../constants/icons";
import "./DesignPreviewPage.css";

// -- §9 DataTable デモデータ --------------------------------------------------
interface DemoLead {
  id: string;
  name: string;
  company: string;
  status: string;
  score: number;
}

const DEMO_LEADS: DemoLead[] = [
  { id: "1", name: "田中 一郎",   company: "株式会社A商事",     status: "対応済み",  score: 92 },
  { id: "2", name: "鈴木 花子",   company: "B株式会社",         status: "保留中",    score: 75 },
  { id: "3", name: "佐藤 次郎",   company: "Cコーポレーション", status: "未対応",    score: 40 },
  { id: "4", name: "伊藤 三郎",   company: "D合同会社",         status: "対応済み",  score: 88 },
  { id: "5", name: "山田 美咲",   company: "E株式会社",         status: "保留中",    score: 61 },
];

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "neutral"> = {
  "対応済み": "success",
  "保留中":   "warning",
  "未対応":   "danger",
};

const DEMO_LEAD_COLUMNS: DataTableColumn<DemoLead>[] = [
  { key: "name",    header: "名前",     width: "140px", sortable: true },
  { key: "company", header: "会社名",   sortable: true },
  {
    key: "status",
    header: "ステータス",
    width: "120px",
    renderCell: (row) => (
      <Badge variant={STATUS_VARIANT[row.status] ?? "neutral"} appearance="soft" size="sm">
        {row.status}
      </Badge>
    ),
  },
  { key: "score", header: "スコア", width: "72px", sortable: true },
];

// -- 幅セレクタの選択肢 -------------------------------------------------------
const WIDTH_BANDS = [
  { label: "モバイル (375px)",   value: 375  },
  { label: "タブレット (768px)", value: 768  },
  { label: "PC (全幅)",          value: null },
] as const;

type BandValue = 375 | 768 | null;

// -- セクションヘッダー --------------------------------------------------------
function SectionHeader({ title, desc }: { title: string; desc?: string }) {
  return (
    <div className="dp-section-header">
      <h3 className="dp-section-title">{title}</h3>
      {desc != null && <p className="dp-section-desc">{desc}</p>}
    </div>
  );
}

// -- トークン値サマリ ----------------------------------------------------------
const TOKEN_SUMMARY = [
  { token: "--comp-btn-radius",           desc: "ボタン角丸",               expected: "6px (radius-md)"    },
  { token: "--comp-card-radius",          desc: "カード角丸",               expected: "8px (radius-lg)"    },
  { token: "--comp-card-padding",         desc: "カード余白 PC/タブレット",  expected: "24px (space-6)"     },
  { token: "--comp-card-padding-compact", desc: "カード余白 モバイル",      expected: "16px (space-4)"     },
  { token: "--comp-card-gap",             desc: "カード間ギャップ",          expected: "24px (space-6)"     },
  { token: "--comp-input-radius",         desc: "入力コントロール角丸",      expected: "6px (radius-md)"    },
  { token: "--comp-input-height-sm",      desc: "入力 sm 最小高",           expected: "28px"               },
  { token: "--comp-input-height-mobile",  desc: "入力 モバイルタッチ最小高", expected: "44px (WCAG 2.5.5)"  },
];

// -- Select デモ用オプション --------------------------------------------------
const DEMO_SELECT_OPTIONS = [
  { value: "active",   label: "有効 (Active)"   },
  { value: "pending",  label: "保留 (Pending)"  },
  { value: "closed",   label: "終了 (Closed)"   },
];

// -- バリアント表示ラベル -------------------------------------------------------
const VARIANT_LABEL: Record<string, string> = {
  primary:   "主要 (primary)",
  secondary: "補助 (secondary)",
  ghost:     "控えめ (ghost)",
  danger:    "破壊的 (danger)",
};

export default function DesignPreviewPage() {
  const [bandWidth, setBandWidth] = useState<BandValue>(null);

  // §9 DataTable 状態
  const [tableSortKey, setTableSortKey]   = useState<string>("name");
  const [tableSortDir, setTableSortDir]   = useState<SortDir>("asc");
  const [tableSelected, setTableSelected] = useState<Set<string>>(new Set());
  const [tableDensity,  setTableDensity]  = useState<"compact" | "default" | "relaxed">("default");

  const sortedLeads = [...DEMO_LEADS].sort((a, b) => {
    const av = (a as Record<string, unknown>)[tableSortKey];
    const bv = (b as Record<string, unknown>)[tableSortKey];
    const cmp = String(av).localeCompare(String(bv), "ja");
    return tableSortDir === "asc" ? cmp : -cmp;
  });

  return (
    <PageLayout navKey="nav.designPreview" subtitleKey="designPreview.subtitle">
      {/* -- 幅セレクタ -- */}
      <div className="dp-band-selector">
        <span className="dp-band-label">プレビュー幅:</span>
        {WIDTH_BANDS.map((b) => (
          <button
            key={String(b.value)}
            className={`dp-band-btn${bandWidth === b.value ? " dp-band-btn--active" : ""}`}
            onClick={() => setBandWidth(b.value as BandValue)}
          >
            {b.label}
          </button>
        ))}
      </div>

      {/* -- プレビュー枠 -- */}
      <div
        className="dp-preview-frame"
        style={bandWidth != null ? { maxWidth: bandWidth, margin: "0 auto" } : undefined}
      >

        {/* [1] デザイントークン確認 */}
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

        {/* [2] ボタン — 種類 × サイズ */}
        <section className="dp-section">
          <SectionHeader
            title="2. ボタン — 種類 × サイズ (variant x size)"
            desc="主要＝その画面で一番押してほしい操作 / 補助＝その次 / 控えめ＝軽い操作 / 破壊的＝削除など取り消せない操作"
          />

          {(["primary", "secondary", "ghost", "danger"] as const).map((variant) => (
            <div key={variant} className="dp-row">
              <span className="dp-row-label">{VARIANT_LABEL[variant]}</span>
              <div className="dp-row-items">
                <Button variant={variant} size="sm">小 (sm)</Button>
                <Button variant={variant} size="md">中 (md)</Button>
                <Button variant={variant} size="lg">大 (lg)</Button>
              </div>
            </div>
          ))}
        </section>

        {/* [3] ボタン — 状態 */}
        <section className="dp-section">
          <SectionHeader
            title="3. ボタン — 状態 (states)"
            desc="無効＝押せない状態（薄く表示）。読み込み中＝処理中のスピナー表示。横幅いっぱい＝コンテナ全幅に伸縮。"
          />

          <div className="dp-row">
            <span className="dp-row-label">通常</span>
            <div className="dp-row-items">
              <Button variant="primary">通常</Button>
            </div>
          </div>
          <div className="dp-row">
            <span className="dp-row-label">無効 (disabled)</span>
            <div className="dp-row-items">
              <Button variant="primary" disabled>無効</Button>
              <Button variant="secondary" disabled>無効</Button>
              <Button variant="ghost" disabled>無効</Button>
              <Button variant="danger" disabled>無効</Button>
            </div>
          </div>
          <div className="dp-row">
            <span className="dp-row-label">読み込み中 (loading)</span>
            <div className="dp-row-items">
              <Button variant="primary" loading>保存中...</Button>
              <Button variant="secondary" loading>読み込み中</Button>
            </div>
          </div>
          <div className="dp-row">
            <span className="dp-row-label">横幅いっぱい (fullWidth)</span>
            <div className="dp-row-items dp-row-items--full">
              <Button variant="primary" fullWidth>横幅いっぱいのボタン</Button>
            </div>
          </div>
          <div className="dp-row">
            <span className="dp-row-label">アイコンのみ (icon only)</span>
            <div className="dp-row-items">
              <Button variant="primary" iconOnly aria-label="追加">+</Button>
              <Button variant="ghost" iconOnly aria-label="閉じる">
                <X size={16} aria-hidden="true" />
              </Button>
              <Button variant="secondary" iconOnly aria-label="設定">
                <PAGE_ICONS.settingsSolid size={16} aria-hidden="true" />
              </Button>
            </div>
          </div>
        </section>

        {/* [4] カード — 種類 × 余白 */}
        <section className="dp-section">
          <SectionHeader
            title="4. カード — 種類 × 余白 (variant x density)"
            desc="容器＝汎用の囲み / クリック可＝hover で浮き上がる / 数値＝上部にアクセントライン。余白は既定 24px・詰め 16px の 2 種。"
          />

          {(["container", "interactive", "metric"] as const).map((variant) => (
            <div key={variant} className="dp-card-row">
              <div className="dp-card-col">
                <span className="dp-card-col-label">
                  {variant === "container"   ? "容器 (container)" :
                   variant === "interactive" ? "クリック可 (interactive)" :
                                              "数値 (metric)"}
                  {" "}/ 既定 (24px)
                </span>
                <Card variant={variant} density="default">
                  <p className="dp-card-title">
                    {variant === "container"   ? "容器 (container)" :
                     variant === "interactive" ? "クリック可 (interactive)" :
                                                "数値 (metric)"}
                  </p>
                  <p className="dp-card-body">
                    padding: 24px (--comp-card-padding)
                    <br />
                    radius: 8px (--comp-card-radius)
                  </p>
                </Card>
              </div>
              <div className="dp-card-col">
                <span className="dp-card-col-label">
                  {variant === "container"   ? "容器 (container)" :
                   variant === "interactive" ? "クリック可 (interactive)" :
                                              "数値 (metric)"}
                  {" "}/ 詰め (16px)
                </span>
                <Card variant={variant} density="compact">
                  <p className="dp-card-title">
                    {variant === "container"   ? "容器 (container)" :
                     variant === "interactive" ? "クリック可 (interactive)" :
                                                "数値 (metric)"}
                  </p>
                  <p className="dp-card-body">
                    padding: 16px (--comp-card-padding-compact)
                    <br />
                    radius: 8px (--comp-card-radius)
                  </p>
                </Card>
              </div>
            </div>
          ))}
        </section>

        {/* [5] カードグリッド — 間隔検証 */}
        <section className="dp-section">
          <SectionHeader title="5. カードグリッド — 間隔検証 (gap = 24px)" />
          <div className="dp-card-grid">
            {["カード A", "カード B", "カード C"].map((label) => (
              <Card key={label} variant="container">
                <p className="dp-card-title">{label}</p>
                <p className="dp-card-body">gap: var(--comp-card-gap) = 24px</p>
              </Card>
            ))}
          </div>
        </section>

        {/* [6] フォーム入力 — 全状態 */}
        <section className="dp-section">
          <SectionHeader
            title="6. フォーム入力 — 全状態 (states)"
            desc="通常・focus（選択中・青枠）・エラー（赤枠＋エラーメッセージ）・無効（薄く表示）の見え方を確認します。"
          />

          <div className="dp-form-grid">
            {/* テキスト入力 (TextField) */}
            <div>
              <span className="dp-card-col-label">テキスト入力 (TextField) / 通常</span>
              <TextField label="会社名" placeholder="会社名を入力" helperText="補助テキストの表示例。" />
            </div>
            <div>
              <span className="dp-card-col-label">テキスト入力 (TextField) / 必須 (required)</span>
              <TextField label="メールアドレス" type="email" placeholder="you@example.com" required />
            </div>
            <div>
              <span className="dp-card-col-label">テキスト入力 (TextField) / エラー (error)</span>
              <TextField
                label="メールアドレス"
                type="email"
                defaultValue="不正な入力値"
                error="メールアドレスの形式が正しくありません。"
                required
              />
            </div>
            <div>
              <span className="dp-card-col-label">テキスト入力 (TextField) / 無効 (disabled)</span>
              <TextField label="アカウント ID" defaultValue="ACC-00123" disabled helperText="変更できません。" />
            </div>

            {/* 選択 (Select) */}
            <div>
              <span className="dp-card-col-label">選択 (Select) / 通常</span>
              <Select label="ステータス" options={DEMO_SELECT_OPTIONS} placeholder="-- 選択してください --" helperText="補助テキストの表示例。" />
            </div>
            <div>
              <span className="dp-card-col-label">選択 (Select) / 必須 (required)</span>
              <Select label="カテゴリ" options={DEMO_SELECT_OPTIONS} placeholder="-- 選択してください --" required />
            </div>
            <div>
              <span className="dp-card-col-label">選択 (Select) / エラー (error)</span>
              <Select label="地域" options={DEMO_SELECT_OPTIONS} error="選択肢を選んでください。" required />
            </div>
            <div>
              <span className="dp-card-col-label">選択 (Select) / 無効 (disabled)</span>
              <Select label="通貨" options={[{ value: "jpy", label: "JPY — 日本円" }]} defaultValue="jpy" disabled helperText="このアカウントでは固定です。" />
            </div>

            {/* 複数行入力 (Textarea) */}
            <div>
              <span className="dp-card-col-label">複数行入力 (Textarea) / 通常</span>
              <Textarea label="メモ" placeholder="メモを入力してください..." helperText="チーム全員に表示されます。" />
            </div>
            <div>
              <span className="dp-card-col-label">複数行入力 (Textarea) / エラー (error)</span>
              <Textarea label="メッセージ" placeholder="メッセージを入力..." error="メッセージを入力してください。" required />
            </div>
            <div>
              <span className="dp-card-col-label">複数行入力 (Textarea) / 無効 (disabled)</span>
              <Textarea label="テンプレート本文" defaultValue="このテンプレートはロックされています。" disabled helperText="変更できません。" />
            </div>
          </div>
        </section>

        {/* [7] フォーム入力 — サイズ比較 */}
        <section className="dp-section">
          <SectionHeader
            title="7. フォーム入力 — サイズ比較 (sm / md / lg)"
            desc="小 (sm)＝28px 最小高 / 中 (md)＝既定 / 大 (lg)＝44px 最小高（モバイルタッチ対応）"
          />

          <div className="dp-form-grid">
            <div>
              <span className="dp-card-col-label">テキスト入力 / 小 (sm)</span>
              <TextField label="小サイズ" placeholder="sm 入力" size="sm" />
            </div>
            <div>
              <span className="dp-card-col-label">テキスト入力 / 中・既定 (md)</span>
              <TextField label="中サイズ（既定）" placeholder="md 入力" size="md" />
            </div>
            <div>
              <span className="dp-card-col-label">テキスト入力 / 大 (lg)</span>
              <TextField label="大サイズ" placeholder="lg 入力" size="lg" />
            </div>
            <div>
              <span className="dp-card-col-label">選択 / 小 (sm)</span>
              <Select label="小サイズ" options={DEMO_SELECT_OPTIONS} size="sm" />
            </div>
            <div>
              <span className="dp-card-col-label">選択 / 中・既定 (md)</span>
              <Select label="中サイズ（既定）" options={DEMO_SELECT_OPTIONS} size="md" />
            </div>
            <div>
              <span className="dp-card-col-label">選択 / 大 (lg)</span>
              <Select label="大サイズ" options={DEMO_SELECT_OPTIONS} size="lg" />
            </div>
          </div>
        </section>

        {/* [8] バッジ・ステータス */}
        <section className="dp-section">
          <SectionHeader
            title="8. バッジ・ステータス (Badge)"
            desc="variant 5 × appearance 2 × size 2。ドット付きの例も確認できる。"
          />

          {/* variant × appearance */}
          {(["neutral", "info", "success", "warning", "danger"] as const).map((variant) => (
            <div key={variant} className="dp-row">
              <span className="dp-row-label">{variant}</span>
              <div className="dp-row-items">
                <Badge variant={variant} appearance="soft"  size="sm">{variant} / soft / sm</Badge>
                <Badge variant={variant} appearance="soft"  size="md">{variant} / soft / md</Badge>
                <Badge variant={variant} appearance="solid" size="sm">{variant} / solid / sm</Badge>
                <Badge variant={variant} appearance="solid" size="md">{variant} / solid / md</Badge>
              </div>
            </div>
          ))}

          {/* ドット付き */}
          <div className="dp-row">
            <span className="dp-row-label">dot</span>
            <div className="dp-row-items">
              <Badge variant="success" dot>対応済み</Badge>
              <Badge variant="warning" dot>保留中</Badge>
              <Badge variant="danger"  dot>要対応</Badge>
              <Badge variant="info"    dot>処理中</Badge>
              <Badge variant="neutral" dot>未分類</Badge>
            </div>
          </div>

          {/* アイコン付き */}
          <div className="dp-row">
            <span className="dp-row-label">icon</span>
            <div className="dp-row-items">
              <Badge variant="success" icon={<PAGE_ICONS.settingsSolid size={10} />}>設定済み</Badge>
              <Badge variant="danger"  icon={<X size={10} />}>エラー</Badge>
            </div>
          </div>
        </section>

        {/* [9] データテーブル */}
        <section className="dp-section">
          <SectionHeader
            title="9. データテーブル (DataTable)"
            desc="ソート・行選択・density 3種・空状態の目視確認。"
          />

          {/* density セレクタ */}
          <div className="dp-row">
            <span className="dp-row-label">density</span>
            <div className="dp-row-items">
              {(["compact", "default", "relaxed"] as const).map((d) => (
                <button
                  key={d}
                  type="button"
                  className={`dp-band-btn${tableDensity === d ? " dp-band-btn--active" : ""}`}
                  onClick={() => setTableDensity(d)}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* テーブル本体 */}
          <DataTable<DemoLead>
            columns={DEMO_LEAD_COLUMNS}
            data={sortedLeads}
            rowKey={(r) => r.id}
            sortKey={tableSortKey}
            sortDir={tableSortDir}
            onSort={(k, d) => { setTableSortKey(k); setTableSortDir(d); }}
            selectable
            selectedKeys={tableSelected}
            onSelectChange={setTableSelected}
            density={tableDensity}
            emptyState={<span>データがありません</span>}
          />

          {/* 空状態 */}
          <div className="dp-row">
            <span className="dp-row-label">empty</span>
            <div style={{ width: "100%" }}>
              <DataTable<DemoLead>
                columns={DEMO_LEAD_COLUMNS}
                data={[]}
                rowKey={(r) => r.id}
                emptyState={<span>該当するデータがありません</span>}
              />
            </div>
          </div>
        </section>

      </div>
    </PageLayout>
  );
}

// -- トークン実測値を CSS から読み出す行コンポーネント -------------------------
function TokenRow({ token, desc, expected }: { token: string; desc: string; expected: string }) {
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
