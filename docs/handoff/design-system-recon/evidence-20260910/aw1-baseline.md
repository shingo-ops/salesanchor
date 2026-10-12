Base SHA: 3210edeea250e269102bedd3546ebc48ddb89b77 (origin/main snapshot; frontend/src identical at worktree HEAD 3f4dbbdf9, git diff --stat empty)

# AW-1 baseline

chromium: 147.0.7727.15

CSS order:
1. index.css (+@import tokens.css, components/field-size.css inlined at index.css:1-2)
2. components.css
3. company-forms.css
4. pages/inbox/InboxPage.css
5. components/FormField.css

Dark selector: `:root.force-dark` (index.css:220, tokens.css:577); html class force-dark. Probe: #1e293b | bg=rgb(30, 41, 59)

Warnings/console: none

## light / 1280 / normal

| property | karte | header | tabbar | mold_md | mold_sm |
|---|---|---|---|---|---|
| padding-top | 7px | 4px | 0px | 8px | 4px |
| padding-right | 9px | 20px | 8px | 20px | 20px |
| padding-bottom | 7px | 4px | 0px | 8px | 4px |
| padding-left | 9px | 12px | 8px | 12px | 8px |
| border-top-width | 1px | 1px | 1px | 1px | 1px |
| border-right-width | 1px | 1px | 1px | 1px | 1px |
| border-bottom-width | 1px | 1px | 1px | 1px | 1px |
| border-left-width | 1px | 1px | 1px | 1px | 1px |
| border-top-style | solid | solid | solid | solid | solid |
| border-right-style | solid | solid | solid | solid | solid |
| border-bottom-style | solid | solid | solid | solid | solid |
| border-left-style | solid | solid | solid | solid | solid |
| border-top-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-right-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-bottom-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-left-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-top-left-radius | 6px | 20px | 4px | 6px | 6px |
| border-top-right-radius | 6px | 20px | 4px | 6px | 6px |
| border-bottom-right-radius | 6px | 20px | 4px | 6px | 6px |
| border-bottom-left-radius | 6px | 20px | 4px | 6px | 6px |
| font-size | 13.6px | 13.6px | 12px | 14.4px | 13.6px |
| font-family | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| font-weight | 400 | 400 | 400 | 400 | 400 |
| line-height | normal | normal | normal | 21.6px | 20.4px |
| color | rgb(26, 32, 44) | rgb(26, 32, 44) | rgb(74, 85, 104) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| background-image | none | url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E") | none | url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E") | url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E") |
| background-position | 0% 0% | calc(100% - 8px) 50% | 0% 0% | calc(100% - 8px) 50% | calc(100% - 8px) 50% |
| background-repeat | repeat | no-repeat | repeat | no-repeat | no-repeat |
| height | 32px | 36px | 36px | 39.6094px | 30.3906px |
| min-height | 0px | 0px | 0px | 0px | 28px |
| box-shadow | none | none | none | none | none |
| outline-style | none | none | none | none | none |
| outline-width | 3px | 3px | 3px | 3px | 3px |
| outline-color | rgb(26, 32, 44) | rgb(26, 32, 44) | rgb(74, 85, 104) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| appearance | none | none | auto | none | none |
| cursor | default | pointer | pointer | pointer | pointer |
| transition-property | border-color | border-color, background-color | all | border-color, box-shadow | border-color, box-shadow |
| transition-duration | 0.1s | 0.15s, 0.15s | 0s | 0.1s, 0.1s | 0.1s, 0.1s |
| white-space | pre | nowrap | pre | pre | pre |
| offsetHeight | 32 | 36 | 36 | 40 | 30 |

## Properties that change (vs light/1280/normal baseline)

