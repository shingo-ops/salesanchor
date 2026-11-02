/**
 * ADR-1054 段 3: 編集の画面のフォームの初めの値を写しから作る（この 1 か所だけ）。
 * - 名前（key）に今の人の uid を入れる。人が変わった最初の描画では写しが無いので、フォームは空で ready は false（K5）。
 * - 人がまだ直していない時だけ、取り直した写しでフォームを作り直す。直し始めた後は作り直さない。
 */
import { useCallback, useState, type Dispatch, type SetStateAction } from "react";

import { useAuth } from "../../contexts/AuthContext";

export function useSeededForm<D, F>(
  key: string,
  data: D | undefined,
  toForm: (d: D) => F,
  empty: F,
): { form: F; setForm: Dispatch<SetStateAction<F>>; ready: boolean } {
  const { user } = useAuth();
  const fullKey = `${user?.uid ?? ""}\u0000${key}`;
  const [seed, setSeed] = useState<{ key: string; data: D; form: F; base: F } | null>(null);
  if (data !== undefined && (seed === null || seed.key !== fullKey || (data !== seed.data && seed.form === seed.base))) {
    const form = toForm(data);
    setSeed({ key: fullKey, data, form, base: form });
  }
  const setForm = useCallback(
    (next: SetStateAction<F>) =>
      setSeed((s) =>
        s === null ? s : { ...s, form: typeof next === "function" ? (next as (p: F) => F)(s.form) : next },
      ),
    [],
  );
  const ready = data !== undefined && seed !== null && seed.key === fullKey;
  return { form: seed !== null && ready ? seed.form : empty, setForm, ready };
}
