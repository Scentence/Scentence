"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";

const BACKEND_URL = "/api";

interface ChatRoom {
    thread_id: string;
    title: string;
    last_chat_dt: string;
}

interface SidebarProps {
    isOpen: boolean;
    activeThreadId?: string;
    onToggle: () => void;
    onNewChat: () => void;
    onSelectThread: (id: string) => void;
    loading: boolean;
    showToggleButton?: boolean;
    currentMemberId?: number | null; // ✅ [수정] 부모(Page)로부터 전달받는 유저 ID
}

const Sidebar = ({ isOpen, activeThreadId, onToggle, onNewChat, onSelectThread, loading, showToggleButton = false, currentMemberId }: SidebarProps) => {
    const { data: session } = useSession(); // 카카오 로그인 세션
    const [chatRooms, setChatRooms] = useState<ChatRoom[]>([]);
    const [userNickname, setUserNickname] = useState("Guest");

    // [1] 사이드바가 열리거나 유저 ID가 변경될 때 목록 불러오기
    useEffect(() => {
        console.log("[Sidebar Debug] Current Props:", { isOpen, currentMemberId, sessionUserId: session?.user?.id });

        // 1. Props로 전달받은 ID가 있으면 최우선 사용
        if (currentMemberId) {
            console.log("[Sidebar] Fetching rooms for member_id (Prop):", currentMemberId);
            fetch(`${BACKEND_URL}/chat/rooms/${currentMemberId}`)
                .then(res => {
                    console.log("[Sidebar] API Response Status:", res.status);
                    return res.json();
                })
                .then(data => {
                    console.log("[Sidebar] Loaded Rooms:", data);
                    setChatRooms(data.rooms || []);
                })
                .catch(err => console.error("History Load Error:", err));
            return;
        }

        // 2. Props가 없으면 세션 기반으로만 조회
        if (session?.user?.id) {
            setUserNickname(session.user.name || "User");
            if (isOpen) {
                console.log("[Sidebar] Fetching rooms for member_id (Session):", session.user.id);
                fetch(`${BACKEND_URL}/chat/rooms/${session.user.id}`)
                    .then(res => res.json())
                    .then(data => setChatRooms(data.rooms || []))
                    .catch(err => console.error("History Load Error:", err));
            }
            return;
        }
    }, [isOpen, session, currentMemberId]);

    return (
        <>
            {showToggleButton && (
                <button onClick={onToggle} className="fixed top-4 left-4 z-[60] p-2 hover:bg-[#F2F1EE] rounded-lg transition-colors bg-white/50 backdrop-blur-sm md:bg-transparent">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6 text-[#393939]">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                    </svg>
                </button>
            )}

            {/* [SIDEBAR CONTAINER] md:relative로 변경하여 Flex 밀어내기 지원 */}
            <div className={`fixed top-[72px] bottom-0 left-0 z-[40] w-64 bg-white border-r border-[#E5E4DE] transition-transform duration-300 transform 
                ${isOpen ? "translate-x-0" : "-translate-x-full"} 
                md:relative md:top-0 md:translate-x-0 md:z-0 md:h-full`}>
                <div className="flex h-full flex-col p-4 pt-4">
                    <div className="flex justify-between items-center mb-6 px-2">
                        <span className="text-[10px] font-bold tracking-widest text-[#8E8E8E]">RECENT HISTORY</span>
                        {/* [수정] 중복 X 버튼 제거 (비상식적 UI 개선) */}
                    </div>

                    <button onClick={onNewChat} disabled={loading} className="group flex items-center justify-center gap-2 rounded-xl border border-[#E5E4DE] bg-[#FAF8F5] py-3 text-sm font-medium text-[#393939] transition-all hover:bg-[#F2F1EE] disabled:opacity-50">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-5 w-5 transition-transform group-hover:rotate-180"><path strokeLinecap="round" strokeLinejoin="round" d="M16 9h5M3 19v-5m0 0h5m-5 0l3 3a8 8 0 0013-3M4 10a8 8 0 0113-3l3 3m0-5v5" /></svg>
                        새로운 대화 시작
                    </button>

                    {/* ✅ 실제 대화 목록 렌더링 영역 */}
                    <div className="mt-8 flex-1 overflow-y-auto custom-scrollbar space-y-1">
                        {chatRooms.length > 0 ? (
                            chatRooms.map((room) => (
                                <button
                                    key={room.thread_id}
                                    onClick={() => onSelectThread(room.thread_id)}
                                    // [수정] 클릭 후 회색 음영 남지 않도록 active active highlight 제거. 호버 시에만 반응.
                                    className={`w-full text-left px-3 py-3 rounded-xl transition-colors hover:bg-[#FAF8F5] ${activeThreadId === room.thread_id ? "font-semibold text-[#393939]" : ""}`}
                                >
                                    <p className="text-sm text-[#393939] truncate">{room.title || "이전 대화"}</p>
                                    <p className="text-[10px] text-[#BCBCBC] mt-1">{new Date(room.last_chat_dt).toLocaleDateString()}</p>
                                </button>
                            ))
                        ) : (
                            <p className="px-2 text-xs text-[#BCBCBC]">이전 대화가 없습니다.</p>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
};

export default Sidebar;
