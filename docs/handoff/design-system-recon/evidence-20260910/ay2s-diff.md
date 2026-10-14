# before/after 差分

|画面@幅|item|class(後)|border(後)|radius(後)|height 前→後|width 前→後|left 前→後|縦中心差 後(前)|doc sW/cW 前→後|
|---|---|---|---|---|---|---|---|---|---|
|inventory-filter-w1280|inventory-qty-min|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|96→96|130.17→130.17|[0] ([0])|1280/1280→1280/1280|
|inventory-filter-w1280|inventory-qty-max|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|96→96|248.95→248.95|[0] ([0])|1280/1280→1280/1280|
|inventory-filter-w1280|inventory-price-min|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|112→112|387.13→387.13|[0] ([0])|1280/1280→1280/1280|
|inventory-filter-w1280|inventory-price-max|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|112→112|521.91→521.91|[0] ([0])|1280/1280→1280/1280|
|inventory-filter-w1440|inventory-qty-min|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|96→96|130.17→130.17|[0] ([0])|1440/1440→1440/1440|
|inventory-filter-w1440|inventory-qty-max|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|96→96|248.95→248.95|[0] ([0])|1440/1440→1440/1440|
|inventory-filter-w1440|inventory-price-min|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|112→112|387.13→387.13|[0] ([0])|1440/1440→1440/1440|
|inventory-filter-w1440|inventory-price-max|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|112→112|521.91→521.91|[0] ([0])|1440/1440→1440/1440|
|inventory-filter-w375|inventory-qty-min|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→44|96→96|-11.83→-11.83|[0] ([0])|375/375→375/375|
|inventory-filter-w375|inventory-qty-max|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→44|96→96|106.95→106.95|[0] ([0])|375/375→375/375|
|inventory-filter-w375|inventory-price-min|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→44|112→112|-11.83→-11.83|[0] ([0])|375/375→375/375|
|inventory-filter-w375|inventory-price-max|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→44|112→112|122.95→122.95|[0] ([0])|375/375→375/375|
|knowledge-aliases-w1280|rules-search|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|480→480|278→278|[-0.01, -0.01, -0.01] ([0, 0, 0])|1280/1280→1280/1280|
|knowledge-aliases-w1280|aliases-search|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|480→480|278→278|[-0.01, -0.01, -0.01] ([0, 0, 0])|1280/1280→1280/1280|
|knowledge-aliases-w1440|rules-search|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|480→480|278→278|[-0.01, -0.01, -0.01] ([0, 0, 0])|1440/1440→1440/1440|
|knowledge-aliases-w1440|aliases-search|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→39.61|480→480|278→278|[-0.01, -0.01, -0.01] ([0, 0, 0])|1440/1440→1440/1440|
|knowledge-aliases-w375|rules-search|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→44|327→327|24→24|[52, 52, 52] ([39.5, 39.5, 39.5])|375/375→375/375|
|knowledge-aliases-w375|aliases-search|comp-field__input|1px solid rgb(226, 232, 240)|6px|19→44|327→327|24→24|[52, 52, 52] ([39.5, 39.5, 39.5])|375/375→375/375|

## API 呼出（/conversations/stream 除外）

- inventory-filter-w1280: 前 4 件 / 後 4 件 / 一致=True
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
- inventory-filter-w1440: 前 4 件 / 後 4 件 / 一致=True
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
- inventory-filter-w375: 前 4 件 / 後 4 件 / 一致=True
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
    - GET /inventory?page=1&per_page=50&sort=release_date&order=desc&merge_same_post=true&tcg_type=pokemon_booster_box
- knowledge-aliases-w1280: 前 2 件 / 後 2 件 / 一致=True
    - GET /super-admin/knowledge?q=abc
    - GET /super-admin/aliases?q=xyz
- knowledge-aliases-w1440: 前 2 件 / 後 2 件 / 一致=True
    - GET /super-admin/knowledge?q=abc
    - GET /super-admin/aliases?q=xyz
- knowledge-aliases-w375: 前 2 件 / 後 2 件 / 一致=True
    - GET /super-admin/knowledge?q=abc
    - GET /super-admin/aliases?q=xyz

## console errors 件数

- inventory-filter-w1280: 前 0 / 後 0
- inventory-filter-w1440: 前 0 / 後 0
- inventory-filter-w375: 前 0 / 後 0
- knowledge-aliases-w1280: 前 0 / 後 0
- knowledge-aliases-w1440: 前 0 / 後 0
- knowledge-aliases-w375: 前 0 / 後 0
