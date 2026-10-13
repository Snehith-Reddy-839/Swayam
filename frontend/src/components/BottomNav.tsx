"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Compass, Users, Clock, PlusCircle } from "lucide-react";

export function BottomNav() {
  const pathname = usePathname();

  // Hide bottom nav on specific fullscreen pages if desired
  const isReceipt = pathname.startsWith("/receipt");
  if (isReceipt) return null;

  const navItems = [
    { href: "/", label: "Home", icon: Home },
    { href: "/discover", label: "Menu", icon: Compass },
    { href: "/create", label: "Create", icon: PlusCircle, highlight: true },
    { href: "/join", label: "Join", icon: Users },
    { href: "/history", label: "Orders", icon: Clock },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-[#EFE8DE] px-3 py-2 flex items-center justify-around shadow-lg">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));

        if (item.highlight) {
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex flex-col items-center -mt-5"
            >
              <div className="w-12 h-12 rounded-full bg-[#FF5C00] text-white flex items-center justify-center shadow-lg shadow-[#FF5C00]/30 hover:scale-105 active:scale-95 transition-transform">
                <Icon className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-bold text-[#FF5C00] mt-1">{item.label}</span>
            </Link>
          );
        }

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex flex-col items-center gap-1 py-1 px-2.5 rounded-lg transition-colors ${
              isActive ? "text-[#FF5C00]" : "text-[#71717A] hover:text-[#1A1A1A]"
            }`}
          >
            <Icon className="w-5 h-5" />
            <span className={`text-[10px] ${isActive ? "font-bold text-[#FF5C00]" : "font-medium"}`}>
              {item.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