### karte
- normal/1280/dark: color: rgb(26, 32, 44) -> rgb(241, 245, 249); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- normal/390/light: (no change)
- normal/390/dark: color: rgb(26, 32, 44) -> rgb(241, 245, 249); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- focus/1280/light: border-top-color: rgb(221, 224, 228) -> rgb(30, 58, 138); border-right-color: rgb(221, 224, 228) -> rgb(30, 58, 138); border-bottom-color: rgb(221, 224, 228) -> rgb(30, 58, 138); border-left-color: rgb(221, 224, 228) -> rgb(30, 58, 138)
- focus/1280/dark: border-top-color: rgb(221, 224, 228) -> rgb(91, 141, 217); border-right-color: rgb(221, 224, 228) -> rgb(91, 141, 217); border-bottom-color: rgb(221, 224, 228) -> rgb(91, 141, 217); border-left-color: rgb(221, 224, 228) -> rgb(91, 141, 217); color: rgb(26, 32, 44) -> rgb(241, 245, 249); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- focus/390/light: border-top-color: rgb(221, 224, 228) -> rgb(30, 58, 138); border-right-color: rgb(221, 224, 228) -> rgb(30, 58, 138); border-bottom-color: rgb(221, 224, 228) -> rgb(30, 58, 138); border-left-color: rgb(221, 224, 228) -> rgb(30, 58, 138)
- focus/390/dark: border-top-color: rgb(221, 224, 228) -> rgb(91, 141, 217); border-right-color: rgb(221, 224, 228) -> rgb(91, 141, 217); border-bottom-color: rgb(221, 224, 228) -> rgb(91, 141, 217); border-left-color: rgb(221, 224, 228) -> rgb(91, 141, 217); color: rgb(26, 32, 44) -> rgb(241, 245, 249); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- hover/1280/light: (no change)
- hover/1280/dark: color: rgb(26, 32, 44) -> rgb(241, 245, 249); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- hover/390/light: (no change)
- hover/390/dark: color: rgb(26, 32, 44) -> rgb(241, 245, 249); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- disabled/1280/light: (no change)
- disabled/1280/dark: color: rgb(26, 32, 44) -> rgb(241, 245, 249); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- disabled/390/light: (no change)
- disabled/390/dark: color: rgb(26, 32, 44) -> rgb(241, 245, 249); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)

### header
- normal/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- normal/390/light: (no change)
- normal/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- focus/1280/light: border-top-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-right-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-bottom-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-left-color: rgb(226, 232, 240) -> rgb(30, 58, 138); box-shadow: none -> rgba(30, 58, 138, 0.15) 0px 0px 0px 3px
- focus/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-right-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-bottom-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-left-color: rgb(226, 232, 240) -> rgb(91, 141, 217); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); box-shadow: none -> rgba(91, 141, 217, 0.3) 0px 0px 0px 3px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- focus/390/light: border-top-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-right-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-bottom-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-left-color: rgb(226, 232, 240) -> rgb(30, 58, 138); box-shadow: none -> rgba(30, 58, 138, 0.15) 0px 0px 0px 3px
- focus/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-right-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-bottom-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-left-color: rgb(226, 232, 240) -> rgb(91, 141, 217); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); box-shadow: none -> rgba(91, 141, 217, 0.3) 0px 0px 0px 3px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- hover/1280/light: border-top-color: rgb(226, 232, 240) -> rgb(203, 213, 224); border-right-color: rgb(226, 232, 240) -> rgb(203, 213, 224); border-bottom-color: rgb(226, 232, 240) -> rgb(203, 213, 224); border-left-color: rgb(226, 232, 240) -> rgb(203, 213, 224); background-color: rgb(255, 255, 255) -> rgb(226, 232, 240)
- hover/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(71, 85, 105); border-right-color: rgb(226, 232, 240) -> rgb(71, 85, 105); border-bottom-color: rgb(226, 232, 240) -> rgb(71, 85, 105); border-left-color: rgb(226, 232, 240) -> rgb(71, 85, 105); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(51, 65, 85); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- hover/390/light: border-top-color: rgb(226, 232, 240) -> rgb(203, 213, 224); border-right-color: rgb(226, 232, 240) -> rgb(203, 213, 224); border-bottom-color: rgb(226, 232, 240) -> rgb(203, 213, 224); border-left-color: rgb(226, 232, 240) -> rgb(203, 213, 224); background-color: rgb(255, 255, 255) -> rgb(226, 232, 240)
- hover/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(71, 85, 105); border-right-color: rgb(226, 232, 240) -> rgb(71, 85, 105); border-bottom-color: rgb(226, 232, 240) -> rgb(71, 85, 105); border-left-color: rgb(226, 232, 240) -> rgb(71, 85, 105); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(51, 65, 85); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- disabled/1280/light: (no change)
- disabled/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- disabled/390/light: (no change)
- disabled/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)

