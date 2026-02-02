"use client";

import { FormEvent, useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import ChatList from "../../components/Chat/ChatList";
import { Message } from "../../components/Chat/MessageItem";
import ChatSidebar from "../../components/Chat/Sidebar"; // 좌측 채팅 기록 사이드바
import NavSidebar from "../../components/common/sidebar"; // 우측 내비게이션 팝오버
import MagneticButton from "../../components/common/MagneticButton"; // [NEW] 마그네틱 버튼 추가
import UserProfileMenu from "../../components/common/UserProfileMenu"; // [NEW] UserProfileMenu 추가
import { SavedPerfumesProvider } from "../../contexts/SavedPerfumesContext";

const API_URL = "/api/chat";

export default function ChatPage() {
    const { data: session } = useSession(); // 카카오 로그인 세션
    const router = useRouter();
    const [isSidebarOpen, setIsSidebarOpen] = useState(false); // 좌측 채팅 내역 사이드바
    const [isNavOpen, setIsNavOpen] = useState(false); // 우측 내비게이션 팝오버
    const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false); // [NEW] 프로필 메뉴 상태

    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [statusLog, setStatusLog] = useState("");
    const [isMounted, setIsMounted] = useState(false);
    const [threadId, setThreadId] = useState("");
    const [memberId, setMemberId] = useState<number | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // [Profile Logic] 메인 페이지와 동일하게 이식
    const [localUser, setLocalUser] = useState<{ memberId?: string | null; email?: string | null; nickname?: string | null; roleType?: string | null; isAdmin?: boolean } | null>(null);
    const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);

    useEffect(() => {
        setIsMounted(true);
        const stored = localStorage.getItem("localAuth");
        if (stored) {
            try {
                setLocalUser(JSON.parse(stored));
            } catch (error) {
                setLocalUser(null);
            }
        }

        const savedId = localStorage.getItem("chat_thread_id");
        if (savedId) {
            setThreadId(savedId);
        } else {
            const newId = crypto.randomUUID();
            localStorage.setItem("chat_thread_id", newId);
            setThreadId(newId);
        }
    }, []);

    useEffect(() => {
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const currentId = session?.user?.id || localUser?.memberId;

        if (!currentId) {
            setProfileImageUrl(null);
            setMemberId(null);
            return;
        }

        setMemberId(parseInt(currentId, 10));

        fetch(`${apiBaseUrl}/users/profile/${currentId}`)
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (data?.profile_image_url) {
                    const url = data.profile_image_url.startsWith("http")
                        ? data.profile_image_url
                        : `${apiBaseUrl}${data.profile_image_url}`;
                    setProfileImageUrl(url);
                }
            })
            .catch(() => setProfileImageUrl(null));
    }, [localUser, session]);

    const displayName = session?.user?.name || localUser?.nickname || localUser?.email?.split('@')[0] || "Guest";
    const isLoggedIn = Boolean(session || localUser);

    const scrollToBottom = useCallback(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
        }
    }, []);

    useEffect(() => {
        // DOM 렌더링 딜레이를 고려해 약간 지연
        setTimeout(() => scrollToBottom(), 50);
    }, [messages, scrollToBottom]);

    if (!isMounted) return <div className="min-h-screen bg-[#FAF8F5]" />;

    const handleNewChat = () => {
        if (loading) return;
        const newId = crypto.randomUUID();
        localStorage.setItem("chat_thread_id", newId);
        setThreadId(newId);
        setMessages([]);
        setInputValue("");
        setError("");
    };

    const handleSelectThread = async (id: string) => {
        if (loading) return;

        setLoading(true);
        setThreadId(id);
        localStorage.setItem("chat_thread_id", id); // 로컬 스토리지 갱신

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat/history/${id}`);
            if (!response.ok) throw new Error("내역 로드 실패");

            const data = await response.json();
            // 백엔드 필드명(text)을 프론트엔드 필드명(text)에 맞춰 매핑
            const formattedMessages = data.messages.map((m: any) => ({
                role: m.role,
                text: m.text,
                isStreaming: false
            }));

            setMessages(formattedMessages);
            // setIsSidebarOpen(false); // [수정] 리스트 선택 시 사이드바 자동 닫힘 방지 (사용자 요청)
        } catch (err) {
            console.error(err);
            setError("대화 내역을 불러오는데 실패했습니다.");
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const trimmed = inputValue.trim();
        if (!trimmed || !threadId) return;

        // [★추가] 로그인 정보(MemberID) 가져오기 (카카오 세션 또는 로컬 로그인)
        let currentMemberId = 0;
        let currentUserMode = "BEGINNER";

        // 1. 멤버 ID 결정 (카카오 세션 우선, 없으면 로컬)
        if (session?.user?.id) {
            currentMemberId = parseInt(session.user.id, 10);
        } else {
            // 로컬 로그인 확인
            try {
                const localAuth = localStorage.getItem("localAuth");
                if (localAuth) {
                    const parsed = JSON.parse(localAuth);
                    if (parsed && parsed.memberId) {
                        currentMemberId = parseInt(parsed.memberId, 10);
                    }
                }
            } catch (e) {
                console.error("Member ID Parsing Error:", e);
            }
        }

        // 2. 유저 모드 결정 (항상 localAuth 확인)
        try {
            const localAuth = localStorage.getItem("localAuth");
            if (localAuth) {
                const parsed = JSON.parse(localAuth);
                if (parsed && parsed.user_mode) {
                    currentUserMode = parsed.user_mode;
                }
            }
        } catch (e) {
            console.error("User Mode Parsing Error:", e);
        }
        setMessages((prev) => prev.map(m => ({ ...m, isStreaming: false })));
        setMessages((prev) => [...prev, { role: "user", text: trimmed, isStreaming: false }]);
        setInputValue("");
        setError("");
        setLoading(true);
        setStatusLog("AI가 요청을 분석 중입니다...");

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_query: trimmed,
                    thread_id: threadId,
                    member_id: currentMemberId,
                    user_mode: currentUserMode
                }),
            });

            if (!response.ok || !response.body) throw new Error("서버 연결 실패");

            setMessages((prev) => [...prev, { role: "assistant", text: "", isStreaming: true }]);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let done = false;
            let buffer = "";

            while (!done) {
                const { value, done: readerDone } = await reader.read();
                done = readerDone;
                if (value) {
                    const chunk = decoder.decode(value, { stream: true });
                    buffer += chunk;
                    const lines = buffer.split("\n\n");
                    buffer = lines.pop() || "";
                    for (const line of lines) {
                        const trimmedLine = line.trim();
                        if (!trimmedLine.startsWith("data: ")) continue;
                        try {
                            const data = JSON.parse(trimmedLine.replace("data: ", ""));
                            console.log("Stream Data:", data);
                            if (data.type === "answer") {
                                setStatusLog("");
                                setMessages((prev) => {
                                    const updated = [...prev];
                                    const lastIndex = updated.length - 1;
                                    const lastMsg = updated[lastIndex];

                                    if (lastMsg.role === "assistant") {
                                        let nextChunk = data.content;
                                        const prevText = lastMsg.text;
                                        const prevTrimmed = prevText.trimEnd();
                                        if (
                                            prevTrimmed.endsWith("---") &&
                                            !prevText.endsWith("\n") &&
                                            typeof nextChunk === "string" &&
                                            nextChunk.startsWith("##")
                                        ) {
                                            nextChunk = `\n${nextChunk}`;
                                        }
                                        updated[lastIndex] = {
                                            ...lastMsg,
                                            text: prevText + nextChunk
                                        };
                                    }
                                    return updated;
                                });
                            } else if (data.type === "log") {
                                setStatusLog(data.content);
                            } else if (data.type === "error") {
                                setStatusLog(`오류: ${data.content}`);
                            }
                        } catch (e: any) {
                            console.error(e);
                        }
                    }
                }
            }
        } catch (e: any) {
            setError("오류가 발생했습니다.");
        } finally {
            setLoading(false);
            setStatusLog("");
        }
    };

    return (
        <SavedPerfumesProvider memberId={memberId}>
            <div className="flex flex-col h-[100dvh] bg-[#FDFBF8] overflow-hidden text-black relative font-sans">

                {/* 1. 스마트 사이드바 (Nav용 Popover) */}
                <NavSidebar
                    isOpen={isNavOpen}
                    onClose={() => setIsNavOpen(false)}
                    context="home"
                />

                {/* [STANDARD HEADER] Fully Transparent for Chat Page (Standard Size Icons, z-30 to match Wiki) */}
                <header className="fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-6 md:px-10 py-5 bg-transparent border-b border-transparent">
                    {/* 로고 영역: Wiki와 동일하게 div로 감싸 구조 통일 */}
                    <div className="flex items-center gap-4">
                        <Link href="/" className="text-lg font-bold text-black tracking-[0.15em] uppercase hover:opacity-70 transition">
                            SCENTENCE
                        </Link>
                    </div>

                    {/* 우측 상단 UI: 로그인 상태 및 사이드바 토글 버튼 (표준) */}
                    {/* 우측 상단 UI: Perfume Wiki와 동일하게 통일 */}
                    <div className="flex items-center gap-4">
                        {!isLoggedIn ? (
                            <div className="flex items-center gap-2 text-sm font-medium text-gray-400">
                                <Link href="/login" className="hover:text-black transition-colors">Sign in</Link>
                                <span className="text-gray-300">|</span>
                                <Link href="/signup" className="hover:text-black transition-colors">Sign up</Link>
                            </div>
                        ) : (
                            <div className="flex items-center gap-3">
                                <button
                                    id="profile-menu-toggle"
                                    onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
                                    className="block w-9 h-9 rounded-full overflow-hidden border border-gray-100 shadow-sm hover:opacity-80 transition-opacity"
                                >
                                    <img
                                        src={profileImageUrl || "/default_profile.png"}
                                        alt="Profile"
                                        className="w-full h-full object-cover"
                                        onError={(e) => { e.currentTarget.src = "/default_profile.png"; }}
                                    />
                                </button>
                                <UserProfileMenu
                                    isOpen={isProfileMenuOpen}
                                    onClose={() => setIsProfileMenuOpen(false)}
                                />
                            </div>
                        )}

                        <button
                            id="global-menu-toggle"
                            onClick={() => setIsNavOpen(!isNavOpen)}
                            className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
                        >
                            {isNavOpen ? (
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            ) : (
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5m-16.5 6.75h16.5" />
                                </svg>
                            )}
                        </button>
                    </div>
                </header>

                {/* 3. Content Wrapper (Sidebar + Main) */}
                <div className="flex-1 flex relative overflow-hidden pt-[72px]">

                    {/* Left Chat Sidebar Container: 데스크탑에서 영역을 실제로 차지하여 본문을 밀어냄 */}
                    <div
                        className={`hidden md:block overflow-hidden transition-all duration-300 ease-in-out ${isSidebarOpen ? "w-64" : "w-0"}`}
                    >
                        <ChatSidebar
                            isOpen={isSidebarOpen}
                            activeThreadId={threadId}
                            onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
                            onNewChat={handleNewChat}
                            onSelectThread={handleSelectThread}
                            loading={loading}
                            showToggleButton={false}
                            currentMemberId={memberId} // ✅ [수정] Page에서 파악한 MemberID 전달
                        />
                    </div>

                    {/* Mobile Sidebar: 모바일에서는 화면을 덮는 기존 방식 유지 */}
                    <div className="md:hidden">
                        <ChatSidebar
                            isOpen={isSidebarOpen}
                            activeThreadId={threadId}
                            onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
                            onNewChat={handleNewChat}
                            onSelectThread={handleSelectThread}
                            loading={loading}
                            showToggleButton={false}
                            currentMemberId={memberId} // ✅ [수정] Page에서 파악한 MemberID 전달
                        />
                    </div>

                    {/* Main Chat Area: 사이드바가 밀어주는 만큼 가시 너비가 변하며 내부 mx-auto 콘텐츠가 자동 리정렬됨
                        [수정] h-full 제거: Flex 컨테이너 안에서 높이를 자동 조절하도록 변경 (하단 겹침 방지 핵심)
                        [수정] gap-6: 출력창(스크롤 영역)과 입력창 사이에 물리적인 간격을 줌
                    */}
                    <main className="flex-1 flex flex-col relative bg-[#FDFBF8] overflow-hidden gap-3">

                        {/* ✅ 사이드바 토글 버튼 (헤더 바로 아래 좌측)
                            [수정] absolute 배치: 콘텐츠 영역을 밀어내지 않도록 띄움 (헤더와 대화창 사이 불필요한 공백 제거)
                        */}
                        <div className="absolute top-2 left-4 z-30">
                            <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-[#555]">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" strokeLinecap="round" strokeLinejoin="round" />
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v18" />
                                </svg>
                            </button>
                        </div>

                        {/* Chat Messages: 너비를 제한하여 가독성을 높이고 입력창과 밸런스를 맞춤
                            [수정] pb-10: 사용자가 직접 조정한 하단 여백 유지
                            [수정] pt-5: 헤더와 너무 딱 붙지 않도록 상단에 살짝 여백 추가
                            [수정] no-scrollbar 제거: 스크롤바 노출 (사용자 요청)
                         */}
                        <div className="flex-1 overflow-y-auto pt-5 pb-10 custom-scrollbar">
                            {/* [수정 가이드] 챗봇 출력창 너비 조절
                                - max-w-5xl: 가장 표준적인 챗봇 너비 (약 1024px).
                                - w-full: 반응형 대응
                                - mx-auto: 중앙 정렬
                             */}
                            <div className={`w-full max-w-5xl mx-auto px-4 ${messages.length === 0 ? "h-full" : ""}`}>
                                <ChatList
                                    messages={messages}
                                    loading={loading}
                                    statusLog={statusLog}
                                    messagesEndRef={messagesEndRef}
                                    scrollToBottom={scrollToBottom}
                                    userName={displayName}
                                />
                            </div>
                        </div>

                        {/* ✅ 채팅 입력창 (사이드바 간섭 없애고 볼륨감있게 수정 Floating Box) */}
                        {/* [수정 가이드] 채팅 입력창 너비 조절
                            - max-w-5xl: 출력창과 동일하게 맞춤 (균형 유지)
                            - w-full: 화면이 좁아질 때 유연하게 줄어듦
                            - px-4: 좌우 여백 확보
                        */}
                        <div className="shrink-0 px-4 pb-5 z-30 w-[80%] max-w-3xl mx-auto">
                            <form onSubmit={handleSubmit} className="relative bg-white rounded-[26px] shadow-sm border border-[#E5E4DE] focus-within:ring-1 focus-within:ring-[#D97757]/30 transition-all">
                                <div className="flex items-center min-h-[50px] pr-2">
                                    <textarea
                                        className="flex-1 w-full bg-transparent py-3 pl-5 text-[#393939] placeholder:text-gray-400 outline-none resize-none text-base custom-scrollbar"
                                        placeholder={"어떤 향수를 찾으시나요? 무엇이든 물어보세요."}
                                        rows={1}
                                        value={inputValue}
                                        onChange={(e) => {
                                            setInputValue(e.target.value);
                                            e.target.style.height = 'auto';
                                            e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
                                        }}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault();
                                                handleSubmit(e as any);
                                            }
                                        }}
                                        disabled={loading}
                                    />
                                    <div className="flex shrink-0 gap-2 items-center">
                                        <button
                                            className={`
                                                flex items-center justify-center transition-all duration-200 ease-in-out
                                                ${inputValue.trim()
                                                    ? "bg-gradient-to-r from-[#FF9F9F] to-[#D97757] text-white shadow-md hover:shadow-lg hover:scale-105 active:scale-95"
                                                    : "bg-gray-100 text-gray-300 cursor-not-allowed"}
                                            `}
                                            type="submit"
                                            disabled={loading || !inputValue.trim()}
                                            style={{ width: "38px", height: "38px", borderRadius: "50%" }}
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                                                <path fillRule="evenodd" d="M10.5 3a.75.75 0 0 1 .75.75v2.25h1.5V3.75a.75.75 0 0 1 1.5 0v3a.75.75 0 0 1-.75.75h-3a.75.75 0 0 1-.75-.75v-3a.75.75 0 0 1 .75-.75ZM7.5 9a2.25 2.25 0 0 1 2.25-2.25h4.5A2.25 2.25 0 0 1 16.5 9v9.75a2.25 2.25 0 0 1-2.25 2.25h-4.5A2.25 2.25 0 0 1 7.5 18.75V9ZM12 11.25a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z" clipRule="evenodd" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </form>
                            <div className="text-center mt-3">
                                <span className="text-[11px] text-gray-400">AI는 가끔 실수할 때도 있습니다. 따뜻한 마음으로 대화해 주세요.</span>
                            </div>
                        </div>
                    </main>

                    {/* Mobile/Nav Overlay */}
                    {/* Mobile/Nav Overlay Strategy */}



                    {/* 2. 좌측 ChatSidebar용 오버레이 (모바일 전용) 
                        - md:hidden: 데스크탑에서는 오버레이를 숨겨서 본문 클릭(입력 등)을 허용
                        - onClick 제거: 사용자가 "버튼으로만 닫기"를 원하므로 배경 클릭 닫기 비활성화
                    */}
                    {isSidebarOpen && (
                        <div
                            className="absolute inset-0 bg-transparent z-40 md:hidden"
                        // onClick={() => setIsSidebarOpen(false)} // 사용자 요청으로 비활성화
                        />
                    )}
                </div>
            </div>
        </SavedPerfumesProvider>
    );
}
