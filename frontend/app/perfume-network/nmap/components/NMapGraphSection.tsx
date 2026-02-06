import React, { useEffect, useRef, useMemo, useState } from "react";
import Script from "next/script";
import { NetworkPayload, NetworkNode, NetworkEdge, LabelsData } from "../types";
import { ACCORD_DESCRIPTIONS, ACCORD_LABELS, BRAND_LABELS, getAccordColor, hexToRgba } from "../../config";

interface Props {
  fullPayload: NetworkPayload | null;
  labelsData: LabelsData | null;
  selectedPerfumeId: string | null;
  setSelectedPerfumeId: (id: string | null) => void;
  displayLimit: number;
  setDisplayLimit: (limit: number) => void;
  minSimilarity: number;
  setMinSimilarity: (val: number) => void;
  topAccords: number;
  selectedAccords: string[];
  selectedBrands: string[];
  selectedSeasons: string[];
  selectedOccasions: string[];
  selectedGenders: string[];
  showMyPerfumesOnly: boolean;
  myPerfumeIds: Set<string>;
  logActivity: (data: { perfume_id?: number; accord_selected?: string; filter_changed?: string; selected_accords_override?: string[] }) => void;
  memberId: string | null;
  setShowLoginPrompt: (show: boolean) => void;
  setShowMyPerfumesOnly: (show: boolean | ((prev: boolean) => boolean)) => void;
}

