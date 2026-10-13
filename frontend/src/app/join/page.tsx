"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Users,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  Lock,
  Compass,
  Check,
} from "lucide-react";
import { api, saveStoredGuestSession, getStoredGuestSession } from "@/lib/api";

const AVATAR_COLORS = [
  "#FF5C00", // Tangerine
  "#10B981", // Emerald
  "#6366F1", // Indigo
  "#EC4899", // Pink
  "#8B5CF6", // Purple
  "#06B6D4", // Cyan
  "#F59E0B", // Amber
  "#3B82F6", // Blue
];

function JoinGroupContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [code, setCode] = useState(searchParams?.get("code") || "");
  const [displayName, setDisplayName] = useState("");
  const [selectedColor, setSelectedColor] = useState(AVATAR_COLORS[0]);
  const [passcode, setPasscode] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const existing = getStoredGuestSession();
    if (existing?.display_name && !displayName) {
      setDisplayName(existing.display_name);
      if (existing.avatar_color) setSelectedColor(existing.avatar_color);
    }
  }, []);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim() || !displayName.trim()) {
      setErrorMsg("Please enter both the 6-character group code and your name.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg(null);

      const participant = await api.joinGroup(code.trim().toUpperCase(), {
        display_name: displayName.trim(),
        avatar_color: selectedColor,
        passcode: passcode.trim() || undefined,
      });

      // Save session in local storage
      saveStoredGuestSession({
        id: participant.id,
        session_token: "guest_token_" + participant.id,
        display_name: participant.display_name,
        avatar_color: participant.avatar_color,
      });

      // Redirect to the group cart
      router.push(`/group/${code.trim().toUpperCase()}`);
    } catch (err: any) {
      console.error("Join failed:", err);
      setErrorMsg(err.message || "Failed to join group. Verify the invite code.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 sm:px-6 py-10 sm:py-16">
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 sm:p-8 shadow-sm">
        <div className="text-center mb-6">
          <div className="w-14 h-14 rounded-2xl bg-[#FFF4ED] text-[#FF5C00] flex items-center justify-center mx-auto mb-3 shadow-md shadow-[#FF5C00]/20">
            <Users className="w-7 h-7" />
          </div>
          <h1 className="text-2xl font-black text-[#1A1A1A] font-['Outfit',sans-serif]">
            Join Group Order
          </h1>
          <p className="text-xs text-[#71717A] mt-1">
            Enter the 6-character code shared by your friend to start ordering together.
          </p>
        </div>

        {errorMsg && (
          <div className="mb-5 p-3.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleJoin} className="space-y-4">
          {/* Invite Code Input */}
          <div>
            <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5">
              6-Character Join Code
            </label>
            <input
              type="text"
              required
              maxLength={8}
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="e.g. MUNCH9"
              className="w-full text-center text-2xl font-black font-mono tracking-widest uppercase py-3 rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 focus:border-[#FF5C00] text-[#FF5C00]"
            />
          </div>

          {/* Display Name */}
          <div>
            <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5">
              Your Name (Visible to Roommates)
            </label>
            <input
              type="text"
              required
              maxLength={50}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Rohan (Room 304)"
              className="w-full px-4 py-2.5 text-sm rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 focus:border-[#FF5C00] font-medium"
            />
          </div>

          {/* Avatar Color Picker */}
          <div>
            <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-2">
              Choose Avatar Color
            </label>
            <div className="flex items-center justify-between gap-1.5 bg-[#FAF8F5] p-2.5 rounded-xl border border-[#EFE8DE]">
              {AVATAR_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setSelectedColor(c)}
                  className={`w-7 h-7 rounded-full transition-transform flex items-center justify-center text-white ${
                    selectedColor === c ? "scale-110 ring-2 ring-offset-2 ring-[#1A1A1A]" : "hover:scale-105"
                  }`}
                  style={{ backgroundColor: c }}
                >
                  {selectedColor === c && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                </button>
              ))}
            </div>
          </div>

          {/* Optional Passcode */}
          <div>
            <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1">
              <Lock className="w-3.5 h-3.5 text-[#71717A]" />
              <span>Group Passcode (if host set one)</span>
            </label>
            <input
              type="password"
              value={passcode}
              onChange={(e) => setPasscode(e.target.value)}
              placeholder="Optional"
              className="w-full px-4 py-2.5 text-sm rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 font-medium"
            />
          </div>

          {/* Join CTA */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 bg-[#FF5C00] hover:bg-[#E55200] disabled:bg-zinc-300 text-white py-3.5 rounded-xl font-bold text-sm shadow-lg shadow-[#FF5C00]/25 transition-all active:scale-95 cursor-pointer"
            >
              {isSubmitting ? (
                <span>Joining Group...</span>
              ) : (
                <>
                  <span>Join & View Group Cart</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>

        <div className="mt-6 pt-5 border-t border-[#EFE8DE] text-center">
          <Link
            href="/create"
            className="text-xs font-bold text-[#FF5C00] hover:text-[#E55200]"
          >
            Don&apos;t have a code? Create a new group order →
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function JoinGroupPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-md mx-auto px-4 py-16 text-center space-y-4">
          <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
          <p className="text-xs text-[#71717A]">Loading Join Page...</p>
        </div>
      }
    >
      <JoinGroupContent />
    </Suspense>
  );
}
