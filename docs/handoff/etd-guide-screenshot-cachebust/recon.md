# Recon: ETD ガイド step1-07 スクショ キャッシュバスティング

## 変更対象

| ファイル:行 | 内容 |
|------------|------|
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:418` | `/images/fedex-setup/step1-07-overview.png` → `-v2.png` に更新 |
| `frontend/public/images/fedex-setup/step1-07-overview-v2.png` | 旧ファイルをリネーム（内容同一） |

## 問題の背景

nginx が `cache-control: max-age=31536000, immutable` を返しており、
ファイルを更新しても既存 URL ではブラウザが強制リロードしても再取得しない。
ファイル名にバージョンを付与することで URL 自体を変え、確実に新画像を取得させる。

## 既存 ADR 確認

- ADR-027: i18n 必須（画像パス変更は対象外）
- ETD ガイド固有 ADR なし
