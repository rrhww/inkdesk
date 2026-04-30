import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { OWNER_SESSION_COOKIE, resolveProtectedAppRedirect } from "./lib/owner-session";

export function proxy(request: NextRequest) {
  const redirectTarget = resolveProtectedAppRedirect(
    request.nextUrl.pathname,
    request.cookies.get(OWNER_SESSION_COOKIE)?.value
  );

  if (!redirectTarget) {
    return NextResponse.next();
  }

  return NextResponse.redirect(new URL(redirectTarget, request.url));
}

export const config = {
  matcher: ["/app/:path*"]
};
