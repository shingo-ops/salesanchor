/**
 * §4 カード — 種類 × 余白
 * §5 カードグリッド — 間隔検証
 */
import { Card } from "../../../components/Card";
import { SectionHeader } from "./_shared";

export function CardSection() {
  return (
    <>
      {/* §4: 種類 × 余白 */}
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

      {/* §5: カードグリッド */}
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
    </>
  );
}
