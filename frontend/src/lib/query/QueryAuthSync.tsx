/**
 * ADR-1054: 利用者が変わったら（ログアウトを含む）写しを全部消す。画面は描かない。
 * user の変化は、Firebase の onAuthStateChanged・自社ログインの subscribeSession・
 * api.ts の 401 → expireSession の 3 つの道すべてから AuthContext の user に届く。
 * 画面の部品が取りに行く（描いた後の useEffect）より先に消すため、useLayoutEffect を使う。
 */
import { useLayoutEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../contexts/AuthContext";

export function QueryAuthSync(): null {
  const { user } = useAuth();
  const uid = user?.uid ?? null;
  const queryClient = useQueryClient();
  const previousUid = useRef(uid);

  useLayoutEffect(() => {
    if (previousUid.current === uid) return;
    previousUid.current = uid;
    // clear() だけでは開いている画面に知らせないので、取り消し → 写しを初めに戻す → 消す の順にする。
    // resetQueries() は開いている写しをその場で取り直す（前の人の key で通信が出る）ので使わず、
    // 各写しの reset() で開いている画面に知らせるだけにする。
    void queryClient.cancelQueries();
    queryClient.getQueryCache().getAll().forEach((query) => query.reset());
    queryClient.clear();
    queryClient.getMutationCache().clear();
  }, [uid, queryClient]);

  return null;
}
