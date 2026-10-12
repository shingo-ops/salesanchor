# 段階1 ベースライン測定結果（生データ）

> この文書は何か（専門用語なしの1行）: 受信箱をスマホ・タブレット・PCの3つの幅で撮影し、横にはみ出した量と44px未満の押す部品の数を、コマンドで集計した記録。直してはいない。

コマンド: `cd frontend && npx playwright test --project=vl-mobile-390 --project=vl-tablet-768 --project=vl-desktop-1280`（モックデータ・ライト表示・Playwright 1.59.1）。以下の表は同じ JSON から node で機械集計した値で、手で数えていない。

状態の定義: A = 初期表示（goto 直後、操作なし） / B = "Taro Sender" をクリックした後。**一覧のみの状態は今回の測定対象外（初期表示で会話が選択されるため）。**

## 集計（scrollWidth − innerWidth / 44px未満の件数）

| 幅(project) | 状態 | scrollWidth | innerWidth | scrollWidth − innerWidth | 表示中の操作部品数 | 44px未満の件数 |
|---|---|---|---|---|---|---|
| vl-mobile-390 | A | 390 | 390 | 0 | 52 | 33 |
| vl-mobile-390 | B | 390 | 390 | 0 | 52 | 33 |
| vl-tablet-768 | A | 768 | 768 | 0 | 55 | 46 |
| vl-tablet-768 | B | 768 | 768 | 0 | 55 | 46 |
| vl-desktop-1280 | A | 1280 | 1280 | 0 | 53 | 44 |
| vl-desktop-1280 | B | 1280 | 1280 | 0 | 53 | 44 |

## 観察事実

### (a) A と B は同一

A と B の指標（上表の全列と区画の測定値）は3幅とも同じ（node で比較し3幅とも true）。画像の md5 は、下の採用した1回分では3幅とも A と B が同じ。md5 の生出力:

```
MD5 (vl-desktop-1280-A.png) = 9c2ae8ee783a81c2ac16c1eea70eeaca
MD5 (vl-desktop-1280-B.png) = 9c2ae8ee783a81c2ac16c1eea70eeaca
MD5 (vl-mobile-390-A.png) = d49218b2bb5708f5537e94aad670178c
MD5 (vl-mobile-390-B.png) = d49218b2bb5708f5537e94aad670178c
MD5 (vl-tablet-768-A.png) = 055d6d860ac2ccbe7d99255de6485dd8
MD5 (vl-tablet-768-B.png) = 055d6d860ac2ccbe7d99255de6485dd8
```

**撮影のばらつき（観察）**: 同じコマンドを4回実行したうち、vl-tablet-768 の B の画像だけが2回、A と異なる md5 になった（その画像では一覧が「読み込み中…」の表示に戻っていた）。数値は4回とも A と B で同一。下の画像と JSON は4回目（全6枚で A と B の md5 が一致した回）のもの。

### (b) 初期表示(A)で見えている区画（isVisible() と boundingBox を spec 内で測定。目視ではない）

isVisible = Playwright の `locator.isVisible()`。画面内 = boundingBox が viewport（幅×高さ）と交わるか（node で算出）。

| 幅 | viewport | 会話一覧 `.inbox-conversation-list` | メッセージ表示 `.inbox-center-header` | 右のカルテ `.inbox-right-panel` |
|---|---|---|---|---|
| vl-mobile-390 | 390x844 | isVisible=true / 画面内=true / x=12,y=325,w=378,h=276 | isVisible=true / 画面内=true / x=12,y=602,w=378,h=81 | isVisible=true / 画面内=false / x=0,y=844,w=390,h=675 |
| vl-tablet-768 | 768x1024 | isVisible=true / 画面内=true / x=66,y=223,w=245,h=801 | isVisible=true / 画面内=true / x=312,y=132,w=456,h=81 | isVisible=true / 画面内=false / x=768,y=0,w=396,h=1024 |
| vl-desktop-1280 | 1280x900 | isVisible=true / 画面内=true / x=66,y=223,w=442,h=677 | isVisible=true / 画面内=true / x=509,y=132,w=361,h=81 | isVisible=true / 画面内=true / x=884,y=78,w=396,h=822 |

### (c) 原因（コード上の該当行。読むだけで変更していない）

`frontend/src/pages/inbox/useInboxState.ts`

