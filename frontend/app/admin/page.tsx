'use client';

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import PageLayout from "@/components/common/PageLayout";
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
  const router = useRouter(); // Add useRouter
  const [memberId, setMemberId] = useState<string | null>(null);
  const [verifiedRoleType, setVerifiedRoleType] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(true);
  const [members, setMembers] = useState<MemberRow[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const apiBaseUrl = "/api";

  // localAuth 제거: 세션 id만 사용
  useEffect(() => {
    if (session?.user?.id) {
      setMemberId(String(session.user.id));
      return;
    }
    if (session === null) {
      setIsVerifying(false);
    }
  }, [session]);

  const isAdmin = (verifiedRoleType || "").toUpperCase() === "ADMIN";

  // Redirect if not admin after verification
  useEffect(() => {
    // Wait until verification is complete
    if (isVerifying) return;

    // If verification finished and NOT admin
    if (!isAdmin) {
      const timer = setTimeout(() => {
        router.push("/");
      }, 2000); // Redirect after 2s
      return () => clearTimeout(timer);
    }
  }, [isVerifying, isAdmin, router]);

  // Step 2: Verify Role from Server
  useEffect(() => {
    if (!memberId) return;
    const controller = new AbortController();

    const verifyRole = async () => {
      setIsVerifying(true);
      try {
        const response = await fetch(`${apiBaseUrl}/users/profile/${memberId}`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          setVerifiedRoleType(null);
          return;
        }
        const data = await response.json().catch(() => null);
        // Only trust the role returned from the fresh server call
        setVerifiedRoleType(data?.role_type || "USER");
      } catch (error) {
        if ((error as Error).name !== 'AbortError') {
          setVerifiedRoleType(null);
        }
      } finally {
        setIsVerifying(false);
      }
    };

    verifyRole();

    return () => controller.abort();
  }, [apiBaseUrl, memberId]);

  useEffect(() => {
    if (!memberId || !isAdmin) return;
    const controller = new AbortController();

    const loadMembers = async () => {
      setIsLoading(true);
      setMessage(null);
      try {
        const response = await fetch(
          `${apiBaseUrl}/users/admin/members`,
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
        `${apiBaseUrl}/users/admin/members/${targetId}/status?status=${status}`,
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
    <>
      <style jsx global>{`
        @keyframes bounce-subtle {
          0%, 100% { transform: translateY(0) rotate(-25deg); }
          50% { transform: translateY(-3px) rotate(-20deg); }
        }
      `}</style>

      <PageLayout subTitle="ADMIN" className="min-h-screen bg-[#FDFBF8] text-black flex flex-col font-sans selection:bg-black selection:text-white">

        <main className="flex-1 px-5 py-12 w-full max-w-6xl mx-auto pt-[100px] space-y-10">
          {!isAdmin && !isVerifying && (
            <div className={`${liquidGlassBlock} p-12 text-center text-gray-500 shadow-xl`}>
              접근 권한이 없습니다. 메인으로 이동합니다...
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
      </PageLayout>
    </>
  );
}
