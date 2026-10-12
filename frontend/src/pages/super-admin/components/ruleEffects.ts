/**
 * tcg_status_master の effect・match_type の値（バックエンド backend/app/services/tcg_status_values.py と同じ値）。
 * 予約の手がかり（便PO）の行は、resolve_status_v2 ではなく v102_status_context が読む。
 */
export const EFFECT_OUTPUT = "OUTPUT";
export const EFFECT_EXCLUDE = "EXCLUDE";
export const EFFECT_HEADING = "HEADING";
export const EFFECT_DATE_AHEAD = "DATE_AHEAD";
export const EFFECT_RELEASE_AHEAD = "RELEASE_AHEAD";

export const MATCH_REGEX = "REGEX";
export const MATCH_LITERAL = "LITERAL";
export const MATCH_DEFAULT = "DEFAULT";
export const MATCH_RELEASE = "RELEASE";

export const CONTEXT_EFFECTS: readonly string[] = [EFFECT_RELEASE_AHEAD, EFFECT_DATE_AHEAD, EFFECT_HEADING];

export const isContextEffect = (effect: string): boolean => CONTEXT_EFFECTS.includes(effect);

/** 効果を選んだときの照合方法の初期値（発売日は文字の照合ではない。予約の手がかりの残りは正規表現。従来の効果は完全一致のまま） */
export const defaultMatchTypeFor = (effect: string): string => {
  if (effect === EFFECT_RELEASE_AHEAD) return MATCH_RELEASE;
  return isContextEffect(effect) ? MATCH_REGEX : MATCH_LITERAL;
};

/** 同じ canonical に効果が複数あるとき、今の効果を勝手に変えない。1つだけのときはその効果にそろえる。 */
export const effectAfterCanonicalChange = (
  options: ReadonlyArray<{ canonical: string; effect: string }>,
  canonical: string,
  currentEffect: string,
): string => {
  const effects = Array.from(new Set(options.filter((o) => o.canonical === canonical).map((o) => o.effect)));
  return effects.length === 1 ? effects[0] : currentEffect;
};
