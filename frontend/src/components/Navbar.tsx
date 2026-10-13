"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UtensilsCrossed, Users, Plus, Compass, Clock, Sparkles } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-[#EFE8DE] shadow-xs">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-10 h-10 rounded-xl bg-[#FF5C00] flex items-center justify-center text-white shadow-md shadow-[#FF5C00]/25 group-hover:scale-105 transition-transform">
            <UtensilsCrossed className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-xl tracking-tight text-[#1A1A1A]">MunchMate</span>
              <span className="bg-[#FFF4ED] text-[#FF5C00] border border-[#FFD9C6] text-[10px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider">
                Hostel
              </span>
            </div>
            <p className="text-[11px] text-[#71717A] hidden sm:block -mt-0.5 font-medium">
              Group Ordering Made Effortless
            </p>
          </div>
        </Link>

        {/* Center Nav Links */}
        <nav className="hidden md:flex items-center gap-1 bg-[#FAF8F5] p-1 rounded-xl border border-[#EFE8DE]">
          <Link
            href="/discover"
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
              pathname === "/discover"
                ? "bg-white text-[#FF5C00] shadow-xs"
                : "text-[#555555] hover:text-[#1A1A1A]"
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            Discover Menu
          </Link>
          <Link
            href="/join"
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
              pathname.startsWith("/join")
                ? "bg-white text-[#FF5C00] shadow-xs"
                : "text-[#555555] hover:text-[#1A1A1A]"
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            Join with Code
          </Link>
          <Link
            href="/history"
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 ${
              pathname === "/history"
                ? "bg-white text-[#FF5C00] shadow-xs"
                : "text-[#555555] hover:text-[#1A1A1A]"
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            My Orders
          </Link>
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-2.5">
          <Link
            href="/join"
            className="hidden sm:flex text-xs font-semibold text-[#555555] hover:text-[#1A1A1A] px-3 py-2 rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] hover:bg-[#F4EFEB] transition-colors"
          >
            Enter Code
          </Link>
          <Link
            href="/create"
            className="flex items-center gap-1.5 bg-[#FF5C00] hover:bg-[#E55200] text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-md shadow-[#FF5C00]/25 transition-all hover:shadow-lg hover:shadow-[#FF5C00]/35 active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>Create Group</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
