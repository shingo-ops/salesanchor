# ADR-116: main デプロイ成功スタンプ

## ステータス
採択（提案日: 2026-06-11）

## 文脈（なぜ）
- `active-work.md` は develop マージ日（PR#列）を記録するが、**本番（main）デプロイ日は空白**だった。
- 「このブランチはいつ本番に出たか」を追跡できないため、障害対応・リリースノート作成に時間がかかっていた。
- ADR-114（develop 自動 DONE スタンプ）の設計を踏襲し、本番側にも同様の記録機構が必要と判断した。

## 決定（何を）
1. `active-work.md` に `main` 列を追加（7列目）し、本番デプロイ成功日（`YYYY-MM-DD`）を記録する。
2. `.github/workflows/deploy.yml` の smoke/health 200 通過後に「Stamp main deploy date」ステップを追加する。
3. スタンプ対象: `DONE` 状態かつ `main` 列が空の行。冪等設計（再デプロイで二重打ちしない）。
4. スタンプ失敗はデプロイをブロックしない（`continue-on-error: true`）。
5. `PIPELINE_PAT` で develop ブランチへ自動プッシュバックする。
6. `scripts/check-active-work-format.sh` の `EXPECTED_COLS` を 6→7 に更新し CI でスキーマ整合性を担保する。

## 理由
- `success()` 条件を使うことで、ロールバック（Finalize が exit 1）時はスタンプされない。
- `continue-on-error: true` で PAT 期限切れ等の一時障害がデプロイ全体を止めない。
- develop ブランチへのプッシュバックは ADR-114 と同じパターンを踏襲。

## 影響
- `active-work.md` の全行を 6列→7列へマイグレーションが必要（本 PR で実施済み）。
- 新規ワークツリー作成スクリプト（`new-worktree.sh`）も 7列テンプレートに更新。
- `PIPELINE_PAT` シークレットが未設定の場合はスタンプのみ失敗（デプロイ本体は継続）。
