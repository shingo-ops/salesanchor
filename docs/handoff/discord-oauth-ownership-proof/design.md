# design: Discord 連携の戻り口で、サーバーの持ち主を Discord に確かめてから保存する（G3）

- 状態: 設計案作成済み・設計審査済み（2回目 APPROVE・推奨4件反映）。実装は未着手
- 基準: origin/main 5574bf327
- 根拠: docs/handoff/discord-oauth-ownership-proof/recon.md（以下 recon）
- 前の設計: docs/handoff/cross-tenant-user-ref-guard/design.md 1・7・8 節（G3 を次の作業に積んだ）
- 関係する ADR: ADR-091（ボットの招待の流れ）・ADR-075（秘密は GitHub Secrets だけ）・ADR-072（commit 後の reset_tenant_context）・ADR-146（共通ボット1台）・ADR-135/136（deploy.yml を含む PR の GO）・ADR-1003（委任の GO と例外: secrets の変更は PO 本人）

## 0. PO の言葉（原文）

- 2026-11-06 Opus の選択肢「1. 次の作業の設計を始める【おすすめ】」への回答「1」
- 2026-11-07 KGI 案（K1〜K4）への選択肢「1. この4つで進める【おすすめ】」への回答「1」
- 常設の条件「推測は禁止して事実確認を怠らずに確実性を重視して…配線とDBのSSOTは遵守してデータを分散させることは禁止。…分からないことは聞いてくれ。確立したなら進める。」

## 1. 目的と、利用者に見える変化

- 目的: 連携ボタンの戻り口で、Discord が「このサーバーにボットを入れた」と答えたサーバーだけを保存する。Discord を通らずに戻り口を開いて任意の番号を登録する道（recon 1 の結論）を閉じる
- 利用者に見える変化:
  - 普段どおり Discord の画面でサーバーを選んでボットを入れれば、今までどおり「接続済み」になる（顧客用・自社用とも）
  - Discord を通らずに戻り口を開いた場合・Discord の答えと番号が違う場合は、保存されず、画面に失敗が出る
  - 本番に秘密の鍵が入っていない間は、連携ボタンを押すと「一時的に開始できません」が出る（Discord へは進まない）

## 2. 成功条件（KGI・PO 承認 2026-11-07「1」）

| # | 成功条件 | 今 | 目標 | 判定 |
|---|---|---|---|---|
| K1 | Discord を通らずに戻り口を開いて番号を送ったときに保存される行 | ある（recon 1） | 0 | 自動試験: code なし・Discord が拒否する code・Discord の答えと URL の番号が違う、の3通りで行が増えない／変わらない |
| K2 | Discord の画面でボットを入れたときにつながる | つながる | つながる | 反映後、PO がテナント001で顧客用・自社用を解除→再接続し「接続済み」が出る |
| K3 | 保存される番号が Discord の答えの番号だけ | URL の番号 | Discord の答え | 自動試験（保存値＝交換の応答の guild.id）＋反映後の本番の新しい行の guild_id が、PO が選んだサーバーの番号と一致 |
| K4 | 秘密の鍵の値が出る所（画面・記録・アプリのログ・コード） | — | 0 | `git grep` で値が無い（10 節）・試験でアプリのログ・転送先 URL・応答に鍵が出ない。あわせて code・access_token もアプリのログに出さない |

## 3. 対象と対象外

対象:
- backend/app/routers/discord_oauth.py（開始口の前提の確かめ・戻り口の code の交換）
- docker-compose.yml の backend の環境変数に DISCORD_CLIENT_SECRET を1行
- .github/workflows/deploy.yml の .env 書き込みに DISCORD_CLIENT_SECRET を2行（消す sed と heredoc）
- backend/app/main.py の起動時の警告に DISCORD_CLIENT_SECRET を足す
- backend/tests/test_discord_oauth.py の戻り口の試験の書き換えと追加。開始口の今の試験 :190・:219・:246 には試験用の鍵の環境変数を入れる（4-2 で鍵が無いと 503 になるため）
- docs/adr/ADR-091 に追記（戻り口は code を交換し、応答の guild だけを使う）＋ `node scripts/generate-adr-index.js`

