# 仮想マシンが要る試験を GitHub で行う（vm-test-on-gha）

この文書は何か(専門用語なしの1行): PO の Mac（メモリ 8GB）で試験用の小さなパソコン（仮想マシン）を作らず、GitHub が貸すコンピュータで試験するテーマの表紙。

## 背景（事実）
2026-10-16 22:18 JST の実測で、Mac のスワップ（メモリ不足分のディスク逃がし）6144MB 中 4880MB 使用、負荷平均 23.8（15分）。試験用の仮想マシン（colima profile `ai-ops-bin-d`、メモリ 4GB）が動いていた。消えた後の 22:33 はスワップ 1987MB（生出力 /tmp/CC報告ファイル/agent-console-slow/）。

## 境界
- 対象: これから書くカード・手順書で「Mac 上に一時的な colima profile を作って試す」ことをやめ、GitHub Actions の手動起動 workflow `sandbox-test` で試す。そのための workflow・試験置き場・規則・見張り。
- 対象外: Mac の開発用 DB（colima profile `default`。colima-idle-stop が自動停止済み）／ profile `sa-private-ci`／ 実装中の他テーマのカード（例 docs/handoff/ai-ops-247/card-stage3-bin-d.md）の書き換え／ 本番サーバー。

## ステータス
- あるべき姿: PO 発言転記済み（2026-10-16）
- KGI: PO 承認済み（2026-10-16 チャット「y」）
- 設計: 設計案作成済み・Opus 自己審査済み（同一 AI による審査）。実装未着手。

## 子文書
- [あるべき姿](./ideal-state.md)
- [KGI](./kgi.md)
- 設計: [docs/handoff/vm-test-on-gha/design.md](../../handoff/vm-test-on-gha/design.md)（recon も同じフォルダ）
