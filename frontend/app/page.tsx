"use client";

import { FormEvent, useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  role: "user" | "assistant";
  text: string;
};

const API_URL = "http://localhost:8000/chat";

// [수정 1] useTypewriter 삭제됨 (서버 스트리밍 속도 그대로 이용)

// [수정 2] MessageItem 단순화
const MessageItem = ({ message }: { message: Message }) => {
  return (
    <div className={`flex w-full ${message.role === "user" ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-sm ${message.role === "user"
          ? "bg-slate-800 text-slate-100"
          : "bg-slate-700/50 text-slate-100"
          }`}
      >
        <p className="mb-1 font-semibold uppercase tracking-[0.2em] text-[0.6rem] text-slate-400">
          {message.role === "user" ? "나" : "AI"}
        </p>

        {message.role === "assistant" ? (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ node, ...props }) => (
                  <a {...props} target="_blank" rel="noopener noreferrer" className="text-pink-400 hover:underline" />
                ),
                img: ({ node, ...props }) => (
                  <span className="mx-auto my-6 block h-[250px] w-[250px] overflow-hidden rounded-2xl shadow-lg border border-slate-600/50 relative">
                    <img
                      {...props}
                      className="h-full w-full object-cover object-center scale-125"
                      alt={props.alt || "Perfume Image"}
                    />
                  </span>
                ),
                h2: ({ node, ...props }) => (
                  <h2 {...props} className="text-xl font-bold mt-8 mb-3 text-white border-l-4 border-pink-500 pl-3" />
                ),
                hr: ({ node, ...props }) => (
                  <hr {...props} className="my-10 border-slate-600" />
                ),
                em: ({ node, ...props }) => (
                  <em {...props} className="not-italic text-violet-400 font-bold mr-1" />
                ),
                strong: ({ node, ...props }) => (
                  <strong {...props} className="text-pink-300 font-extrabold" />
                ),
              }}
            >
              {/* [수정] typedText 대신 원본 text 그대로 출력 */}
              {message.text}
            </ReactMarkdown>
            {/* [추가] 커서 깜빡임 효과 (생성 중일 때만 보임) */}
          </div>
        ) : (
          <p>{message.text}</p>
        )}
      </div>
    </div>
  );
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // [추가] 진행 상태 로그 (예: "🔎 조사 완료: ...")
  const [statusLog, setStatusLog] = useState("");

  // [추가] 자동 스크롤 Ref
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, statusLog]); // 메시지나 로그가 바뀔 때마다 스크롤

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = inputValue.trim();
    if (!trimmed) return;

    // 1. 유저 메시지 추가
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setInputValue("");
    setError("");
    setLoading(true);
    setStatusLog("AI가 요청을 분석 중입니다..."); // 초기 로그

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_query: trimmed,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("서버 연결 실패");
      }

      // 2. 봇 응답용 빈 말풍선 미리 추가
      setMessages((prev) => [...prev, { role: "assistant", text: "" }]);

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

          // SSE 포맷은 double newline(\n\n)으로 구분됨
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || ""; // 불완전한 마지막 조각은 버퍼에 남김

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine.startsWith("data: ")) continue;

            try {
              const jsonStr = trimmedLine.replace("data: ", "");
              const data = JSON.parse(jsonStr);

              // [수정 3] 핵심 스트리밍 로직

              // Case A: 답변 토큰 도착 (한 글자씩)
              if (data.type === "answer") {
                setStatusLog("");
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastIndex = updated.length - 1;
                  const lastMsg = updated[lastIndex];

                  // [중요] 덮어쓰기(=)가 아니라 이어붙이기(+=)
                  if (lastMsg.role === "assistant") {
                    updated[lastIndex] = {
                      ...lastMsg,
                      text: lastMsg.text + data.content, // 새로운 문자열 생성
                    };
                  }
                  return updated;
                });
              }
              // Case B: 로그 메시지 도착 (Researcher 단계)
              else if (data.type === "log") {
                setStatusLog(data.content);
              }
              // Case C: 에러 처리
              else if (data.type === "error") {
                setStatusLog(`오류: ${data.content}`);
              }

            } catch (e) {
              console.error("JSON Parsing Error:", e);
            }
          }
        }
      }
    } catch (e) {
      setError("응답을 받아오는 중 오류가 발생했습니다.");
      setMessages((prev) => [...prev, { role: "assistant", text: "죄송합니다. 오류가 발생했습니다." }]);
    } finally {
      setLoading(false);
      setStatusLog(""); // 종료 시 로그 초기화
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 px-4 py-12 text-slate-50">
      <div className="mx-auto w-full max-w-3xl space-y-8">

        <header className="space-y-2 text-center sm:text-left">
          <p className="text-sm uppercase tracking-[0.4em] text-slate-400">Perfume Assistant</p>
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-semibold text-white">SCENTENCE AI</h1>
            <button
              onClick={() => { setMessages([]); setInputValue(""); }}
              disabled={loading}
              className="group flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800/50 px-4 py-2 text-xs font-medium text-slate-300 transition-all hover:bg-slate-700 hover:text-white"
            >
              새 대화
            </button>
          </div>
          <p className="text-slate-300">LangGraph & Real-time Streaming</p>
        </header>

        <section className="relative min-h-[500px] flex flex-col rounded-2xl border border-slate-800 bg-white/5 p-6 shadow-lg shadow-slate-900/40">
          <div className="flex-1 space-y-6 overflow-y-auto pb-4 custom-scrollbar">
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center text-slate-500 space-y-2">
                <p>원하는 향기나 분위기를 말씀해주세요.</p>
                <p className="text-xs text-slate-600">예) "여름에 쓰기 좋은 시트러스 향수 추천해줘"</p>
              </div>
            )}

            {messages.map((msg, idx) => (
              <MessageItem key={idx} message={msg} />
            ))}

            {/* [추가] 상태 로그 표시 (검색 중일 때 하단에 작게 뜸) */}
            {loading && statusLog && (
              <div className="flex justify-start animate-fade-in">
                <div className="flex items-center gap-2 rounded-lg bg-slate-800/50 px-4 py-2 text-xs text-pink-300 border border-pink-500/20">
                  <span className="animate-spin">⏳</span> {statusLog}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </section>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex gap-3">
            <input
              className="flex-1 rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-base text-white outline-none focus:border-pink-500/50 transition-colors disabled:opacity-50"
              placeholder="질문을 입력하세요..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={loading}
            />
            <button
              className="rounded-2xl bg-gradient-to-r from-pink-600 to-purple-600 px-6 py-3 font-semibold text-white hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
              type="submit"
              disabled={loading}
            >
              {loading ? "..." : "전송"}
            </button>
          </div>
          {error && <p className="text-sm text-rose-300 text-center">{error}</p>}
        </form>
      </div>
    </div>
  );
}