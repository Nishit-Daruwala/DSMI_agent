"use client";

import { useAuth } from "@/lib/auth";
import { BrainCircuit, LayoutDashboard, Cpu, Clock, FileBarChart, LogOut, Loader2 } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-[#00D4FF] animate-spin" />
      </div>
    );
  }

  // Don't show layout on landing or login page
  if (!user || pathname === "/" || pathname === "/login") {
    return <>{children}</>;
  }

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Live Research", href: "/research", icon: Cpu },
    { name: "History", href: "/history", icon: Clock },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top Navbar */}
      <nav className="bg-[#060B14] sticky top-0 z-50 border-b border-[#1e293b] shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-8">
              <Link href="/dashboard" className="flex items-center gap-2">
                <BrainCircuit className="w-6 h-6 text-[#00D4FF]" />
                <span className="font-bold text-lg text-white tracking-tight">DSMI Agent</span>
              </Link>
              
              <div className="hidden md:flex items-center gap-1">
                {navItems.map((item) => {
                  const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                        isActive 
                          ? "bg-[rgba(0,212,255,0.1)] text-[#00D4FF]" 
                          : "text-[#9BA6C3] hover:text-white hover:bg-[rgba(255,255,255,0.05)]"
                      }`}
                    >
                      <item.icon className="w-4 h-4" />
                      {item.name}
                    </Link>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-sm hidden sm:block">
                <span className="text-[#9BA6C3]">Welcome, </span>
                <span className="text-white font-medium">{user.name}</span>
              </div>
              <button 
                onClick={logout}
                className="p-2 text-[#9BA6C3] hover:text-red-400 hover:bg-red-400/10 rounded-md transition-colors"
                title="Logout"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        {children}
      </main>
    </div>
  );
}
