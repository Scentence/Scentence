"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSavedPerfumes } from "../../contexts/SavedPerfumesContext";

export type Message = {
    role: "user" | "assistant";
    text: string;
    isStreaming?: boolean;
};

const BACKEND_URL = "/api";

// ✅ 1. 저장 버튼 컴포넌트 (카카오 세션 지원)
const SaveButton = ({ id, name }: { id: string; name: string }) => {
    const { data: session } = useSession(); // 카카오 로그인 세션
    const { isSaved: checkSaved, addSavedPerfume } = useSavedPerfumes();
    const perfumeId = parseInt(id);
    const [isSaved, setIsSaved] = useState(false);
    const [loading, setLoading] = useState(false);

    // Check if perfume is already saved on mount
    useEffect(() => {
        setIsSaved(checkSaved(perfumeId));
    }, [perfumeId, checkSaved]);

    const handleSave = async () => {
        let memberId = 0;

        // 카카오 로그인 세션 확인
        if (session?.user?.id) {
            memberId = parseInt(session.user.id, 10);
        } else {
            // 로컬 로그인 확인
            try {
                const localAuth = localStorage.getItem("localAuth");
                if (localAuth) {
                    const parsed = JSON.parse(localAuth);
                    if (parsed && parsed.memberId) {
                        memberId = parseInt(parsed.memberId, 10);
                    }
                }
            } catch (e) {
                console.error("로그인 정보 파싱 실패:", e);
            }
        }

        if (memberId === 0) {
            alert("로그인이 필요한 서비스입니다.");
            return;
        }

        setLoading(true);
        try {
            const res = await fetch(`${BACKEND_URL}/users/me/perfumes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    member_id: memberId,
                    perfume_id: parseInt(id),
                    perfume_name: name,
                }),
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "저장 실패");

            if (data.status === "already_exists") {
                alert("이미 내 향수에 저장되어 있어요! 😉");
                setIsSaved(true);
                addSavedPerfume(perfumeId);
            } else {
                alert(`'${name}'이(가) 내 향수로 저장되었습니다! 💖`);
                setIsSaved(true);
                addSavedPerfume(perfumeId);
            }
        } catch (e: any) {
            console.error(e);
            alert(`저장 중 오류가 발생했습니다: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <button
            onClick={handleSave}
            disabled={isSaved || loading}
            className={`mt-3 mb-1 flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-sm
                ${isSaved
                    ? "bg-gray-100 text-gray-400 cursor-default border border-gray-200"
                    : "bg-white text-pink-600 hover:bg-pink-50 border border-pink-200 hover:border-pink-300"
                }`}
        >
            {loading ? <span>⏳ 저장 중...</span> : isSaved ? <>✅ 저장됨</> : (
                <>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                        <path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.36 2.25 12.174 2.25 8.25 2.25 5.322 4.714 3 7.688 3A5.5 5.5 0 0112 5.052 5.5 5.5 0 0116.313 3c2.973 0 5.437 2.322 5.437 5.25 0 3.925-2.438 7.111-4.739 9.256a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.219l-.022.012-.007.004-.003.001a.752.752 0 01-.704 0l-.003-.001z" />
                    </svg>
                    내 향수로 저장
                </>
            )}
        </button>
    );
};

// ✅ 2. 텍스트 파서 및 마크다운 스타일링
const parseMessageContent = (text: string) => {
    if (!text) return null;

    const regex = /(\[\[SAVE:\d+:[^\]]+\]\])/g;
    const parts = text.split(regex);

    return parts.map((part, index) => {
        const match = part.match(/^\[\[SAVE:(\d+):([^\]]+)\]\]$/);

        if (match) {
            return <SaveButton key={index} id={match[1]} name={match[2]} />;
        }

        if (!part.trim()) {
            return (
                <span key={index} className="whitespace-pre-wrap">
                    {part}
                </span>
            );
        }

        return (
            <ReactMarkdown
                key={index}
                remarkPlugins={[remarkGfm]}
                components={{
                    // [기존 유지] 링크
                    a: ({ node, ...props }: any) => (
                        <a {...props} target="_blank" rel="noopener noreferrer" className="text-pink-600 hover:underline" />
                    ),

                    // [기존 유지] 이미지 (Rounded-2xl 사각형 유지)
                    img: ({ node, ...props }: any) => {
                        return (
                            <span className="mx-auto my-6 block h-40 w-40 md:h-[250px] md:w-[250px] overflow-hidden rounded-2xl shadow-lg border border-slate-200 relative bg-white">
                                <img
                                    {...props}
                                    className="h-full w-full object-contain p-2 transition-all duration-300"
                                    alt={props.alt || "Perfume Image"}
                                />
                            </span>
                        );
                    },

                    // [기존 유지] h2: 핑크색 보더 포인트 (브랜드명 등)
                    h2: ({ node, ...props }: any) => (
                        <h2 {...props} className="text-lg font-bold mt-6 mb-3 text-[#393939] border-l-4 border-pink-500 pl-3 leading-none" />
                    ),

                    // [★신규 추가] h3: 소제목 (분위기, 향기 구성 등) 강조 스타일
                    // 밑줄과 굵은 폰트로 섹션을 명확히 나눕니다.
                    h3: ({ node, ...props }: any) => (
                        <h3 {...props} className="text-base font-bold mt-6 mb-2 text-slate-800 border-b-2 border-slate-100 pb-1" />
                    ),

                    // [기존 유지] 기타 스타일
                    hr: ({ node, ...props }: any) => <hr {...props} className="my-8 border-[#E5E4DE]" />,
                    em: ({ node, ...props }: any) => (
                        <em {...props} className="not-italic text-violet-600 font-bold mr-1" />
                    ),
                    strong: ({ node, ...props }: any) => <strong {...props} className="text-pink-600 font-extrabold" />,
                    p: ({ node, ...props }: any) => <p {...props} className="mb-3 last:mb-0 leading-relaxed text-slate-700" />,

                    // [기존 유지] 리스트
                    ul: ({ node, ...props }: any) => <ul {...props} className="list-disc pl-5 mb-4 space-y-1 text-sm" />,
                    li: ({ node, ...props }: any) => <li {...props} className="pl-1" />,

                    // [★디자인 수정] 인용구 (노트 설명, 코멘트 강조용)
                    // 회색 박스 대신 깔끔한 핑크색 라인 스타일 적용
                    blockquote: ({ node, ...props }: any) => (
                        <blockquote
                            {...props}
                            className="my-3 pl-4 border-l-[3px] border-pink-300 text-sm text-slate-600 italic bg-transparent"
                        />
                    ),

                    // [기존 유지] 테이블
                    table: ({ node, ...props }: any) => (
                        <div className="overflow-x-auto my-4 rounded-lg border border-gray-100">
                            <table {...props} className="w-full text-sm text-left text-gray-600" />
                        </div>
                    ),
                    thead: ({ node, ...props }: any) => (
                        <thead {...props} className="text-xs text-gray-500 uppercase bg-gray-50 border-b border-gray-100" />
                    ),
                    tbody: ({ node, ...props }: any) => (
                        <tbody {...props} className="bg-white divide-y divide-gray-50" />
                    ),
                    tr: ({ node, ...props }: any) => <tr {...props} className="hover:bg-gray-50 transition-colors" />,
                    th: ({ node, ...props }: any) => (
                        <th {...props} className="px-4 py-2 font-semibold text-center whitespace-nowrap" />
                    ),
                    td: ({ node, ...props }: any) => (
                        <td {...props} className="px-4 py-2 text-center whitespace-nowrap" />
                    ),
                }}
            >
                {part}
            </ReactMarkdown>
        );
    });
};

