# 色トークン SSOT 完成エビデンス

> 目的: frontend の色がSSOT化された事実と、再発を止める仕組みの実在を、実測で証跡化する。
> 基準SHA: origin/main 36de75eaa8051e22af22ee12f60f0dfe9c75d665（2026-07-14 測定）
> 測定方法: 実装者(shingo-cc)がターミナルで実行した grep/awk の生出力に基づく。設計パートナーはrepoを読まず、実測値のみで判断。

## 1. 命題
- 命題1: frontend の色は全てSSOT化されている（正引き・逆引きで証明）。
- 命題2: 今後も定着・継続させる仕組みが実在・稼働している。

## 2. 命題1のエビデンス（SSOT化）
### 2-1. 逆引き（使用→定義）: 画面の色はトークン経由か
- CSSプロパティへの生hex直書き（index/tokens除外・コメント除外): 0 件
- 生rgb/rgba直書き（コメント除外): 0 件
- → 画面で使う色は全て var(--*) 経由。直書きゼロ。

### 2-2. 正引き（定義→使用）: 定義した色は使われているか
- 真の孤児トークン（var参照0 かつ 名前文字列出現0）: 0 件
- → 辞書に未使用のゴミなし。

### 2-3. 重複（同色複数名）の解消
- 役割が同一で同色の「悪い重複」: 0 組
  - 主要な悪い重複（--accent と同色だった --indicator / --sidebar-item-active-color / --sidebar-item-active-border）は別名化で解消済み（PR #2914）。
- 同色だが役割が異なるため独立保持したトークン（下記3節）: これはSSOT違反ではない。値の正はそれぞれ1つ。

## 3. 役割違いで独立保持したトークン（意図的・重複ではない）
| 色値 | トークン | 独立の理由 |
|---|---|---|
| #ffffff | --bg-surface / --on-accent / --spinner-on-accent-head 等 | 「面の背景」と「前景（アクセント上の文字/アイコン）」で役割が真逆。統合するとアクセント変更時に前景が消える |
| #ebeff8 | --sidebar-item-hover-bg / --sidebar-item-active-bg | 「ホバー」と「選択中」。将来別濃度に分けたい典型のため独立維持 |
| セマンティック各色 | --danger と --danger-text 等 | 「塗り」と「文字」で役割が別 |

## 4. 命題2のエビデンス（継続の仕組み）
- 機械の関所: .github/workflows/design-token-guard.yml が frontend/src/** のPRで発火。本体 scripts/check-design-token-ratchet.sh が「hex本数が前より増えたらブロック」= 新規の色直書きを機械的に阻止。
- 人間の関所: scripts/check-process-artifacts.js が frontend/src 変更に GO記録（PO承認）必須を課す。実績: PR #2895 が本関所で要GO判定され、GO後にマージ。
- → 「機械（増加ブロック）＋人間（承認）」の二重関所が実在・稼働。

## 5. 結論
基準SHA 36de75ea 時点で、frontend の色は「直書き0・孤児0・悪い重複0」を実測で確認。再発防止の二重関所も稼働。色トークンのSSOT化は完成状態にある。
残課題（本エビデンスの対象外・別テーマ）: px寸法のハードコード撲滅。

## 6. 再測定の手順（将来この文書を検証する人へ）
- 逆引き: `grep -rInE "(color|background|border|fill|box-shadow|outline|stroke)[^;{}]*#[0-9a-fA-F]{3,6}" frontend/src --include=*.css | grep -vE "frontend/src/(index|tokens)\\.css:" | grep -vE "/\\*|\\*/|//"` が 0 行。
- 正引き（孤児）: 各 --token について var(--token) 参照数と名前文字列出現が共に0のものが無いこと。
- 関所: design-token-guard.yml と check-design-token-ratchet.sh が存在すること。
