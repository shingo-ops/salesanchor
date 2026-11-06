# パスワードの保存方法 — 最高水準・危険・外部事例の調査

> この文書は何か：PO の問い「最高水準は？ハッシュじゃないと外部攻撃にさらされるリスクがある？外部での導入事例と成功事例と成功要因、失敗事例と失敗要因を…5w2h化して…数値にして」（2026-11-06）への調査記録です。設計の判断はまだしていません（草案）。

- 調べた人: Claude Opus（手元で一次資料を取得・照合）。実測と repo の事実はクラウドの Sonnet（[measure.md](measure.md)）。
- 取得日: 2026-11-06（UTC 14:25）。一次資料の原文は取得してから抜き出した。
- 書き方: 【事実】＝出典の原文または実測で確かめた／【推測】＝根拠から導いたが確かめていない／【未確認】＝調べたが確かめられなかった。

---

## 1. 最高水準は何か（A）

### 1-1. 3 つの基準の原文

| 基準 | 原文（抜粋） | 出典 |
|---|---|---|
| OWASP Password Storage Cheat Sheet | "Use Argon2id with a minimum configuration of 19 MiB of memory, an iteration count of 2, and 1 degree of parallelism." | 【事実】OWASP CheatSheetSeries の原稿 `cheatsheets/Password_Storage_Cheat_Sheet.md` :11（https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Password_Storage_Cheat_Sheet.md 、公開ページ https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html ） |
| 同上（同じ強さの 5 通り） | "m=47104 (46 MiB), t=1, p=1 / m=19456 (19 MiB), t=2, p=1 / m=12288 (12 MiB), t=3, p=1 / m=9216 (9 MiB), t=4, p=1 / m=7168 (7 MiB), t=5, p=1" — "These configuration settings provide an equal level of defense, and the only difference is a trade off between CPU and RAM usage." | 【事実】同 :112-118 |
| 同上（強さの決め方） | "There is no golden rule for the ideal work factor … As a general rule, calculating a hash should take less than one second." | 【事実】同 :85 |
| 同上（ペッパー） | "Consider using a pepper to provide additional defense in depth (though alone, it provides no additional secure characteristics)." / "the pepper … should not be stored along with the generated hash … stored in 'secrets vaults' or HSMs" | 【事実】同 :15・:67-68 |
| RFC 9106（Argon2 の正式仕様） | "select Argon2id with t=1 iteration, p=4 lanes, m=2^(21) (2 GiB of RAM), 128-bit salt, and 256-bit tag size. This is the FIRST RECOMMENDED option." / "If much less memory is available … Argon2id with t=3 iterations, p=4 lanes, m=2^(16) (64 MiB of RAM) … SECOND RECOMMENDED option." | 【事実】https://www.rfc-editor.org/rfc/rfc9106.txt §4（取得した原文の 581-589 行） |
| 同上（塩） | "16 bytes is RECOMMENDED for password hashing. The salt SHOULD be unique for each password." | 【事実】同 §3.1（195-200 行） |
| NIST SP 800-63B-4（米国政府の基準・2025 年最終版） | "Passwords SHALL be salted and hashed using a suitable password hashing scheme." / "The chosen cost factor SHOULD be as high as practical without negatively impacting verifier performance. It SHOULD be increased over time" / "The salt SHALL be at least 32 bits in length" | 【事実】https://pages.nist.gov/800-63-4/sp800-63b/authenticators/ |
| 同上（秘密の鍵＝ペッパー） | "verifiers SHOULD perform an additional iteration of a keyed hashing or encryption operation using a secret key known only to the verifier … The secret key value SHALL be stored separately from the hashed passwords." | 【事実】同上 |
| 同上（漏洩パスワードの照合） | "verifiers SHALL compare the prospective secret against a blocklist that contains known commonly used, expected, or compromised passwords. The entire password SHALL be subject to comparison" | 【事実】同上 |
| 同上（長さ） | "SHALL require passwords that are used as a single-factor authentication mechanism to be a minimum of 15 characters … multi-factor … minimum of eight characters … SHOULD permit a maximum password length of at least 64 characters." / "SHALL NOT impose other composition rules" / "SHALL NOT require subscribers to change passwords periodically" | 【事実】同上 |
| 同上（試行回数） | "Verifiers SHALL implement a rate-limiting mechanism…" / "the verifier SHALL limit consecutive failed authentication attempts … to no more than 100" | 【事実】同上 |

