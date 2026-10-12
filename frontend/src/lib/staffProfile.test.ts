import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { avatarErrorKind, hasEnglishNames, toSameOriginAvatarUrl } from './staffProfile';

describe('hasEnglishNames', () => {
  it('requires both surname and given name', () => {
    expect(hasEnglishNames({ surname_en: 'Yamada', given_name_en: 'Taro' })).toBe(true);
    expect(hasEnglishNames({ surname_en: 'Yamada', given_name_en: '' })).toBe(false);
    expect(hasEnglishNames({ surname_en: '', given_name_en: 'Taro' })).toBe(false);
    expect(hasEnglishNames({ surname_en: null, given_name_en: null })).toBe(false);
  });

  it('treats whitespace-only as empty', () => {
    expect(hasEnglishNames({ surname_en: '   ', given_name_en: 'Taro' })).toBe(false);
  });
});

describe('avatarErrorKind', () => {
  it('maps image validation codes to invalidImage', () => {
    expect(avatarErrorKind(new ApiError('x', 400, { code: 'AVATAR_INVALID_TYPE' }))).toBe('invalidImage');
    expect(avatarErrorKind(new ApiError('x', 413, { code: 'AVATAR_TOO_LARGE' }))).toBe('invalidImage');
  });

  it('maps everything else to saveFailed', () => {
    expect(avatarErrorKind(new ApiError('x', 500, { code: 'AVATAR_SAVE_FAILED' }))).toBe('saveFailed');
    expect(avatarErrorKind(new ApiError('x', 500, 'plain string'))).toBe('saveFailed');
    expect(avatarErrorKind(new Error('network'))).toBe('saveFailed');
  });
});

describe('toSameOriginAvatarUrl', () => {
  it('converts an absolute API url to its same-origin path', () => {
    expect(toSameOriginAvatarUrl('https://api.salesanchor.jp/api/public/staff-avatars/abc.webp')).toBe(
      '/api/public/staff-avatars/abc.webp',
    );
  });

  it('returns null for empty input', () => {
    expect(toSameOriginAvatarUrl(null)).toBeNull();
    expect(toSameOriginAvatarUrl('')).toBeNull();
  });

  it('keeps relative or non-api urls unchanged', () => {
    expect(toSameOriginAvatarUrl('/api/public/staff-avatars/abc.webp')).toBe('/api/public/staff-avatars/abc.webp');
    expect(toSameOriginAvatarUrl('https://example.com/a.png')).toBe('https://example.com/a.png');
  });

  it('keeps an invalid url string unchanged', () => {
    expect(toSameOriginAvatarUrl('not a url')).toBe('not a url');
  });

  it('keeps a protocol-relative url unchanged', () => {
    expect(toSameOriginAvatarUrl('//evil.example/api/public/staff-avatars/abc.webp')).toBe(
      '//evil.example/api/public/staff-avatars/abc.webp',
    );
  });

  it('keeps a non-avatar /api/ path on another host unchanged', () => {
    expect(toSameOriginAvatarUrl('https://evil.example/api/v1/secret')).toBe('https://evil.example/api/v1/secret');
  });

  it('converts the avatar path even on another host (same public route)', () => {
    expect(toSameOriginAvatarUrl('https://other.example/api/public/staff-avatars/abc.webp')).toBe(
      '/api/public/staff-avatars/abc.webp',
    );
  });
});
