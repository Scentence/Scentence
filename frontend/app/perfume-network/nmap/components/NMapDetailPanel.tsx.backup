import React, { useMemo } from "react";
import { NetworkPayload, NetworkNode, LabelsData } from "../types";
import { BRAND_LABELS, ACCORD_LABELS, getAccordColor } from "../../config";

interface Props {
  selectedPerfumeId: string | null;
  fullPayload: NetworkPayload | null;
  labelsData: LabelsData | null;
  selectedAccords: string[];
  logActivity: (data: {
    accord_selected?: string;
    perfume_id?: number;
    filter_changed?: string;
    selected_accords_override?: string[];
  }) => void;
}

export default function NMapDetailPanel({
  selectedPerfumeId,
  fullPayload,
  labelsData,
  selectedAccords,
  logActivity,
}: Props) {
  const fmtAccord = (v: string) => {
    const trimmed = v.trim();
    if (trimmed === "Fougère" || trimmed === "Foug\\u00e8re" || trimmed.includes("Foug")) return "푸제르";
    return labelsData?.accords[trimmed] || ACCORD_LABELS[trimmed] || v;
  };
  const fmtBrand = (v: string) => labelsData?.brands[v.trim()] || BRAND_LABELS[v.trim()] || v;
  
  const getStatusBadge = (status?: string | null) => {
    if (!status) return null;
    const normalized = status.trim().toUpperCase();
    const map: Record<string, { label: string; className: string }> = {
      HAVE: { label: "보유", className: "bg-[#E8F0FF] text-[#3B5CC9]" },
      WANT: { label: "위시", className: "bg-[#FFE8EE] text-[#C24B6B]" },
      HAD: { label: "과거", className: "bg-[#F2F2F2] text-[#7A6B57]" },
      RECOMMENDED: { label: "추천", className: "bg-[#E8F6EC] text-[#2F7D4C]" },
    };
    const matched = map[normalized];
    return matched || { label: normalized, className: "bg-[#F8F4EC] text-[#8A7C68]" };
  };

  const selectedPerfumeInfo = useMemo(() => {
    if (!fullPayload || !selectedPerfumeId) return null;
    const p = fullPayload.nodes.find(n => n.id === selectedPerfumeId) as NetworkNode | undefined;
    if (!p) return null;

    const weights = new Map<string, number>();
    fullPayload.edges.forEach(e => {
      if (e.type === "HAS_ACCORD" && e.from === selectedPerfumeId) {
        weights.set(e.to.replace("accord_", ""), e.weight ?? 0);
      }
    });

    const accordEntries = Array.from(weights.entries()).sort((a,b) => b[1]-a[1]);
    const accordList = accordEntries.slice(0, 5).map(([acc]) => acc);
    
    const scoreMap = new Map<string, number>();
    fullPayload.edges.forEach(e => {
      if (e.type === "SIMILAR_TO") {
        if (e.from === selectedPerfumeId) scoreMap.set(e.to, e.weight ?? 0);
        else if (e.to === selectedPerfumeId) scoreMap.set(e.from, e.weight ?? 0);
      }
    });

    const similar = Array.from(scoreMap.entries())
      .map(([id, score]) => {
        const simP = fullPayload.nodes.find(n => n.id === id) as NetworkNode | undefined;
        if (!simP) return null;
        const common = (p.accords || []).filter(a => (simP.accords || []).includes(a));
        const added = (simP.accords || []).filter(a => !(p.accords || []).includes(a));
        return { perfume: simP, score, commonAccords: common, newAccords: added };
      })
      .filter((x): x is NonNullable<typeof x> => x !== null)
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);

    return { perfume: p, accordList, similar };
  }, [fullPayload, selectedPerfumeId]);

  if (!selectedPerfumeInfo) {
    return (
      <div className="rounded-3xl bg-white/80 border border-[#E2D7C5] p-6 min-h-[400px] flex flex-col items-center justify-center text-center py-12 space-y-4">
        <div className="w-16 h-16 rounded-full bg-[#F8F4EC] flex items-center justify-center text-3xl">✨</div>
        <h3 className="text-lg font-semibold mb-1 text-[#C8A24D]">궁금한 향수를 클릭해보세요</h3>
      </div>
    );
  }

  const { perfume, accordList, similar } = selectedPerfumeInfo;
  const accordText = accordList.map((acc, idx) => idx === 0 ? `${fmtAccord(acc)}(대표)` : fmtAccord(acc)).join(", ");
  const statusBadge = getStatusBadge(perfume.register_status);
  const matchedAccords = selectedAccords.filter(acc => accordList.map(a => a.toLowerCase()).includes(acc.toLowerCase()));
  const unmatchedAccords = accordList.filter(acc => !matchedAccords.some(m => m.toLowerCase() === acc.toLowerCase()));

  return (
    <div className="rounded-3xl bg-white/80 border border-[#E2D7C5] p-6 min-h-[400px] space-y-5 flex flex-col">
      <div className="flex-1 space-y-5">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <p className="text-sm text-[#7A6B57]">
              <span className="font-bold text-[#C8A24D] text-lg">{perfume.label}</span> 향수를 선택하셨어요.
            </p>
            {statusBadge && <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${statusBadge.className}`}>{statusBadge.label}</span>}
          </div>
          <div className="space-y-2 text-sm leading-relaxed text-[#2E2B28]">
            {matchedAccords.length > 0 ? (
              <p>
                이 향수는 선택하신 <span className="font-bold text-[#C8A24D]">{matchedAccords.map(fmtAccord).join(", ")}</span>가 포함되어 있고
                {unmatchedAccords.length > 0 && <> <span className="font-semibold text-[#5C5448]">{unmatchedAccords.slice(0, 3).map(fmtAccord).join(", ")}</span>도 포함되어 있어요.</>}
              </p>
            ) : (
              <p>이 향수는 <span className="font-semibold text-[#5C5448]">{accordText}</span> 로 구성되어 있어요.</p>
            )}
          </div>
        </div>

        <div className="border-t border-[#E6DDCF] pt-6 space-y-4">
          <p className="text-sm font-semibold text-[#4D463A]">유사한 향수 Top3</p>
          {similar.length > 0 ? (
            <div className="space-y-3">
              {similar.slice(0, 3).map(({ perfume, score, newAccords }) => (
                <div key={perfume.id} className="p-4 rounded-2xl border border-[#E6DDCF] bg-white hover:border-[#C8A24D] transition-all cursor-pointer group hover:shadow-md">
                  <div className="flex justify-between items-start mb-3">
                    <div className="space-y-1">
                      <span className="text-sm font-bold group-hover:text-[#C8A24D] transition-colors block">{perfume.label}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-[#7A6B57]">{fmtBrand(perfume.brand || "")}</span>
                        {getStatusBadge(perfume.register_status) && <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${getStatusBadge(perfume.register_status)!.className}`}>{getStatusBadge(perfume.register_status)!.label}</span>}
                      </div>
                    </div>
                    <span className="text-[10px] font-bold text-[#C8A24D] bg-[#C8A24D]/10 px-2 py-1 rounded-md whitespace-nowrap ml-2">유사도 {Math.round(score * 100)}%</span>
                  </div>
                  <p className="text-xs text-[#2E2B28] leading-relaxed">
                    <span className="font-bold text-[#C8A24D]">{perfume.label}</span>은(는) {(perfume.accords || []).slice(0, 4).map(fmtAccord).join(", ")} 로 구성되어있지만 
                    {newAccords.length > 0 ? <> <span className="font-semibold text-[#C8A24D]">{newAccords.slice(0, 2).map(fmtAccord).join(", ")}</span> 새로운 분위기도 느낄 수 있는 향수에요.</> : <>어 비슷한 분위기를 즐길 수 있는 향수에요.</>}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center bg-[#F8F4EC]/50 rounded-2xl border border-dashed border-[#E6DDCF]">
              <p className="text-xs text-[#7A6B57]">비슷한 향수를 찾을 수 없어요.<br/>닮은 정도를 조금 낮춰보세요.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