### 1-2. まとめ

- 【事実】OWASP の「最低限」は 19 MiB・2 回・1 並列。いまの設定（backend/app/auth/passwords.py:14 の m=19456・t=2・p=1）はこの最低限そのもの。
- 【事実】RFC 9106 の 1 番目の推奨は 2 GiB・1 回・4 並列。2 番目の推奨（メモリが少ない場合）は 64 MiB・3 回・4 並列。
- 【事実】3 基準とも「サーバーが耐えられる範囲でできるだけ重く」「機械が速くなったら上げる」と書いている。固定の「最高値」は無い。
- 【推測】「最高水準」として現実に選べるのは、RFC 9106 の 2 番目（64 MiB・t=3・p=4）か、OWASP 範囲内でメモリを増やした設定。2 GiB はログイン 1 回ごとに 2 GiB を使うので、同時ログインでサーバーのメモリが尽きる（OWASP :83 "could be used by an attacker to carry out a denial of service attack"）。実測は measure.md。

---

## 2. ハッシュにしない／弱いハッシュだと何が危ないか（B）

- 【事実】OWASP :7 "Passwords should never be stored in plain text … Fast hashing algorithms such as SHA‑256 are not suitable for password storage because they allow attackers to perform large numbers of guesses quickly."
- 【事実】OWASP :62 ペッパーの目的として「データベースだけ（SQL の注入や予備の写し）を取られた場合」を想定している。つまり想定する攻撃は「DB の中身が外へ出た後に、手元で総当たりされる」こと。
- 起こり方（事例 3 章から）:
  1. 平文で保存 → 漏れた瞬間に全員分が読める（RockYou 3,260 万件）。
  2. 暗号化（元に戻せる形）で保存 → 鍵か仕組みが分かれば全員分が戻る。同じパスワードは同じ値になり、ヒントから当てられる（Adobe 1.5 億件）。
  3. 速いハッシュ（MD5・SHA-1）・塩なし → 同じパスワードの人がまとめて割れる（LinkedIn 1.17 億件）。
  4. 強いハッシュの横に弱い写しを残す → 弱い方から割られる（Ashley Madison 1,126 万件）。
  5. 社内の記録に平文が混ざる → 漏れていなくても罰金（Meta 9,100 万ユーロ）。
- 【事実】強いハッシュでも、利用者の弱いパスワード（123456 など）は割られる（Ashley Madison の bcrypt 部分で 4,007 件・3 章 S1）。だからハッシュの強さと、弱いパスワードを登録させない照合（NIST の blocklist）は両方要る。

---

## 3. 外部事例（5W2H）

5W2H: いつ（When）／どこ（Where）／誰が（Who）／何を（What）／なぜ（Why）／どうやって（How）／どれだけ（How much・How many）。

### 失敗事例

#### F1. RockYou（2009 年 12 月）— 平文で保存

| 項目 | 内容 |
|---|---|
| いつ | 2009 年 12 月 |
| どこ・誰 | 米 RockYou（SNS 向けアプリ会社）、攻撃者 1 名以上 |
| 何を | 利用者 32,603,388 件のパスワードを平文のまま保存 |
| なぜ | パスワードをハッシュにしていなかった。入口は SQL 注入の穴（Imperva が通知済みだったが直すのが遅れた） |
| どうやって | SQL 注入で DB を取り、一覧を公開 |
| どれだけ | 32,603,388 件が読める形で流出。「123456」が 290,731 人。約半数が名前・辞書の語・単純な並び（Imperva の分析） |
| 出典 | 【事実】https://www.theregister.com/2009/12/16/rockyou_password_snafu/ 、https://www.scworld.com/news/rockyou-hack-reveals-most-common-password-123456 、https://techcrunch.com/?p=137660 。罰金・和解の額は【未確認】（見つからなかった） |
| 失敗要因 | 平文保存。漏れた瞬間に解読の手間が 0。 |

