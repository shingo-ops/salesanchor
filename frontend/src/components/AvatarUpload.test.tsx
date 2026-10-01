import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { AvatarUpload } from './AvatarUpload';

const labels = {
  choose: 'Choose image', change: 'Change image', remove: 'Remove', uploading: 'Saving...',
  hint: 'JPG, PNG or WebP, 2MB or smaller', imageAlt: 'Icon', errorAction: 'Choose another image',
};

afterEach(cleanup);

describe('AvatarUpload', () => {
  it('shows the empty placeholder and only the choose button when no image is set', () => {
    render(<AvatarUpload onSelect={vi.fn()} onDelete={vi.fn()} labels={labels} />);

    expect(screen.queryByRole('img')).toBeNull();
    expect(screen.getByTestId('avatar-preview').className).toContain('comp-avatar-upload__preview--empty');
    expect(screen.getByRole('button', { name: 'Choose image' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Remove' })).toBeNull();
  });

  it('shows the image with change and remove buttons when an image is set', () => {
    const onDelete = vi.fn();
    render(<AvatarUpload imageUrl="https://example.com/a.webp" onSelect={vi.fn()} onDelete={onDelete} labels={labels} />);

    expect((screen.getByRole('img', { name: 'Icon' }) as HTMLImageElement).src).toBe('https://example.com/a.webp');
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }));
    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Change image' })).toBeTruthy();
  });

  it('calls onSelect with the chosen file', () => {
    const onSelect = vi.fn();
    render(<AvatarUpload onSelect={onSelect} onDelete={vi.fn()} labels={labels} />);
    const file = new File(['x'], 'a.png', { type: 'image/png' });

    fireEvent.change(screen.getByTestId('avatar-file-input'), { target: { files: [file] } });

    expect(onSelect).toHaveBeenCalledExactlyOnceWith(file);
  });

  it('only offers jpg, png and webp in the file picker', () => {
    render(<AvatarUpload onSelect={vi.fn()} onDelete={vi.fn()} labels={labels} />);

    expect(screen.getByTestId('avatar-file-input').getAttribute('accept')).toBe('image/jpeg,image/png,image/webp');
  });

  it('disables the buttons while uploading', () => {
    render(<AvatarUpload imageUrl="https://example.com/a.webp" uploading onSelect={vi.fn()} onDelete={vi.fn()} labels={labels} />);

    expect((screen.getByRole('button', { name: 'Remove' }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('shows the error with an action button that runs onErrorAction', () => {
    const onErrorAction = vi.fn();
    render(<AvatarUpload errorMessage="Could not save." onErrorAction={onErrorAction} onSelect={vi.fn()} onDelete={vi.fn()} labels={labels} />);

    expect(screen.getByRole('alert').textContent).toContain('Could not save.');
    fireEvent.click(screen.getByRole('button', { name: 'Choose another image' }));
    expect(onErrorAction).toHaveBeenCalledTimes(1);
  });

  it('hides the error area when there is no error', () => {
    render(<AvatarUpload onSelect={vi.fn()} onDelete={vi.fn()} labels={labels} />);

    expect(screen.queryByRole('alert')).toBeNull();
  });
});
