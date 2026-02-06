"use client";

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface CardTriggerBannerProps {
  message: string;
  onAccept: () => void;
  onDismiss: () => void;
}

/**
 * 향수 맵 탐색 중 카드 생성을 유도하는 하단 플로팅 배너
 */
const CardTriggerBanner = ({ message, onAccept, onDismiss }: CardTriggerBannerProps) => {
  return (
    <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-[90] w-[calc(100%-32px)] max-w-md">
      <motion.div
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 100, opacity: 0 }}
        className="bg-[#2E2B28] text-white p-5 rounded-[24px] shadow-2xl border border-white/10 backdrop-blur-xl"
      >
        <div className="flex items-start gap-3 sm:gap-4">
          {/* 아이콘 */}
          <div className="w-10 h-10 sm:w-12 sm:h-12 flex-shrink-0 rounded-2xl bg-gradient-to-br from-[#C8A24D] to-[#B69140] flex items-center justify-center text-xl sm:text-2xl shadow-inner">
            🫧
          </div>

          {/* 메시지 및 버튼 */}
          <div className="flex-1 min-w-0 space-y-3 sm:space-y-4">
            <div className="space-y-1">
              <h4 className="text-[13px] sm:text-sm font-bold text-[#C8A24D]">향 MBTI 분석 준비 완료!</h4>
              <p className="text-[11px] sm:text-xs text-white/80 leading-relaxed break-keep">
                {message || "탐색하신 데이터를 바탕으로 당신의 향 MBTI를 확인해보세요."}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-2">
              <button
                onClick={onAccept}
                className="w-full sm:flex-1 py-2 sm:py-2.5 rounded-xl bg-white text-[#2E2B28] text-[11px] sm:text-xs font-bold hover:bg-[#F8F4EC] transition-colors active:scale-95 whitespace-nowrap"
              >
                향 MBTI 확인하기
              </button>
              <button
                onClick={onDismiss}
                className="w-full sm:w-auto px-4 py-2 sm:py-2.5 rounded-xl bg-white/10 text-white/60 text-[11px] sm:text-xs font-bold hover:bg-white/20 transition-colors whitespace-nowrap"
              >
                나중에
              </button>
            </div>
          </div>

          {/* 닫기 버튼 */}
          <button
            onClick={onDismiss}
            className="text-white/40 hover:text-white transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </motion.div>
    </div>
  );
};

export default CardTriggerBanner;
