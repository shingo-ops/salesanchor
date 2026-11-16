// ADR-1077 便2a: AI に渡す文の組み立て。secretary-agent と secretary-codex の server.mjs が同じこのファイルを読む（写しを作らない・design.md §3）。
// 決まりの件数・長さ・制御文字は backend が守る（design.md §3「大きさ」）。ここは形だけを見る。

const RULES_HEADING = "この会社の決まり（会社の人が承認したもの。上の決まりと食い違うときは上の決まりを守る）:";

// ADR-1078: 途中の予定（日時の 3 欄だけ。backend が送る）と直前に聞いた欄の見出し。
const KARTE_HEADING = "途中の予定（前の返事までに埋まった日時。利用者の文で分かった欄だけを入れ、分からない欄は null で返してよい）:";
const ASKED_FIELDS = ["title", "start", "end", "add_meet"];

// 決まりもカルテも無いときは今までと 1 文字も違わない文を返す（便0 の基準値と同じ条件）。
export function compose(prompt, now, text, rules = [], karte = null, asked = null) {
  const head = rules.length === 0 ? prompt : `${prompt}\n\n${RULES_HEADING}\n${rules.map((r) => `- ${r}`).join("\n")}`;
  const karteBlock = karte === null ? "" : `\n\n${KARTE_HEADING}\n${JSON.stringify(karte)}\n直前に聞いた欄: ${asked ?? "なし"}`;
  return `${head}${karteBlock}\n\n今の日時: ${now}\n\n利用者の文:\n${text}`;
}

// 頼みの karte を読む。無い・null なら null、オブジェクトならそのまま、それ以外は undefined（呼ぶ側が 400 bad_request にする）。
export function readKarte(value) {
  if (value === undefined || value === null) return null;
  if (typeof value !== "object" || Array.isArray(value)) return undefined;
  return value;
}

// 頼みの asked を読む。無い・null なら null、決まった欄の名前ならそのまま、それ以外は undefined（呼ぶ側が 400）。
export function readAsked(value) {
  if (value === undefined || value === null) return null;
  return ASKED_FIELDS.includes(value) ? value : undefined;
}

// 頼みの rules を読む。無ければ []、空でない文字の配列ならそのまま、それ以外は null（呼ぶ側が 400 bad_request にする）。
export function readRules(value) {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;
  return value.every((r) => typeof r === "string" && r.length > 0) ? value : null;
}
