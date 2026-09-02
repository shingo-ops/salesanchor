import React, { useEffect, useMemo, useRef, useState } from 'react';
import { exactSourceLineMatches, parseSourceLineReference, sourceRawLines } from './sourceRawNavigation';
import './source-raw-pane.css';

export type SourceLineJump = { line: number; requestId: number };

export function SourceRawPane({ sourceMessageId, rawText, itemCount, jump }: { sourceMessageId: string; rawText: string; itemCount: number; jump?: SourceLineJump }) {
  const lines = useMemo(() => sourceRawLines(rawText), [rawText]);
  const lineElements = useRef<Record<number, HTMLSpanElement | null>>({});
  const [query, setQuery] = useState('');
  const [activeMatch, setActiveMatch] = useState(0);
  const [highlightLine, setHighlightLine] = useState<number>();
  const lineReference = parseSourceLineReference(query);
  const matches = lineReference ? (lineReference <= lines.length ? [lineReference] : []) : exactSourceLineMatches(lines, query);
  const status = query && matches.length === 0 ? '該当行がありません' : matches.length > 1 ? `${activeMatch + 1} / ${matches.length}` : '';
  const moveToLine = (line: number) => {
    const element = lineElements.current[line];
    if (!element) return;
    element.scrollIntoView({ block: 'center', behavior: 'smooth' });
    setHighlightLine(line);
  };
  const moveToMatch = (nextIndex: number) => {
    if (!matches.length) return;
    const index = (nextIndex + matches.length) % matches.length;
    setActiveMatch(index);
    moveToLine(matches[index]);
  };
  useEffect(() => { if (jump) { setQuery(`L${String(jump.line).padStart(4, '0')}`); setActiveMatch(0); moveToLine(jump.line); } }, [jump?.requestId]);
  useEffect(() => { if (!highlightLine) return; const timer = window.setTimeout(() => setHighlightLine(undefined), 2600); return () => window.clearTimeout(timer); }, [highlightLine]);
  return <aside className="source-raw"><div className="source-raw-pane"><div className="source-meta"><span>原文 1件</span><span>抽出商品 {itemCount}件</span></div><form className="source-search" onSubmit={(event) => { event.preventDefault(); moveToMatch(0); }}><label htmlFor={`source-search-${sourceMessageId}`}>原文検索</label><input id={`source-search-${sourceMessageId}`} value={query} onChange={(event) => { setQuery(event.target.value); setActiveMatch(0); }} placeholder="L0006 または文字列" /><button type="submit">移動</button>{matches.length > 1 && <><button type="button" onClick={() => moveToMatch(activeMatch - 1)}>前へ</button><button type="button" onClick={() => moveToMatch(activeMatch + 1)}>次へ</button></>}<output aria-live="polite">{status}</output></form><div className="raw" aria-label="原文全文">{lines.map((line) => <span key={line.number} ref={(element) => { lineElements.current[line.number] = element; }} data-line-number={line.number} className={highlightLine === line.number ? 'raw-line raw-line-highlight' : 'raw-line'}>{line.text}</span>)}</div></div></aside>;
}
