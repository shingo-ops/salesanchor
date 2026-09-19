/**
 * /super-admin/masters — 「各種マスタ」タブ。
 *
 * 商品マスタの選択肢（プルダウン候補）を「名称（日本語）」「名称（英語）」のみで
 * 追加・編集・削除する。各区分とも UI は統一:
 *   検索窓 + 検索ボタン / 名称 ja・en の追加フォーム / 行ごとに編集・削除 /
 *   行のドラッグで並び替え（sort_order を更新）。
 *
 * データ源:
 *   - 8 区分（商品種類/セット種別/レアリティ/言語/単位/HSコード/品目/素材）
 *     → public.product_attribute_masters（/super-admin/product-masters）
 *   - TCGシリーズ → public.tcg_type_master（/super-admin/tcg/types）
 *     ※ 種別(ポケモンカード等)を名称のみで管理。code は内部自動採番で UI 非表示。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { MasterListEditor, type MasterDataSource } from "../../components/master-list-editor";

const ATTRIBUTES = [
  { key: "product_kind", labelKey: "superAdmin.attrMasters.attr.productKind" },
  { key: "set_type", labelKey: "superAdmin.attrMasters.attr.setType" },
  { key: "tcg_series", labelKey: "superAdmin.attrMasters.attr.tcgSeries" },
  { key: "rarity", labelKey: "superAdmin.attrMasters.attr.rarity" },
  { key: "language", labelKey: "superAdmin.attrMasters.attr.language" },
  { key: "unit", labelKey: "superAdmin.attrMasters.attr.unit" },
  { key: "hs_code", labelKey: "superAdmin.attrMasters.attr.hsCode" },
  { key: "item", labelKey: "superAdmin.attrMasters.attr.item" },
  { key: "material", labelKey: "superAdmin.attrMasters.attr.material" },
] as const;

interface AttributeMasterApi {
  id: number;
  label_ja: string;
  label_en: string | null;
  sort_order: number;
}

/** public.product_attribute_masters を name_ja/name_en にマップしたデータ源。 */
function attributeSource(attribute: string): MasterDataSource {
  const base = "/super-admin/product-masters";
  return {
    list: async () => {
      const rows = await api.get<AttributeMasterApi[]>(
        `${base}?attribute=${encodeURIComponent(attribute)}`,
      );
      return rows.map((r) => ({ id: r.id, name_ja: r.label_ja, name_en: r.label_en }));
    },
    create: async (nameJa, nameEn) => {
      await api.post(base, { attribute, label_ja: nameJa, label_en: nameEn, sort_order: 1000 });
    },
    update: async (id, nameJa, nameEn) => {
      await api.patch(`${base}/${id}`, { label_ja: nameJa, label_en: nameEn });
    },
    remove: async (id) => {
      await api.delete(`${base}/${id}`);
    },
    reorder: async (orderedIds) => {
      await Promise.all(
        orderedIds.map((id, i) => api.patch(`${base}/${id}`, { sort_order: (i + 1) * 10 })),
      );
    },
  };
}

interface TcgTypeApi {
  id: number;
  name_ja: string;
  name_en: string | null;
  sort_order: number;
}

/** public.tcg_type_master（TCG 種別）を name_ja/name_en で管理するデータ源。 */
const tcgTypeSource: MasterDataSource = {
  list: async () => {
    const rows = await api.get<TcgTypeApi[]>("/super-admin/tcg/types");
    return rows.map((r) => ({ id: r.id, name_ja: r.name_ja, name_en: r.name_en }));
  },
  create: async (nameJa, nameEn) => {
    // code は backend が自動採番（UI 非入力）。
    await api.post("/super-admin/tcg/types", {
      name_ja: nameJa, name_en: nameEn, sort_order: 1000, is_active: true,
    });
  },
  update: async (id, nameJa, nameEn) => {
    await api.patch(`/super-admin/tcg/types/${id}`, { name_ja: nameJa, name_en: nameEn });
  },
  remove: async (id) => {
    await api.delete(`/super-admin/tcg/types/${id}`);
  },
  reorder: async (orderedIds) => {
    await Promise.all(
      orderedIds.map((id, i) => api.patch(`/super-admin/tcg/types/${id}`, { sort_order: (i + 1) * 10 })),
    );
  },
};

export default function ProductMastersTab() {
  const { t } = useTranslation();
  const [attr, setAttr] = useState<string>(ATTRIBUTES[0].key);
  const source = attr === "tcg_series" ? tcgTypeSource : attributeSource(attr);

  return (
    <div className="product-masters-tab">
      <h3>{t("superAdmin.attrMasters.title")}</h3>
      <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-sm)", marginTop: 0 }}>
        {t("superAdmin.attrMasters.desc")}
      </p>

      <div
        role="tablist"
        aria-label={t("superAdmin.attrMasters.title")}
        style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", margin: "0.5rem 0 1rem" }}
      >
        {ATTRIBUTES.map((a) => (
          <button
            key={a.key}
            role="tab"
            aria-selected={attr === a.key}
            className={attr === a.key ? "btn-primary" : "btn-secondary"}
            onClick={() => setAttr(a.key)}
            style={{ padding: "var(--space-1) var(--space-3)" }}
            data-testid={`attr-master-tab-${a.key}`}
          >
            {t(a.labelKey)}
          </button>
        ))}
      </div>

      {/* key={attr} で区分切替時に内部 state をリセット（再マウント） */}
      <MasterListEditor key={attr} source={source} />
    </div>
  );
}
