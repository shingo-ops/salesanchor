/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';
import { playwright } from '@vitest/browser-playwright';
const dirname = typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url));

// More info at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon
export default defineConfig({
  plugins: [react()],
  build: {
    // Vite 8 / lightningcss のデフォルト target が "baseline-widely-available" (Safari 16.4+) のため、
    // @media (max-width: 767px) を Level 4 range 構文 (width<=767px) に変換してしまう。
    // iOS < 16.4 (Safari < 16.4) は Level 4 range 構文に非対応 → 全 @media が無視される。
    // safari14 をターゲットに含めることで従来の max-width: 形式を維持する。
    cssTarget: ['chrome87', 'safari14', 'firefox78', 'edge88'],
  },
  server: {
    host: true,
    port: 5173
  },
  test: {
    // カバレッジ設定（SSoT: この1箇所のみ。閾値変更もここだけ）
    // フェーズ管理: Phase 0(なし) → Phase 0.5(1%) → Phase 1(10%) → Phase 2(40%) → Phase 3(60%) → Phase 4(75%)
    // 現在: Phase 0.5 — 初回テスト導入（35テスト・3ファイル）で 0.69% 達成。
    // Phase 1(10%) へは invoices/quotes/roles/products 等の未テストルーターに相当する
    // フロントエンドロジックのテストを追加して引き上げる。
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.stories.{ts,tsx}',
        'src/**/*.d.ts',
        'src/main.tsx',
        'src/vite-env.d.ts',
        'src/i18n.ts',
      ],
      thresholds: {
        // Phase 0.5: 初回テスト 35件（3ファイル）で達成した実測値ベース。
        // 次のスプリントでテスト追加後に段階的に引き上げる。
        statements: 0.5,
        branches: 0.3,
        functions: 0.5,
        lines: 0.5,
      },
    },
    projects: [
      // Unit テストプロジェクト（カバレッジ計測対象）
      {
        extends: true,
        test: {
          name: 'unit',
          environment: 'jsdom',
          include: ['src/**/*.test.{ts,tsx}'],
          globals: true,
          // Firebase 初期化バイパス（環境変数なしでも動くように）
          setupFiles: ['src/test-setup.ts'],
        },
      },
      // Storybook ブラウザテストプロジェクト（カバレッジ対象外）
      {
        extends: true,
        plugins: [
          storybookTest({
            configDir: path.join(dirname, '.storybook')
          }),
        ],
        test: {
          name: 'storybook',
          browser: {
            enabled: true,
            headless: true,
            provider: playwright({}),
            instances: [{
              browser: 'chromium'
            }]
          }
        }
      }
    ]
  }
});