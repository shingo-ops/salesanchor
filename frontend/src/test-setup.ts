/**
 * Vitest グローバルセットアップ（unit テスト専用）
 *
 * 毎回の試験の前に、単体試験用の開発ログインを登録する（src/test-utils/devSession.ts）。
 * 自社ログインの動きを試す試験は、自分の beforeEach で registerDevSession(null) を呼ぶ。
 */

import { beforeEach } from "vitest";
import { registerTestDevSession } from "./test-utils/devSession";

beforeEach(() => {
  registerTestDevSession();
});
