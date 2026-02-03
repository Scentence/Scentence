import NextAuth from "next-auth";
import KakaoProvider from "next-auth/providers/kakao";

const handler = NextAuth({
    providers: [
        KakaoProvider({
            clientId: process.env.KAKAO_CLIENT_ID!,
            clientSecret: process.env.KAKAO_CLIENT_SECRET!,
        }),
    ],
    callbacks: {
        async signIn({ user, account }) {
            if (account?.provider === 'kakao') {
                try {
                    // Docker Compose 환경을 기본값으로 사용 (서비스명 기반 통신)
                    const BACKEND_URL =
                        process.env.BACKEND_INTERNAL_URL ??
                        process.env.NEXT_PUBLIC_API_URL ??
                        "http://backend:8000";  // Docker Compose 서비스명

                    const response = await fetch(`${BACKEND_URL}/users/login`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            kakao_id: account.providerAccountId,
                            nickname: user.name,
                            email: user.email,
                            profile_image: user.image
                        })
                    });

                    if (!response.ok) {
                        return true;
                    }

                    const data = await response.json();

                    // 탈퇴 대기 중인 계정인 경우
                    if (data?.withdraw_pending && data?.member_id) {
                        return `/recover?memberId=${data.member_id}`;
                    }

                    // 동일 이메일로 가입된 로컬 계정이 있는 경우 → 계정 연결 페이지로 이동
                    if (data?.link_available && data?.existing_member_id) {
                        const params = new URLSearchParams({
                            email: user.email || '',
                            kakao_id: account.providerAccountId,
                            kakao_nickname: user.name || '',
                            kakao_profile_image: user.image || '',
                            existing_member_id: String(data.existing_member_id)
                        });
                        return `/link-account?${params.toString()}`;
                    }

                    // DB에서 받은 정보를 user 객체에 저장
                    user.id = data.member_id;
                    (user as any).roleType = data.role_type || "USER";
                    (user as any).userMode = data.user_mode || "BEGINNER";
                    console.log('[NextAuth signIn] member_id:', data.member_id, 'role_type:', data.role_type, 'user_mode:', data.user_mode);
                    return true;
                } catch (error) {
                    console.error('Sync Error:', error);
                    return true;
                }
            }
            return true;
        },
        async jwt({ token, user }) {
            if (user) {
                token.id = user.id;
                token.roleType = (user as any).roleType || "USER";
                token.userMode = (user as any).userMode || "BEGINNER";
            }
            return token;
        },
        async session({ session, token }) {
            if (session.user) {
                session.user.id = token.id as string;
                (session.user as any).roleType = token.roleType as string;
                (session.user as any).userMode = token.userMode as string;
            }
            return session;
        }
    }
});

export { handler as GET, handler as POST };