```ts
  const [searchParams, setSearchParams] = useSearchParams();
  const initialLeadIdRaw = searchParams.get("lead_id");
  const initialLeadId = initialLeadIdRaw && !isNaN(Number(initialLeadIdRaw))
    ? Number(initialLeadIdRaw)
    : null;
```

(行 168-172。`lead_id` の URL パラメータから初期値を作る。`/lead-chat` を開くだけなら null)

```ts
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(initialLeadId);
```

(行 199)

```ts
  // 初期表示: 会話未選択かつ一覧が存在する場合、先頭を自動選択
  useEffect(() => {
    if (selectedLeadId !== null || convLoading || filteredConversations.length === 0) return;
    selectLead(filteredConversations[0].lead_id);
  }, [filteredConversations, selectedLeadId, convLoading, selectLead]);
```

(行 625-629。会話が未選択・読み込み完了・一覧が1件以上のとき、先頭の会話を自動で選ぶ。`initialLeadId` の出どころは行 169 の `searchParams.get("lead_id")`)

## 撮影画像

- stage1/vl-mobile-390-A.png
- stage1/vl-mobile-390-B.png
- stage1/vl-tablet-768-A.png
- stage1/vl-tablet-768-B.png
- stage1/vl-desktop-1280-A.png
- stage1/vl-desktop-1280-B.png

## 生JSON（testInfo.attach("metrics") の中身そのまま）

### vl-mobile-390 / A

```json
{
  "project": "vl-mobile-390",
  "state": "A",
  "overflow": {
    "scrollWidth": 390,
    "innerWidth": 390,
    "diff": 0
  },
  "visibleInteractiveCount": 52,
  "smallTargetCount": 33,
  "smallTargets": [
    {
      "element": "button",
      "className": "icon-btn",
      "label": "受信箱の設定",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab active",
      "label": "すべてのメッセージ",
      "width": 160.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "リード",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "商談中",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "既存顧客",
      "width": 89.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "追客",
      "width": 60.8,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "アーカイブ",
      "width": 102.9,
      "height": 36
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "プラットフォーム",
      "width": 146,
      "height": 36
    },
    {
      "element": "input",
      "className": "search-input-field inbox-search-input",
      "label": "",
      "width": 281.8,
      "height": 37
    },
    {
      "element": "button",
      "className": "inbox-manage-btn",
      "label": "管理",
      "width": 72.2,
      "height": 35
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "未読",
      "width": 44.8,
      "height": 29.6
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "フォローアップ",
      "width": 114.5,
      "height": 29.6
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "送信先言語",
      "width": 74,
      "height": 36
    },
    {
      "element": "button",
      "className": "karte-toggle-btn",
      "label": "顧客情報",
      "width": 92,
      "height": 28
    },
    {
      "element": "button",
      "className": "inbox-header-menu-btn",
      "label": "その他の操作",
      "width": 38,
      "height": 38
    },
    {
      "element": "button",
      "className": "msg-translate-btn",
      "label": "翻訳",
      "width": 18,
      "height": 18
    },
    {
      "element": "textarea",
      "className": "inbox-textarea",
      "label": "",
      "width": 188,
      "height": 40.3
    },
    {
      "element": "input",
      "className": "sr-only",
      "label": "画像を添付",
      "width": 1,
      "height": 1
    },
    {
      "element": "button",
      "className": "send-attach-btn",
      "label": "画像を添付",
      "width": 28,
      "height": 28
    },
    {
      "element": "button",
      "className": "inbox-send-btn",
      "label": "送信",
      "width": 32,
      "height": 32
    },
    {
      "element": "button",
      "className": "karte-close-btn",
      "label": "閉じる",
      "width": 24,
      "height": 24
    },
    {
      "element": "button",
      "className": "karte-open-link",
      "label": "顧客ページを開く →",
      "width": 111,
      "height": 18
    },
    {
      "element": "input",
      "className": "right-panel-field karte-field-empty",
      "label": "",
      "width": 366,
      "height": 33.6
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—24h以内3日以内3日超",
      "width": 366,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—高中低",
      "width": 366,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—未確認競合あり",
      "width": 366,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—小中大",
      "width": 366,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 366,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 366,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 366,
      "height": 31
    },
    {
      "element": "button",
      "className": "mobile-menu-action",
      "label": "ダークモード",
      "width": 358,
      "height": 42
    },
    {
      "element": "button",
      "className": "mobile-menu-action",
      "label": "英語",
      "width": 358,
      "height": 42
    },
    {
      "element": "button",
      "className": "mobile-menu-action mobile-menu-action--danger",
      "label": "サインアウト",
      "width": 358,
      "height": 42
    }
  ],
  "panes": {
    "conversationList": {
      "selector": ".inbox-conversation-list",
      "isVisible": true,
      "boundingBox": {
        "x": 12,
        "y": 325,
        "width": 378,
        "height": 276
      }
    },
    "messageThread": {
      "selector": ".inbox-center-header",
      "isVisible": true,
      "boundingBox": {
        "x": 12,
        "y": 602,
        "width": 378,
        "height": 81
      }
    },
    "karteRightPanel": {
      "selector": ".inbox-right-panel",
      "isVisible": true,
      "boundingBox": {
        "x": 0,
        "y": 844,
        "width": 390,
        "height": 675
      }
    }
  }
}
```

