/**
 * 解析精度管理（新方式）の原文ペイン。
 *
 * 行番号つきで原文を表示し、選択中のブロックの範囲と見出しの範囲を色分けする。
 * 行の分割は sourceRawLines（sourceRawNavigation.ts）を再利用する。
 * 既存の SourceRawPane（強調は1行・2.6秒で消える）は変更せず、別部品として作る。
 */
import { useEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import { sourceRawLines } from "./sourceRawNavigation";
import "./shadow-source-pane.css";

export interface LineRange {
  start: number | null;
  end: number | null;
}

interface Props {
  rawText: string;
  blockRange?: LineRange | null;
  headingRange?: LineRange | null;
}

function inRange(line: number, range?: LineRange | null): boolean {
  if (!range || range.start == null || range.end == null) return false;
  return line >= range.start && line <= range.end;
}

export function ShadowSourcePane({ rawText, blockRange, headingRange }: Props) {
  const { t } = useTranslation();
  const lines = useMemo(() => sourceRawLines(rawText), [rawText]);
  const lineElements = useRef<Record<number, HTMLDivElement | null>>({});

  const firstBlockLine = blockRange?.start ?? null;
  useEffect(() => {
    if (firstBlockLine == null) return;
    // jsdom には scrollIntoView が無いので存在を確かめてから呼ぶ
    lineElements.current[firstBlockLine]?.scrollIntoView?.({ block: "center", behavior: "smooth" });
  }, [firstBlockLine]);

  return (
    <section className="shadow-source-pane" aria-label={t("shadowAccuracy.source.title")}>
      <div className="shadow-source-legend">
        <span className="shadow-source-legend-item shadow-source-legend-item--block">
          {t("shadowAccuracy.source.legendBlock")}
        </span>
        <span className="shadow-source-legend-item shadow-source-legend-item--heading">
          {t("shadowAccuracy.source.legendHeading")}
        </span>
      </div>
      <div className="shadow-source-lines">
        {lines.map((line) => {
          const isBlock = inRange(line.number, blockRange);
          const isHeading = inRange(line.number, headingRange);
          const classes = [
            "shadow-source-line",
            isBlock ? "shadow-source-line--block" : "",
            isHeading ? "shadow-source-line--heading" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <div
              key={line.number}
              ref={(element) => {
                lineElements.current[line.number] = element;
              }}
              className={classes}
              data-line-number={line.number}
              data-range={isBlock ? "block" : isHeading ? "heading" : undefined}
            >
              <span className="shadow-source-line-no">{line.number}</span>
              <span className="shadow-source-line-text">{line.text.replace(/\n$/, "")}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
