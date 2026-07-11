import { afterEach, describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "@/lib/server-api";

describe("server API base URL", () => {
  const originalPublicApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  afterEach(() => {
    if (originalPublicApiBaseUrl === undefined) {
      delete process.env.NEXT_PUBLIC_API_BASE_URL;
      return;
    }

    process.env.NEXT_PUBLIC_API_BASE_URL = originalPublicApiBaseUrl;
  });

  it("uses the same-origin API rewrite from browser code", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8080";

    expect(resolveApiBaseUrl()).toBe("/api");
  });
});