#### F2. Adobe（2013 年 10 月）— 暗号化（元に戻せる形）とヒントを平文で保存

| 項目 | 内容 |
|---|---|
| いつ | 2013 年 10 月（州との和解 2016 年 11 月 7 日） |
| どこ・誰 | 米 Adobe |
| 何を | 1 億 5,300 万件（Have I Been Pwned の数え方では 1 億 5,240 万件）の ID・メール・暗号化したパスワード・平文のヒント |
| なぜ | 一方向のハッシュでなく 3DES の ECB 方式で暗号化。同じパスワードは同じ値になる。ヒントにパスワードそのものを書いた人が多い |
| どうやって | 同じ値の人をまとめ、ヒントを突き合わせて推し当てる |
| どれだけ | 15 州の司法長官に 100 万ドル。集団訴訟の原告側弁護士費用 118 万ドル |
| 出典 | 【事実】https://haveibeenpwned.com/breach/Adobe 、https://production.jdsupra.com/legalnews/adobe-settles-with-15-states-for-2013-44431 、https://www.itnews.com.au/news/adobe-settles-giant-2013-data-breach-class-action-suit-407993 |
| 失敗要因 | 「暗号化＝元に戻せる」形を選んだ。塩が無い（同じ値が並ぶ）。ヒントを平文で置いた。 |

#### F3. LinkedIn（2012 年 6 月、全容判明 2016 年 5 月）— 塩なし SHA-1

| 項目 | 内容 |
|---|---|
| いつ | 2012 年（当初 650 万件と発表）、2016 年 5 月に 1 億 1,700 万件と判明 |
| どこ・誰 | 米 LinkedIn |
| 何を | 塩なしの SHA-1 で保存したパスワード |
| なぜ | 速いハッシュ・塩なし。同じパスワードは同じ値になり、一度割れば全員分が割れる |
| どうやって | 2012 年に 650 万件の値が掲示板に出た。2016 年に約 1 億 1,700 万件（メールとパスワード）が売りに出た |
| どれだけ | 1 億 1,700 万件。簡単な 50 種類のパスワードだけで 200 万件超（LeakedSource） |
| 出典 | 【事実】https://krebsonsecurity.com/2016/05/as-scope-of-2012-breach-expands-linkedin-to-again-reset-passwords-for-some-users/ 、https://techcrunch.com/2016/05/18/117-million-linkedin-emails-and-passwords-from-a-2012-hack-just-got-posted-online 。全体の解読率は【未確認】（数字が見つからなかった） |
| 失敗要因 | 速いハッシュ＋塩なし。発覚から全容判明まで 4 年。 |

#### F4. Ashley Madison（2015 年 7〜9 月）— 強いハッシュの横に弱い写し

| 項目 | 内容 |
|---|---|
| いつ | 2015 年 7 月流出、9 月に解読の報告 |
| どこ・誰 | カナダ Avid Life Media（Ashley Madison）、解読したのは研究者集団 CynoSure Prime |
| 何を | 約 3,600 万件。本体は bcrypt（強いハッシュ・強さ 12） |
| なぜ | 2012 年 6 月以前の口座では、別に「名前＋小文字にしたパスワード」の MD5 値（$loginkey）も保存していた |
| どうやって | 速い MD5 の方を割り、大文字小文字だけ bcrypt と照合して直した |
| どれだけ | 弱い写しのある 1,526 万件のうち 1,126 万件超を約 10 日で解読 |
| 出典 | 【事実】https://www.csoonline.com/article/2982938/ashley-madison-coding-blunder-made-over-11-million-passwords-easy-to-crack.html 、https://securityaffairs.com/40046/hacking/ashley-madison-pwd-crack.html |
| 失敗要因 | 強いハッシュを入れても、弱い写しが 1 か所残ると全体の強さはその弱い方になる。 |

