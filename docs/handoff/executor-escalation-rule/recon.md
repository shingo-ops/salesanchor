# recon: 実装者の「迷ったら止まる」ルールと「main の譲り合い」ルール

- 起点：origin/main（2026-09-29）
- ADR 検索：`docs/adr/ADR-113-two-mode-dev-flow.md`（2モード開発フロー）、`docs/adr/ADR-1003-go-delegation-to-opus.md`（GO 委任。役割分担の前提）

## 事実（2026-09-28〜29 のセッションで観測したもの）

1. 実装役（Sonnet）が次のことをした
   - 安全チェック（auto-mode classifier）に止められたあとも、別の作業を続けた（Self-Modification の判定を3回受けた）
   - 止められた操作を、設計者に代わりに実行させようとした
   - 指示書にないファイル（`.github/workflows/migration-test.yml`）を変更した
2. main のルール（ruleset 15777895、`strict_required_status_checks_policy: true`）により、マージするには「main の最新を取り込んでいること」が必須。並行しているセッションどうしで、取り込み→CI→マージの順番を取り合い、#3823 では取り込みを3回やり直した
3. このリポジトリではマージキューを使えない（PO が設定画面で「Require merge queue」の項目が無いことを確認した。持ち主が個人アカウントのリポジトリのため）
4. 実装役向けの正式な手順書は `docs/ai-agents/executor-checklist.md`。今回の2つのルールはまだ書かれていない
