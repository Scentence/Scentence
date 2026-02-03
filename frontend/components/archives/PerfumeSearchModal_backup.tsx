/* PerfumeSearchModal.tsx (Color Updated) */
"use client";

import { useState } from 'react';

interface SearchResult {
    perfume_id: number;
    name: string;
    brand: string;
    image_url: string | null;
}

interface Props {
    memberId: string | null;
    onClose: () => void;
    onAdd: (perfume: SearchResult, status: string) => void;
}

export default function PerfumeSearchModal({ memberId, onClose, onAdd }: Props) {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [loading, setLoading] = useState(false);

    const handleSearch = async () => {
        if (!query.trim()) return;
        try {
            setLoading(true);
            const res = await fetch(`/api/perfumes/search?q=${encodeURIComponent(query)}`);
            if (res.ok) {
                const data = await res.json();
                setResults(data);
            }
        } catch (error) {
            console.error("Search failed:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") handleSearch();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-white w-full max-w-lg rounded-3xl shadow-2xl flex flex-col max-h-[80vh] overflow-hidden">

                <div className="flex items-center justify-between p-6 border-b border-gray-50 bg-[#FDFBF8]">
                    <h2 className="text-[#333] font-bold text-lg">향수 추가하기</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-800 text-2xl transition">&times;</button>
                </div>

                <div className="p-6 bg-white">
                    <div className="flex gap-3 relative">
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="향수 이름이나 브랜드를 검색해보세요"
                            className="flex-1 bg-gray-50 text-[#333] px-4 py-4 rounded-xl border-none focus:ring-2 focus:ring-[#C5A55D]/50 focus:bg-white transition text-sm font-medium placeholder-gray-400"
                        />
                        <button
                            onClick={handleSearch}
                            className="px-6 py-3 bg-[#C5A55D] text-white font-bold rounded-xl hover:bg-[#B09045] transition shadow-lg shadow-[#C5A55D]/30"
                        >
                            검색
                        </button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-3 bg-white custom-scrollbar">
                    {results.length === 0 ? (
                        <div className="text-center py-10 text-gray-400">
                            {loading ? "검색 중..." : "검색 결과가 없습니다."}
                        </div>
                    ) : (
                        results.map((perfume) => (
                            <div key={perfume.perfume_id} className="group flex items-center gap-4 p-3 bg-white border border-gray-100 rounded-2xl hover:border-[#C5A55D]/30 hover:shadow-lg transition">
                                <div className="w-14 h-16 bg-[#f9f9f9] rounded-xl flex items-center justify-center overflow-hidden">
                                    {perfume.image_url ? (
                                        <img src={perfume.image_url} alt={perfume.name} className="max-w-full max-h-full object-contain mix-blend-multiply" />
                                    ) : <span className="text-gray-300 text-[10px]">No img</span>}
                                </div>

                                <div className="flex-1 min-w-0">
                                    <p className="text-[#333] font-bold text-sm truncate">{perfume.name}</p>
                                    <p className="text-[#999] text-xs font-medium uppercase tracking-wide truncate">{perfume.brand}</p>
                                </div>

                                {/* 추가 버튼 (Color Updated) */}
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => onAdd(perfume, 'HAVE')}
                                        className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-100 hover:bg-indigo-600 hover:text-white transition text-xs font-bold"
                                    >
                                        보유
                                    </button>
                                    <button
                                        onClick={() => onAdd(perfume, 'WANT')}
                                        className="px-3 py-1.5 rounded-lg bg-rose-50 text-rose-500 border border-rose-100 hover:bg-rose-500 hover:text-white transition text-xs font-bold"
                                    >
                                        위시
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
