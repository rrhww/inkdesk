import assert from "node:assert/strict";
import test from "node:test";

test("owner session helpers define the hidden owner entry and protect the private system", async () => {
  const module = await import("../lib/owner-session");

  assert.equal(module.OWNER_SESSION_COOKIE, "inkvault_owner_session");
  assert.equal(module.hasOwnerSession(undefined), false);
  assert.equal(module.hasOwnerSession(""), false);
  assert.equal(module.hasOwnerSession("invalid"), true);
  assert.equal(module.hasOwnerSession("session-token-value"), true);
  assert.equal(module.resolveRootDestination(undefined), "login");
  assert.equal(module.resolveRootDestination("session-token-value"), "app");
  assert.equal(module.resolveProtectedAppRedirect("/app", undefined), "/login");
  assert.equal(module.resolveProtectedAppRedirect("/app/topics", "session-token-value"), null);
});