#### F5. Meta（Facebook・Instagram、2019 年 3 月発覚・2024 年 9 月 27 日処分）— 社内の記録に平文

| 項目 | 内容 |
|---|---|
| いつ | 2019 年 3 月に Meta が当局へ届出、2024 年 9 月 27 日に処分 |
| どこ・誰 | アイルランドのデータ保護委員会（DPC）が Meta Platforms Ireland を処分 |
| 何を | 一部の利用者のパスワードを、社内の仕組みに暗号化もハッシュもせず保存 |
| なぜ | 社内の記録（ログ等）に平文が混ざった。外部への流出の証拠は無いと Meta は説明 |
| どうやって | 社内の点検で見つかり届出 |
| どれだけ | 罰金 9,100 万ユーロと戒告。GDPR 第 33 条 1 項・5 項、第 5 条 1 項 f、第 32 条 1 項の違反 |
| 出典 | 【事実】https://www.rte.ie/news/business/2024/0927/1472310-meta-fined-91m-by-dpc-for-password-storage-issues 、https://irishtimes.com/business/2024/09/27/facebook-owner-meta-fined-91m-by-irish-data-protection-commission |
| 失敗要因 | 保存の正本はハッシュでも、記録・ログに平文が流れ込む道があった。漏れていなくても罰金になる。 |

#### F6. Yahoo（2013 年、全容判明 2017 年 10 月）— 届出の遅れ

| 項目 | 内容 |
|---|---|
| いつ | 2013 年に流出、2017 年 10 月に「30 億件すべて」と訂正、2018 年 4 月に SEC 罰金 |
| どこ・誰 | 米 Yahoo（現 Altaba） |
| 何を | 30 億件の口座（暗号化したパスワード・秘密の質問を含む） |
| なぜ | 経営陣への報告と公表が 2 年以上遅れた（SEC の認定）。ハッシュの方式は【未確認】（MD5 とする記事はあるが一次資料で確かめられなかった） |
| どれだけ | SEC 罰金 3,500 万ドル。Verizon による買収額が 3 億 5,000 万ドル下がった |
| 出典 | 【事実】https://gizmodo.com/sec-fines-yahoo-35-million-for-failing-to-disclose-hac-1825501358 、https://www.techradar.com/news/yahoo-now-claims-all-3-billion-accounts-were-affected-in-2013-data-breach |
| 失敗要因 | 保存方式の弱さに加え、発覚後の届出の遅れで金額が大きくなった。 |

#### F7. LastPass（2022 年 8〜12 月）— 古い口座の弱い強さ設定が上がっていなかった

| 項目 | 内容 |
|---|---|
| いつ | 2022 年に保管庫の写しを盗まれた。2023 年 9 月に暗号資産の盗難との結びつきが報じられた |
| どこ・誰 | 米 LastPass（パスワード管理サービス） |
| 何を | 利用者の保管庫（主パスワードから PBKDF2 で鍵を作る） |
| なぜ | 新しい既定は 100,100 回だが、古い口座は 5,000 回など低いまま残っていた（自動で上げていなかった） |
| どれだけ | 約 150 人から 3,500 万ドル超の暗号資産が盗まれたと Krebs が報じた（【未確認】Krebs の原文は取得できず、二次資料の引用） |
| 出典 | https://www.hivesystems.com/blog/examining-the-lastpass-breach-through-our-password-table 、https://hivesecurity.gitlab.io/blog/password-managers-after-lastpass-still-safe |
| 失敗要因 | 強さの設定を上げても、古い保存値を上げ直す仕組み（ログイン時の再ハッシュ）が無いと古い弱い値が残る。 |

### 成功事例