### vl-mobile-390 / B

```json
{
  "project": "vl-mobile-390",
  "state": "B",
  "overflow": {
    "scrollWidth": 390,
    "innerWidth": 390,
    "diff": 0
  },
  "visibleInteractiveCount": 52,
  "smallTargetCount": 33,
  "smallTargets": [
    {
      "element": "button",
      "className": "icon-btn",
      "label": "受信箱の設定",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab active",
      "label": "すべてのメッセージ",
      "width": 160.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "リード",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "商談中",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "既存顧客",
      "width": 89.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "追客",
      "width": 60.8,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "アーカイブ",
      "width": 102.9,
      "height": 36
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "プラットフォーム",
      "width": 146,
      "height": 36
    },
    {
      "element": "input",
      "className": "search-input-field inbox-search-input",
      "label": "",
      "width": 281.8,
      "height": 37
    },
    {
      "element": "button",
      "className": "inbox-manage-btn",
      "label": "管理",
      "width": 72.2,
      "height": 35
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "未読",
      "width": 44.8,
      "height": 29.6
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "フォローアップ",
      "width": 114.5,
      "height": 29.6
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "送信先言語",
      "width": 74,
      "height": 36
    },
    {
      "element": "button",
      "className": "karte-toggle-btn",
      "label": "顧客情報",
      "width": 92,
      "height": 28
    },
    {
      "element": "button",
      "className": "inbox-header-menu-btn",
      "label": "その他の操作",
      "width": 38,
      "height": 38
    },
    {
      "element": "button",
      "className": "msg-translate-btn",
      "label": "翻訳",
      "width": 18,
      "height": 18
    },
    {
      "element": "textarea",
      "className": "inbox-textarea",
      "label": "",
      "width": 188,
      "height": 40.3
    },
    {
      "element": "input",
      "className": "sr-only",
      "label": "画像を添付",
      "width": 1,
      "height": 1
    },
    {
      "element": "button",
      "className": "send-attach-btn",
      "label": "画像を添付",
      "width": 28,
      "height": 28
    },
    {
      "element": "button",
      "className": "inbox-send-btn",
      "label": "送信",
      "width": 32,
      "height": 32
    },
    {
      "element": "button",
      "className": "karte-close-btn",
      "label": "閉じる",
      "width": 24,
      "height": 24
    },
    {
      "element": "button",
      "className": "karte-open-link",
      "label": "顧客ページを開く →",
      "width": 111,
      "height": 18
    },
    {
      "element": "input",
      "className": "right-panel-field karte-field-empty",
      "label": "",
      "width": 366,
      "height": 33.6
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—24h以内3日以内3日超",
      "width": 366,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—高中低",
      "width": 366,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—未確認競合あり",
      "width": 366,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—小中大",
      "width": 366,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 366,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 366,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 366,
      "height": 31
    },
    {
      "element": "button",
      "className": "mobile-menu-action",
      "label": "ダークモード",
      "width": 358,
      "height": 42
    },
    {
      "element": "button",
      "className": "mobile-menu-action",
      "label": "英語",
      "width": 358,
      "height": 42
    },
    {
      "element": "button",
      "className": "mobile-menu-action mobile-menu-action--danger",
      "label": "サインアウト",
      "width": 358,
      "height": 42
    }
  ],
  "panes": {
    "conversationList": {
      "selector": ".inbox-conversation-list",
      "isVisible": true,
      "boundingBox": {
        "x": 12,
        "y": 325,
        "width": 378,
        "height": 276
      }
    },
    "messageThread": {
      "selector": ".inbox-center-header",
      "isVisible": true,
      "boundingBox": {
        "x": 12,
        "y": 602,
        "width": 378,
        "height": 81
      }
    },
    "karteRightPanel": {
      "selector": ".inbox-right-panel",
      "isVisible": true,
      "boundingBox": {
        "x": 0,
        "y": 844,
        "width": 390,
        "height": 675
      }
    }
  }
}
```

