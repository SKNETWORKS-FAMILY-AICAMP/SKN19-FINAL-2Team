"use client";

/**
 * Providers
 * -----------------------------
 * 앱 전역에서 NextAuth 세션을 사용할 수 있게 해주는 래퍼.
 * localAuth 동기화는 완전히 제거하고, NextAuth 세션만 사용한다.
 *
 * 사용 위치:
 * - app/layout.tsx 최상단에서 children 감싸는 용도
 */
import { SessionProvider } from "next-auth/react";

export function Providers({ children }: { children: React.ReactNode }) {
    return (
        <SessionProvider>
            {children}
        </SessionProvider>
    );
}
