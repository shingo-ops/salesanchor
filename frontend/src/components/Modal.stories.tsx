import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { Modal } from './Modal';
import { Button } from './Button';

const meta = {
  title: 'Components/Modal',
  component: Modal,
  tags: ['autodocs'],
  args: {
    open: false,
    onClose: () => {},
    title: 'モーダルタイトル',
    size: 'md',
    dismissOnOverlay: true,
    children: <p>モーダルの本体コンテンツです。</p>,
  },
} satisfies Meta<typeof Modal>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: (args) => {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button variant="secondary" onClick={() => setOpen(true)}>モーダルを開く</Button>
        <Modal {...args} open={open} onClose={() => setOpen(false)} />
      </>
    );
  },
};

export const Sm: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button variant="secondary" onClick={() => setOpen(true)}>sm を開く</Button>
        <Modal open={open} onClose={() => setOpen(false)} title="小サイズ (sm)" size="sm">
          <p>max-width: 420px</p>
        </Modal>
      </>
    );
  },
};

export const Lg: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button variant="secondary" onClick={() => setOpen(true)}>lg を開く</Button>
        <Modal open={open} onClose={() => setOpen(false)} title="大サイズ (lg)" size="lg">
          <p>max-width: 800px</p>
        </Modal>
      </>
    );
  },
};

export const WithFooter: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button variant="primary" onClick={() => setOpen(true)}>フッタ付きを開く</Button>
        <Modal
          open={open}
          onClose={() => setOpen(false)}
          title="フッタ付きモーダル"
          footer={
            <>
              <Button variant="secondary" onClick={() => setOpen(false)}>キャンセル</Button>
              <Button variant="primary"   onClick={() => setOpen(false)}>保存</Button>
            </>
          }
        >
          <p>フッタにアクションボタンを配置した例です。</p>
        </Modal>
      </>
    );
  },
};