### vl-tablet-768 / A

```json
{
  "project": "vl-tablet-768",
  "state": "A",
  "overflow": {
    "scrollWidth": 768,
    "innerWidth": 768,
    "diff": 0
  },
  "visibleInteractiveCount": 55,
  "smallTargetCount": 46,
  "smallTargets": [
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "ダッシュボード",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "スケジュール",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item active",
      "label": "受信箱3",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "在庫表",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "発注管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "見積・請求管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "顧客管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "管理センター",
      "width": 53,
      "height": 42
    },
    {
      "element": "button",
      "className": "comp-btn comp-btn--ghost",
      "label": "テンプレート",
      "width": 121.8,
      "height": 36
    },
    {
      "element": "button",
      "className": "comp-btn comp-btn--ghost",
      "label": "FAQ",
      "width": 70,
      "height": 36
    },
    {
      "element": "button",
      "className": "icon-btn",
      "label": "受信箱の設定",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab active",
      "label": "すべてのメッセージ",
      "width": 160.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "リード",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "商談中",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "既存顧客",
      "width": 89.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "追客",
      "width": 60.8,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "アーカイブ",
      "width": 102.9,
      "height": 36
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "プラットフォーム",
      "width": 146,
      "height": 36
    },
    {
      "element": "input",
      "className": "search-input-field inbox-search-input",
      "label": "",
      "width": 144.5,
      "height": 37
    },
    {
      "element": "button",
      "className": "inbox-manage-btn",
      "label": "管理",
      "width": 72.2,
      "height": 35
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "未読",
      "width": 44.8,
      "height": 29.6
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "フォローアップ",
      "width": 114.5,
      "height": 29.6
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "送信先言語",
      "width": 74,
      "height": 36
    },
    {
      "element": "button",
      "className": "karte-toggle-btn",
      "label": "顧客情報",
      "width": 92,
      "height": 28
    },
    {
      "element": "button",
      "className": "inbox-header-menu-btn",
      "label": "その他の操作",
      "width": 38,
      "height": 38
    },
    {
      "element": "button",
      "className": "msg-translate-btn",
      "label": "翻訳",
      "width": 18,
      "height": 18
    },
    {
      "element": "textarea",
      "className": "inbox-textarea",
      "label": "",
      "width": 262.3,
      "height": 40.3
    },
    {
      "element": "input",
      "className": "sr-only",
      "label": "画像を添付",
      "width": 1,
      "height": 1
    },
    {
      "element": "button",
      "className": "send-attach-btn",
      "label": "画像を添付",
      "width": 28,
      "height": 28
    },
    {
      "element": "button",
      "className": "inbox-send-btn",
      "label": "送信",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "karte-close-btn",
      "label": "閉じる",
      "width": 24,
      "height": 24
    },
    {
      "element": "button",
      "className": "karte-open-link",
      "label": "顧客ページを開く →",
      "width": 111,
      "height": 18
    },
    {
      "element": "input",
      "className": "right-panel-field karte-field-empty",
      "label": "",
      "width": 371,
      "height": 33.6
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—24h以内3日以内3日超",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—高中低",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—未確認競合あり",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—小中大",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "button",
      "className": "avatar-btn",
      "label": "ユーザーメニューを開く",
      "width": 40,
      "height": 40
    },
    {
      "element": "button",
      "className": "user-drawer-close",
      "label": "閉じる",
      "width": 32,
      "height": 27.6
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "アカウント設定",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "ダークモード",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "英語",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action user-drawer-action--danger",
      "label": "サインアウト",
      "width": 259,
      "height": 42
    }
  ],
  "panes": {
    "conversationList": {
      "selector": ".inbox-conversation-list",
      "isVisible": true,
      "boundingBox": {
        "x": 66,
        "y": 223,
        "width": 245,
        "height": 801
      }
    },
    "messageThread": {
      "selector": ".inbox-center-header",
      "isVisible": true,
      "boundingBox": {
        "x": 312,
        "y": 132,
        "width": 456,
        "height": 81
      }
    },
    "karteRightPanel": {
      "selector": ".inbox-right-panel",
      "isVisible": true,
      "boundingBox": {
        "x": 768,
        "y": 0,
        "width": 396,
        "height": 1024
      }
    }
  }
}
```

