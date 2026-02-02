'use client';

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import Sidebar from "@/components/common/sidebar";
import UserProfileMenu from "@/components/common/UserProfileMenu";

interface MemberRow {
  member_id: string;
  email: string | null;
  nickname: string | null;
  join_channel: string | null;
  join_dt: string | null;
  member_status: string | null;
}

const statusOptions = ["NORMAL", "LOCK", "DORMANT", "WITHDRAW_REQ", "WITHDRAW"] as const;

export default function AdminPage() {
  const { data: session } = useSession();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [profileImageUrl, setProfileImageUrl] = useState<string | null>(null);
  const [memberId, setMemberId] = useState<string | null>(null);
  const [roleType, setRoleType] = useState<string | null>(null);
  const [members, setMembers] = useState<MemberRow[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const apiBaseUrl = "/api";
  useEffect(() => {
    if (session?.user?.id) {
      setMemberId(String(session.user.id));
      return;
    }
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem("localAuth");
    if (!stored) return;
    try {
      const parsed = JSON.parse(stored);
      if (parsed?.memberId) {
        setMemberId(String(parsed.memberId));
      }
      if (parsed?.roleType) {
        setRoleType(parsed.roleType);
      } else if (parsed?.isAdmin) {
        setRoleType("ADMIN");
      }
    } catch (error) {
      return;
    }
  }, [session]);

  const isAdmin = (roleType || "").toUpperCase() === "ADMIN";

  useEffect(() => {
    if (!memberId || roleType) return;
    const controller = new AbortController();

    const loadRole = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/users/profile/${memberId}`, {
          signal: controller.signal,
        });
        if (!response.ok) return;
        const data = await response.json().catch(() => null);
        if (data?.role_type) {
          setRoleType(data.role_type);
        }
        if (data?.profile_image_url) {
          // URL 처리 로직 (Sidebar와 동일)
          const url = data.profile_image_url.startsWith("http")
            ? data.profile_image_url
            : `${apiBaseUrl}${data.profile_image_url}`;
          setProfileImageUrl(url);
        }
      } catch (error) {
        return;
      }
    };

    loadRole();

    return () => controller.abort();
  }, [apiBaseUrl, memberId, roleType]);

  useEffect(() => {
    if (!memberId || !isAdmin) return;
    const controller = new AbortController();

    const loadMembers = async () => {
      setIsLoading(true);
      setMessage(null);
      try {
        const response = await fetch(
          `${apiBaseUrl}/users/admin/members?admin_member_id=${memberId}`,
          { signal: controller.signal }
        );
        if (!response.ok) {
          const data = await response.json().catch(() => null);
          setMessage(data?.detail || "관리자 목록 조회에 실패했습니다.");
          return;
        }
        const data = await response.json();
        setMembers(data.members ?? []);
      } catch (error) {
        setMessage("관리자 목록 조회에 실패했습니다.");
      } finally {
        setIsLoading(false);
      }
    };

    loadMembers();

    return () => controller.abort();
  }, [apiBaseUrl, isAdmin, memberId]);

  const updateStatus = async (targetId: string, status: string) => {
    if (!memberId) return;
    try {
      const response = await fetch(
        `${apiBaseUrl}/users/admin/members/${targetId}/status?admin_member_id=${memberId}&status=${status}`,
        { method: "PATCH" }
      );
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setMessage(data?.detail || "상태 변경에 실패했습니다.");
        return;
      }
      setMembers((prev) =>
        prev.map((item) =>
          item.member_id === targetId ? { ...item, member_status: status } : item
        )
      );
    } catch (error) {
      setMessage("상태 변경에 실패했습니다.");
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFBF8] text-black flex flex-col font-sans">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        context="home"
      />

      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-transparent z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* [STANDARD HEADER] Simplified for Admin */}
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-5 py-4 bg-[#FDFBF8] border-b border-[#F0F0F0]">
        <Link href="/" className="text-xl font-bold tracking-tight text-black">
          Scentence 관리자 페이지
        </Link>

        <div className="flex items-center gap-6">
          {/* User Profile Button */}
          <div className="relative">
            <button
              id="profile-menu-toggle"
              onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
              className="block w-9 h-9 rounded-full overflow-hidden border border-gray-100 shadow-sm hover:opacity-80 transition-opacity"
            >
              <img
                src={profileImageUrl || "/default_profile.png"}
                alt="Profile"
                className="w-full h-full object-cover"
                onError={(e) => { e.currentTarget.src = "/default_profile.png"; }}
              />
            </button>
            <UserProfileMenu
              isOpen={isProfileMenuOpen}
              onClose={() => setIsProfileMenuOpen(false)}
            />
          </div>

          {/* 글로벌 내비게이션 토글 버튼 */}
          <button
            id="global-menu-toggle"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-1 rounded-md hover:bg-gray-100 transition-colors"
          >
            {isSidebarOpen ? (
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-[#555]">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9h16.5m-16.5 6.75h16.5" />
              </svg>
            )}
          </button>
        </div>
      </header>

      <main className="flex-1 px-5 py-8 w-full max-w-[95%] mx-auto pt-[80px] space-y-6">
        <div>
        </div>

        {!isAdmin && (
          <div className="rounded-2xl border border-[#EEE] p-6 text-sm text-[#666]">
            관리자 권한이 없습니다.
          </div>
        )}

        {isAdmin && (
          <section className="rounded-2xl border border-[#EEE] p-6 space-y-4 animate-on-scroll">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">회원 목록</h3>
              {isLoading && <span className="text-xs text-[#999]">불러오는 중...</span>}
            </div>

            {message && <p className="text-xs text-red-600">{message}</p>}

            <div className="overflow-x-auto">
              <table className="w-full text-sm table-fixed">
                <thead className="text-left text-[#666]">
                  <tr>
                    <th className="py-2 w-20">MEMBER_ID</th>
                    <th className="py-2 w-52">이메일</th>
                    <th className="py-2 w-40">닉네임</th>
                    <th className="py-2 w-28">가입일</th>
                    <th className="py-2 w-28">상태</th>
                    <th className="py-2 w-24">가입 방식</th>
                    <th className="py-2 w-32">관리</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.member_id} className="border-t">
                      <td className="py-2 truncate">{member.member_id}</td>
                      <td className="py-2 truncate">{member.email ?? "-"}</td>
                      <td className="py-2 truncate">{member.nickname ?? "-"}</td>
                      <td className="py-2">{member.join_dt ? new Date(member.join_dt).toLocaleDateString() : "-"}</td>
                      <td className="py-2">{member.member_status ?? "-"}</td>
                      <td className="py-2">{member.join_channel ?? "-"}</td>
                      <td className="py-2">
                        <select
                          className="rounded border border-[#DDD] px-2 py-1 text-sm outline-none focus:border-black transition-colors"
                          value={member.member_status ?? "NORMAL"}
                          onChange={(event) => updateStatus(member.member_id, event.target.value)}
                        >
                          {statusOptions.map((status) => (
                            <option key={status} value={status}>
                              {status}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
