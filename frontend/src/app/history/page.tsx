"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Clock,
  Receipt,
  Users,
  ShoppingBag,
  ArrowRight,
  Sparkles,
  ExternalLink,
  Plus,
  Compass,
} from "lucide-react";
import { getStoredGuestSession, GuestSession, getRecentGroups, RecentGroupItem } from "@/lib/api";

export default function HistoryPage() {
  const [session, setSession] = useState<GuestSession | null>(null);
  const [recentGroups, setRecentGroups] = useState<RecentGroupItem[]>([]);

  useEffect(() => {
    const s = getStoredGuestSession();
    setSession(s);

    const stored = getRecentGroups();
    const defaults: RecentGroupItem[] = [
      {
        code: "MUNCH9",
        title: "Hostel Block B — Maggi & Drinks",
        location: "Room 304",
        status: "OPEN",
        items: 7,
      },
      {
        code: "EXAM26",
        title: "Midnight Study Session Snacks",
        location: "Study Room 2",
        status: "LOCKED",
        items: 9,
      },
    ];

    const codes = new Set(stored.map((g) => g.code.toUpperCase()));
    const merged = [...stored, ...defaults.filter((d) => !codes.has(d.code.toUpperCase()))];
    setRecentGroups(merged);
  }, []);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-6">
      {/* Profile Header */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center text-xl font-black text-white shadow-md shadow-[#FF5C00]/20"
            style={{ backgroundColor: session?.avatar_color || "#FF5C00" }}
          >
            {session?.display_name ? session.display_name.charAt(0).toUpperCase() : "M"}
          </div>
          <div>
            <span className="text-[10px] font-bold text-[#FF5C00] uppercase tracking-wider bg-[#FFF4ED] px-2 py-0.5 rounded border border-[#FFD9C6]">
              Hostel Resident Profile
            </span>
            <h1 className="text-xl sm:text-2xl font-black text-[#1A1A1A] mt-1 font-['Outfit',sans-serif]">
              {session?.display_name || "Guest Roommate"}
            </h1>
            <p className="text-xs text-[#71717A]">
              Friction-free session active • Saved preferences
            </p>
          </div>
        </div>

        <Link
          href="/create"
          className="flex items-center gap-1.5 bg-[#FF5C00] hover:bg-[#E55200] text-white px-4 py-2.5 rounded-xl text-xs font-bold shadow-md shadow-[#FF5C00]/25 transition-transform active:scale-95 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>New Group Order</span>
        </Link>
      </div>

      {/* Quick Access to Recent Demo Groups */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-extrabold text-[#1A1A1A] font-['Outfit',sans-serif]">
            Active & Recent Groups
          </h2>
          <span className="text-xs text-[#71717A]">Quick Access</span>
        </div>

        <div className="space-y-3">
          {recentGroups.map((grp, idx) => (
            <div
              key={idx}
              className="p-4 rounded-2xl bg-[#FAF8F5] border border-[#EFE8DE] hover:border-[#FFD9C6] transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs font-black text-[#FF5C00] bg-[#FFF4ED] px-2 py-0.5 rounded border border-[#FFD9C6]">
                    {grp.code}
                  </span>
                  <span className="text-[10px] font-bold text-[#10B981] bg-emerald-50 px-2 py-0.5 rounded">
                    ● {grp.status}
                  </span>
                </div>
                <h3 className="font-bold text-sm text-[#1A1A1A]">{grp.title}</h3>
                <p className="text-xs text-[#71717A] mt-0.5">
                  Delivering to: <strong className="text-[#555555]">{grp.location}</strong>
                </p>
              </div>

              <div className="flex items-center gap-2 self-end sm:self-center">
                <Link
                  href={`/group/${grp.code}/summary`}
                  className="bg-white hover:bg-zinc-100 text-[#1A1A1A] border border-[#EFE8DE] px-3 py-1.5 rounded-xl text-xs font-bold transition-colors shadow-2xs"
                >
                  View Summary
                </Link>
                <Link
                  href={`/group/${grp.code}`}
                  className="bg-[#FF5C00] hover:bg-[#E55200] text-white px-3.5 py-1.5 rounded-xl text-xs font-bold shadow-xs transition-colors flex items-center gap-1"
                >
                  <span>Open Cart</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Frequently Ordered Hostel Munchies */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-extrabold text-[#1A1A1A] font-['Outfit',sans-serif]">
            Your Frequent Favorites
          </h2>
          <Link href="/discover" className="text-xs font-bold text-[#FF5C00] hover:underline flex items-center gap-1">
            <span>Explore All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            {
              name: "Maggi 2-Minute Masala",
              price: "₹14",
              tag: "Noodles",
              img: "https://images.unsplash.com/photo-1612927601601-6638404737ce?auto=format&fit=crop&w=400&q=80",
            },
            {
              name: "Kurkure Masala Munch",
              price: "₹20",
              tag: "Crunchy",
              img: "https://images.unsplash.com/photo-1566478989037-eec170784d0b?auto=format&fit=crop&w=400&q=80",
            },
            {
              name: "Red Bull Energy Drink",
              price: "₹125",
              tag: "All-Nighter",
              img: "https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=400&q=80",
            },
          ].map((item, i) => (
            <div
              key={i}
              className="bg-[#FAF8F5] p-3 rounded-2xl border border-[#EFE8DE] flex items-center gap-3"
            >
              <img src={item.img} alt={item.name} className="w-12 h-12 rounded-xl object-cover" />
              <div>
                <span className="font-extrabold text-xs text-[#1A1A1A] block line-clamp-1">
                  {item.name}
                </span>
                <span className="text-xs font-black text-[#FF5C00] block">{item.price}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
