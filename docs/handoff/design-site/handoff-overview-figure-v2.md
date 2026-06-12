# 実装指示書: 設計図書サイト「全体図 — データの流れ」差し替え（v2）

**作成**: Planner（Web Claude）／**承認**: Shingo（2026-06-13 見た目合意済み）
**正本根拠**: ADR-095（注文から書類を自動生成・CRM/SFA分離）、ADR-096（商談＝SFAフロー）、ADR-101（見積は登録前でも発行可・承認で請求書へ変換）、ADR-104（入金確認後に発送）
**G4指摘対応**: ①商談が図に不在 ②見積書が時系列と逆順に見える — の2点を解消する

---

## 0. 作業ルール（最重要）

- 本書のコードと文言を**一字一句そのまま**使用する。改善・言い換え・並び替え・色変更・要素追加を一切しない。
- 変更対象は **§2で特定するブロックのみ**。ナビ・他セクション・CSS定義・他ページの本文には触れない。
- 不明点・既存構造と本書の前提が食い違う場合は、**作業を止めて差分を報告**する（推測で進めない）。
- docs-only 変更。PR タイトル: `docs(design-site): 全体図v2 — 商談追加・書類を時系列順に再構成（G4指摘対応）`

---

## 1. 変更内容の要約（What）

`docs/design-site/index.html` の「全体図 — データの流れ」セクションにある図ブロック（旧SVG＋凡例＋キャプション）を、§3 の完成コードに**丸ごと置換**する。

旧図との違い（参考情報。実装判断には使わない）:
- 商談（SFA・破線）を顧客マスタと注文の間に追加
- 派生書類4枚を扇形配置→時系列の鎖（見積書→請求書→出荷予定→顧客実績）に変更
- 各書類に「いつ生まれるか」のタグを追加
- 凡例をSVG内蔵に変更
- 注記（注文レコードは見積段階から育つ）を追加

---

## 2. 置換対象の特定方法

1. `docs/design-site/index.html` 内で見出し `全体図 — データの流れ` を検索する。
2. その見出しに属する図ブロック全体＝「旧 `<svg>`」「旧凡例マークアップ（SVG外のHTMLとして存在する場合はそれも）」「旧キャプション段落（『人が手入力するのは…』で始まる `<p>`）」を置換範囲とする。
3. セクション見出し自体は変更しない。
4. 置換後、`grep -rl "見積書" docs/design-site/ --include="*.html"` で**同一の旧全体図SVGが他ページ（sa-01.html等）にも埋め込まれていないか確認**する。埋め込みがあれば、そのページの図も §3 と同一コードに置換する。無ければ index.html のみ。

---

## 3. 完成コード（このブロックをそのまま貼る）

