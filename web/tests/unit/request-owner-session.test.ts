import { beforeEach, describe, expect, it, vi } from "vitest";

const cookiesMock = vi.fn();
const redirectMock = vi.fn((location: string) => {
  throw new Error(`REDIRECT:${location}`);
});

vi.mock("next/headers", () => ({
  cookies: cookiesMock
}));

vi.mock("next/navigation", () => ({
  redirect: redirectMock
}));

describe("request owner session", () => {
  beforeEach(() => {
    vi.resetModules();
    cookiesMock.mockReset();
    redirectMock.mockClear();
  });

  it("redirects to login when a real request has no owner cookie", async () => {
    cookiesMock.mockResolvedValue({
      get: vi.fn().mockReturnValue(undefined)
    });

    const module = await import("@/lib/request-owner-session");

    await expect(module.requireRequestOwnerSession()).rejects.toThrow("REDIRECT:/login");
    expect(redirectMock).toHaveBeenCalledWith("/login");
  });

  it("returns the owner session when the cookie is present", async () => {
    cookiesMock.mockResolvedValue({
      get: vi.fn().mockReturnValue({
        value: "owner-session-token"
      })
    });

    const module = await import("@/lib/request-owner-session");

    await expect(module.requireRequestOwnerSession()).resolves.toBe("owner-session-token");
    expect(redirectMock).not.toHaveBeenCalled();
  });

  it("keeps fixture-based renders working when no request context exists", async () => {
    cookiesMock.mockRejectedValue(new Error("outside request scope"));

    const module = await import("@/lib/request-owner-session");

    await expect(module.requireRequestOwnerSession()).resolves.toBeUndefined();
    expect(redirectMock).not.toHaveBeenCalled();
  });
});
