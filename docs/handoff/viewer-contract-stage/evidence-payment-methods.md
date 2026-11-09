# 振込先の表の形と守り — 外部事例（5W2H）

調べた日: 2026-11-10。調べ方: Web 検索の結果と、その公式ページ・報道の記載。数値は出典の記載のまま。出典に無い数は書かない。
使う先: design.md §3-4（振込先の3表）・§5（取らなかった案）・§6（危険と対処）・§10（外部事例）。

## 成功事例・決まり

### F1 GitLab — 1表に全種類を並べる形（STI）を新しい表で使わない

| 項目 | 内容 |
|---|---|
| Who | GitLab（開発の決まりの文書） |
| What | 新しい表を、1表に種類の列を持つ形（Single Table Inheritance）で作らない。種類ごとに別の表を作る |
| When | 決まりの追加は 2017 年のコミット「Document not using STI」 |
| Where | GitLab の開発文書 [Single Table Inheritance](https://docs.gitlab.com/development/database/single_table_inheritance) |
| Why | 表が大きくなる、索引が増える、軽いロックが溢れて障害につながりうる、種類で絞る手間、種類名を毎行持つ費用 |
| How | 種類ごとに表を分ける |
| How much | 速さや障害件数の数値は文書に無い（見つからなかったもの参照） |
| 当てはめ | 振込先を1表に全種類の欄で持つ案を取りやめ、一覧＋種類ごとの詳細の表にした |

### F2 Stripe — 種類の値＋種類と同じ名前の詳細

| 項目 | 内容 |
|---|---|
| Who | Stripe（決済の API） |
| What | 支払い方法（PaymentMethod）は `type` を持ち、その種類と同じ名前の詳細を持つ（例: sepa_debit は iban、us_bank_account は口座番号など） |
| When | 2026-11-10 時点の公式 API 文書 |
| Where | [create](https://docs.stripe.com/api/payment_methods/create)・[object](https://docs.stripe.com/api/payment_methods/object) |
| Why | 種類ごとに要る項目が違うため |
| How | 共通の部分（id・種類）と種類ごとの詳細を分ける |
| How much | 導入数などの数値は文書に無い |
| 当てはめ | 一覧（id・種類・表示名）と、bank / wise の詳細の表を1対1で結ぶ形の根拠 |

### F5 Xero — 振込先が変わったことを他の人に知らせる仕組み

| 項目 | 内容 |
|---|---|
| Who | Xero（会計ソフト）の利用者 |
| What | 取引先の口座が変わった知らせが、直した本人にしか届かない。これが詐欺の一件につながったと利用者が書いている |
| When | 2026-11-10 時点の要望の掲示 |
| Where | [Xero product ideas](https://productideas.xero.com/forums/939198-for-small-businesses/suggestions/44961091-email-settings-set-which-users-to-receive-bank-a) |
| Why | 書き換えた人以外が気づけない |
| How | 外部の道具（XBert・OutflowGuard）で補っている利用者がいる |
| How much | 被害額の数値は掲示に無い |
| 当てはめ | 今回は記録（audit_logs）と発行時の写しで守る。知らせる仕組みは作らず、§6 に残す |

### F7 PCI DSS 3.4.1 — 番号は伏せて見せる

| 項目 | 内容 |
|---|---|
| Who | カード業界の安全基準（PCI DSS） |
| What | カード番号を画面に出すときは伏せる。見せてよいのは最大で先頭6桁と末尾4桁 |
| Where | [AWS PCI maturity model](https://pci-maturitymodel.security.aws.dev/en/recommendation/r3.3/)（AWS による解説。PCI SSC の原文では確かめていない＝未確認） |
| 当てはめ | 記録（audit_logs）の口座番号と IBAN は下4桁だけにする（A32）。カードの基準を口座に借りた形で、口座への法的な決まりではない |

### F8 UK Finance — 警告と情報共有で振込詐欺が減った

| 項目 | 内容 |
|---|---|
| Who | UK Finance（英国の銀行業界団体） |
| What | 本人に振り込ませる詐欺（APP）の被害 |
| When | 2024 年の数値（2025 年の報告） |
| Where | [Annual Fraud Report 2025](https://www.ukfinance.org.uk/policy-and-guidance/reports-and-publications/annual-fraud-report-2025) |
| Why | アプリ内の警告と、銀行どうしの情報共有を理由に挙げている |
| How much | 被害 4億5,070万ポンド（前年比 −2%）、件数 −20% |
| 当てはめ | 振込先の差し替えは「気づける仕組み」で減る、という根拠。今回は記録と写しまで |
| 限界 | 翌年（2025 年の数値）の報告では被害が増えたとする検索結果がある（未確認。元の報告書で確かめていない）。減った効果が続くとは言えない |

## 失敗事例

### F3 日本航空 — 偽の請求書で振込先を差し替えられた

| 項目 | 内容 |
|---|---|
| Who | 日本航空 |
| What | 取引先を装ったメールの偽の請求書で、振込先を香港の銀行口座に変えられ、支払った |
| When | 2017 年 7〜9 月。公表は 2017-12-20 |
| Where | [ITmedia](https://www.itmedia.co.jp/business/articles/1801/10/news097.html)・[政治山](https://seijiyama.jp/article/news/omn20171222-4.html) |
| Why | 振込先の変更をメールだけで受けた |
| How | 航空機のリース料と貨物の支払い |
| How much | 約3億8,400万円（リース料 約3億6,000万円＋貨物 約2,400万円） |

### F4 トヨタ紡織の欧州子会社 — 偽の指示で送金

| 項目 | 内容 |
|---|---|
| Who | トヨタ紡織の欧州子会社 |
| What | 偽の指示による送金 |
| When | 公表 2019-09-06 |
| Where | [Forbes JAPAN](https://forbesjapan.com/articles/detail/29551) |
| How much | 約40億円 |
| 対処の案内 | 口座の変更は電話で確かめるよう公的機関が案内している、とする報道がある（出典の原文は未確認） |

### F9 FBI IC3 — ビジネスメール詐欺の被害（米国 2024 年）

| 項目 | 内容 |
|---|---|
| Who | FBI のインターネット犯罪苦情センター（IC3） |
| When | 2024 年 |
| Where | [IC3 2024 report](https://www.ic3.gov/AnnualReport/Reports/2024_IC3Report.pdf) |
| How much | 被害 2,770,151,146 ドル、届け出 21,442 件 |

### F6 Lovable — RLS の付け忘れで表が外から読めた

| 項目 | 内容 |
|---|---|
| Who | Lovable で作られたアプリ（CVE-2025-48757） |
| What | 行ごとの見える範囲の決まり（RLS）が無い・弱い表が外から読めた |
| When | 2025 年 |
| Where | [Superblocks](https://www.superblocks.com/blog/lovable-rls-breach) |
| How much | 1,645 件中 170 件（10.3%）、303 の口 |
| 当てはめ | 新しい4表は A21（他社が見えない）と A22（全会社で RLS を比べる）で試験する |

### F10 RLS の会社の切り替え漏れ（実験）

| 項目 | 内容 |
|---|---|
| What | PgBouncer の後ろで `SET`（`SET LOCAL` でない）を使うと、次の客に前の会社の値が残った |
| Where | [daily.dev](https://daily.dev/posts/postgresql-row-level-security-for-saas-what-we-measured-wxhmymmnr) |
| How much | 請求書 267,023 件が次の客に見えた（PostgreSQL 17 の実験。個人のブログの実験で、第三者の確かめは未確認） |
| 当てはめ | 社内の ADR-072（commit 後に reset_tenant_context）と lint の Rule B・C が同じ漏れを止めている |

## 見つからなかったもの

- 「一覧＋種類ごとの詳細」と「1表に全部」を、速さ・不具合の数で比べた公開の測定。GitLab・Stripe とも形の決まりで、数値は載っていない。
- Wise のメール送金で日本円が届くかの公式の確約。公式の説明は、受け取りは7日以内、100万円を超える額・米ドルの Swift 宛・Swift の口座情報宛はできない、まで。実際に届くかは試しの送金で確かめる（design.md §3-4）。

## 適用の限界

- 被害額（F3・F4・F8・F9）は、振込先の差し替えが起きたときの大きさの根拠で、この設計で防げる額ではない。この設計は「記録が残る」「発行済みの請求書が後から変わらない」までを約束する。
- F1・F2 は形の根拠で、成功の数値ではない。
- 数値の照合（審査役の Web 検索 2026-11-10）: Lovable の 170／1,645（10.3%）と 303 の口は一致。IC3 の 21,442 件と約 27.7 億ドルは一致（1ドル単位の値は元の PDF で未確認）。UK Finance の 4億5,000万ポンド台・−2%・件数 −20% は一致。
