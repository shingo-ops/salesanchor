# ADR-1008: 「人」の正本は public.users.id 一本にする（名簿 staff は会社内の詳細）

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（PO 方針 2026-10-12「SSOTの定義に基づき正本は1箇所で管理したい」。進め方 design.md §4 に PO「y」2026-10-13。列の削除（P4）は PO 本人の GO を別途要する） |
| 作成日 | 2026-10-12 |
| 起案 | Claude Opus（設計担当） + しんごさん（PO 方針・個別決定） |
| 関連 | ADR-023（スタッフの3層同期・提案）、ADR-091（Discord 接続）、ADR-159（Discord 上のスタッフ識別）、ADR-1003（GO 委任）、ADR-1007（migration は構造だけ）、段階1 #4162、段階2 #4163 |
| 根拠 | docs/handoff/person-ssot-users-id/recon.md、docs/handoff/person-ssot-users-id/design.md |

---

## Context

- 「人」を指す番号が2種類ある。public.users.id（ログインの正本）と tenant.staff.id（会社ごとの名簿）。2026-10-12 の本番では名簿7行のうち users に紐付くのは1行だけだった。
- staff.id を参照する外部キーが43本、users.id を参照する外部キーが32本あり、同じ「担当者」の意味で両方が使われている。
- companies.sales_rep_id は staff.id を参照するのに、analytics.py は users.id として結合しており、t4 の会社42件の担当者が別テナントの人の名前で集計されていた。
- メール・ロール・Firebase の識別が users と staff の両方にあり、名簿の行は「メールの一致」で引かれていた（primary_email に一意制約なし）。

## Decision

1. 人の正本は public.users（1人1行）。is_active=false は「ログイン不可」を表す。
2. 名簿 tenant.staff はその会社の中の詳細（氏名・かな・英字・Discord・電話・在籍状態）。staff.user_id は NOT NULL・UNIQUE で users(id) を参照する。
3. 人を指す列（担当者・作成者・接続した人・送信者・既読者・Bot の持ち主・歩合の対象・カレンダーの持ち主など）は users(id) を参照する。新しく足す列も同じ。名簿の付属表（staff_emails・staff_ui_preferences）だけは staff.id のままとする。
4. ロールは user_roles だけ（段階2 #4163）。メールは users.email だけ。名簿の重複列（staff.role_id・staff.primary_email・staff.firebase_uid）と users.role は削除する（削除は PO 本人の GO）。
5. 名簿に人を足すときは、users・staff・user_roles を1つのトランザクションで作る。原則としてログインする人だけを登録し、ログインしない人は users に is_active=false で持つ。

### PO の個別決定（2026-10-12・原文）

- t6 の商談8件（leads.assigned_to=10）の担当者: 「review@（ログイン用の10番）にする： 8件を review@ の担当として付け替えます。」
- ログインしない人の扱い: 「y 基本的にログインする人間しか登録しない」
- t4 staff 7（review@ と同じメール）: 「y」（問い: 7番の人を tenant 4 の名簿から外してよいですか）

## Why

- ログイン・権限（user_roles）・目標・カレンダー・分析がすでに users.id で動いている。staff を正本にすると、それらすべてを作り直すことになる。
- users は public（全テナント共通）、staff はテナントごとの表なので、1つの表に統合するとテナント分離の作りを壊す。
- 番号の種類が混ざった列は、数値が偶然一致すると別人として黙って結合される（t4 の42件で実際に起きた）。

## Consequences

| 弊害 | 対処 |
|---|---|
| 列の参照先の変更と値の付け替えを、migration（構造）とデータ変更（値）に分けるため、デプロイ直後の短い間は値が古い番号のまま残る | 各 PR の本番確認の直後に、値の付け替え（D1〜D3）を行う。悪化する点が無いことを design.md §6 で確認済み |
| 列名を *_user_id に改めるため、API の項目名と画面が変わる | 同じ PR で API・画面・試験を直す |
| ログインしない人にも users 行（is_active=false）ができる | users を起点に全行を並べる処理は無い（recon.md）。ログイン判定は is_active=TRUE が条件 |

## 外部事例

該当事例なし。1つの実体を1つの表で持つという正規化の原則にのみ依拠する。
