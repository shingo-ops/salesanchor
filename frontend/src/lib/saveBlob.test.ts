// invoice-create-portfolio R6: saveBlob（design-v2 §3-6・K15）
import { afterEach, describe, expect, it, vi } from 'vitest';
import { saveBlob } from './saveBlob';

const originalURL = URL;
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('saveBlob', () => {
  it('clicks one attached download link with the file name, then removes it and revokes the URL', () => {
    const create = vi.fn().mockReturnValue('blob:fixture');
    const revoke = vi.fn();
    class MockURL extends originalURL { static createObjectURL = create; static revokeObjectURL = revoke; }
    vi.stubGlobal('URL', MockURL);
    const clicks: { href: string; download: string; attached: boolean }[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      clicks.push({ href: this.getAttribute('href') ?? '', download: this.download, attached: document.body.contains(this) });
    });
    const blob = new Blob(['%PDF'], { type: 'application/pdf' });
    saveBlob(blob, 'IN-0011-01.pdf');
    expect(create).toHaveBeenCalledExactlyOnceWith(blob);
    expect(clicks).toEqual([{ href: 'blob:fixture', download: 'IN-0011-01.pdf', attached: true }]);
    expect(document.querySelectorAll('a[download]').length).toBe(0);
    expect(revoke).toHaveBeenCalledExactlyOnceWith('blob:fixture');
  });
});