対象外（理由つき）:
- 画面（frontend）: 新しい失敗の理由は、今ある受け取り（recon 5）で「接続に失敗しました（理由: …）」（顧客用）／「接続に失敗しました」の文（自社用）として出る。文言の追加は別作業
- 招待の scope の変更: 今の scope で code が付くと ADR-091 に記録がある（recon 2・8 U1）。付かなかったときの手当ては 6 節
- 既存の4行の点検（recon 8 U2）: ボットの鍵が要る。別作業として台帳に積む（8 節）
- access_token の取り消し: 保存も記録もしないで捨てる。取り消しの呼び出しは足さない（scope は bot と applications.commands だけで、利用者の情報は読めない）

## 4. 変更前と変更後

### 4-1. 秘密の鍵の読み方（discord_oauth.py・新規）

変更前: :51 に client id だけ。

変更後（:51 の下に足す）:
```python
_DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"


def _client_secret() -> str:
    # 値はログ・応答・転送先 URL に出さない（K4）
    return os.getenv("DISCORD_CLIENT_SECRET", "")
```
モジュール読み込み時に固定しない（試験で環境変数を差し替えられるように、呼ぶたびに読む）。

### 4-2. 開始口（:133 の前に足す）

```python
    if not _client_secret():
        logger.error("[discord_oauth] DISCORD_CLIENT_SECRET 未設定のため開始しない")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="一時的に Discord 連携を開始できません（設定不足）",
        )
```
理由: 鍵が無いまま Discord でボットを入れさせると、戻り口で必ず失敗し、ボットだけサーバーに残る。先に止める。

### 4-3. code の交換（新規の関数）

```python
class _ExchangeError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


async def _exchange_code_for_guild_id(code: str) -> str:
    """code を Discord で交換し、応答の guild.id を返す（公式: Advanced Bot Authorization）。"""
    secret = _client_secret()
    if not secret:
        raise _ExchangeError("discord_not_configured")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _DISCORD_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": _DISCORD_CALLBACK_URL,
                },
                auth=(_DISCORD_CLIENT_ID, secret),
            )
    except httpx.HTTPError as e:
        logger.warning("[discord_oauth] code 交換の通信失敗: %s", type(e).__name__)
        raise _ExchangeError("code_exchange_failed") from None
    if resp.status_code != 200:
        err = ""
        try:
            err = str(resp.json().get("error", ""))[:40]
        except (ValueError, AttributeError):
            pass
        logger.warning("[discord_oauth] code 交換の拒否 status=%d error=%s", resp.status_code, err)
        raise _ExchangeError("code_exchange_failed")
    try:
        guild = resp.json().get("guild") or {}
        gid = str(guild.get("id", ""))
    except (ValueError, AttributeError):
        gid = ""
    if not re.fullmatch(r"\d{17,19}", gid):
        logger.warning("[discord_oauth] 交換の応答に guild が無い")
        raise _ExchangeError("missing_guild_in_token")
    return gid
```
- `import httpx` を先頭に足す
- 応答の本文・access_token・refresh_token・code・鍵はログに出さない。出すのは status と Discord の `error` の語（例 `invalid_grant`）だけ
- 応答の本文が辞書でない JSON でも、`AttributeError` を受けて 500 にしない（:109・:116 の両方）
- Discord からの転送の URL には Discord の決まりで code が入る。web サーバーのアクセスログには残る。code は1回だけ使え、交換には鍵が要るので、code だけでは保存も横取りもできない。アプリのログには書かない
- `httpx` の `data=` は `application/x-www-form-urlencoded` で送る（公式の条件）。`auth=(id, secret)` は HTTP Basic（公式の条件）

### 4-4. 戻り口（:160-254）

変更前の引数: `guild_id`・`state`。変更後: `code: str | None = Query(None)` を足す。

処理の順（変更後）:
1. state なし → `missing_state`（今と同じ・:173-174）
2. guild_id なし → `missing_guild_id`（今と同じ）
3. guild_id の形 → `invalid_guild_id`（今と同じ）
4. state を使う → Redis 失敗 `redis_error`／無効 `invalid_state`（今と同じ・1回だけ使う）
5. purpose・tenant_id の確かめ（今と同じ :196-209）
6. **新規**: `code` が無い → `{base}discord_status=error&reason=missing_code`（保存しない）
7. **新規**: `verified = await _exchange_code_for_guild_id(code)`。`_ExchangeError` → `{base}discord_status=error&reason=<e.reason>`（保存しない）
8. **新規**: `verified != guild_id` → warning ログ（tenant・purpose・両方の番号）→ `{base}discord_status=error&reason=guild_mismatch`（保存しない）
9. set_tenant_context → INSERT … に渡す guild_id は `verified`（今の :229 の `guild_id` を置き換える）。監査の new_data も `verified` と `"verified_by": "token_exchange"` を足す
10. 以降（IntegrityError・reset_tenant_context・connected）は今と同じ

