# §Z 担当限定の文書レビュー

対象: /Users/tanizawashingo/worktrees/salesanchor/release-frontend-ssot-contracts/docs/specs/design-system/design.md §Z。HEAD d715d998877e899206ba9bb4f82c726fc3175b30 上の作業中文書を読取。製品・正式文書は変更していない。本レビューは限定されたAPI契約の照合であり、全体設計の独立第二者レビューとは称さない。

除外: remaining-components旧版と最新/tmpの既知差分、bucket→既存badgeVariant実CSSへの訂正、Card状態追加（root修正予定）。実装後の表示・操作試験が未実施であること自体は設計不合格理由にしない。

## 修正が必要な事項

### 1. 裸本体1要素とleadingIcon ReactNodeが両立しない

- design.md:796はinput/select/textareaを1個返しdiv/labelを増やさない。
- :813は同じ本体propsへleadingIcon?:ReactNodeを定義。
- inputは子要素を描画できず、select/textareaへ任意アイコンReactNodeを子として挿入する設計にもできない。兄弟要素やwrapperを追加する場合は1要素契約から外れる。
- 修正案: 裸本体はleadingInset等の既存アイコン用余白だけ受け、実アイコンは既存外側ownerが保持する。アイコンを描画する別の合成部品を作る場合は、裸本体の契約と別のprops表にする。

### 2. SelectControlのappearance公開値と新表の値が矛盾

- design.md:796は既存SelectControlを拡張して互換維持する方針。
- :812はappearance=standard/embeddedを本体共通propsとして定義。
- 実物 Select.tsx:28,39-46はappearance=field/bare（既定bare）。Select.tsx:120は内部呼出しでfieldを渡す。
- 未指定時のbare幅autoとfield幅100%の差もある。field/bareを単にstandardへまとめると幅・class条件が消える。
- 修正案: SelectControlのfield/bareを公開互換として維持し、新しいsurfaceAppearance等の別軸を定義するか、appearance表をTextFieldControl/TextareaControlだけに限定する。旧値→新挙動・既定値の対応を明記する。

### 3. EmptyStateのReactNode拡張と既存p要素の整合が未定義

- design.md:872でtitle/descriptionをReactNodeへ拡張。
- 実物 EmptyState.tsx:52,54はp要素内へそのまま挿入する。
- ReactNodeはdiv/p/複数ブロックを含められるため、既存pのまま全ReactNodeを保証すると不正なHTMLの入れ子を許す。
- 修正案: 今回抽出した利用元は文字列のtitleへ分離可能なので、文字・inline内容に限定する契約を記載するか、blockを受けるslotのDOMをdivへ明示変更する。元のchildren=<p>をtitle={<p>}としてそのまま渡さない。単なる型拡張だけでは完了しない。

### 4. TabsのbuttonAttributesと共通管理属性・二重callbackの優先順位が未定義

- design.md:870はnative安全属性と既存onClick(event)を受け、順序を利用元で保存する。
- 現在 Tabs.tsx:74-88はrole/type/aria-selected/disabled/className/onClickを本体が固定所有し、disabledでなければonChange(key)を実行する。
- 新しいnative属性転送の後先でdisabled/type/roleが上書きされる可能性がある。item.onClick内で既に状態更新する場合、続くonChangeが同じ更新を再実行する設計にもなり得る。
- 修正案: buttonAttributes型から共通所有するrole/type/aria-selected/disabled/className/styleとonClickを除外し、onClick(event)を独立した項目callbackとする。disabled時は両方実行しない。onClick→onChangeなのか、preventDefault時にonChangeを抑止するのか、項目callback自身が更新を持つ場合の扱いを明記する。既存の処理順を保つ対象を1つのcallbackへまとめる案でもよいが、二重更新を避ける契約が必要。

## 実装カード前に明示するとよい範囲

- design.md:800のnativeSizeはinput/selectだけに適用する。textareaにはnative size属性がないため、共通全本体へ無差別転送しない。
- :809 invalidとnative aria-invalidが同時指定された際、同値維持/共通エラー状態のどちらを優先するかを明記する。現在のフォームwrapperはerror時にaria-invalidを自動付与しておらず、この付与自体は同値移管ではない。
- :818の配置class入口は、既存classNameを制限された型へ狭めるのかlayoutClassNameを新設するのかをカードで一意にする。SelectのclassNameは外側div、SelectControlはnativeという契約は明記済みで妥当。

## 結論

上記1〜4は、実装者が解釈しないと公開API/DOM/操作が決まらない。担当限定判定はREVISE。根拠のある矛盾と未定義を挙げたものであり、未実装のブラウザーテストを設計完了の前提にしていない。

## 最新追記の再照合

root通知後に§Z末尾を再読取。CSSI-0231 indicator=none、CSSI-0233 resize=none、CSSI-0038 Checkbox所有、karte-toggle-btn 1279px、Card状態4種の追記を確認。bucket訂正とCard状態の既知残件は指摘対象外のままとした。

上記1〜4は最新追記後にも残る。特にSelectControlは末尾でindicator=noneという追加propsも確定したので、appearance=standard/embeddedと既存field/bareの互換表を同じ節へ揃える必要がある。これは表示テスト待ちではなく公開API語彙の整合問題。

## 4指摘修正後の再レビュー

§Z:796,800,809,812-813,870,872,900-906を再確認。

1. leadingInset booleanでinputの余白だけ指定し外側アイコン保持: 解消。
2. Select field/bare/defaultbareを保持しstandard/embeddedは別部品のみ: 解消。
3. EmptyState string+p保持、detailsはdescription後action前のdivで未指定時DOMなし: 解消。
4. item onClickを追加せずonChange(key,event)1入口、disabled時呼出しなし、buttonAttributes所有key除外: 二重callback・所有権問題は解消。

付記したnativeSize適用要素、aria-invalid非自動変更、layoutClassNameの同DOM適用と配置限定も反映済み。

### 新規1点: イベントの型

最新design.md:870はonChange第2引数を「native MouseEvent」と記載する。現行React onClickに渡されるイベントはReact.MouseEvent<HTMLButtonElement>であり、DOMのMouseEventではない。既存イベント契約を保存するならReact.MouseEvent<HTMLButtonElement>を変換せず同じオブジェクトのまま渡すと明記する必要がある。event.nativeEventへ変換するとReactイベントのcurrentTarget等の契約が変わる。

今回の範囲で残る修正はこのイベント型表記1点。全体設計・実装の合格を意味しない。

## 最終判定（文言訂正案と保存状態の区別）

rootが提示した最終文言「React.MouseEvent<HTMLButtonElement>を変換せず第2引数で渡す（event.nativeEventへ変換しない）」を採用する限定API契約案はAPPROVE。最初の4指摘とイベント型の論点は、この文言で全て解消し、担当範囲の追加残件なし。これは全体設計の独立第二者審査・実装結果の承認ではない。

最終ファイル確認時点ではdesign.md:870がまだ旧「native MouseEvent」だったため、正式文書への訂正保存済みとは宣言しない。rootはこの1文の保存を確認してから、本報告の限定APPROVEを確定文書へ反映すること。