### tabbar
- normal/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(74, 85, 104) -> rgb(203, 213, 225); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(74, 85, 104) -> rgb(203, 213, 225)
- normal/390/light: (no change)
- normal/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(74, 85, 104) -> rgb(203, 213, 225); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(74, 85, 104) -> rgb(203, 213, 225)
- focus/1280/light: border-top-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-right-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-bottom-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-left-color: rgb(226, 232, 240) -> rgb(30, 58, 138); color: rgb(74, 85, 104) -> rgb(26, 32, 44); outline-color: rgb(74, 85, 104) -> rgb(26, 32, 44)
- focus/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-right-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-bottom-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-left-color: rgb(226, 232, 240) -> rgb(91, 141, 217); color: rgb(74, 85, 104) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(74, 85, 104) -> rgb(241, 245, 249)
- focus/390/light: border-top-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-right-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-bottom-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-left-color: rgb(226, 232, 240) -> rgb(30, 58, 138); color: rgb(74, 85, 104) -> rgb(26, 32, 44); outline-color: rgb(74, 85, 104) -> rgb(26, 32, 44)
- focus/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-right-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-bottom-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-left-color: rgb(226, 232, 240) -> rgb(91, 141, 217); color: rgb(74, 85, 104) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(74, 85, 104) -> rgb(241, 245, 249)
- hover/1280/light: (no change)
- hover/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(74, 85, 104) -> rgb(203, 213, 225); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(74, 85, 104) -> rgb(203, 213, 225)
- hover/390/light: (no change)
- hover/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(74, 85, 104) -> rgb(203, 213, 225); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(74, 85, 104) -> rgb(203, 213, 225)
- disabled/1280/light: (no change)
- disabled/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(74, 85, 104) -> rgb(203, 213, 225); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(74, 85, 104) -> rgb(203, 213, 225)
- disabled/390/light: (no change)
- disabled/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(74, 85, 104) -> rgb(203, 213, 225); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(74, 85, 104) -> rgb(203, 213, 225)

### mold_md
- normal/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- normal/390/light: height: 39.6094px -> 44px; min-height: 0px -> 44px; offsetHeight: 40 -> 44
- normal/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); height: 39.6094px -> 44px; min-height: 0px -> 44px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249); offsetHeight: 40 -> 44
- focus/1280/light: border-top-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-right-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-bottom-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-left-color: rgb(226, 232, 240) -> rgb(30, 58, 138); box-shadow: none -> rgba(30, 58, 138, 0.15) 0px 0px 0px 3px
- focus/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-right-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-bottom-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-left-color: rgb(226, 232, 240) -> rgb(91, 141, 217); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); box-shadow: none -> rgba(91, 141, 217, 0.3) 0px 0px 0px 3px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- focus/390/light: border-top-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-right-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-bottom-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-left-color: rgb(226, 232, 240) -> rgb(30, 58, 138); height: 39.6094px -> 44px; min-height: 0px -> 44px; box-shadow: none -> rgba(30, 58, 138, 0.15) 0px 0px 0px 3px; offsetHeight: 40 -> 44
- focus/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-right-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-bottom-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-left-color: rgb(226, 232, 240) -> rgb(91, 141, 217); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); height: 39.6094px -> 44px; min-height: 0px -> 44px; box-shadow: none -> rgba(91, 141, 217, 0.3) 0px 0px 0px 3px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249); offsetHeight: 40 -> 44
- hover/1280/light: (no change)
- hover/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- hover/390/light: height: 39.6094px -> 44px; min-height: 0px -> 44px; offsetHeight: 40 -> 44
- hover/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); height: 39.6094px -> 44px; min-height: 0px -> 44px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249); offsetHeight: 40 -> 44
- disabled/1280/light: background-color: rgb(255, 255, 255) -> rgb(226, 232, 240); background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000 -> none; background-position: calc(100% - 8px) 50% -> 0% 0%; background-repeat: no-repeat -> repeat; cursor: pointer -> not-allowed
- disabled/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(51, 65, 85); background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000 -> none; background-position: calc(100% - 8px) 50% -> 0% 0%; background-repeat: no-repeat -> repeat; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249); cursor: pointer -> not-allowed
- disabled/390/light: background-color: rgb(255, 255, 255) -> rgb(226, 232, 240); background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000 -> none; background-position: calc(100% - 8px) 50% -> 0% 0%; background-repeat: no-repeat -> repeat; height: 39.6094px -> 44px; min-height: 0px -> 44px; cursor: pointer -> not-allowed; offsetHeight: 40 -> 44
- disabled/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(51, 65, 85); background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000 -> none; background-position: calc(100% - 8px) 50% -> 0% 0%; background-repeat: no-repeat -> repeat; height: 39.6094px -> 44px; min-height: 0px -> 44px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249); cursor: pointer -> not-allowed; offsetHeight: 40 -> 44

