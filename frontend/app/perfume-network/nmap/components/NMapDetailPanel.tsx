import React, { useMemo } from "react";
import { NetworkPayload, NetworkNode, LabelsData } from "../types";
import { BRAND_LABELS, ACCORD_LABELS, getAccordColor, ACCORD_DESCRIPTIONS, hexToRgba } from "../../config";

interface Props {
  selectedPerfumeId: string | null;
  selectedAccordName: string | null;
  onClose: () => void;
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
  selectedAccordName,
  onClose,
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

    const accordEntries = Array.from(weights.entries()).sort((a, b) => b[1] - a[1]);
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

  const selectedAccordInfo = useMemo(() => {
    if (!fullPayload || !selectedAccordName) return null;
    const description = ACCORD_DESCRIPTIONS[selectedAccordName] || "";

    // 이 노트를 포함하는 향수들 찾기
    const accordNodeId = `accord_${selectedAccordName}`;
    const includingPerfumes = fullPayload.edges
      .filter(e => e.type === "HAS_ACCORD" && e.to === accordNodeId)
      .map(e => {
        const p = fullPayload.nodes.find(n => n.id === e.from) as NetworkNode | undefined;
        return p ? { perfume: p, weight: e.weight } : null;
      })
      .filter((x): x is NonNullable<typeof x> => x !== null)
      .sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0))
      .slice(0, 6);

    return { name: selectedAccordName, description, perfumes: includingPerfumes };
  }, [fullPayload, selectedAccordName]);

  const renderContent = () => {
    if (selectedPerfumeInfo) {
      const { perfume, accordList, similar } = selectedPerfumeInfo;
      const accordText = accordList.map((acc, idx) => idx === 0 ? `${fmtAccord(acc)}(대표)` : fmtAccord(acc)).join(", ");
      const statusBadge = getStatusBadge(perfume.register_status);
      const matchedAccords = selectedAccords.filter(acc => accordList.map(a => a.toLowerCase()).includes(acc.toLowerCase()));
      const unmatchedAccords = accordList.filter(acc => !matchedAccords.some(m => m.toLowerCase() === acc.toLowerCase()));

      return (
        <div className="space-y-4 sm:space-y-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3 w-full pr-8">
              <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl overflow-hidden border border-[#E6DDCF] bg-white flex-shrink-0">
                <img src={perfume.image} alt={perfume.label} className="w-full h-full object-cover" />
              </div>
              <div className="min-w-0 flex-1 space-y-0.5 sm:space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-lg sm:text-xl font-bold text-[#2E2B28] break-words leading-tight">{perfume.label}</h3>
                  {statusBadge && <span className={`text-[9px] sm:text-[10px] px-1.5 sm:px-2 py-0.5 rounded-full font-semibold ${statusBadge.className}`}>{statusBadge.label}</span>}
                </div>
                <p className="text-xs sm:text-sm text-[#7A6B57] truncate">{fmtBrand(perfume.brand || "")}</p>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-[#FDFBF8] border border-[#E6DDCF] text-sm leading-relaxed text-[#5C5448]">
            {matchedAccords.length > 0 ? (
              <p>
                이 향수는 선택하신 <span className="font-bold text-[#C8A24D]">{matchedAccords.map(fmtAccord).join(", ")}</span> 분위기가 잘 느껴지며,
                {unmatchedAccords.length > 0 && <> <span className="font-semibold">{unmatchedAccords.slice(0, 3).map(fmtAccord).join(", ")}</span> 향도 함께 조화를 이루고 있어요.</>}
              </p>
            ) : (
              <p>이 향수는 주로 <span className="font-semibold">{accordText}</span> 분위기를 자아내며 풍부한 향의 매력을 가지고 있어요.</p>
            )}
          </div>

          <div className="space-y-3 sm:space-y-4">
            <p className="text-xs sm:text-sm font-bold text-[#2E2B28]">유사한 분위기의 향수 추천</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3">
              {similar.slice(0, 4).map(({ perfume, score }) => (
                <div key={perfume.id} className="p-2 sm:p-3 rounded-xl border border-[#E6DDCF] bg-white hover:border-[#C8A24D] transition-all group flex items-center gap-2 sm:gap-3">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg overflow-hidden border border-[#F8F4EC] flex-shrink-0">
                    <img src={perfume.image} alt={perfume.label} className="w-full h-full object-cover" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-[11px] sm:text-xs font-bold text-[#2E2B28] block truncate group-hover:text-[#C8A24D]">{perfume.label}</span>
                    <span className="text-[9px] sm:text-[10px] text-[#C8A24D] font-bold">{Math.round(score * 100)}% 일치</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }

    if (selectedAccordInfo) {
      const { name, description, perfumes } = selectedAccordInfo;
      return (
        <div className="space-y-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full flex items-center justify-center text-3xl shadow-sm border border-[#E6DDCF]" style={{ backgroundColor: hexToRgba(getAccordColor(name), 0.1) }}>
              ✨
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#2E2B28]">{fmtAccord(name)}</h3>
              <p className="text-xs text-[#C8A24D] font-semibold">{name} Accord</p>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-[#FDFBF8] border border-[#E6DDCF]">
            <p className="text-sm text-[#5C5448] leading-relaxed whitespace-pre-wrap">{description || "이 분위기에 대한 설명이 준비 중이에요."}</p>
          </div>

          <div className="space-y-4">
            <p className="text-sm font-bold text-[#2E2B28]">{fmtAccord(name)} 분위기를 느낄 수 있는 대표 향수</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {perfumes.map(({ perfume }) => (
                <div key={perfume.id} className="p-2 rounded-xl border border-[#E6DDCF] bg-white hover:border-[#C8A24D] transition-all text-center space-y-2">
                  <div className="w-full aspect-square rounded-lg overflow-hidden border border-[#F8F4EC] bg-[#FDFBF8]">
                    <img src={perfume.image} alt={perfume.label} className="w-full h-full object-cover p-1" />
                  </div>
                  <span className="text-[10px] font-bold text-[#2E2B28] block truncate px-1">{perfume.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <>
      {/* 모바일 배경 (lg 미만일 때만) */}
      <div
        className="fixed inset-0 z-[90] bg-black/40 backdrop-blur-sm lg:hidden animate-fade-in"
        onClick={onClose}
      />

      {/* 우측 고정 사이드 패널 (데스크탑) / 하단 시트 (모바일) */}
      <div
        className="fixed inset-x-4 bottom-4 top-20 z-[100] lg:inset-y-0 lg:right-0 lg:left-auto lg:w-[340px] lg:m-0 bg-white shadow-2xl overflow-hidden border-l border-[#E6DDCF] flex flex-col animate-slide-in-right rounded-3xl lg:rounded-none"
        onClick={e => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-5 right-5 w-10 h-10 rounded-full hover:bg-black/5 flex items-center justify-center transition-colors z-20 bg-white/80 backdrop-blur-md border border-[#E6DDCF]"
        >
          <span className="text-2xl text-[#7A6B57]">×</span>
        </button>

        <div className="flex-1 p-6 sm:p-8 overflow-y-auto custom-scrollbar pt-16">
          {renderContent()}
        </div>

        {/* 모바일 전용 확인 버튼 */}
        <div className="p-6 pt-2 flex justify-center border-t border-[#F8F4EC]/50 lg:hidden">
          <button
            onClick={onClose}
            className="px-12 py-3.5 rounded-full bg-[#2E2B28] text-white text-sm font-bold hover:bg-[#4D463A] transition-all shadow-lg active:scale-95 w-full"
          >
            확인
          </button>
        </div>
      </div>
    </>
  );
}
