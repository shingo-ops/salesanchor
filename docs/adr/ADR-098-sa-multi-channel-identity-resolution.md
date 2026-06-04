# ADR-098: 多チャネル名寄せ＋直リンクテンプレSSOT（ADR-SA-04）

## Status
Accepted（Messenger/Instagramの内部URLのみ実機検証が残る）

## Date
2026-06-04（起案: Hikky-dev / PO: shingo-ops）

## Context（背景）

顧客は複数チャネル（Messenger/Instagram/WhatsApp/Discord/Telegram、将来Email）から来る。プラットフォーム間に「同一人物」を判定する共通キーは無い。

連絡先タブは現状「手入力のURL欄」になっており、以下の問題が混在：
- 旧式：`DISCORD ID = username#0000` は2023年廃止
- 誤リンク：`m.me`/`instagram.com` はスタッフが顧客スレッドを開けない

---

## Decision（What / Why / Scope）

### 確定した設計

#### 1. 名寄せ方針

チャネルをまたいで発言を1顧客に束ねる。**完全自動の同一人物判定は前提にしない**（手動紐付け or 本人申告が現実解）。

#### 2. 保存するのはIDのみ（リンクは保存しない）

リンクはIDから都度自動生成。

| チャネル | 保存するID |
|---|---|
| Messenger | page_id / bm_id / psid |
| Instagram | igsid（＋page_id/bm_id） |
| WhatsApp | phone（国際形式・記号なし） |
| Telegram | username（無ければphone） |
| Discord | guild_id / channel_id |

#### 3. リンクテンプレ表（SSOT）

1か所に持つ（1チャネル＝1行＝「URLの型＋差し込むID」）。型が変わってもこの1か所を直すだけ。

#### 4. 連絡先タブの表示

**IDから自動生成されたクリック要素**に置換。URL文字列は見せない・編集させない。

#### 5. Discord

Bot を OAuth でテナントのサーバーに招待し、guild_id＋channel_id を保存 → `discord.com/channels/{guild_id}/{channel_id}` の安定リンク。

### 仕組み（意図）

IDが真実、リンクは導出。安定3チャネル（WhatsApp/Telegram/Discord）はリスクゼロ。手入力URLの腐敗・旧式混在が消える。

---

## 実装上の注意（誤実装防止）

- **Messenger/Instagram の Business Suite インボックスURLはMeta未文書化の内部URLで壊れ得る。** テンプレ表の**1セルに隔離**し、壊れてもそこだけ直せるようにする。`m.me`/`instagram.com` は使わない（スタッフ起点で顧客スレッドを開けない）。実機検証はMeta担当パートナー領域。
- いま実装でロックすべきは「リンクの形」ではなく **「チャネルごとに何のIDを保存するか」**。
- 名寄せに自動同一判定を組まない（誤マージ事故防止）。
- ※ **チャネル受信の取り込み（webhook/API）本体は別サブシステム＝要設計**（→付録2・会話ログ/多チャネル取り込み）。本ADRは「保存するID」と「リンク生成」を定義する。

---

## 依存・関連

- 会話ログ: ADR-096
- 取り込み（要設計）: ADR-095付録2
- テナント分離: ADR-106
