# design: 担当者アイコンを同一オリジンのパスで表示する

対象ADR: ADR-159
参照: docs/handoff/csp-allow-avatar-images/recon.md

## 方針
CSP も nginx も変更しない。フロントだけで、画面表示用に絶対 URL を同一オリジンのパス（/api/...）へ変換する。
Discord 用の絶対 URL（backend 出力）は変更しない。

## 変更
- frontend/src/lib/staffProfile.ts: toSameOriginAvatarUrl(url) を追加（new URL の pathname が /api/public/staff-avatars/ 始まり（定数 STAFF_AVATAR_PUBLIC_PATH）ならパスを返す。null・不正値・それ以外はそのまま）
- frontend/src/pages/account-settings/ProfileSection.tsx: AvatarUpload の imageUrl に適用
- frontend/src/lib/staffProfile.test.ts: 単体テスト追加

## 基準
|基準|検証方法|
|---|---|
|api.salesanchor.jp の絶対 URL が /api/public/staff-avatars/<token>.webp に変わる|vitest staffProfile.test.ts（11件 PASS（同ファイル全体。うち toSameOriginAvatarUrl は7件））|
|null・空・非 API URL は変化しない|同上|
|CSP 無変更で画像が表示される（img-src 'self' に合致）|デプロイ後にアカウント設定画面で目視（未確認）|
|同一オリジン経路が公開ルートに届く|recon.md の curl（404 application/json）|

## 外部・過去事例の参照と我々への応用
CSP の img-src を広げず、リバースプロキシ経由の同一オリジン配信にする方式は一般的な最小権限の対処。
別案（img-src に https://api.salesanchor.jp 追加）は nginx.conf 変更で deploy が nginx -t なしに force-recreate するため不採用。

## リスク / 戻し方
- リスク: pathname が /api/ 始まりでない将来の URL 形式では変換されず従来通り（壊れ画像の可能性）。
- 戻し方: PR を revert。

過去事例: commit 53b3cbc28 は CSP img-src に blob: を足す形で対処した。今回は同じ nginx 変更を避け、フロント変換で済ませる。

## 維持の仕組み
- toSameOriginAvatarUrl の単体テスト（staffProfile.test.ts）が CI で常時実行される。
- アプリ CSP（img-src 'self'）は変更しないため、他画像と同じ制約下で動く。
- 守り手: .github/workflows の frontend テスト（vitest）
