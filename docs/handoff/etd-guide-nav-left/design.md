# design: ETD ガイド 左ナビ左寄せ＋テストキー注記削除

## 参照
- recon: `docs/handoff/etd-guide-nav-left/recon.md`
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 変更方針

### 変更1: 左ナビ列を左端へ

**問題**: #2546 で `.etd-guide__substep-pane` に `max-width: 900px; margin-inline: auto` を移設したため、左ナビも 900px 枠の中に入り、見出し/intro の左端と揃わない。

**方針**:
- `.etd-guide__substep-pane` から `max-width`/`margin-inline`/`width` を削除（全幅グリッドに）
- 左ナビ（160px）は自然に左端へ（見出し/intro と揃う）
- 詳細エリアに `max-width: calc(var(--max-width-setup-guide) - var(--size-substep-nav) - var(--space-4))` を追加
  → 詳細の幅上限を「900px − ナビ幅 − gap」に設定し、スクショ等が無制限に伸びるのを防ぐ

### 変更2: テストキー注記カード削除

**方針**:
- TSX の `.etd-guide__note--info` div（`fedexEtdGuideStep1SandboxNote` キー）を完全削除
- ja.json・en.json の `fedexEtdGuideStep1SandboxNote` キーを削除

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| 左ナビ（1-1/1-2…）の左端が見出しテキストの左端と揃う | ブラウザ目視: 両者の x 座標が一致 |
| 右詳細テキスト＋スクショが無制限に広がらない（最大幅制限あり） | ブラウザ目視: 詳細が calc(900px-160px-gap) 以内に収まる |
| テストキー注記カード（青帯）が表示されない | ブラウザでステップ1を表示し注記なしを確認 |
| 768px 縦積みフォールバック維持 | ブラウザ幅 768px 以下で目視 |
| `npm run lint` / `npm run build` 通過 | CI 確認 |

## 外部・過去事例の参照と我々への応用

CSS Grid で「左列を全幅の左端に固定・右列に最大幅を設定」するパターンは
コンテンツサイドバーレイアウト（Content + Sidebar）として一般的。
親の centering を外して子の detail に max-width を与える構成は
MDN CSS Grid Layout ガイドの "Auto-placement" 事例と同等。
将来 DHL/UPS 等で同じ 2ペインガイドを追加する際も同パターンを流用できる。
