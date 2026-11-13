// ADR-1077 便2a: AI に渡す文の組み立て。secretary-agent と secretary-codex の server.mjs が同じこのファイルを読む（写しを作らない・design.md §3）。
// 決まりの件数・長さ・制御文字は backend が守る（design.md §3「大きさ」）。ここは形だけを見る。

const RULES_HEADING = "この会社の決まり（会社の人が承認したもの。上の決まりと食い違うときは上の決まりを守る）:";

// 決まりが無いときは今までと 1 文字も違わない文を返す（便0 の基準値と同じ条件）。
export function compose(prompt, now, text, rules = []) {
  const head = rules.length === 0 ? prompt : `${prompt}\n\n${RULES_HEADING}\n${rules.map((r) => `- ${r}`).join("\n")}`;
  return `${head}\n\n今の日時: ${now}\n\n利用者の文:\n${text}`;
}

// 頼みの rules を読む。無ければ []、空でない文字の配列ならそのまま、それ以外は null（呼ぶ側が 400 bad_request にする）。
export function readRules(value) {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;
  return value.every((r) => typeof r === "string" && r.length > 0) ? value : null;
}