### vl-tablet-768 / B

```json
{
  "project": "vl-tablet-768",
  "state": "B",
  "overflow": {
    "scrollWidth": 768,
    "innerWidth": 768,
    "diff": 0
  },
  "visibleInteractiveCount": 55,
  "smallTargetCount": 46,
  "smallTargets": [
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "ダッシュボード",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "スケジュール",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item active",
      "label": "受信箱3",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "在庫表",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "発注管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "見積・請求管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "顧客管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "管理センター",
      "width": 53,
      "height": 42
    },
    {
      "element": "button",
      "className": "comp-btn comp-btn--ghost",
      "label": "テンプレート",
      "width": 121.8,
      "height": 36
    },
    {
      "element": "button",
      "className": "comp-btn comp-btn--ghost",
      "label": "FAQ",
      "width": 70,
      "height": 36
    },
    {
      "element": "button",
      "className": "icon-btn",
      "label": "受信箱の設定",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab active",
      "label": "すべてのメッセージ",
      "width": 160.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "リード",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "商談中",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "既存顧客",
      "width": 89.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "追客",
      "width": 60.8,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "アーカイブ",
      "width": 102.9,
      "height": 36
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "プラットフォーム",
      "width": 146,
      "height": 36
    },
    {
      "element": "input",
      "className": "search-input-field inbox-search-input",
      "label": "",
      "width": 144.5,
      "height": 37
    },
    {
      "element": "button",
      "className": "inbox-manage-btn",
      "label": "管理",
      "width": 72.2,
      "height": 35
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "未読",
      "width": 44.8,
      "height": 29.6
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "フォローアップ",
      "width": 114.5,
      "height": 29.6
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "送信先言語",
      "width": 74,
      "height": 36
    },
    {
      "element": "button",
      "className": "karte-toggle-btn",
      "label": "顧客情報",
      "width": 92,
      "height": 28
    },
    {
      "element": "button",
      "className": "inbox-header-menu-btn",
      "label": "その他の操作",
      "width": 38,
      "height": 38
    },
    {
      "element": "button",
      "className": "msg-translate-btn",
      "label": "翻訳",
      "width": 18,
      "height": 18
    },
    {
      "element": "textarea",
      "className": "inbox-textarea",
      "label": "",
      "width": 262.3,
      "height": 40.3
    },
    {
      "element": "input",
      "className": "sr-only",
      "label": "画像を添付",
      "width": 1,
      "height": 1
    },
    {
      "element": "button",
      "className": "send-attach-btn",
      "label": "画像を添付",
      "width": 28,
      "height": 28
    },
    {
      "element": "button",
      "className": "inbox-send-btn",
      "label": "送信",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "karte-close-btn",
      "label": "閉じる",
      "width": 24,
      "height": 24
    },
    {
      "element": "button",
      "className": "karte-open-link",
      "label": "顧客ページを開く →",
      "width": 111,
      "height": 18
    },
    {
      "element": "input",
      "className": "right-panel-field karte-field-empty",
      "label": "",
      "width": 371,
      "height": 33.6
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—24h以内3日以内3日超",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—高中低",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—未確認競合あり",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—小中大",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "button",
      "className": "avatar-btn",
      "label": "ユーザーメニューを開く",
      "width": 40,
      "height": 40
    },
    {
      "element": "button",
      "className": "user-drawer-close",
      "label": "閉じる",
      "width": 32,
      "height": 27.6
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "アカウント設定",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "ダークモード",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "英語",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action user-drawer-action--danger",
      "label": "サインアウト",
      "width": 259,
      "height": 42
    }
  ],
  "panes": {
    "conversationList": {
      "selector": ".inbox-conversation-list",
      "isVisible": true,
      "boundingBox": {
        "x": 66,
        "y": 223,
        "width": 245,
        "height": 801
      }
    },
    "messageThread": {
      "selector": ".inbox-center-header",
      "isVisible": true,
      "boundingBox": {
        "x": 312,
        "y": 132,
        "width": 456,
        "height": 81
      }
    },
    "karteRightPanel": {
      "selector": ".inbox-right-panel",
      "isVisible": true,
      "boundingBox": {
        "x": 768,
        "y": 0,
        "width": 396,
        "height": 1024
      }
    }
  }
}
```

