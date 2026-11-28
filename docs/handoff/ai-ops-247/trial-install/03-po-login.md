# 03 PO が手で行うログインの順番（段取り 4）

正の設計: `server-agent-design.md` §12-3 段取り 4。やさしい言葉で書いています。

## 先に守ること

- この段で、担当（ops-agent の Claude）に**仕事を頼まない**。話しかけるのは、ペアにするための確かめだけです。
- ボットの鍵・ログインの札の**値を AI に見せない**。チャットにも文書にも貼らない。打つのは PO の手だけ。
- 管理者が窓（ターミナル）を開いてくれます。PO はその窓で打ちます。
- この段は **G7（つなぐ先の制限）を付けません**（ログインの通り道を塞ぐ恐れがあるため・設計 §12-3 段取り 4）。そのかわり、道具の制限（G4）は 01 で入っているので、担当は Bash を使えず、監視の 19100 番などへも届きません。

## 順番

### A. Discord でボットを作る（PO の手・ブラウザ）

1. https://discord.com/developers/applications で **New Application** を押し、名前を付けます。
2. **Bot** の欄でユーザー名を作り、**Reset Token** を押してボットの鍵（トークン）を出します。**ここで見える値は、だれにも見せず、この後の手順 D-2 の見えない入力だけに使います。**
3. 同じ Bot の設定の **Privileged Gateway Intents** で **Message Content Intent** を ON にします。
4. **OAuth2 > URL Generator** で `bot` を選び、次の権限だけ ON にします: View Channels・Send Messages・Send Messages in Threads・Create Public Threads・Read Message History・Attach Files・Add Reactions。
5. 同じ Bot の設定で **Public Bot を切ります**（自分だけが入れられるようにする）。
6. Discord の **設定 → 詳細設定 → 開発者モード** を入れ、自分のアイコンを右クリックして **「ユーザーIDをコピー」** で番号を控えます（手順 D-2 で使う。値はどこにも書かない）。
7. できた URL を開き、自分のサーバーにボットを入れます。

（出どころ: https://code.claude.com/docs/en/channels の Discord の手順）

### B. 管理者が上限付きの窓を開く

管理者が、prod2 で次の 1 行を打ちます（G2・G8 の上限付き・G7 なし。`02-install.sh` と同じ形）。

```
sudo systemd-run --uid=ops-agent --pty --wait --collect --working-directory=/home/ops-agent/work -p MemoryHigh=1200M -p MemoryMax=1500M -p MemorySwapMax=0 -p OOMScoreAdjust=1000 -p ProtectSystem=strict -p ReadWritePaths=/home/ops-agent -p "InaccessiblePaths=/home/ubuntu /root /opt/salesanchor-monitoring" -p PrivateTmp=yes -p NoNewPrivileges=yes -E HOME=/home/ops-agent -E PATH=/home/ops-agent/.local/bin:/home/ops-agent/.bun/bin:/usr/local/bin:/usr/bin:/bin /bin/bash
```

開いた窓は ops-agent として動いています。窓を閉じれば、その上限付きの場所も消えます。

### C. サブスクでログインする（PO の手）

1. 窓で `claude` と打って開きます。
2. 画面の案内どおりにブラウザでログインします（claude.ai のサブスク）。ログインの札は画面に出ても、どこにも写さない・貼らない。
3. 画面の確認が出たら、内容を読んで答えます。作業の場所を信頼するか聞かれたら「はい」を選びます。

### D. Discord の道具を入れて鍵を置く（PO の手）

`/discord:configure` と `/discord:access` は**使いません**。理由: 中で Write の道具を使うため 01 の制限（G4）で止まり、鍵も会話の記録に残るため。鍵は管理者の台本 03b で、窓の外から置きます。

1. B の窓のシェル（`claude` の外）で次を打ちます:
   `claude plugin install discord --marketplace anthropics/claude-plugins-official -s user`
2. 窓を閉じます。PO 本人が自分の端末で `sudo bash 03b-put-discord-keys.sh` を流し、見えない入力に**ボットの鍵（手順 A-2）と自分の利用者番号（手順 A-6）**を貼ります。画面の共有と端末の記録（録画・ログ）は切っておきます。
3. ここではペア（合言葉）も、許可名簿を切り替える命令も要りません（名簿は 03b で allowlist に置きました）。

### E. 終わらせる

1. 窓の `claude` を閉じ、窓を閉じます。
2. 管理者に「終わった」と伝えます。次は管理者が `04-check-and-start.sh` を流します。

## 止まったとき（未確認の点）

- 画面が止まって見えるときの読み方（読むだけ）: `sudo -u ops-agent tmux -S /home/ops-agent/.tmux/ops-agent.sock capture-pane -p -t ops-agent`

- **D の `claude plugin install` が失敗した場合**: 画面の言葉をそのまま設計担当（Opus）へ伝えます。**自分で `settings.json` をゆるめたり直したりしないでください。**
- `claude` のログインが通らない／Discord の道具が動かない場合も、同じく止めて報告します。G7 を付けて試すのは、設計担当の指示があってからです。
- どの場合も、鍵・札の値は報告に書きません。