#### S1. Ashley Madison の bcrypt 部分（2015 年 8 月）— 強いハッシュで解読が 0.07%

| 項目 | 内容 |
|---|---|
| いつ | 2015 年 8 月 |
| どこ・誰 | 研究者 Dean Pierce が、流出した bcrypt（強さ 12・口座ごとの塩）の値を試した |
| 何を | 最初の 600 万件 |
| なぜ効いたか | bcrypt が遅く、塩が口座ごとに違うため、1 件ずつ当てるしかない |
| どうやって | 画像処理の部品（GPU）4 枚の機械で 5 日 3 時間、約 7,000 万回の推し当て |
| どれだけ | 1 秒に 156 回しか試せず、解読は 4,007 件（0.07%）。割れたのは 123456（202 件）・password（105 件）など弱いもの |
| 出典 | 【事実】https://motherboard.vice.com/read/someone-cracked-4000-ashley-madison-passwords-and-loads-of-them-are-awful 、https://news.sophos.com/en-us/2015/08/31/what-ashley-madison-got-right/ |
| 成功要因 | 遅いハッシュ＋口座ごとの塩。比べると、同じ流出の弱い MD5 部分（F4）は約 10 日で 1,126 万件。 |
| 限界 | 弱いパスワードは割れる。弱いパスワードを登録させない照合が別に要る。 |

#### S2. Slack（2015 年 2〜3 月）— bcrypt で保存値からの解読の証拠なし

| 項目 | 内容 |
|---|---|
| いつ | 2015 年 2 月に約 4 日間の侵入、3 月 27 日に公表 |
| どこ・誰 | 米 Slack |
| 何を | 利用者の情報の DB（パスワードは bcrypt＋口座ごとの塩） |
| どうやって守った | 保存値から解読された証拠は無いと発表。同時に 2 段階の確認（2FA）を出した |
| どれだけ | 2019 年に、攻撃者がログイン画面にコードを入れて平文を盗んでいた可能性が分かり、約 1%（約 6 万 5,000 件）のパスワードを初期化 |
| 出典 | 【事実】https://threatpost.com/slack-discloses-breach-of-its-user-profile-database-implements-2fa/111872 、https://www.techtarget.com/enterprise-software/news/252467015/Slack-resets-passwords-possibly-compromised-in-2015-hack 。6 万 5,000 件は https://siliconrepublic.com/?p=826490 の見出し |
| 成功要因 | 保存は強いハッシュだった。限界: 入力の途中で盗む攻撃は、保存方式では防げない。 |

#### S3. Dropbox（2012 年流出・2016 年 8 月に全容）— 移行中だった bcrypt 半分

| 項目 | 内容 |
|---|---|
| いつ | 2012 年流出、2016 年 8 月に確認 |
| どこ・誰 | 米 Dropbox。Troy Hunt（Have I Been Pwned の運営者）が中身を確認 |
| 何を | 68,648,009 件。半分が bcrypt、半分が塩付き SHA-1（SHA-1 から bcrypt へ移している途中） |
| どうやって守った | 2012 年半ばより前の、変更していない口座のパスワードを強制初期化 |
| どれだけ | 約 3,200 万件が bcrypt。解読の件数は【未確認】（公開の数字が見つからなかった） |
| 出典 | 【事実】https://www.securityweek.com/68-million-exposed-old-dropbox-hack 、https://threatpost.com/68-million-credentials-spilled-in-2012-dropbox-hack/120253 |
| 成功要因 | 古い方式から新しい方式へ移す仕組みがあった。限界: 移行が終わっていなかった半分は弱いまま。 |

- 【未確認】Argon2id で保存していた会社が流出し、解読率が公表された事例は見つからなかった（検索した範囲で）。

---

## 4. 事例から言えること（成功要因と失敗要因）

