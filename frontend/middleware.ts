import { NextResponse, NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";

// BFF 게이트키퍼: 세션을 해독해 백엔드로 전달할 헤더를 주입
export async function middleware(req: NextRequest) {
  const pathname = req.nextUrl.pathname;

  // API 경로만 적용 (NextAuth 내부 경로 제외)
  if (!pathname.startsWith("/api/")) return NextResponse.next();
  if (pathname.startsWith("/api/auth")) return NextResponse.next();

  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  const headers = new Headers(req.headers);

  if (token?.id) headers.set("X-Scentence-User-Id", String(token.id));
  if (token?.roleType) headers.set("X-Scentence-Role", String(token.roleType));
  if (token?.userMode) headers.set("X-Scentence-User-Mode", String(token.userMode));

  const internalSecret = process.env.INTERNAL_REQUEST_SECRET;
  if (internalSecret) headers.set("X-Scentence-Internal-Secret", internalSecret);

  return NextResponse.next({ request: { headers } });
}

export const config = {
  matcher: ["/api/:path*"],
};
