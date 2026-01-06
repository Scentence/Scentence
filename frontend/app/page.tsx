"use client";

import { FormEvent, useState } from "react";

type Message = {
  role: "user" | "assistant";
  text: string;
};

type ChatMeta = {
  clarified_query?: string;
  research_result?: string;
  conversation_history?: { question: string; answer: string }[];
};

const API_URL = "http://localhost:8000/chat";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState<ChatMeta | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = inputValue.trim();
    if (!trimmed) {
      return;
    }

    const updatedMessages = [...messages, { role: "user", text: trimmed }];
    setMessages(updatedMessages as Message[]);
    setInputValue("");
    setError("");
    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_query: trimmed }),
      });

      if (!response.ok) {
        throw new Error("서버 응답 오류");
      }

      const payload = await response.json();

      setMeta({
        clarified_query: payload.clarified_query,
        research_result: payload.research_result,
        conversation_history: payload.conversation_history,
      });

      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: payload.final_response ?? "응답을 생성할 수 없습니다." },
      ]);
    } catch (e) {
      setError("서버 연결 또는 응답 처리에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 px-4 py-12 text-slate-50">
      <div className="mx-auto w-full max-w-3xl space-y-8">
        <header className="space-y-2">
          <p className="text-sm uppercase tracking-[0.4em] text-slate-400">Perfume Assistant</p>
          <h1 className="text-3xl font-semibold text-white">간단한 챗 인터페이스</h1>
          <p className="text-slate-300">
            질문을 입력하면 백엔드의 LangGraph 워크플로우를 호출하여 단계별 응답을 생성합니다.
          </p>
        </header>

        <section className="rounded-2xl border border-slate-800 bg-white/5 p-6 shadow-lg shadow-slate-900/40">
          <div className="space-y-4">
            {messages.length === 0 && (
              <p className="text-slate-400">아래 입력창에 질문을 입력하고 엔터를 눌러 시작하세요.</p>
            )}
            <div className="space-y-3">
              {messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`rounded-2xl px-4 py-3 text-sm ${
                    message.role === "user"
                      ? "bg-slate-800 text-slate-100 self-end"
                      : "bg-slate-700/70 text-white"
                  }`}
                >
                  <p className="font-semibold uppercase tracking-[0.2em] text-[0.6rem] text-slate-400">
                    {message.role === "user" ? "나" : "앱"}
                  </p>
                  <p className="pt-1 leading-relaxed">{message.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex gap-3">
            <input
              className="flex-1 rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-base text-white outline-none placeholder:text-slate-500"
              placeholder="예) 시트러스 향 추천"
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              disabled={loading}
            />
            <button
              className="rounded-2xl bg-gradient-to-r from-pink-500 to-purple-500 px-5 py-3 text-sm font-semibold uppercase tracking-wide text-white disabled:opacity-50"
              type="submit"
              disabled={loading}
            >
              {loading ? "전송 중..." : "전송"}
            </button>
          </div>
          {error && <p className="text-sm text-rose-300">{error}</p>}
        </form>

        {meta && (
          <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-200">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">메타 정보</p>
            {meta.clarified_query && (
              <p className="pt-2">
                <strong className="text-slate-300">명확화 요청:</strong> {meta.clarified_query}
              </p>
            )}
            {meta.research_result && (
              <p className="pt-2">
                <strong className="text-slate-300">조사 결과:</strong> {meta.research_result}
              </p>
            )}
            {meta.conversation_history?.length ? (
              <div className="pt-2">
                <p className="text-slate-300">대화 이력:</p>
                <ul className="mt-1 space-y-1 text-slate-300">
                  {meta.conversation_history.map((item, idx) => (
                    <li key={`history-${idx}`} className="rounded-xl bg-slate-800/60 px-3 py-2 text-xs">
                      <p className="font-semibold text-slate-100">Q: {item.question}</p>
                      <p>A: {item.answer}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        )}
      </div>
    </div>
  );
}