// ✅ 3. 최종 조립 (기존 유지)
const MessageItem = ({ message }: { message: Message }) => {
    if (message.role === "assistant" && !message.text) return null;

    return (
        <div className={`flex w-full ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            {/* [수정 가이드] 말풍선 너비 조절
                - max-w-[90%]: 모바일에서 화면의 90%까지 시원하게 차지
                - md:max-w-[80%]: 데스크탑에서는 너무 길어지지 않게 80% 정도로 제한 (가독성 최적화)
            */}
            {/* [수정 가이드] 말풍선 너비 조절
                - max-w-[90%]: 모바일에서 화면의 90%까지 시원하게 차지
                - md:max-w-[80%]: 데스크탑에서는 너무 길어지지 않게 80% 정도로 제한 (가독성 최적화)
            */}
            <div className={`max-w-[90%] md:max-w-[80%] rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-sm ${message.role === "user"
                ? "bg-[#E5E4DE] text-[#393939]"
                : "bg-white text-[#393939] border border-[#E5E4DE]"
                }`}>
                <div className="mb-1 font-semibold uppercase tracking-[0.2em] text-[0.6rem] text-[#8E8E8E]">
                    {message.role === "user" ? "나" : "AI"}
                </div>
                {message.role === "assistant" ? (
                    <div className="w-full break-words">
                        {parseMessageContent(message.text)}
                    </div>
                ) : (
                    <div className="whitespace-pre-wrap break-words">{message.text}</div>
                )}
            </div>
        </div>
    );
};

export default MessageItem;
