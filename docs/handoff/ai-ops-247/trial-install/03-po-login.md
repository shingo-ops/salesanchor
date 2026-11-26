# 03 PO が手で行うログインの順番（段取り 4）

正の設計: `server-agent-design.md` §12-3 段取り 4。やさしい言葉で書いています。

## 先に守ること

- この段で、担当（ops-agent の Claude）に**仕事を頼まない**。話しかけるのは、ペアにするための確かめだけです。
- ボットの鍵・ログインの札の**値を AI に見せない**。チャットにも文書にも貼らない。打つのは PO の手だけ。
- 管理者が窓（ターミナル）を開いてくれます。PO はその窓で打ちます。
- この段は **G7（つなぐ先の制限）を付けません**（ログインの通り道を塞ぐ恐れがあるため・設計 §12-3 段取り 4）。そのかわり、道具の制限（G4）は 01 で入っているので、担当は Bash を使えず、監視の 19187 番などへも届きません。

## 順番

### A. Discord でボットを作る（PO の手・ブラウザ）

1. https://discord.com/developers/applications で **New Application** を押し、名前を付けます。
2. **Bot** の欄でユーザー名を作り、**Reset Token** を押してボットの鍵（トークン）を出します。**ここで見える値は、だれにも見せず、この後の手順 D の入力だけに使います。**
3. 同じ Bot の設定の **Privileged Gateway Intents** で **Message Content Intent** を ON にします。
4. **OAuth2 > URL Generator** で `bot` を選び、次の権限だけ ON にします: View Channels・Send Messages・Send Messages in Threads・Create Public Threads・Read Message History・Attach Files・Add Reactions。
5. できた URL を開き、自分のサーバーにボットを入れます。

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
3. 画面の確認（フォルダを信頼するか等）が出たら、内容を読んで答えます。

### D. Discord の道具を入れて鍵を打つ（PO の手）

窓の `claude` の中で、順に打ちます。

1. `/plugin install discord@claude-plugins-official`（導入範囲を聞かれたら user を選ぶ）
2. 入れたあと `Run /reload-plugins to apply.` と出たら、案内に従います。
3. `/discord:configure` ＋ ボットの鍵（手順 A-2 の値）。**この 1 行を打つのは PO の手だけ。**（出どころ: 公式の手順は `/discord:configure <token>`）
4. `claude` をいったん閉じ、`claude --channels plugin:discord@claude-plugins-official` で開き直します。
5. スマホの Discord から、作ったボットに DM を送ります。ボットがペアの合言葉を返します。
6. 窓の `claude` で `/discord:access pair <合言葉>` を打ちます。
7. `/discord:access policy allowlist` を打ちます（自分のアカウントだけにする）。

### E. 終わらせる

1. 窓の `claude` を閉じ、窓を閉じます。
2. 管理者に「終わった」と伝えます。次は管理者が `04-check-and-start.sh` を流します。

## 止まったとき（未確認の点）

- **D の手順が「許可されていない」と断られた場合**: 01 で入れた道具の制限（G4）が、プラグインの設定用の命令（`/plugin install`・`/discord:configure`・`/discord:access`）まで止めた可能性があります。これは未確認です（設計 §12-7 の「G4 の設定の書き方が CLI で効くか」）。**自分で `settings.json` をゆるめたり直したりしないでください。** そこで止めて、設計担当（Opus）に画面の言葉をそのまま伝えます。
- `claude` のログインが通らない／Discord の道具が動かない場合も、同じく止めて報告します。G7 を付けて試すのは、設計担当の指示があってからです。
- どの場合も、鍵・札の値は報告に書きません。
