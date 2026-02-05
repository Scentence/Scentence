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
    // AUTH 스위치: 필요 시 ENV로 auth 비활성화 가능
    const authEnabled = process.env.NEXT_PUBLIC_ENABLE_AUTH === "true";

    return (
        <SessionProvider
            // authEnabled=false면 세션이 항상 null
            session={authEnabled ? undefined : null}
            // authEnabled=false면 불필요한 세션 refetch 방지
            refetchInterval={authEnabled ? undefined : 0}
            refetchOnWindowFocus={authEnabled ? undefined : false}
        >
            {children}
        </SessionProvider>
    );
}
