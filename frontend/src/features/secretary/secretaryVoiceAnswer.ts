/**
 * 声の「はい／いいえ」の判定（秘書の声で会話・予定の確かめ）。
 * 語の一覧は翻訳キー secretary.voiceMode.yesWords / noWords（| 区切り）から呼ぶ側が渡す。
 * この中に日本語の語は書かない。
 */

export type YesNo = "yes" | "yesMore" | "no" | "unknown";

/** NFKC にして英字を小文字にする（句読点・空白はそのまま） */
function fold(s: string): string {
  return s.normalize("NFKC").toLowerCase().replace(/[‘’]/g, "'");
}

/** 句読点・記号・空白を除く */
function squash(s: string): string {
  return s.replace(/[\s\p{P}\p{S}]/gu, "");
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const LATIN_WORD = /^[a-z][a-z' ]*$/;

interface Prepared {
  /** NFKC・小文字だけにした形（句読点を残す） */
  folded: string;
  /** 句読点と空白を除いた形 */
  squashed: string;
  /** 文の頭の句読点・空白だけを除いた形 */
  leading: string;
}

function prepare(text: string): Prepared {
  const folded = fold(text).trim();
  return {
    folded,
    squashed: squash(folded),
    leading: folded.replace(/^[\s\p{P}\p{S}]+/u, ""),
  };
}

function matchesAnywhere(p: Prepared, word: string): boolean {
  if (LATIN_WORD.test(word)) {
    return new RegExp(`(?<![a-z0-9'])${escapeRegExp(word)}(?![a-z0-9'])`).test(p.folded);
  }
  const w = squash(word);
  return w !== "" && p.squashed.includes(w);
}

function matchesAtStart(p: Prepared, word: string): boolean {
  if (LATIN_WORD.test(word)) {
    return new RegExp(`^${escapeRegExp(word)}(?![a-z0-9'])`).test(p.leading);
  }
  const w = squash(word);
  return w !== "" && p.squashed.startsWith(w);
}

/** はい の語を文の頭から（長い語から順に・取り除けなくなるまで）取り除いた残りが空か */
function onlyYesWords(p: Prepared, words: string[]): boolean {
  const forms = words
    .map((w) => squash(fold(w)))
    .filter((w) => w !== "")
    .sort((a, b) => b.length - a.length);
  let rest = p.squashed;
  for (;;) {
    const hit = forms.find((w) => rest.startsWith(w));
    if (hit === undefined) break;
    rest = rest.slice(hit.length);
  }
  return rest === "";
}

/** 否定を先に見る。否定が無く、文の頭が肯定の語なら、残りが無ければ yes・あれば yesMore。それ以外は unknown */
export function judgeYesNo(text: string, yesWords: string[], noWords: string[]): YesNo {
  const p = prepare(text);
  const clean = (words: string[]) => words.map((w) => fold(w).trim()).filter((w) => w !== "");
  if (clean(noWords).some((w) => matchesAnywhere(p, w))) return "no";
  const yes = clean(yesWords);
  if (yes.some((w) => matchesAtStart(p, w))) return onlyYesWords(p, yes) ? "yes" : "yesMore";
  return "unknown";
}