| 要因 | 失敗した例 | 成功した例 |
|---|---|---|
| 遅いハッシュ＋口座ごとの塩 | F1 平文・F2 暗号化・F3 塩なし SHA-1 | S1 0.07%・S2 |
| 弱い写しを残さない | F4（1,126 万件） | — |
| 記録・ログに平文を流さない | F5（9,100 万ユーロ） | — |
| 古い保存値を上げ直す | F7・S3 の SHA-1 半分 | S3 は移行の仕組みがあった |
| 弱いパスワードを登録させない | S1 でも割れたのは 123456 など | — |
| 発覚後すぐ届ける | F6（3,500 万ドル・3 億 5,000 万ドル減額） | — |

【推測】Sales Anchor に当てはめると、保存方式（Argon2id）は「成功側」の条件を満たす。残りの差は、(1) 強さを最低限から上げるか、(2) 古い値の上げ直し（needs_rehash）が実際に動いているか、(3) ログ・記録に平文が流れないか、(4) 漏洩パスワードの照合・試行回数の制限。今の実装の有無は measure.md で確かめる。

---

## 5. Sales Anchor の今と基準・事例の差（origin/main 9571ce84e）

実測とリポジトリの事実は [measure.md](measure.md)。下の行番号は Opus が手元で `git show` して照合した。

| 項目 | 基準・事例 | Sales Anchor の今 | 差 |
|---|---|---|---|
| 保存方式 | OWASP 第一推奨 Argon2id | 【事実】Argon2id（backend/app/auth/passwords.py:14） | なし |
| 強さ | OWASP 最低 19 MiB・t=2。RFC 9106 第二推奨 64 MiB・t=3・p=4 | 【事実】19 MiB・t=2・p=1（最低限そのもの） | 最低限。上げる余地あり |
| 1 回の時間 | OWASP「1 秒未満」 | 【事実】クラウド実測で中央値 23.6 ms（measure.md 表 #1） | 余裕あり（本番機の値は【未確認】） |
| サーバーの余裕 | 重すぎると DoS（OWASP :83） | 【事実】backend は 1 プロセス・メモリ 512M・CPU 1.0（backend/Dockerfile:39、docker-compose.yml:173-177） | 2 GiB 設定（RFC 第一推奨）は上限を超え使えない |
| 古い値の上げ直し | F7 LastPass の失敗要因 | 【事実】社員ログイン成功時に再ハッシュ（backend/app/routers/auth.py:483-488）。【事実】閲覧ページのログイン（backend/app/routers/viewer.py:184-188）には無い | 閲覧ページの口座は強さを上げても古いまま残る |
| 弱い写し | F4 Ashley Madison | 【事実】利用者パスワードの保存は Argon2id のみ。bcrypt は bot の API キーだけ（backend/app/routers/bots.py:59） | 見つかっていない |
| ペッパー（別置きの秘密の鍵） | NIST・OWASP とも SHOULD | 【事実】無し（measure.md 2-b） | 無し |
| 弱いパスワードの拒否 | NIST SHALL（漏洩一覧との照合） | 【事実】15〜64 文字、一覧 99,840 行に載るものを拒否（backend/app/auth/password_policy.py:11-12・:30） | 漏洩の全件照合（HIBP 等）は無し |
| 試行回数の制限 | NIST SHALL（連続 100 回以下） | 【事実】口座ごと 10 回で 15 分止める（backend/app/auth/self_tokens.py:29-30）、IP ごと 10 回で 15 分（backend/app/cache.py:307-308） | 基準内 |
| ログ・記録への平文の混入 | F5 Meta の失敗要因 | 【未確認】まだ調べていない | 要調査 |

- 【未確認】backend/app/routers/auth.py:1346 の「許可で入れたときの仕上げ」の経路は、パスワードを照合し直すかどうかを確かめていない。
- 【推測】次に手を入れるとしたら効果の大きい順に、(1) ログ・記録に平文が流れないかの点検、(2) 閲覧ページのログインにも上げ直しを入れる、(3) 強さを上げる（本番機で時間とメモリを測ってから）、(4) ペッパー、(5) 漏洩一覧との全件照合。どれも PO の判断の前の案で、設計はしていない。
