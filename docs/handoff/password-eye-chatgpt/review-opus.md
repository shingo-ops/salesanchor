# review-opus: パスワード欄の目の印を見本に合わせる

## 1回目（2026-10-30・Opus 審査役・HEAD 5dfabaecf876cc741bc62a8f11d286de40e5c59c）
- VERDICT: REVISE
- HIGH H-1: recon.md・design.md・login-round-inputs/design.md §6.2 の追記が未 commit → 中身を変えずに commit して対処
- MEDIUM: なし
- LOW（受け入れ・この PR では直さない）:
  - L-1 受入の実測は /login だけ。再設定画面は計算で収まる（PC 欄 約38.6px にボタン 28px、767px 以下は欄 min-height 44px とボタン 44px）
  - L-2 再設定画面の狭い幅で押したときの背景の角が約1.6px 外に出る（変更前 約4px より小さい。§6.2 で受け入れ済みの範囲）
  - L-3 PasswordField.css:1・PasswordField.tsx:2 の注記が旧設計だけを指す（任意）
  - L-4 §6.2 本文の Button.css 行番号のずれ（既存・範囲外）
- 確認済み: 数値計算と CSS の一致、生の px の追加なし（check:all 0）、詳細度 (0,3,0) が login variant・lg に勝つ、使っている画面3か所、実測が受入条件を満たす

## 2回目
（commit 後の HEAD で再審査。結果は PR に記録）
