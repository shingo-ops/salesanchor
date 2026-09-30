# AU shared implementation cross-review

Verdict: APPROVE. No blocking correctness, behavior, type, or ownership issue found in the reviewed shared diff.

- `buttonAppearance` preserves the prior Button class ordering and tab-specific size/active behavior; Button retains native prop/ref/disabled/loading handling.
- `ButtonLink` uses the same appearance builder, keeps Router `to` and native `href` branches exclusive, forwards anchor refs and native metadata, and rejects disabled/loading/className/style/tab in its public type.
- `HeaderButton` delegates text variants to the standard Button with explicit `type="button"`; the icon branch remains the existing native `icon-btn` path.
- Legacy button CSS, header legacy modifiers, login override, block helper, and mobile legacy rules are removed only after the AST audit reported zero legacy nodes. New CSS contains link underline removal and four layout-only helpers without color, border, font, or padding overrides.
- Tests cover Button native contracts, ButtonLink href/to/ref/modifier/preventDefault/stopPropagation/type exclusions, HeaderButton text/icon behavior, and the one legacy-class assertion updated to the common class.
- Known validation limitation remains unchanged: no visual/browser or production-form verification was performed.

## Reviewed SHA-256

```text
cfd1ef3649e8b8cb3cb7ff53564452094d7963089d7e195e980be803302ec2f6  frontend/src/components/Button.tsx
ba352b277692c14c99c0dd2e788e68bebbc3b92373a1d9582de780d4556e4f86  frontend/src/components/Button.css
df8085bd6dee5a49ab5e450734f55cd59e8fb7b463825b044da7e207fbd7f71b  frontend/src/components/buttonAppearance.ts
ac78317a74c53db4ba5df1fc568784182f01bed71f63c105fb11d8772cb99192  frontend/src/components/ButtonLink.tsx
f09daba451e581a9c18c950019b7aa8f91d4fb58948add3e49c1a56bda23887c  frontend/src/components/ButtonLink.test.tsx
4cc48890844e0b029154c025b6cd806f32619b19a121355d6e84af9806e14c0b  frontend/src/components/HeaderButton.tsx
fe670a1a0b6418cd85d91438024ab9e246ba828af88f891dd107eeb650c21103  frontend/src/components/HeaderButton.test.tsx
1332f2ac7b9bc31769fae0c3db65e768c8f9f36b04dccb77bd415fba49b1a045  frontend/src/components.css
54d96f545a1683a7d16c94e004192051b1b282aba60129bc28699dfedea94365  frontend/src/pages-layout.css
2e21c162e8fe3eef5afb2ef76d4e9aff2ce8575b68e17395947599570bdc1f3c  frontend/src/components/FullPageFormButtonMigration.test.tsx
```
