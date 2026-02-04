'use client';

/**
 * Providers
 * -----------------------------
 * NextAuth의 SessionProvider를 감싸는 전역 Provider 컴포넌트
 *
 * 역할:
 * - 로그인 세션(Session)을 React Context로 앱 전체에 공유
 * - useSession(), signIn(), signOut() 같은 NextAuth 훅을
 *   모든 하위 컴포넌트에서 사용할 수 있게 해줌
 *
 * 사용 위치:
 * - app/layout.tsx 최상단에서 children을 감싸는 용도
 *
 * 주의:
 * - 반드시 'use client'가 필요함 (브라우저 전용)
 * - 이 파일 없으면 로그인 상태 UI 연동 불가
 */

import { SessionProvider, useSession } from "next-auth/react";
import { useEffect } from "react";

/**
 * AuthSync
 * -----------------------------
 * 카카오 로그인 세션을 localStorage의 localAuth에 동기화
 * - 기존 localAuth 기반 코드와 호환성 유지
 * - F12 > Application > Local Storage에서 확인 가능
 */
function AuthSync({ children }: { children: React.ReactNode }) {
    const { data: session, status } = useSession();

    useEffect(() => {
        if (status === "authenticated" && session?.user) {
            // 카카오 로그인 세션이 있으면 localAuth에도 저장
            const user = session.user as any;
            const localAuthData = {
                memberId: user.id,
                email: user.email || "",
                nickname: user.name || "",
                profileImage: user.image || "",
                // roleType removed for security
                user_mode: user.userMode || "BEGINNER",
                provider: "kakao",
                loggedInAt: new Date().toISOString(),
            };
            localStorage.setItem("localAuth", JSON.stringify(localAuthData));
        } else if (status === "unauthenticated") {
            // 로그아웃 시 카카오 세션에서 만든 localAuth만 삭제
            try {
                const existing = localStorage.getItem("localAuth");
                if (existing) {
                    const parsed = JSON.parse(existing);
                    if (parsed.provider === "kakao") {
                        localStorage.removeItem("localAuth");
                    }
                }
            } catch (e) {
                // ignore
            }
        }
    }, [session, status]);

    return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
    const authEnabled = process.env.NEXT_PUBLIC_ENABLE_AUTH === "true";

    return (
        <SessionProvider
            session={authEnabled ? undefined : null}
            refetchInterval={authEnabled ? undefined : 0}
            refetchOnWindowFocus={authEnabled ? undefined : false}
        >
            <AuthSync>{children}</AuthSync>
        </SessionProvider>
    );
}