### vl-desktop-1280 / A

```json
{
  "project": "vl-desktop-1280",
  "state": "A",
  "overflow": {
    "scrollWidth": 1280,
    "innerWidth": 1280,
    "diff": 0
  },
  "visibleInteractiveCount": 53,
  "smallTargetCount": 44,
  "smallTargets": [
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "ダッシュボード",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "スケジュール",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item active",
      "label": "受信箱3",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "在庫表",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "発注管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "見積・請求管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "顧客管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "管理センター",
      "width": 53,
      "height": 42
    },
    {
      "element": "button",
      "className": "comp-btn comp-btn--ghost",
      "label": "テンプレート",
      "width": 121.8,
      "height": 36
    },
    {
      "element": "button",
      "className": "comp-btn comp-btn--ghost",
      "label": "FAQ",
      "width": 70,
      "height": 36
    },
    {
      "element": "button",
      "className": "icon-btn",
      "label": "受信箱の設定",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab active",
      "label": "すべてのメッセージ",
      "width": 160.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "リード",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "商談中",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "既存顧客",
      "width": 89.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "追客",
      "width": 60.8,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "アーカイブ",
      "width": 102.9,
      "height": 36
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "プラットフォーム",
      "width": 146,
      "height": 36
    },
    {
      "element": "input",
      "className": "search-input-field inbox-search-input",
      "label": "",
      "width": 341.8,
      "height": 37
    },
    {
      "element": "button",
      "className": "inbox-manage-btn",
      "label": "管理",
      "width": 72.2,
      "height": 35
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "未読",
      "width": 44.8,
      "height": 29.6
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "フォローアップ",
      "width": 114.5,
      "height": 29.6
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "送信先言語",
      "width": 74,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-thread-action-btn",
      "label": "未読にする",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "msg-translate-btn",
      "label": "翻訳",
      "width": 18,
      "height": 18
    },
    {
      "element": "textarea",
      "className": "inbox-textarea",
      "label": "",
      "width": 167,
      "height": 40.3
    },
    {
      "element": "input",
      "className": "sr-only",
      "label": "画像を添付",
      "width": 1,
      "height": 1
    },
    {
      "element": "button",
      "className": "send-attach-btn",
      "label": "画像を添付",
      "width": 28,
      "height": 28
    },
    {
      "element": "button",
      "className": "inbox-send-btn",
      "label": "送信",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "karte-open-link",
      "label": "顧客ページを開く →",
      "width": 111,
      "height": 18
    },
    {
      "element": "input",
      "className": "right-panel-field karte-field-empty",
      "label": "",
      "width": 371,
      "height": 33.6
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—24h以内3日以内3日超",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—高中低",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—未確認競合あり",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—小中大",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "button",
      "className": "avatar-btn",
      "label": "ユーザーメニューを開く",
      "width": 40,
      "height": 40
    },
    {
      "element": "button",
      "className": "user-drawer-close",
      "label": "閉じる",
      "width": 32,
      "height": 27.6
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "アカウント設定",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "ダークモード",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "英語",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action user-drawer-action--danger",
      "label": "サインアウト",
      "width": 259,
      "height": 42
    }
  ],
  "panes": {
    "conversationList": {
      "selector": ".inbox-conversation-list",
      "isVisible": true,
      "boundingBox": {
        "x": 66,
        "y": 223,
        "width": 442,
        "height": 677
      }
    },
    "messageThread": {
      "selector": ".inbox-center-header",
      "isVisible": true,
      "boundingBox": {
        "x": 509,
        "y": 132,
        "width": 361,
        "height": 81
      }
    },
    "karteRightPanel": {
      "selector": ".inbox-right-panel",
      "isVisible": true,
      "boundingBox": {
        "x": 884,
        "y": 78,
        "width": 396,
        "height": 822
      }
    }
  }
}
```

### vl-desktop-1280 / B

