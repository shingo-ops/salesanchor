import { useTranslation } from "react-i18next";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { LoadingBlock } from "../../components/loading";
import { DashboardIcons } from "../../constants/icons";
import {
  LEAD_CONVERSION_FACTORS_PATH,
  type LeadConversionFactorItem,
  type LeadConversionFactorsResponse,
} from "../../api/funnel";
import { useApiQuery } from "../../lib/query/apiQuery";
import "./LeadConversionFactorsSection.css";

const FactorsIcon = DashboardIcons.forecast;

export function LeadConversionFactorsSection() {
  const { t, i18n } = useTranslation();
  const factorsQuery = useApiQuery<LeadConversionFactorsResponse>(LEAD_CONVERSION_FACTORS_PATH);
  const data = factorsQuery.data ?? null;
  const loading = factorsQuery.isPending;
  const failed = factorsQuery.isError;

  // 画面に出すときだけ小数2桁に丸める（入口は丸めない）
  function fmt(value: number | null): string {
    if (value === null) return "-";
    return value.toLocaleString(i18n.language, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  const columns: DataTableColumn<LeadConversionFactorItem>[] = [
    {
      key: "key",
      header: t("dashboard.leadFactorsColItem"),
      renderCell: (row) => t(`dashboard.leadFactorsItem.${row.key}`),
    },
    {
      key: "odds_ratio",
      header: t("dashboard.leadFactorsColOdds"),
      align: "right",
      renderCell: (row) =>
        row.computable ? fmt(row.odds_ratio) : t("dashboard.leadFactorsNotComputable"),
    },
    {
      key: "ci",
      header: t("dashboard.leadFactorsColCi"),
      align: "right",
      renderCell: (row) =>
        row.computable
          ? `${fmt(row.ci_low)} ~ ${fmt(row.ci_high)}`
          : t("dashboard.leadFactorsNotComputable"),
    },
    {
      key: "significant",
      header: t("dashboard.leadFactorsColSignificant"),
      renderCell: (row) => {
        if (!row.computable) return t("dashboard.leadFactorsNotComputable");
        return row.significant
          ? t("dashboard.leadFactorsSignificantYes")
          : t("dashboard.leadFactorsSignificantNo");
      },
    },
  ];

  function renderBody() {
    if (loading) return <LoadingBlock label={t("dashboard.leadFactorsLoading")} />;
    if (failed || !data) {
      return <p className="db-lead-factors-message">{t("dashboard.leadFactorsError")}</p>;
    }
    if (data.status === "insufficient") {
      return (
        <p className="db-lead-factors-message">
          {t("dashboard.leadFactorsInsufficient", {
            need: data.required_per_item * data.item_count,
          })}
        </p>
      );
    }
    if (data.status === "not_computable") {
      return <p className="db-lead-factors-message">{t("dashboard.leadFactorsNotComputableAll")}</p>;
    }
    const excluded = Object.values(data.excluded).reduce((sum, n) => sum + n, 0);
    return (
      <>
        <p className="db-lead-factors-counts">
          {t("dashboard.leadFactorsCounts", {
            included: data.included_count,
            won: data.won_count,
            lost: data.lost_count,
            excluded,
          })}
        </p>
        <DataTable
          columns={columns}
          data={data.items}
          rowKey={(row) => row.key}
          rowTestId={() => "lead-factors-row"}
        />
      </>
    );
  }

  return (
    <div className="db-section-card db-lead-factors-card" data-testid="lead-factors-section">
      <div className="db-section-header">
        <FactorsIcon aria-hidden="true" className="db-section-icon" />
        <h3>{t("dashboard.leadFactorsTitle")}</h3>
      </div>
      <p className="db-lead-factors-note">{t("dashboard.leadFactorsNoteCausal")}</p>
      <p className="db-lead-factors-note">{t("dashboard.leadFactorsNoteReverse")}</p>
      {renderBody()}
    </div>
  );
}
