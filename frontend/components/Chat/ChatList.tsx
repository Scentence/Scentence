"use client";

import { useEffect, useState, RefObject } from "react";
import MessageItem, { Message } from "./MessageItem";

interface ChatListProps {
    messages: Message[];
    loading: boolean;
    messagesEndRef: RefObject<HTMLDivElement>;
    statusLog?: string;
    userName?: string; // 사용자 이름 추가
}

const GREETINGS = [
    "어서오세요.",
    "만나서 반가워요!",
    "좋은 하루에요!",
    "무엇을 도와드릴까요?"
];

const ChatList = ({ messages, loading, messagesEndRef, statusLog, userName = "Guest" }: ChatListProps) => {
    // 인사말 회전 로직
    const [greetingIndex, setGreetingIndex] = useState(0);

    useEffect(() => {
        if (messages.length === 0) {
            const interval = setInterval(() => {
                setGreetingIndex((prev) => (prev + 1) % GREETINGS.length);
            }, 5000); // 5초마다 변경 (요청사항 반영)
            return () => clearInterval(interval);
        }
    }, [messages.length]);

    // 대화 시작 전 초기 화면 (Hero Section Style Greeting)
    if (messages.length === 0) {
        return (
            <section className="flex-1 h-full overflow-hidden relative flex flex-col items-center justify-center text-center p-6 pb-15">
                {/* Animation Styles */}
                <style>
                    {`
                        @keyframes fadeInUp {
                            from { opacity: 0; transform: translateY(20px); filter: blur(4px); }
                            to { opacity: 1; transform: translateY(0); filter: blur(0); }
                        }
                        .animate-greeting {
                            animation: fadeInUp 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
                        }
                    `}
                </style>
                <div className="flex flex-col items-center gap-4 md:gap-8 opacity-100 max-w-5xl mt-12 md:mt-0">
                    <div className="w-28 h-28 md:w-40 md:h-40 mb-2 drop-shadow-xl transition-transform hover:scale-105 duration-500">
                        <img
                            src="/perfumes/chatlist_icon1.png"
                            alt="Chat Icon"
                            className="w-full h-full object-contain"
                        />
                    </div>
                    <div className="flex flex-col items-center gap-6 md:gap-12">
                        <h1 className="text-2xl md:text-5xl font-bold text-[#2A2A2A] tracking-tight -mt-4">
                            {userName}님,
                        </h1>
                        {/* 텍스트 높이 확보를 위한 Wrapper */}
                        <div className="h-[1.3em] relative flex items-center justify-center overflow-visible w-full min-w-[300px]">
                            <span
                                className="absolute animate-greeting text-3xl md:text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-[#D97757] via-[#FF8F8F] to-[#D97757] bg-[length:200%_auto] bg-center"
                                key={greetingIndex}
                                style={{ whiteSpace: 'nowrap' }}
                            >
                                {GREETINGS[greetingIndex]}
                            </span>
                        </div>
                    </div>
                </div>
            </section>
        );
    }

    return (
        <section className="flex-1 overflow-y-auto no-scrollbar">
            <div className="space-y-6">
                {/* 기존 메시지 목록 렌더링 */}
                {messages.map((msg, idx) => (
                    <MessageItem key={idx} message={msg} />
                ))}

                {/* ✅ 실시간 진행 상태(statusLog) 표시 영역 */}
                {loading && (
                    <div className="flex flex-col gap-2">
                        {/* 1. 백엔드에서 전달된 단계별 상태 로그 표시 */}
                        {statusLog ? (
                            <div className="flex justify-start animate-pulse px-1">
                                <div className="flex items-center gap-2 rounded-2xl bg-white/50 border border-gray-300 px-4 py-2 text-xs text-gray-700 shadow-sm backdrop-blur-sm">
                                    {/* 향수 GIF 아이콘 */}
                                    <img src="/perfume.gif" alt="Loading" className="w-5 h-5 object-contain" />
                                    {statusLog}
                                </div>
                            </div>
                        ) : (
                            /* 2. 로그가 없고 답변 데이터도 아직 오지 않았을 때의 기본 로딩 */
                            messages[messages.length - 1]?.text === "" && (
                                <div className="flex justify-start">
                                    <div className="rounded-2xl bg-white/80 border border-[#E5E4DE] px-5 py-4 text-sm text-[#8E8E8E] animate-pulse shadow-sm">
                                        AI가 답변을 준비하고 있습니다... 💭
                                    </div>
                                </div>
                            )
                        )}
                    </div>
                )}

                {/* 하단 스크롤용 지점 */}
                <div ref={messagesEndRef} />
            </div>
        </section>
    );
};

export default ChatList;
