import type { Meta, StoryObj } from '@storybook/react-vite';
import { AvatarUpload } from './AvatarUpload';

// 外部通信なしでプレビューを確認するため SVG の data URI を使う
const SAMPLE_IMAGE =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="gray"/><circle cx="128" cy="100" r="44" fill="white"/><rect x="48" y="160" width="160" height="96" rx="48" fill="white"/></svg>',
  );

const labels = {
  choose: '画像を選ぶ',
  change: '画像を変更',
  remove: '削除',
  uploading: '保存中...',
  hint: '2MB以下のJPG・PNG・WebP',
  imageAlt: 'アイコン',
  errorAction: '画像を選び直す',
};

const meta = {
  title: 'Components/AvatarUpload',
  component: AvatarUpload,
  tags: ['autodocs'],
  args: {
    labels,
    onSelect: () => {},
    onDelete: () => {},
  },
} satisfies Meta<typeof AvatarUpload>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {};

export const WithImage: Story = {
  args: { imageUrl: SAMPLE_IMAGE },
};

export const Uploading: Story = {
  args: { imageUrl: SAMPLE_IMAGE, uploading: true },
};

export const ErrorState: Story = {
  args: { errorMessage: '2MB以下のJPG・PNG・WebP画像を選んでください。' },
};

export const SaveErrorWithRetry: Story = {
  args: {
    imageUrl: SAMPLE_IMAGE,
    errorMessage: '画像を保存できませんでした。',
    onErrorAction: () => {},
    labels: { ...labels, errorAction: 'もう一度試す' },
  },
};
