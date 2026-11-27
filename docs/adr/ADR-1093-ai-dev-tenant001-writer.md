# ADR-1093: AI 用「試験用テナント（tenant_001）だけに書き込める道」— 本物のお客さまの行には DB の権限で届かない書き込み専用の鍵を作る

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（2026-11-27。設計審査中。実装未着手） |
| 備考 | PO の決定（2026-11-27 チャット）: 「テナント001は開発で使用するテストアカウントなのでdevのテナントである。そのためdev環境では自由に動作させて良いようにしたい」、専用の鍵で進める「1」、つながっている 4 つのサービスは試験用「1」、成功条件の見分け方「1」 |
| 起案日 | 2026-11-27 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1024（読むだけの道。本 ADR はその型を書き込みに広げる）、ADR-1037（ロック待ち 1 秒）、ADR-025（秘密の列の手動投入は常時厳禁）、ADR-135/136（危険パスの GO）、ADR-113（設計持ち込みの様式） |
| 設計・根拠 | [design.md](../handoff/dev-tenant001-writer/design.md)、[recon.md](../handoff/dev-tenant001-writer/recon.md)、[review-architect-1.md](../handoff/dev-tenant001-writer/review-architect-1.md)、[review-architect-2.md](../handoff/dev-tenant001-writer/review-architect-2.md)、[review-architect-3.md](../handoff/dev-tenant001-writer/review-architect-3.md) |

---

## Context（なぜ必要か）

tenant_001（テスト株式会社）は開発・点検に使う試験用のテナント（ADR-1001:136・ADR-1051:19・ADR-1085:16）。それでも本番 DB の中にあるため、試験の行を足す・直すたびに PO の `!` 実行か使い捨て許可が要り、作業が止まる。

今ある AI の道は読むだけ（ADR-1024）。書き込みは何でもできる鍵しかなく、本物のお客さま（tenant_004）の行にも届いてしまう。

事実の根拠は [recon.md](../handoff/dev-tenant001-writer/recon.md)。

## Decision（何を決めたか）

1. DB のロール `ai_dev001_writer` を migration で作る。NOSUPERUSER・NOBYPASSRLS・CONNECTION LIMIT 2・`log_statement=all`・`statement_timeout=60s`・`lock_timeout=1s`・`idle_in_transaction_session_timeout=60s`。
2. 権限は tenant_001 のスキーマの USAGE（CREATE なし）、表の行の読み書き、連番の USAGE だけ。`tenant_meta_config`（public を書き換える引き金がある）と秘密の列（ADR-1024 の拒否の型）には付けない。public には 0 から始め、試験で要ると分かった物だけを足す。
3. 専用の台本（1 文だけ・AUDIT を送れなければ rollback）、専用のコンテナ、強制コマンドと期限つきの専用の鍵。読むだけの道と同じ守り。
4. 境界は DB の権限だけ。台本の語の拒否と Mac の見張りの免除は事故よけ。
5. Mac の見張りの免除は PO 本人が入れる。

## Why（なぜこの形か）

- 書ける範囲を DB の権限で決めるので、台本や鍵に穴があっても tenant_001 の外には書けない。
- tenant_006 に手で足した読み書きのロール（qa_tenant006_rw）は記録に残らず、作り直せないと分かっている。migration で作れば作り直せる。
- 案の比べ: design.md §4。

## Consequences（結果）

- 良い点: tenant_001 への書き込みで PO が待たされる回数が 0 回になる見込み（K8 で測る）。
- 弱い点: 部品が 5 つ増える。tenant_001 に新しい表が増えたら、新しい migration を足すまで書けない。
- 成功条件: design.md §6 の K1〜K8。

## 戻し方

design.md §10（ロールの NOLOGIN → 鍵の 1 行を消す → 見張りの免除を戻す → 権限を外す migration）。