### mold_sm
- normal/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- normal/390/light: height: 30.3906px -> 44px; min-height: 28px -> 44px; offsetHeight: 30 -> 44
- normal/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); height: 30.3906px -> 44px; min-height: 28px -> 44px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249); offsetHeight: 30 -> 44
- focus/1280/light: border-top-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-right-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-bottom-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-left-color: rgb(226, 232, 240) -> rgb(30, 58, 138); box-shadow: none -> rgba(30, 58, 138, 0.15) 0px 0px 0px 3px
- focus/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-right-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-bottom-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-left-color: rgb(226, 232, 240) -> rgb(91, 141, 217); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); box-shadow: none -> rgba(91, 141, 217, 0.3) 0px 0px 0px 3px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- focus/390/light: border-top-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-right-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-bottom-color: rgb(226, 232, 240) -> rgb(30, 58, 138); border-left-color: rgb(226, 232, 240) -> rgb(30, 58, 138); height: 30.3906px -> 44px; min-height: 28px -> 44px; box-shadow: none -> rgba(30, 58, 138, 0.15) 0px 0px 0px 3px; offsetHeight: 30 -> 44
- focus/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-right-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-bottom-color: rgb(226, 232, 240) -> rgb(91, 141, 217); border-left-color: rgb(226, 232, 240) -> rgb(91, 141, 217); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); height: 30.3906px -> 44px; min-height: 28px -> 44px; box-shadow: none -> rgba(91, 141, 217, 0.3) 0px 0px 0px 3px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249); offsetHeight: 30 -> 44
- hover/1280/light: (no change)
- hover/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249)
- hover/390/light: height: 30.3906px -> 44px; min-height: 28px -> 44px; offsetHeight: 30 -> 44
- hover/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(30, 41, 59); height: 30.3906px -> 44px; min-height: 28px -> 44px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249); offsetHeight: 30 -> 44
- disabled/1280/light: background-color: rgb(255, 255, 255) -> rgb(226, 232, 240); background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000 -> none; background-position: calc(100% - 8px) 50% -> 0% 0%; background-repeat: no-repeat -> repeat; cursor: pointer -> not-allowed
- disabled/1280/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(51, 65, 85); background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000 -> none; background-position: calc(100% - 8px) 50% -> 0% 0%; background-repeat: no-repeat -> repeat; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249); cursor: pointer -> not-allowed
- disabled/390/light: background-color: rgb(255, 255, 255) -> rgb(226, 232, 240); background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000 -> none; background-position: calc(100% - 8px) 50% -> 0% 0%; background-repeat: no-repeat -> repeat; height: 30.3906px -> 44px; min-height: 28px -> 44px; cursor: pointer -> not-allowed; offsetHeight: 30 -> 44
- disabled/390/dark: border-top-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-right-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-bottom-color: rgb(226, 232, 240) -> rgb(51, 65, 85); border-left-color: rgb(226, 232, 240) -> rgb(51, 65, 85); color: rgb(26, 32, 44) -> rgb(241, 245, 249); background-color: rgb(255, 255, 255) -> rgb(51, 65, 85); background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000 -> none; background-position: calc(100% - 8px) 50% -> 0% 0%; background-repeat: no-repeat -> repeat; height: 30.3906px -> 44px; min-height: 28px -> 44px; outline-color: rgb(26, 32, 44) -> rgb(241, 245, 249); cursor: pointer -> not-allowed; offsetHeight: 30 -> 44
