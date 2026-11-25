受領確認: card-bin0a を読んだ

# 便0-A 実装報告（手順 3 の S6 で停止）

## 流した手順

- 1（作業場所）: `bash scripts/new-worktree.sh release/ai-assistant-bin0 --claude` で `/root/worktrees/salesanchor/release-ai-assistant-bin0` を作成。起動の失敗は無視した。作った直後の枝は origin/main を指していたため、`git switch -C release/ai-assistant-bin0 origin/release/ai-assistant-bin0` で合わせ、`git log --oneline -1` = `f073a814c` が `origin/release/ai-assistant-bin0` と一致（○）。
  - 事前確認: `git rev-parse --verify origin/main` = ea800930e（○）。**`git config user.name` は `Claude`**（カードの想定は shingo-cc）。push・commit には支障が無いので続行した。PR は作らないので名義の問題は出ない。気づきとして報告する。
- 2（Docker・完成品）: `dockerd` 起動、`docker info` 通過。digest 固定で pull 成功。`hermes --version` = `Hermes Agent v0.23.4`（○）。
- 3（ソース確かめ）: S1・S2・S3・S6・S11 を読んだ。結果は `probe-a-20261125.md` 表 1。S4・S5・S7〜S10・S12 は S6 で止まったため未読（未確認）。
- 4〜7: 流していない。道具のファイル・本物の確かめ・pytest・仕上げの commit は無い。

## 止まった理由（S6・カードの「合わなかったら止まる」）

- カード S6 と design.md §5 は、会話を消す道として「mutation-snapshot → DELETE（409 session_busy・409 unknown_execution）」が部屋の名指しの道（`/p/<部屋名>/` と部屋ごとの鍵）で通ることを前提にしている。
- 完成品の中の実際:
  - `GET /api/sessions/{id}/mutation-snapshot` は `hermes_cli/web_routers/sessions.py:640`。そのルーターは管理画面の app（`hermes_cli/web_server.py:850`）に載る。API の口の道の表（`gateway/platforms/api_server.py:1569-1601`）には無い。つまり API の口（8642）の `/p/<部屋名>/` では通らない見込み（実機の確認は手順 5 の P5 で行う予定だったが、止まったため未実施）。
  - API の口にある消す道は `DELETE /api/sessions/{session_id}`（`api_server.py:1581`・処理 `:2683-2717`）。使用中の断りは 409 だが code は `session_active_turn`（`:2704`）。`session_busy` と `unknown_execution` は API の口のソースに 0 件。
  - `X-Hermes-Session-Id` を読むのは `api_server_openai_routes.py:901`（○）。
- 設計の前提（消す前の確かめ→消す・409 の 2 種の扱い）が API の口では成り立たない。消す前の確かめを管理画面に頼ると、ダッシュボードを動かす必要が出るかもしれない（design.md §5 は「通らなければ止めて考え直す」）。

## 必要な判断（PO・設計役）

1. 消す道を `DELETE /api/sessions/{id}` だけに替える（使用中は 409 `session_active_turn` を待ってやり直す）形で台本と設計を直すか。
2. 管理画面の app も動かして snapshot を使うか（容器のメモリ・守りに影響）。
3. 上記が決まれば、便0-A を S4・S5・S7〜S10・S12 の確かめと手順 4 以降から再開できる。

## 止められた命令・見張りの文面

なし。

## K3 で迷った件

手順 4 に進んでいないので、なし。

## 後片付け

試しの容器（`bin0-src`）は止めて消す。

NEEDS_DECISION: S6 が API の口で合わない（mutation-snapshot は管理画面側のみ・API の口の消す道 DELETE /api/sessions/{id} の使用中は session_active_turn）。消す道の設計の判断が要る