export default function NMapGraphSection({
  fullPayload,
  labelsData,
  selectedPerfumeId,
  setSelectedPerfumeId,
  displayLimit,
  setDisplayLimit,
  minSimilarity,
  setMinSimilarity,
  topAccords,
  selectedAccords,
  selectedBrands,
  selectedSeasons,
  selectedOccasions,
  selectedGenders,
  showMyPerfumesOnly,
  myPerfumeIds,
  logActivity,
  memberId,
  setShowLoginPrompt,
  setShowMyPerfumesOnly,
}: Props) {
  const [scriptReady, setScriptReady] = useState(false);
  const [freezeMotion, setFreezeMotion] = useState(false);
  const [hoveredSimilarPerfumeId, setHoveredSimilarPerfumeId] = useState<string | null>(null);

  // [Network Graph Refs]
  // 그래프가 그려질 DOM 컨테이너와 Vis.js 네트워크 인스턴스, 데이터셋을 참조합니다.
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<any>(null);
  const nodesDataRef = useRef<any>(null);
  const edgesDataRef = useRef<any>(null);

  // [Fix] Vis.js 로드 상태 확인 (Client-Side Navigation 대응)
  // 페이지를 새로고침하면 <Script> 태그의 onLoad가 발생하지만,
  // 다른 페이지에서 링크를 타고 들어오면(SPA 네비게이션) 이미 스크립트가 로드되어 있어서 onLoad가 발생하지 않습니다.
  // 따라서 window 객체에 vis가 이미 있는지 확인하여 scriptReady 상태를 강제로 true로 만들어줍니다.
  useEffect(() => {
    if ((window as any).vis || (window as any).visNetwork) {
      setScriptReady(true);
    }
  }, []);

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

  const filteredPayload = useMemo(() => {
    if (!fullPayload) return null;
    const perfumeNodes = fullPayload.nodes.filter((n): n is NetworkNode => n.type === "perfume" && (!showMyPerfumesOnly || myPerfumeIds.has(n.id)));
    const visiblePerfumeNodes = perfumeNodes.filter(node => {
      if (selectedAccords.length > 0 && (!node.primary_accord || !selectedAccords.includes(node.primary_accord))) return false;
      if (selectedBrands.length > 0 && (!node.brand || !selectedBrands.includes(node.brand))) return false;
      if (selectedSeasons.length > 0 && !selectedSeasons.some(s => node.seasons?.includes(s))) return false;
      if (selectedOccasions.length > 0 && !selectedOccasions.some(o => node.occasions?.includes(o))) return false;
      if (selectedGenders.length > 0 && !selectedGenders.some(g => node.genders?.includes(g))) return false;
      return true;
    });

    const visibleIds = new Set(visiblePerfumeNodes.map(n => n.id));
    const filteredEdges: NetworkEdge[] = [];
    const accordMap = new Map<string, Array<{ to: string, weight: number }>>();

    fullPayload.edges.forEach(edge => {
      if (edge.type === "SIMILAR_TO") {
        if (visibleIds.has(edge.from) && visibleIds.has(edge.to) && (edge.weight ?? 0) >= minSimilarity) filteredEdges.push(edge);
      } else if (edge.type === "HAS_ACCORD" && visibleIds.has(edge.from)) {
        if (!accordMap.has(edge.from)) accordMap.set(edge.from, []);
        accordMap.get(edge.from)!.push({ to: edge.to, weight: edge.weight ?? 0 });
      }
    });

    const selectedAccordIds = new Set(selectedAccords.map(acc => `accord_${acc}`));
    accordMap.forEach((accords, perfumeId) => {
      accords.sort((a, b) => b.weight - a.weight).slice(0, topAccords)
        .filter(acc => selectedAccordIds.has(acc.to))
        .forEach(acc => filteredEdges.push({ from: perfumeId, to: acc.to, type: "HAS_ACCORD", weight: acc.weight }));
    });

    const activeAccordIds = new Set(filteredEdges.filter(e => e.type === "HAS_ACCORD").map(e => e.to));
    const finalNodes = fullPayload.nodes.filter(n => (n.type === "perfume" && visibleIds.has(n.id)) || (n.type === "accord" && activeAccordIds.has(n.id)));
    return { nodes: finalNodes, edges: filteredEdges, meta: fullPayload.meta };
  }, [fullPayload, minSimilarity, topAccords, selectedAccords, selectedBrands, selectedSeasons, selectedOccasions, selectedGenders, showMyPerfumesOnly, myPerfumeIds]);

  const similarPerfumes = useMemo(() => {
    if (!filteredPayload || !selectedPerfumeId) return [];
    const scoreMap = new Map<string, number>();
    filteredPayload.edges.forEach(e => {
      if (e.type === "SIMILAR_TO") {
        if (e.from === selectedPerfumeId) scoreMap.set(e.to, e.weight ?? 0);
        else if (e.to === selectedPerfumeId) scoreMap.set(e.from, e.weight ?? 0);
      }
    });
    const perfumeMap = new Map(filteredPayload.nodes.filter(n => n.type === "perfume").map(n => [n.id, n as NetworkNode]));
    return Array.from(scoreMap.entries()).map(([id, score]) => {
      const p = perfumeMap.get(id);
      return p ? { perfume: p, score } : null;
    }).filter((x): x is NonNullable<typeof x> => x !== null).sort((a, b) => b.score - a.score).slice(0, 5);
  }, [filteredPayload, selectedPerfumeId]);

  const top5SimilarIds = useMemo(() => new Set(similarPerfumes.map(s => s.perfume.id)), [similarPerfumes]);

  const displayPayload = useMemo(() => {
    if (!filteredPayload) return null;
    const allPerfumes = filteredPayload.nodes.filter(n => n.type === "perfume");
    const mustIncludeIds = new Set<string>();
    if (selectedPerfumeId) { mustIncludeIds.add(selectedPerfumeId); top5SimilarIds.forEach(id => mustIncludeIds.add(id)); }
    const mustIncludePerfumes = allPerfumes.filter(p => mustIncludeIds.has(p.id));
    const otherPerfumes = allPerfumes.filter(p => !mustIncludeIds.has(p.id));
    let perfumes = mustIncludePerfumes.length >= displayLimit ? mustIncludePerfumes.slice(0, displayLimit) : [...mustIncludePerfumes, ...otherPerfumes.slice(0, displayLimit - mustIncludePerfumes.length)];
    const perfumeIds = new Set(perfumes.map(p => p.id));
    const edges = filteredPayload.edges.filter(e => e.type === "SIMILAR_TO" ? (perfumeIds.has(e.from) && perfumeIds.has(e.to)) : (e.type === "HAS_ACCORD" && perfumeIds.has(e.from)));
    const accordIds = new Set(edges.filter(e => e.type === "HAS_ACCORD").map(e => e.to));
    const accords = filteredPayload.nodes.filter(n => n.type === "accord" && accordIds.has(n.id));
    return { nodes: [...accords, ...perfumes], edges };
  }, [filteredPayload, displayLimit, selectedPerfumeId, top5SimilarIds]);

  useEffect(() => {
    if (!scriptReady || !displayPayload || !containerRef.current) return;
    const vis = (window as any).vis ?? (window as any).visNetwork;
    if (!vis) return;

    const nodes = displayPayload.nodes.map(n => {
      if (n.type === "perfume") {
        const isSel = n.id === selectedPerfumeId;
        const isSim = top5SimilarIds.has(n.id);
        const isHov = n.id === hoveredSimilarPerfumeId;
        const isBlur = !!selectedPerfumeId && !isSel && !isSim && !isHov;
        const border = getAccordColor(n.primary_accord);
        const statusBadge = getStatusBadge(n.register_status);
        return {
          id: n.id, label: isHov || isSel ? n.label : "", title: `${n.label}\n${fmtBrand(n.brand || "")}${statusBadge ? `\n내 향수 상태: ${statusBadge.label}` : ""}`,
          shape: "circularImage", image: n.image, size: isSel ? 40 : (isSim || isHov ? 32 : (isBlur ? 20 : 26)),
          borderWidth: isSel ? 8 : (isHov ? 7 : (isBlur ? 1 : 4)),
          color: { border: isHov ? "#FFD700" : (isSel ? border : hexToRgba(border, isBlur ? 0.08 : 1)), background: isBlur ? "rgba(255, 251, 243, 0.15)" : "#FFFBF3" },
          opacity: isBlur ? 0.08 : 1, font: { size: isSel ? 14 : 12, bold: true, background: "white", color: isSel ? "#C8A24D" : "#2E2B28" },
          fixed: isSel ? { x: true, y: true } : false, x: isSel ? 0 : undefined, y: isSel ? 0 : undefined,
        };
      }
      const isHigh = !selectedPerfumeId || displayPayload.edges.some(e => e.type === "HAS_ACCORD" && e.to === n.id && (e.from === selectedPerfumeId || top5SimilarIds.has(e.from)));
      const isBlurAccord = selectedPerfumeId && !isHigh;
      return {
        id: n.id, label: isBlurAccord ? "" : fmtAccord(n.label), title: `${fmtAccord(n.label)}\n${ACCORD_DESCRIPTIONS[n.label] || ""}`,
        shape: "dot", size: isHigh ? 24 : (isBlurAccord ? 12 : 18),
        color: { background: hexToRgba(getAccordColor(n.label), isHigh ? 0.7 : (isBlurAccord ? 0.03 : 0.1)) },
        font: { size: isHigh ? 12 : 10, bold: isHigh }, opacity: isBlurAccord ? 0.15 : 1, mass: 5
      };
    });

    const edges = displayPayload.edges.map(e => {
      if (e.type === "SIMILAR_TO") return { from: e.from, to: e.to, hidden: true };
      const isFromSelected = selectedPerfumeId && (e.from === selectedPerfumeId || top5SimilarIds.has(e.from));
      return {
        from: e.from, to: e.to, value: e.weight, hidden: selectedPerfumeId && !isFromSelected,
        color: { color: "#9C8D7A", opacity: isFromSelected ? 0.3 : 0.08 }, width: isFromSelected ? 1.2 : 0.4, dashes: true, smooth: { type: "continuous" }
      };
    });

    if (!networkRef.current) {
      nodesDataRef.current = new vis.DataSet(nodes);
      edgesDataRef.current = new vis.DataSet(edges);
      networkRef.current = new vis.Network(containerRef.current, { nodes: nodesDataRef.current, edges: edgesDataRef.current }, {
        interaction: { hover: true, navigationButtons: true, tooltipDelay: 200 },
        physics: { enabled: !freezeMotion, solver: "forceAtlas2Based", forceAtlas2Based: { gravitationalConstant: -140, centralGravity: 0.01, springLength: 240, springConstant: 0.04, damping: 0.9, avoidOverlap: 2.5 }, stabilization: { enabled: true, iterations: 200 } }
      });
      networkRef.current.on("click", (p: any) => {
        const nodeId = p.nodes[0];
        if (nodeId && !nodeId.startsWith("accord_")) {
          setSelectedPerfumeId(nodeId);
          // 향수 노드 클릭 시 활동 카운트 증가
          const perfumeIdNum = nodeId.match(/\d+/)?.[0];
          if (perfumeIdNum) logActivity({ perfume_id: Number(perfumeIdNum) });
        } else if (nodeId && nodeId.startsWith("accord_")) {
          // 어코드 노드 클릭 시
          const accordName = nodeId.replace("accord_", "");
          logActivity({ accord_selected: accordName });
        } else setSelectedPerfumeId(null);
      });
    } else {
      nodesDataRef.current.update(nodes);
      const toRemove = (nodesDataRef.current.getIds() as string[]).filter(id => !nodes.some(n => n.id === id));
      if (toRemove.length > 0) nodesDataRef.current.remove(toRemove);
      edgesDataRef.current.clear(); edgesDataRef.current.add(edges);
      if (selectedPerfumeId) try { networkRef.current.moveNode(selectedPerfumeId, 0, 0); } catch (e) { }
      networkRef.current.setOptions({ physics: { enabled: !freezeMotion } });
    }
  }, [scriptReady, displayPayload, selectedPerfumeId, freezeMotion, hoveredSimilarPerfumeId]);

  return (
    <div className="space-y-3">
      <Script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js" strategy="afterInteractive" onLoad={() => setScriptReady(true)} />
      <div className="rounded-2xl border border-[#E6DDCF] bg-white/80 p-5 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-2">
            <div className="flex justify-between items-center"><label className="text-[13px] font-bold">1. 표시할 향수 개수</label><span className="text-sm font-bold text-[#C8A24D]">{displayLimit}개</span></div>
            <input type="range" min="1" max="100" value={displayLimit} onChange={e => setDisplayLimit(Number(e.target.value))} className="w-full h-1.5 accent-[#C8A24D]" />
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center"><label className="text-[13px] font-bold">2. 분위기 닮은 정도</label><span className="text-sm font-bold text-[#C8A24D]">{minSimilarity.toFixed(2)}</span></div>
            <input type="range" min="0" max="1" step="0.05" value={minSimilarity} onChange={e => setMinSimilarity(Number(e.target.value))} className="w-full h-1.5 accent-[#C8A24D]" />
          </div>
        </div>
        <div className="flex justify-between items-center pt-4 border-t border-[#E6DDCF]">
          <span className="text-xs text-[#7A6B57]">{filteredPayload?.nodes.filter(n => n.type === "perfume").length || 0}개 향수 발견 • {displayLimit}개 표시 중</span>
          <div className="flex gap-2">
            <button onClick={() => networkRef.current?.fit()} className="h-9 px-4 rounded-full border border-[#E2D7C5] bg-white text-xs font-semibold">화면 맞춤</button>
            <button onClick={() => setFreezeMotion(!freezeMotion)} className="h-9 px-4 rounded-full border border-[#E2D7C5] bg-white text-xs font-semibold">{freezeMotion ? "움직임 재개" : "움직임 멈춤"}</button>
            <button onClick={() => { if (!memberId) setShowLoginPrompt(true); else setShowMyPerfumesOnly(!showMyPerfumesOnly); }} className={`h-9 px-4 rounded-full text-xs font-semibold border transition ${showMyPerfumesOnly ? "bg-[#C8A24D] text-white border-[#C8A24D]" : "bg-white text-[#7A6B57] border-[#E2D7C5] hover:bg-[#F8F4EC]"}`}>{showMyPerfumesOnly ? "전체 향수 보기" : "내 향수 보기"}</button>
          </div>
        </div>
      </div>
      <div className="h-[70vh] rounded-3xl border border-[#E2D7C5] bg-white/90 p-4 relative overflow-hidden">
        <div ref={containerRef} className="h-full w-full" />
      </div>
    </div>
  );
}
