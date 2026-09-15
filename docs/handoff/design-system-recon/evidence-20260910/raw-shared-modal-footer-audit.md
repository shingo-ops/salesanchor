# Modal footer read-only audit

基準: 7606ca9a。git show/git grepとTypeScript構文読取を実行。製品変更0、ブラウザー実行0。

通常Modalの直接利用44箇所を構文走査。明示footerは5（実運用3・見本2）。一覧と行番号はmodal-footer-audit.json。spreadはModal.stories.tsx:29のargsだけで、定義済args:10–17にfooterなし。controls等から任意ReactNodeを渡す操作までは静的列挙の対象外。

## 影響と特殊DOM

- PurchaseDetailPanel.tsx:262–294/304 は3button。末尾submitはform=purchase-detail-form、form本体:309。
- ShippingDetailPanel.tsx:335–367/377 は3button。末尾submitはform=shipping-detail-form、form本体:382。
- PurchaseOrdersFormModal.tsx:129–149 は金額span＋2button。span:131にmarginRight:auto、strongに金額。これは唯一の非button直接子。折返し時も金額と操作の配置、特に大きい金額/日本語/英語を実測する。submitはform=po-form、本体:152。
- Modal.stories.tsx:73 とdesign-preview/sections/ModalSection.tsx:78 は共通Button2個のFragment。
- 全5呼出しのFragmentは実DOM wrapperを増やさない。footer子へのorder/row-reverse等はなし。フォーム所属はform属性で決まり、CSS折返しでは変えない。

## CSS/構造

固定SHA全frontendでcomp-modal-footerはModal.tsx:146の出力とModal.css:82の定義だけ。競合する同selector/子selectorなし。現定義: flex、align-items:center、justify-content:flex-end、gap:space-3、padding、border-top、flex-shrink:0。flex-wrap:wrapのみ追加なら外観色/余白/DOM/イベントを維持し、必要な場合だけ複数行になる。通常Modal以外のloading系は含めない。

Modal.tsx:145はfooter!=null時のみ出力。footerなしの39直接利用には空footerを新設しない。body:72–75はoverflow-y:auto、dialog:27–37は縦flex/max-height/overflow:hidden。折返しでfooter高さが増す分だけbodyの利用高さが減るため、短いviewportでbodyスクロールとfooter表示を測定する必要がある。

Modal.tsx:88–105のTab処理はDOMのfocusable順。CSS折返しはDOM順を変えないが、既存disabled条件を含め実際のTab/Shift+Tab順を測定する。新しいフォーカス移動は今回不要。

## 限界/判定

静的にflex-wrap:wrap先行案を阻害する競合は発見なし。実運用3footerを共通影響範囲として検査すべき。Shippingだけの検査では不足。wrapは単一子のmin-content幅を縮める機能ではないため、極端な長文/大きい金額/拡大で全ケース収まるとは保証しない。親rootが行う実Modalプローブの実測合格前に最終設計合格とはしない。
