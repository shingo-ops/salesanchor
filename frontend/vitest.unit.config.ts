/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    // unit テスト専用の軽量 config。
    // storybook/browser プロジェクトを読み込まず、coverage 実行時の常駐ハングを避ける。
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
        statements: 0.5,
        branches: 0.3,
        functions: 0.5,
        lines: 0.5,
      },
    },
    projects: [
      {
        extends: true,
        test: {
          name: 'unit',
          environment: 'jsdom',
          include: ['src/**/*.test.{ts,tsx}'],
          globals: true,
          setupFiles: ['src/test-setup.ts'],
        },
      },
    ],
  },
});
