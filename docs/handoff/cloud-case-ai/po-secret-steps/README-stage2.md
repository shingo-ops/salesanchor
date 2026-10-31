# 段2: PO の秘密の置き方（台本 2 本・ADR-1052 段2 / stage2-card.md §4）

どちらも PO が Mac で `bash` で実行する（secrets 変更のため PO 本人の操作）。値は画面・引数・記録に出ない作り。段1の台本（a-github-token.sh・b-db-password.sh）とは別物で、段1の鍵・env には触らない。

## 順番

1. **C** `bash c-admin-token.sh`
   - CASE_ADMIN_TOKEN（管理の口の鍵）を作り、GitHub secret と Mac の Keychain（service=salesanchor-case-admin-token）に置く。既にあれば止まる（上書きしない）。
   - 書き込む前に、段1の相談係の鍵の控え（Keychain salesanchor-case-agent-token）と違う値かを比べる。控えが読めない・同じ値なら何も書かずに止まる。
2. **D** `bash d-unmask-db-password.sh`
   - VPS の上で ai_unmask のパスワードを作り、`/home/ubuntu/.config/salesanchor/ai-unmask.env`（権限 600・1 行 `AI_UNMASK_DATABASE_URL=...`）に置く。新しい env が既にあれば止まる。ai_unmask のロールが想定の属性でなければパスワードを設定する前に止まる。
3. **デプロイ**: 次に本線（main）に何かが入ったときのデプロイで、.env に CASE_ADMIN_TOKEN が書かれ、ai-unmask-http が起きる（deploy.yml:380・:639-653）。
4. **確かめ**: C・D の ○/× がすべて ○。デプロイ後は stage2-card.md §5 の受入。

## 途中で止まったとき（段1の README のコマンドは使わない。相談係の鍵を消してしまう）

- C で GitHub secret が ○・Keychain が × のとき: `gh secret delete CASE_ADMIN_TOKEN -R shingo-ops/salesanchor` で消してから C を流し直す。
- C で GitHub secret が × のとき: そのまま C を流し直してよい（Keychain が ○ なら先に `security delete-generic-password -s salesanchor-case-admin-token`）。
- D で「失敗: 「2b. ...」」のとき: DB には何もしていない。ロールの作りを Opus が調べる。
- D で「失敗: 「4. ...」」「失敗: 「5. ...」」のとき: 新しい env が無ければ、そのまま D を流し直してよい（パスワードは作り直される）。
- D で「失敗: 「6. 確かめ」」のとき: 新しい env はもう在る。下の戻し方で env を消してから D をやり直す。

## 戻し方

- GitHub secret: `gh secret delete CASE_ADMIN_TOKEN -R shingo-ops/salesanchor`（管理の口が全員 401 に戻る）
- Keychain: `security delete-generic-password -s salesanchor-case-admin-token`
- VPS: `/home/ubuntu/.config/salesanchor/ai-unmask.env` を消し、DB で `ALTER ROLE ai_unmask PASSWORD NULL`（止め続けるなら `ALTER ROLE ai_unmask NOLOGIN`。stage2-card.md §6）
