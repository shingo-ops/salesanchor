branch: release/drawer-inert-when-closed

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| release/drawer-inert-when-closed | 閉じているパネル（Drawer・Sheet）を「無い物」として扱い、Tab の通り道と読み上げから外す（宿題 D5） | 2026-10-27 00:21 | DONE | 4805 | | A区分（操作の変更・見た目は不変・CSS は1行も触らない）。便5 審査 D5 の宿題。閉じていても中身を描く作り（Drawer.css:39 は横へずらすだけ）なので、閲覧ページのスマホでは閉じたシリーズ一覧 約44要素が Tab の通り道に残る。Modal は閉じると DOM から消えるので対象外。便7 の useFocusTrap.ts に `useInertWhenClosed` を足す形（E5 の罠を避けるため ready 引数を取る）。E1・E5・E6・E7 と D2（メルカリの表示サイズ感）は別便 |
