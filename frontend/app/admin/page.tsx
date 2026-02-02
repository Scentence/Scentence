'use client';

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import Sidebar from "@/components/common/sidebar";
import UserProfileMenu from "@/components/common/UserProfileMenu";
import { Crown } from "lucide-react";

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
          // [이미지 경로 최적화]
          // AWS S3(CloudFront)나 카카오 등 외부 경로는 그대로 쓰고,
          // 로컬 업로드 파일(/uploads/)은 상대 경로를 유지하여 'localhost' 함정을 피합니다.
          // 담당자들이 향후 외부 스토리지를 연동하더라도 코드가 유연하게 대응하도록 설계했습니다.
          const rawUrl = data.profile_image_url;
          const finalUrl = (rawUrl.startsWith("http") || rawUrl.startsWith("/uploads"))
            ? rawUrl
            : `${apiBaseUrl}${rawUrl}`;
          setProfileImageUrl(finalUrl);
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

  // [HYPER-REALISTIC LIQUID GLASS BLOCK] (Sidebar와 동일 스타일)
  const liquidGlassBlock = "bg-gradient-to-br from-white/[0.08] to-transparent backdrop-blur-[16px] border border-white/40 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),inset_0_15px_30px_rgba(255,255,255,0.15),inset_0_-2px_10px_rgba(0,0,0,0.05),0_20px_40px_-10px_rgba(0,0,0,0.2)] overflow-hidden rounded-[32px]";

  return (
    <div className="min-h-screen bg-[#FDFBF8] text-black flex flex-col font-sans selection:bg-black selection:text-white">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        context="home"
      />

      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-transparent z-40"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      <style jsx global>{`
        @keyframes bounce-subtle {
          0%, 100% { transform: translateY(0) rotate(-25deg); }
          50% { transform: translateY(-3px) rotate(-20deg); }
        }
      `}</style>

      {/* [HEADER] Landing Page와 완벽히 동일한 스타일과 간격 적용 */}
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-10 py-5 bg-[#FDFBF8] border-b border-[#F0F0F0]">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-lg font-bold text-black tracking-[0.15em] uppercase hover:opacity-70 transition flex items-center gap-2">
            SCENTENCE
            <span className="text-[10px] bg-black text-white px-2 py-0.5 rounded tracking-widest font-black">ADMIN</span>
          </Link>
        </div>

        <div className="flex items-center gap-4">
          {/* User Profile Button with Admin Crown Easter Egg */}
          <div className="flex items-center gap-3 relative group/profile">
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

              {/* The "Golden Crown" Easter Egg */}
              <div className="absolute -top-3 -left-2 transform -rotate-[25deg] drop-shadow-[0_2px_4px_rgba(0,0,0,0.2)] pointer-events-none group-hover/profile:scale-110 group-hover/profile:rotate-0 transition-all duration-500">
                <Crown
                  size={20}
                  fill="#FFD700"
                  className="text-[#DAA520] animate-bounce-subtle"
                  style={{ animation: 'bounce-subtle 2s infinite ease-in-out' }}
                />
              </div>

              <UserProfileMenu
                isOpen={isProfileMenuOpen}
                onClose={() => setIsProfileMenuOpen(false)}
              />
            </div>
          </div>

          {/* 글로벌 내비게이션 토글 버튼 */}
          <button
            id="global-menu-toggle"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
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

      <main className="flex-1 px-5 py-12 w-full max-w-6xl mx-auto pt-[100px] space-y-10">
        {!isAdmin && (
          <div className={`${liquidGlassBlock} p-12 text-center text-gray-500 shadow-xl`}>
            관리자 권한을 확인하고 있습니다...
          </div>
        )}

        {isAdmin && (
          <section className={`${liquidGlassBlock} p-8 md:p-12 space-y-8 shadow-2xl animate-on-scroll border border-white/60`}>
            <div className="flex items-center justify-between border-b border-black/5 pb-6">
              <div>
                <h3 className="text-2xl font-black tracking-tight">회원 관리 시스템</h3>
                <p className="text-xs text-gray-500 mt-1 uppercase tracking-widest font-bold">Member Management Studio</p>
              </div>
              {isLoading && (
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                  <span className="text-[10px] font-bold text-gray-400 tracking-widest uppercase">Syncing...</span>
                </div>
              )}
            </div>

            {message && (
              <div className="bg-red-50 border border-red-100 text-red-600 px-4 py-3 rounded-xl text-xs font-bold">
                {message}
              </div>
            )}

            <div className="overflow-x-auto no-scrollbar">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-black/5">
                    <th className="pb-4 font-bold text-[10px] tracking-widest uppercase px-2 w-20">ID</th>
                    <th className="pb-4 font-bold text-[10px] tracking-widest uppercase px-2 w-52">Email</th>
                    <th className="pb-4 font-bold text-[10px] tracking-widest uppercase px-2 w-40">Nickname</th>
                    <th className="pb-4 font-bold text-[10px] tracking-widest uppercase px-2 w-28">Date</th>
                    <th className="pb-4 font-bold text-[10px] tracking-widest uppercase px-2 w-28">Status</th>
                    <th className="pb-4 font-bold text-[10px] tracking-widest uppercase px-2 w-24">Channel</th>
                    <th className="pb-4 font-bold text-[10px] tracking-widest uppercase px-2 w-32">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black/5">
                  {members.map((member) => (
                    <tr key={member.member_id} className="group hover:bg-black/[0.02] transition-colors">
                      <td className="py-4 px-2 font-mono text-[11px] text-gray-400">{member.member_id}</td>
                      <td className="py-4 px-2 font-medium truncate">{member.email ?? "-"}</td>
                      <td className="py-4 px-2 font-bold">{member.nickname ?? "-"}</td>
                      <td className="py-4 px-2 text-gray-500">{member.join_dt ? new Date(member.join_dt).toLocaleDateString() : "-"}</td>
                      <td className="py-4 px-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-black tracking-widest ${member.member_status === "NORMAL" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                          }`}>
                          {member.member_status ?? "-"}
                        </span>
                      </td>
                      <td className="py-4 px-2 text-gray-500 uppercase text-[10px] font-bold">{member.join_channel ?? "-"}</td>
                      <td className="py-4 px-2">
                        <select
                          className="w-full bg-white/50 backdrop-blur-sm rounded-lg border border-black/5 px-2 py-1.5 text-xs font-bold outline-none focus:border-black transition-all cursor-pointer shadow-sm hover:shadow-md"
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
