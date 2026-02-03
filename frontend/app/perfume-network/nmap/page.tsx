"use client";

import React, { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import Link from "next/link";
import PageLayout from "@/components/common/PageLayout";
import NMapView from './NMapView';

/**
 * 향수 맵(NMap) 결과 페이지
 * 세션 정보를 관리하고 메인 뷰(NMapView)를 렌더링합니다.
 */
export default function NMapPage() {
  const { data: session } = useSession();
  const [sessionUserId, setSessionUserId] = useState<string | number | undefined>(undefined);
  const [localUser, setLocalUser] = useState<any>(null); // [Fix] Missing state declaration
  const [isMounted, setIsMounted] = useState(false);

  // API 호출 경로 설정
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    // 1. Next-Auth 세션에서 ID 확인
    if (session?.user) {
      const id = (session.user as any).id;
      if (id) {
        setSessionUserId(id);
        return;
      }
    }

    // 2. 로컬 스토리지에서 인증 정보 확인
    const storedAuth = localStorage.getItem('localAuth');
    if (storedAuth) {
      try {
        const parsed = JSON.parse(storedAuth);
        if (parsed.memberId) {
          setSessionUserId(parsed.memberId);
        }
      } catch (e) {
        console.error('Failed to parse localAuth:', e);
      }
    }
  }, [session]);

  // [Profile Logic] 로그인 사용자 정보 및 이미지 연동
  useEffect(() => {
    const authData = localStorage.getItem("localAuth");
    if (authData) {
      try {
        setLocalUser(JSON.parse(authData));
      } catch (e) {
        console.error("Local auth parse error", e);
      }
    }
  }, []); // Added empty dependency array for mount check

  return (
    <PageLayout subTitle="PERFUME MAP">
      <main className="pt-[72px]">
        <NMapView sessionUserId={sessionUserId} />
      </main>
    </PageLayout>
  );
}
