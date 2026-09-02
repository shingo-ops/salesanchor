export type SourceRawLine = { number: number; text: string };

export function sourceRawLines(raw: string): SourceRawLine[] {
  return raw.split('\n').map((part, index, all) => ({ number: index + 1, text: index < all.length - 1 ? `${part}\n` : part }));
}

export function sourceRawText(lines: SourceRawLine[]): string {
  return lines.map((line) => line.text).join('');
}

export function parseSourceLineReference(value: string): number | undefined {
  const match = value.trim().match(/^(?:L)?0*(\d+)(?:\s*-\s*(?:L)?0*\d+)?$/i);
  if (!match) return undefined;
  const line = Number(match[1]);
  return line > 0 ? line : undefined;
}

export function exactSourceLineMatches(lines: SourceRawLine[], query: string): number[] {
  return query ? lines.filter((line) => line.text.includes(query)).map((line) => line.number) : [];
}