```html
<div style="overflow-x:auto">
<svg width="100%" style="min-width:900px" viewBox="0 0 1000 520" role="img" xmlns="http://www.w3.org/2000/svg">
<title>全体図 — データの流れ</title>
<desc>顧客マスタから商談を経て注文に至り、注文から見積書・請求書・出荷予定・顧客実績が時間順に自動生成される</desc>
<defs>
<marker id="arwB" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="#3B82F6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker>
<marker id="arwG" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="#16A34A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker>
<marker id="arwN" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" stroke="#9CA3AF" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker>
</defs>
<rect x="40" y="40" width="220" height="72" rx="10" fill="#EFF6FF" stroke="#3B82F6" stroke-width="1.5"/>
<text x="150" y="67" text-anchor="middle" dominant-baseline="central" font-size="16" font-weight="700" fill="#1D4ED8">顧客マスタ</text>
<text x="150" y="93" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#3B82F6">背骨①・誰に売るか</text>
<rect x="330" y="40" width="220" height="72" rx="10" fill="#EFF6FF" stroke="#3B82F6" stroke-width="1.5" stroke-dasharray="8 5"/>
<text x="440" y="67" text-anchor="middle" dominant-baseline="central" font-size="16" font-weight="700" fill="#1D4ED8">商談（SFA）</text>
<text x="440" y="93" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#3B82F6">初成約までのフロー</text>
<rect x="700" y="40" width="260" height="72" rx="10" fill="#F0FDF4" stroke="#22C55E" stroke-width="1.5"/>
<text x="830" y="67" text-anchor="middle" dominant-baseline="central" font-size="16" font-weight="700" fill="#15803D">商品・在庫マスタ</text>
<text x="830" y="93" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#16A34A">背骨②・何を売るか</text>
<line x1="262" y1="76" x2="324" y2="76" stroke="#3B82F6" stroke-width="2" marker-end="url(#arwB)"/>
<line x1="440" y1="116" x2="487" y2="155" stroke="#3B82F6" stroke-width="2" marker-end="url(#arwB)"/>
<line x1="830" y1="116" x2="566" y2="187" stroke="#16A34A" stroke-width="2" marker-end="url(#arwG)"/>
<polygon points="500,160 600,210 500,260 400,210" fill="#FFF7ED" stroke="#EA580C" stroke-width="2"/>
<text x="500" y="200" text-anchor="middle" dominant-baseline="central" font-size="17" font-weight="700" fill="#C2410C">注文</text>
<text x="500" y="226" text-anchor="middle" dominant-baseline="central" font-size="12.5" fill="#EA580C">交差点</text>
<path d="M500 262 L500 300 L140 300 L140 324" fill="none" stroke="#9CA3AF" stroke-width="2" marker-end="url(#arwN)"/>
<rect x="40" y="330" width="200" height="76" rx="10" fill="#F9FAFB" stroke="#D1D5DB" stroke-width="1.5"/>
<text x="140" y="358" text-anchor="middle" dominant-baseline="central" font-size="15" font-weight="700" fill="#374151">📄 見積書</text>
<text x="140" y="386" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#6B7280">自動生成・見積段階で発行</text>
<rect x="280" y="330" width="200" height="76" rx="10" fill="#F9FAFB" stroke="#D1D5DB" stroke-width="1.5"/>
<text x="380" y="358" text-anchor="middle" dominant-baseline="central" font-size="15" font-weight="700" fill="#374151">📄 請求書</text>
<text x="380" y="386" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#6B7280">自動生成・見積承認で変換</text>
<rect x="520" y="330" width="200" height="76" rx="10" fill="#F9FAFB" stroke="#D1D5DB" stroke-width="1.5"/>
<text x="620" y="358" text-anchor="middle" dominant-baseline="central" font-size="15" font-weight="700" fill="#374151">🚚 出荷予定</text>
<text x="620" y="386" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#6B7280">自動生成・入金確認後</text>
<rect x="760" y="330" width="200" height="76" rx="10" fill="#F9FAFB" stroke="#D1D5DB" stroke-width="1.5"/>
<text x="860" y="358" text-anchor="middle" dominant-baseline="central" font-size="15" font-weight="700" fill="#374151">📊 顧客実績</text>
<text x="860" y="386" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#6B7280">自動集計・完了後に反映</text>
<line x1="242" y1="368" x2="276" y2="368" stroke="#9CA3AF" stroke-width="2" marker-end="url(#arwN)"/>
<line x1="482" y1="368" x2="516" y2="368" stroke="#9CA3AF" stroke-width="2" marker-end="url(#arwN)"/>
<line x1="722" y1="368" x2="756" y2="368" stroke="#9CA3AF" stroke-width="2" marker-end="url(#arwN)"/>
<text x="860" y="434" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#9CA3AF">↻ 顧客カルテに自動表示</text>
<rect x="40" y="470" width="14" height="14" rx="3" fill="#EFF6FF" stroke="#3B82F6"/>
<text x="62" y="477" dominant-baseline="central" font-size="12.5" fill="#4B5563">顧客（背骨①）</text>
<rect x="200" y="470" width="14" height="14" rx="3" fill="#F0FDF4" stroke="#22C55E"/>
<text x="222" y="477" dominant-baseline="central" font-size="12.5" fill="#4B5563">商品・在庫（背骨②）</text>
<rect x="420" y="470" width="14" height="14" rx="3" fill="#FFF7ED" stroke="#EA580C"/>
<text x="442" y="477" dominant-baseline="central" font-size="12.5" fill="#4B5563">注文（交差点）</text>
<rect x="590" y="470" width="14" height="14" rx="3" fill="#F9FAFB" stroke="#9CA3AF"/>
<text x="612" y="477" dominant-baseline="central" font-size="12.5" fill="#4B5563">自動生成・派生値</text>
<rect x="770" y="470" width="14" height="14" rx="3" fill="#EFF6FF" stroke="#3B82F6" stroke-dasharray="4 3"/>
<text x="792" y="477" dominant-baseline="central" font-size="12.5" fill="#4B5563">商談＝フロー（破線）</text>
</svg>
</div>
```

続けて、図の直下に以下の2段落を置く。**1段落目は既存キャプションと同じクラス／スタイルを流用して文言だけ差し替える**。2段落目（注記）は、既存に注記用スタイルが無ければ `style="font-size:13px;color:#6B7280"` をそのまま付与する。

```html
<p>人が手入力するのは各マスタの「属性」と商談の記録だけ。書類・実績はすべて注文から自動導出（派生値）。</p>
<p style="font-size:13px;color:#6B7280">※ 注文のレコードは「見積段階」から存在して育ちます。見積書は商談中（顧客登録前でも）発行でき、承認されると請求書へ変換＝受注確定となります（正本: ADR-101）。</p>
```

---

## 4. 検証チェックリスト（PR本文に結果を記載）

- [ ] index.html の旧図ブロック（旧SVG・旧凡例・旧キャプション）が残存していない
- [ ] §2-4 の grep 結果（他ページの同一図の有無と対応）を記載
- [ ] CI 緑
- [ ] デプロイ後、`/design/` で新図が表示される（認証つき・smoke 全パス）
- [ ] スマホ幅で図ブロックが横スクロールできる（`overflow-x:auto` が効いている）
- [ ] 図中の文言が本書 §3 と一字一句一致（diff で確認）

---

## 5. 本書の根拠（変更しない・参照のみ）

| 図の要素 | 根拠 |
|---|---|
| 商談を顧客の世界（青・破線）に追加 | ADR-095「CRM＝顧客（ストック）／SFA＝商談（フロー）」、ADR-096「商談＝初成約までの一時プロセス」 |
| 書類4枚を時系列の鎖に | ADR-095 KGI「受注→見積→請求→入金→発送→完了」 |
| 見積書「見積段階で発行」 | ADR-101「登録フォーム前でも発行可能」 |
| 請求書「見積承認で変換」 | ADR-101「承認された見積→請求へ変換（QUOTATION→INVOICE差し替え）」 |
| 出荷予定「入金確認後」 | ADR-104（入金→発送） |
| 顧客実績「完了後に自動集計」＋カルテ表示 | ADR-096 自動計算項目（LTV等は注文から集計・手入力禁止） |
