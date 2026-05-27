"use client";

import { usePathname, useRouter } from "next/navigation";
import { isAuthenticated, logout } from "@/lib/auth";
import { useEffect } from "react";

const TABS = [
  { label: "面试中心", path: "/dashboard" },
  { label: "简历管理", path: "/dashboard/resumes" },
  { label: "岗位管理", path: "/dashboard/jds" },
  { label: "题库管理", path: "/dashboard/question-banks" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold">模拟面试 Agent</h1>
          <button
            onClick={logout}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            退出登录
          </button>
        </div>
        <nav className="max-w-6xl mx-auto px-4 flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.path}
              onClick={() => router.push(tab.path)}
              className={`px-4 py-2 text-sm font-medium rounded-t transition-colors ${
                pathname === tab.path
                  ? "bg-gray-50 text-blue-600 border-t border-l border-r border-gray-200"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
