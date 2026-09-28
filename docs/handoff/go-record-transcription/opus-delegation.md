# GO 発行の Opus 委任（ADR-1003）

**この文書は何か（専門用語なしの1行）**: PO が GO 発行権限を Claude Opus 設計担当へ委任した記録。委任の開始・範囲・例外・解除方法・記録の形式をここに集約する。

---

## 状態

**有効**（2026-09-29 開始）

## 開始（PO 発言の原文）

- 2026-09-28「マージもあなたの役割である、GOは私の承認必須だがGO許可したのでマージデプロイまではあなたの管轄である」
- 2026-09-29「GO発行もあなたに権限委譲したいのでルールを変更してくれ、元のルールから変更して次のセッションからキャッチアップできるようにしてくれ」
- 委譲の形として「常時委譲＋例外あり」を選択（2026-09-29）

対象 ADR: [ADR-1003](../../adr/ADR-1003-go-delegation-to-opus.md)

## 範囲

委譲による GO（`GO発行者: POの委任に基づくClaude Opus発行`）を出せるのは、次のすべてを満たす場合に限る。

1. 必須の CI がすべて通る
2. Reviewer エージェントが APPROVE している
3. PO に3行まとめ（対象・変更内容・バックアップ確認）を報告済み

## 例外（PO 本人の GO が必須）

- DROP TABLE / DROP COLUMN を含む migration
- 大量 DELETE
- secrets の変更
- Ruleset・Branch Protection の変更
- `.github/workflows/workflow-lint.yml` の変更
- 外部 GUI（Cloudflare・Firebase 等）の操作
- main / develop への force push

`scripts/check-process-artifacts.js` が機械検証できるのは、このうち「migration の DROP TABLE/COLUMN」と「`.github/workflows/workflow-lint.yml` の変更」のみ。それ以外（大量DELETE・secrets変更・Ruleset/Branch Protection変更・外部GUI操作・force push）は、CLAUDE.md「不可逆操作は必ずPO確認」の既存運用（`permit-danger.sh` 等）で人手により担保する。

## 解除の方法

PO が「委譲停止」と発言した時点で、常時委譲は終了する。解除の記録は本ファイルの「変更履歴」表に追記する。解除後は ADR-136 の元のルール（GO 権限は PO 単独）に戻る。

## GO を出したときの記録の形式

委譲による GO を PR 本文の `### GO記録` に記録する場合は、以下の形式を用いる。

```
### GO記録
- GO発行者: POの委任に基づくClaude Opus発行
- 委任ID: ADR-1003
- 対象PR: #<PR番号>
- HEAD: <コミットSHA>
- 変更の要約: <3行まとめの内容>
- 日時: YYYY-MM-DD HH:MM JST
- レビューと検証の根拠: <必須CI一覧の通過確認／Reviewer APPROVEの根拠>
- GO原文: GO #<PR番号>
- バックアップ確認: あり/なし/該当なし
- 結果: pass/fail
```

## 変更履歴

| 日時 | 内容 | 記録者 |
|------|------|--------|
| 2026-09-29 | 委任開始（ADR-1003 Accepted） | Claude Opus（PO承認に基づく記録） |