```json
{
  "project": "vl-desktop-1280",
  "state": "B",
  "overflow": {
    "scrollWidth": 1280,
    "innerWidth": 1280,
    "diff": 0
  },
  "visibleInteractiveCount": 53,
  "smallTargetCount": 44,
  "smallTargets": [
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "ダッシュボード",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "スケジュール",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item active",
      "label": "受信箱3",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "在庫表",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "発注管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "見積・請求管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "顧客管理",
      "width": 53,
      "height": 42
    },
    {
      "element": "a",
      "className": "sidebar-item",
      "label": "管理センター",
      "width": 53,
      "height": 42
    },
    {
      "element": "button",
      "className": "comp-btn comp-btn--ghost",
      "label": "テンプレート",
      "width": 121.8,
      "height": 36
    },
    {
      "element": "button",
      "className": "comp-btn comp-btn--ghost",
      "label": "FAQ",
      "width": 70,
      "height": 36
    },
    {
      "element": "button",
      "className": "icon-btn",
      "label": "受信箱の設定",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab active",
      "label": "すべてのメッセージ",
      "width": 160.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "リード",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "商談中",
      "width": 75.2,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "既存顧客",
      "width": 89.6,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "追客",
      "width": 60.8,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-full-tab",
      "label": "アーカイブ",
      "width": 102.9,
      "height": 36
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "プラットフォーム",
      "width": 146,
      "height": 36
    },
    {
      "element": "input",
      "className": "search-input-field inbox-search-input",
      "label": "",
      "width": 341.8,
      "height": 37
    },
    {
      "element": "button",
      "className": "inbox-manage-btn",
      "label": "管理",
      "width": 72.2,
      "height": 35
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "未読",
      "width": 44.8,
      "height": 29.6
    },
    {
      "element": "button",
      "className": "inbox-sub-filter-pill",
      "label": "フォローアップ",
      "width": 114.5,
      "height": 29.6
    },
    {
      "element": "select",
      "className": "inbox-platform-select",
      "label": "送信先言語",
      "width": 74,
      "height": 36
    },
    {
      "element": "button",
      "className": "inbox-thread-action-btn",
      "label": "未読にする",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "msg-translate-btn",
      "label": "翻訳",
      "width": 18,
      "height": 18
    },
    {
      "element": "textarea",
      "className": "inbox-textarea",
      "label": "",
      "width": 167,
      "height": 40.3
    },
    {
      "element": "input",
      "className": "sr-only",
      "label": "画像を添付",
      "width": 1,
      "height": 1
    },
    {
      "element": "button",
      "className": "send-attach-btn",
      "label": "画像を添付",
      "width": 28,
      "height": 28
    },
    {
      "element": "button",
      "className": "inbox-send-btn",
      "label": "送信",
      "width": 36,
      "height": 36
    },
    {
      "element": "button",
      "className": "karte-open-link",
      "label": "顧客ページを開く →",
      "width": 111,
      "height": 18
    },
    {
      "element": "input",
      "className": "right-panel-field karte-field-empty",
      "label": "",
      "width": 371,
      "height": 33.6
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—24h以内3日以内3日超",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—高中低",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—未確認競合あり",
      "width": 371,
      "height": 31
    },
    {
      "element": "select",
      "className": "right-panel-field",
      "label": "—小中大",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "input",
      "className": "right-panel-field",
      "label": "",
      "width": 371,
      "height": 31
    },
    {
      "element": "button",
      "className": "avatar-btn",
      "label": "ユーザーメニューを開く",
      "width": 40,
      "height": 40
    },
    {
      "element": "button",
      "className": "user-drawer-close",
      "label": "閉じる",
      "width": 32,
      "height": 27.6
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "アカウント設定",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "ダークモード",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action",
      "label": "英語",
      "width": 259,
      "height": 42
    },
    {
      "element": "button",
      "className": "user-drawer-action user-drawer-action--danger",
      "label": "サインアウト",
      "width": 259,
      "height": 42
    }
  ],
  "panes": {
    "conversationList": {
      "selector": ".inbox-conversation-list",
      "isVisible": true,
      "boundingBox": {
        "x": 66,
        "y": 223,
        "width": 442,
        "height": 677
      }
    },
    "messageThread": {
      "selector": ".inbox-center-header",
      "isVisible": true,
      "boundingBox": {
        "x": 509,
        "y": 132,
        "width": 361,
        "height": 81
      }
    },
    "karteRightPanel": {
      "selector": ".inbox-right-panel",
      "isVisible": true,
      "boundingBox": {
        "x": 884,
        "y": 78,
        "width": 396,
        "height": 822
      }
    }
  }
}
```

