import type { Preview } from '@storybook/react-vite'
import '../src/i18n'
import '../src/index.css'
import { createDevSession } from '../src/lib/auth/devSession'
import { registerDevSession } from '../src/lib/auth/devSessionSlot'

// Storybook は常に開発用の偽ログインで描く（自社 API を呼ばない）
registerDevSession(createDevSession())

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
       color: /(background|color)$/i,
       date: /Date$/i,
      },
    },
  },
};

export default preview;