- 交換（7）は state を使った（4）後に置く。state は1回だけなので、同じ state で code を試し直すことはできない
- 交換（7）は set_tenant_context（9）の前に置く。DB の取引を開いたまま外へ待たない
- 6〜8 の失敗は、`base`（自社用は自社のタブ、顧客用はチャネル画面）へ戻す

### 4-5. 配線（3か所）

- docker-compose.yml backend の :109 の下: `      - DISCORD_CLIENT_SECRET=${DISCORD_CLIENT_SECRET:-}`
- .github/workflows/deploy.yml: :294 の `-e '/^DISCORD_BOT_TOKEN=/d' \` の下に `-e '/^DISCORD_CLIENT_SECRET=/d' \`。:355 の `DISCORD_BOT_TOKEN='${{ secrets.DISCORD_BOT_TOKEN }}'` の下に `DISCORD_CLIENT_SECRET='${{ secrets.DISCORD_CLIENT_SECRET }}'`
- backend/app/main.py:196 の後に、DISCORD_CLIENT_SECRET が空なら warning（起動は止めない。止めると Discord 以外の機能まで止まるため）

触らない: 招待の URL（:94-101 の scope・response_type・redirect_uri）、state の発行と使い方（oauth_state.py）、他の Discord の router、frontend

## 5. 影響範囲（呼び出し元の全走査）

- `/discord/oauth/start` の呼び手: frontend/src/pages/channels/ChannelsPage.tsx:194・frontend/src/pages/admin/DiscordOwnServerPanel.tsx:139（recon1.txt）。どちらも 503 を今の「開始できません」の扱い（Redis 失敗と同じ形）で受ける
- `/discord/oauth/callback`: Discord の転送だけ（公開）。repo 内の呼び手は試験だけ
- 招待の URL を作る所は :102 の1か所（`git grep -n "oauth2/authorize"` で backend・frontend・gas・scripts に他は無い）
- `public.tenant_discord_config` への書き込みはこの戻り口の INSERT だけ（前の設計で PUT を閉じた。#5202）
- DISCORD_CLIENT_SECRET を読む所は新規の `_client_secret()` だけ（1か所。正本は GitHub Secrets → .env → compose → backend の1本道）

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| U1: 今の招待で戻り先に code が付かない（公式は bot と applications.commands だけなら token は要らないと書く・recon 8） | 合流の前に確かめる（12 節 0）。PO の 11/6 の再接続のブラウザの履歴にある戻り口の URL に `code=` があるかを見る。履歴に戻り口の URL が残っていなければ、今のコードのまま会社1で解除→再接続し、その戻り口の URL を見る（今の戻り口は code を見ないので、つながりは変わらない）。`code=` が無ければ、合流の前に PO が開発者画面のボット設定で「Requires OAuth2 Code Grant」を入れ、もう一度会社1で解除→再接続して戻り口の URL に `code=` があるかを見る（公式の勧め・コード変更なし）。それでも無ければ合流しない（設計を戻して PO に聞く） |
| K2 の確かめで、会社1の行が消えたまま残る（画面の連携ボタンは未接続のときだけ出る: frontend/src/pages/channels/ChannelsPage.tsx:530・frontend/src/pages/admin/DiscordOwnServerPanel.tsx:304。解除は行を消す: backend/app/routers/discord_guild_config.py:104・:167） | 確かめは会社1（開発の試しの会社）だけで行う。失敗したら 12 節 4 の戻しの流れ: revert → 反映 → PO がもう一度つなぐ（今の戻り口は code を見ないのでつながる）→ Opus が読み取りの道で会社1の2行が戻ったことを確かめる。止まる範囲: 戻るまで、会社1の顧客用サーバーの書き込みは会社を引けない（backend/app/discord_gateway/client.py:101-119 `_resolve_tenant_id` の guild から会社を引く処理）。他の会社（4・6）の行には触らない |
| 鍵が GitHub Secrets に入る前に反映される | 開始口が 503 で止まる（4-2）。連携は止まるが、偽の登録は入らない。順番は 12 節で「鍵 → 合流」に固定 |
| 鍵がログに出る | ログに出す値を status と error の語だけに限る（4-3）。試験で caplog と転送先 URL に鍵の文字が無いことを確かめる |
| Discord の応答が遅い | 10 秒で打ち切り `code_exchange_failed`。DB の取引は開く前（4-4） |
| 開発者画面で鍵を作り直すと前の鍵が無効になる（U3） | repo で使う所は 0（recon 3）。作り直して問題ない |
| deploy.yml を触る | ADR-135/136 の危険パス。GO 記録が要る（12 節） |

## 7. 代替案と選んだ理由

| 案 | 内容 | 採否と理由 |
|---|---|---|
| A（採用） | 戻り口で code を交換し、応答の guild.id だけを保存 | Discord 公式が示す確かめ方。guild_id は hint としてだけ使えと公式が書く |
| B | ボットの鍵で「ボットがそのサーバーに入っているか」を確かめる | ボットが入っていることは、操作した人が持ち主である証明にならない（前の設計 7 節 D と同じ理由）。他人が入れたボットのサーバーを横取りできる |
| C | 開始口で state を返さない | 呼び手は招待 URL から state を読める（URL の中にある）。閉じきれない |
| D | scope に identify を足して必ず code の流れにする | 利用者の Discord の画面に項目が増える。U1 が起きたときは、まず開発者画面の設定で手当てする（6 節 U1）。それでも code が付かなければ合流せず、この案を含めて PO に聞く |

## 8. 維持の仕組み

- 守り手: backend/tests/test_discord_oauth.py の戻り口の試験（10 節）。code の交換を外すと K1 の試験が赤になる
- ADR-091 に追記: 「戻り口は code を交換し、応答の guild だけを保存する。URL の guild_id は使わない」
- 別作業（台帳に積む）: 既存4行のサーバーにボットが入っているかの点検（recon 8 U2）
- 別作業: Discord の失敗理由の画面の文言（3 節 対象外）

## 9. 戻し方

- 実装の PR を revert する。DB の変更は無い
- GitHub Secrets の DISCORD_CLIENT_SECRET は残しても害は無い（読む所が無くなるだけ）
- 開発者画面で「code grant を必須」を入れていた場合は、PO が外す（6 節）

## 10. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| code なしで戻り口を開くと `reason=missing_code`、行が増えない | backend の自動試験（consume_state を差し替え・DB の行数を前後で比べる） |
| Discord が拒否する code（400 invalid_grant）で `reason=code_exchange_failed`、行が増えない | 自動試験（httpx.MockTransport・recon 4 の手本） |
| 応答の guild.id と URL の guild_id が違うと `reason=guild_mismatch`、行が増えない／変わらない | 自動試験 |
| 応答に guild が無いと `reason=missing_guild_in_token` | 自動試験 |
| 正しい code で、応答の guild.id が保存され connected | 自動試験（保存値を読む） |
| 交換の送り方が公式どおり（form・Basic・grant_type・code・redirect_uri） | 自動試験で MockTransport が受けた要求を確かめる |
| 鍵が無いと開始口が 503、戻り口は `discord_not_configured` | 自動試験 |
| アプリのログと転送先 URL に鍵・code・access_token が出ない | 自動試験（caplog・location に試験用の値が含まれない） |
| K4: 鍵の値がコードと文書に無い | Opus は鍵の値を持たない。合流の前に `git grep -n -iE "DISCORD_CLIENT_SECRET\s*[=:]\s*['\"]?[A-Za-z0-9_-]{20,}"` が 0 件（値の形の文字列が書かれていない）。鍵は GitHub Secrets だけにある（`gh secret list` で名前だけ確かめる） |
| state を1回使ったら同じ state で2回目は `invalid_state` | 既存の試験の形（今と同じ） |
| 既存の試験（戻り口 :306 など・開始口 :190・:219・:246）を code あり／鍵ありの形に直して緑 | CI |
| 自社用の戻り先が `/admin/discord-config?tab=own&…` のまま | 自動試験 |
| deploy.yml と compose に DISCORD_CLIENT_SECRET が入る | 差分の審査・反映後に `gh run view` で deploy 成功 |
| K2: 本番で顧客用・自社用がつながる | 反映後、PO がテナント001で解除→再接続 |
| K3: 本番の新しい行の guild_id が PO の選んだサーバー | 読み取りの道で `ai_ro.public__tenant_discord_config` の会社1の2行（updated_at が反映後） |

## 11. 外部・過去事例の参照と我々への応用

- Discord 公式（docs.discord.com/developers/topics/oauth2「Advanced Bot Authorization」2026-11-06 取得）: guild_id は hint、確かめは code grant。数値の事例は無い。応用: 4-3・4-4
- 過去事例（この repo）: ADR-091:137-185（PR #1481 失敗・#1483 で戻り口が呼ばれるようになった）。応用: 招待の scope は変えない（7 節 D）
- 数値の外部事例は使わない（この変更の成否は K1〜K4 の自動試験と本番の再接続で判定でき、他社の数値は根拠にならない）

## 12. 実装の進め方（1つの作業）

順番を固定する:
0. **済み（2026-11-07）**: 戻り口の URL に `code` が付くことを確かめた（recon 8）。以下は記録として残す。U1 を確かめる: PO が、11/6 にテナント001で再接続したときのブラウザの履歴から、`api.salesanchor.jp/api/v1/discord/oauth/callback` の URL に `code=` があるかだけを見て答える（値は書き写さない）。履歴に無い場合・`code=` が無い場合は 6 節 U1 の手当て
1. 実装（クラウドの Sonnet・実装カード）→ CI 緑 → 審査役 → GO 記録（委任・ADR-1003。deploy.yml を含むので ADR-136 の3行まとめを PO に出す）
2. **合流の前に**、PO が秘密の鍵を入れる（secrets の変更は PO 本人・ADR-1003 例外）:
   1. Discord 開発者画面 → Sales Anchor のアプリ（client id 1499458730171961535）→ OAuth2 → Client Secret → Reset Secret → 出た値を写す（1回しか表示されない）
   2. GitHub の shingo-ops/salesanchor → Settings → Secrets and variables → Actions → New repository secret → 名前 `DISCORD_CLIENT_SECRET`、値を貼る
   3. Opus が `gh secret list` で名前があることだけ確かめる（値は見ない）
3. 合流 → 反映（deploy 成功を確かめる）
4. PO がテナント001で顧客用・自社用を解除→再接続（K2）。失敗したら、その場で次の戻しの流れにする: (1) Opus が PR を revert する（revert の PR も deploy.yml を含むので、委任の GO 記録を残してから合流）して反映 (2) PO がもう一度つなぐ (3) Opus が読み取りの道で会社1の顧客用・自社用の2行があることを確かめる。会社4・6 の行は触らない
5. Opus が読み取りの道で K3 を確かめる

## 13. 審査（Architect）

### 1回目（2026-11-06 15:31Z・クラウドの Opus・読み取りのみ・対象 c774b7d5e・照合 origin/main 8a13f5328）: REVISE

- C1 ×（recon の試験の行番号1か所）／C2 未確認（クラウドから docs.discord.com に届かない）／C3 ○（tenant_discord_config への書き込みは discord_oauth.py:221 の INSERT だけ。他は SELECT と DELETE）／C4 ○条件つき／C5 ×／C6 ○
- Q1 必須: K2 の確かめで失敗すると会社1の行が消えたまま残る → 6 節に行を足し、12 節 4 に戻しの流れを書いた
- Q2 推奨: 転送の URL の code はアクセスログに残る → K4 の対象を「アプリのログ」と明記し、4-3 に理由を書いた
- Q3 推奨: 開始口の今の試験は鍵が無いと赤 → 3 節と 10 節に足した
- Q4 推奨: 拒否の応答の本文が辞書でないと AttributeError → 4-3 :109 の except を直した
- Q5 推奨: recon 6 の行番号を直した
- Q6 推奨: K4 の `git grep` の確かめを 10 節に足した
- C2 の代わり: Opus が手元で公式を 2026-11-07 に再取得した。交換の URL・項目・form だけ・Basic 認証・応答の guild は 4-3 と一致。一方で公式は「bot と applications.commands だけなら token は要らない」と書くので、U1 を実装の前に確かめる順に変えた（12 節 0・6 節）

### 2回目（2026-11-06 15:37Z・クラウドの Opus・対象 1ca54cbf9）: APPROVE

- Q1〜Q6 すべて直った（引用の行は origin/main と一致）。必須の指摘は 0
- R1 推奨: client.py の引用を :101-119 に → 直した
- R2 推奨: revert の PR にも GO 記録が要る → 12 節 4 に書いた
- R3 推奨: 開発者画面の設定の後は解除→再接続しないと新しい URL が残らない・履歴に無いときの手順 → 6 節 U1 に書いた
- R4 推奨: 7 節 D の言い切りが 6 節と食い違う → 6 節に合わせた
- 推奨4件の直しは文言だけで、手順の順番と判定は変えていない
