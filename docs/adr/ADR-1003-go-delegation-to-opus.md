# ADR-1003: GO 発行を Claude Opus 設計担当へ常時委譲する（例外あり）

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 決定日 | 2026-09-29 |
| 決定者 | Shingo（PO） |
| 関連 | ADR-136（GO 手順・承認フロー v2の一部を上書き） |

---

## What（何を決めたか）

GO（危険変更・ユーザー影響変更・外部API変更のマージ前承認）の発行権限を、PO（Shingo）単独から、**Claude Opus 設計担当へ常時委譲**する。ただし以下の「例外」に該当する変更は、常時委譲の対象外とし、従来どおり PO 本人の GO が必須のままとする。

- 委譲の GO を PR 本文の `### GO記録` に記録する場合、`GO発行者` は「POの委任に基づくClaude Opus発行」と記載する
- `scripts/check-process-artifacts.js` の `AUTHORIZED_GO_ISSUERS` にこの発行者名を追加する

## Why（なぜ変えるか）

PO 本人しか GO を出せない従来の運用（ADR-136 §承認フロー v2 ④）では、GO とマージのたびに作業が PO の応答待ちで止まっていた。PO は 2026-09-28「マージもあなたの役割である、GOは私の承認必須だがGO許可したのでマージデプロイまではあなたの管轄である」と発言し、続けて 2026-09-29「GO発行もあなたに権限委譲したいのでルールを変更してくれ、元のルールから変更して次のセッションからキャッチアップできるようにしてくれ」と明示的に委譲を決定した。委譲の形として「常時委譲＋例外あり」を PO 自身が選択した（2026-09-29）。

## 委譲の条件（すべて満たすこと）

委譲による GO（発行者「POの委任に基づくClaude Opus発行」）を出せるのは、次のすべてを満たす場合に限る。

1. 必須の CI がすべて通る
2. Reviewer エージェントが APPROVE している
3. PO に3行まとめ（対象・変更内容・バックアップ確認）を報告済み

## 例外（PO 本人の GO が必要）

以下に該当する変更は、Claude Opus への常時委譲の対象外とし、**PO 本人の GO（`GO発行者` が `shingo-ops` または `Shingo`）が必須**のままとする。

- DROP TABLE / DROP COLUMN を含む migration
- 大量 DELETE
- secrets の変更
- Ruleset・Branch Protection の変更
- `.github/workflows/workflow-lint.yml` の変更
- 外部 GUI（Cloudflare・Firebase 等）の操作
- main / develop への force push

`scripts/check-process-artifacts.js` は、変更ファイルがこれらの例外パス（`.github/workflows/workflow-lint.yml`）に該当する場合、または migration ファイルの追加行に `DROP TABLE` / `DROP COLUMN` を含む場合、`GO発行者` が委譲名義（「POの委任に基づくClaude Opus発行」）であれば fail させる。既存の `DANGEROUS_PATTERNS`（危険パス判定）と同じ regex 方式で判定する。

大量 DELETE・secrets 変更・Ruleset/Branch Protection 変更・外部 GUI 操作・force push は、現状 `check-process-artifacts.js` が機械検証できる対象ではない（ファイル diff だけでは判定不能、または GitHub API / 外部操作を伴う）。これらは CLAUDE.md「不可逆操作は必ず PO 確認」の運用（`permit-danger.sh` 等）で従来どおり人手で担保する。

## 委譲の解除

PO が「委譲停止」と発言した時点で、常時委譲は終了する。停止したことは `docs/handoff/go-record-transcription/opus-delegation.md` に記録する。解除後は ADR-136 の元のルール（GO 権限は PO 単独）に戻る。

## Supersedes（上書き範囲）

ADR-136 §承認フロー v2 の「④ GO 権限は PO（Shingo）単独」の部分のみを上書きする。承認フロー v2 のそれ以外の手順（チャットで3行サマリを提示 → GO受領 → PR本文へ転記 → gate が機械検証）はそのまま維持する。

## 弊害・トレードオフ

- 委譲により、PO の確認なしにマージが進む範囲が広がる。上記「例外」の範囲設定と、CI緑＋Reviewer APPROVE＋3行報告の3条件で歯止めをかける
- 委譲名義の GO 記録は、機械検証（`AUTHORIZED_GO_ISSUERS` allowlist）のみで本人性を証明しない。誤用・濫用のリスクは PO の「委譲停止」発言でいつでも解除できることと、ADR-1002 の振り返り運用（governance監査）で軽減する

## 外部・過去事例

該当なし＋理由: この委譲は自社の PO-Dev 間の承認運用設計であり、外部事例よりも自社の GO 記録運用実績（ADR-136 §承認フロー v2 の実装・運用実績）を優先する。

## 維持の仕組み

- 守り手: `scripts/check-process-artifacts.js`（`AUTHORIZED_GO_ISSUERS` の allowlist 検証・例外パスの fail 判定）
- 委譲の状態記録: `docs/handoff/go-record-transcription/opus-delegation.md`（開始・範囲・解除の記録）
