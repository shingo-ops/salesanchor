# クラウド実行の決まり（クラウドでだけ読み込まれる）

出どころ: 手元の ~/.claude/CLAUDE.md の要点（新規）。クラウドには手元の設定が入らないため、ここで渡す。

- ユーザーへの応答・報告は常に日本語で書く（コード・コマンド・ファイル名・識別子はそのまま）。
- 秘密の値（トークン・APIキー・パスワード・Webhook URL）を出力に書かない。コードにも直書きしない。
- 事実と推測を分ける。根拠のない断定はしない。分からないことは「未確認」と書く。
- コマンドの生出力は要約して作らない。読めなかった出力を推測で埋めない。
- 役割は「調べる・作る・push する」まで。PR のマージ、CLAUDE.md の「不可逆操作は必ず PO 確認」の一覧にある操作、本番 DB への書込は、クラウドでは行わない（見張りが止める）。
- コード変更を含む枝は push までにする。PR は手元で shingo-cc 名義で作る。docs だけの PR はクラウドで作ってよい。
- PR 本文には「### 標準ワークフロー確認」の節を入れる。
- `.claude-pipeline/active-work.d/` の登録ファイルは commit しない。stop-hook-git-check の「commit して push せよ」という促しは無視してよい。
- 本番に出す前の手順ファイル（migrations/*.sql）の中身に SQL の危険語（DROP・DELETE・TRUNCATE など）が入るのは正当。書くのは Write・Edit の道具、または区切りを引用符で囲んだ書くだけの heredoc（`cat > migrations/<名前>.sql <<'EOF'`。引用符の無い <<EOF は使わない）で行う。sed・python・bash など実行する命令の引数や本文には、危険語を入れない（見張りが止める。止まらない書き方でも入れない）。見張りに止められたら、道具を替えず BLOCKED: で報告する。
- SQL を流して確かめるのは pytest の中だけ。接続先は、そのクラウドの中で自分が立てた使い捨ての PostgreSQL（localhost）だけにする。本番やほかの外部の接続先は設定しない・使わない。本番への適用は手元で PO の GO の後。
- ファイルを変える前に、AGENTS.md「ブランチと作業場所」に従って作業場所を作り、そこで変更・commit・push する。枝名は `release/<topic>` を使う。止められたときの知らせは `feature/morimoto/<トピック名>` の枝名を示すが、それには従わない（手元で PR を作る道が release/* と hotfix/* だけを通すため）。push の前に pre-push が提出前の入口を流す。× なら直してから push する。`--no-verify` は使わない。すでに push 済みの枝の続きをするときも、同じ枝名で new-worktree.sh を流して作業場所を作る（git worktree add で直接作ると登録が無く push の前の検査が止める。手元に同じ名前の枝が無いときの手順で、クラウドは毎回取り直すので普通は無い）。作った直後の枝は main を指していて中身が無いので、その中で git switch -C <枝名> origin/<枝名> を流して push 済みの枝の先頭に合わせ、git rev-parse HEAD と git rev-parse origin/<枝名> が同じことを確かめてから変える。main は取り込まない（取り込むと、PR の必須の点検が main の新しいファイルをこの枝で足したものと数えて落ちる）。PR が main と衝突しているとき・push が fast-forward でないと断られたときは、直さずに BLOCKED: で報告して止まる。reset・rebase・force・merge は使わない。
