"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Sparkles,
  Users,
  MapPin,
  Clock,
  ShieldCheck,
  Check,
  Copy,
  Share2,
  ArrowRight,
  Split,
  Lock,
  UtensilsCrossed,
  Info,
} from "lucide-react";
import { api, GroupDetail, saveStoredGuestSession, saveRecentGroup } from "@/lib/api";

export default function CreateGroupPage() {
  const router = useRouter();

  // Form State
  const [title, setTitle] = useState("Late Night Hostel Maggi & Drinks");
  const [hostName, setHostName] = useState("");
  const [storeMode, setStoreMode] = useState("late_night_snacks");
  const [deliveryLocation, setDeliveryLocation] = useState("Hostel Block B, Room 304");
  const [cartClosingMinutes, setCartClosingMinutes] = useState(30);
  const [participantLimit, setParticipantLimit] = useState(15);
  const [feePolicy, setFeePolicy] = useState("EQUAL_SPLIT");
  const [passcode, setPasscode] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Success State
  const [createdGroup, setCreatedGroup] = useState<GroupDetail | null>(null);
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !deliveryLocation.trim()) {
      setErrorMsg("Please provide a group title and delivery location.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMsg(null);

      const group = await api.createGroup({
        title: title.trim(),
        host_name: hostName.trim() || "Host",
        store_mode: storeMode,
        delivery_location: deliveryLocation.trim(),
        cart_closing_minutes: Number(cartClosingMinutes),
        participant_limit: Number(participantLimit),
        fee_policy: feePolicy,
        passcode: passcode.trim() || undefined,
      });

      // Save guest session for host
      saveStoredGuestSession({
        id: group.host_participant_id || group.id,
        session_token: "host_token",
        display_name: hostName.trim() || "Host",
        avatar_color: "#FF5C00",
      });

      // Save to recent groups
      saveRecentGroup({
        code: group.invite_code,
        title: group.title,
        location: group.delivery_location,
        status: group.cart_status,
        items: 0,
      });

      setCreatedGroup(group);
    } catch (err: any) {
      console.error("Create group failed:", err);
      setErrorMsg(err.message || "Failed to create group order. Please check inputs.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopy = () => {
    if (!createdGroup) return;
    const url = `${window.location.origin}/group/${createdGroup.invite_code}`;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleNativeShare = () => {
    if (!createdGroup || typeof navigator === "undefined" || !navigator.share) return;
    const url = `${window.location.origin}/group/${createdGroup.invite_code}`;
    navigator.share({
      title: createdGroup.title,
      text: `Join our late-night MunchMate group order! Delivery to: ${createdGroup.delivery_location}`,
      url,
    }).catch(() => {});
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
      {createdGroup ? (
        /* Success Screen */
        <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 sm:p-8 shadow-xl text-center space-y-6 animate-in zoom-in-95 duration-200">
          <div className="w-16 h-16 rounded-full bg-[#ECFDF5] text-[#10B981] flex items-center justify-center mx-auto shadow-md shadow-[#10B981]/20">
            <Check className="w-8 h-8 stroke-[3]" />
          </div>

          <div>
            <span className="text-xs font-bold text-[#10B981] uppercase tracking-wider bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
              Group Order Created Successfully!
            </span>
            <h1 className="text-2xl sm:text-3xl font-black text-[#1A1A1A] mt-3 font-['Outfit',sans-serif]">
              {createdGroup.title}
            </h1>
            <p className="text-xs sm:text-sm text-[#71717A] mt-1">
              Delivering to: <strong className="text-[#1A1A1A]">{createdGroup.delivery_location}</strong>
            </p>
          </div>

          {/* Share Box */}
          <div className="bg-[#FAF8F5] p-5 rounded-2xl border border-[#EFE8DE] space-y-3">
            <span className="text-xs font-bold text-[#71717A] uppercase tracking-wider block">
              Share this Join Code with Roommates
            </span>
            <div className="text-4xl font-black font-mono tracking-widest text-[#FF5C00] select-all">
              {createdGroup.invite_code}
            </div>

            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 bg-white hover:bg-[#FFF4ED] text-[#FF5C00] border border-[#FFD9C6] px-4 py-2 rounded-xl text-xs font-bold transition-colors shadow-xs"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                <span>{copied ? "Link Copied!" : "Copy Share Link"}</span>
              </button>

              {typeof navigator !== "undefined" && "share" in navigator && (
                <button
                  onClick={handleNativeShare}
                  className="flex items-center gap-1.5 bg-white hover:bg-[#FAF8F5] text-[#1A1A1A] border border-[#EFE8DE] px-4 py-2 rounded-xl text-xs font-bold transition-colors shadow-xs"
                >
                  <Share2 className="w-4 h-4" />
                  <span>Share</span>
                </button>
              )}
            </div>
          </div>

          {/* Action button */}
          <div className="pt-2">
            <Link
              href={`/group/${createdGroup.invite_code}`}
              className="w-full flex items-center justify-center gap-2 bg-[#FF5C00] hover:bg-[#E55200] text-white py-3.5 rounded-xl font-bold text-sm shadow-lg shadow-[#FF5C00]/25 transition-all active:scale-95"
            >
              <span>Go to Collaborative Group Cart</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      ) : (
        /* Create Order Form */
        <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 sm:p-8 shadow-sm">
          <div className="mb-6">
            <div className="inline-flex items-center gap-1.5 bg-[#FFF4ED] text-[#FF5C00] text-[11px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider mb-2 border border-[#FFD9C6]">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Step 1: Group Setup</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-[#1A1A1A] font-['Outfit',sans-serif]">
              Create a Group Order
            </h1>
            <p className="text-xs sm:text-sm text-[#71717A] mt-1">
              Configure your order pool. Your roommates will join via link without needing to register.
            </p>
          </div>

          {errorMsg && (
            <div className="mb-6 p-3.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center gap-2">
              <span className="font-bold">Error:</span> {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Group Title */}
            <div>
              <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5">
                Group Order Name
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Late Night Hostel Maggi & Drinks"
                className="w-full px-4 py-2.5 text-sm rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 focus:border-[#FF5C00] font-medium"
              />
            </div>

            {/* Host Name & Store Mode */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5">
                  Your Display Name (Host)
                </label>
                <input
                  type="text"
                  required
                  value={hostName}
                  onChange={(e) => setHostName(e.target.value)}
                  placeholder="e.g. Bhavya"
                  className="w-full px-4 py-2.5 text-sm rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 focus:border-[#FF5C00] font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5">
                  Ordering Mode
                </label>
                <select
                  value={storeMode}
                  onChange={(e) => setStoreMode(e.target.value)}
                  className="w-full px-4 py-2.5 text-sm rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 focus:border-[#FF5C00] font-medium"
                >
                  <option value="late_night_snacks">Late Night Snacks & Munchies</option>
                  <option value="grocery">Hostel Pantry Essentials</option>
                  <option value="canteen">Campus Night Canteen</option>
                </select>
              </div>
            </div>

            {/* Delivery Location */}
            <div>
              <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-[#FF5C00]" />
                <span>Delivery Location / Campus Room</span>
              </label>
              <input
                type="text"
                required
                value={deliveryLocation}
                onChange={(e) => setDeliveryLocation(e.target.value)}
                placeholder="e.g. Hostel Block B, Room 304, North Campus"
                className="w-full px-4 py-2.5 text-sm rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 focus:border-[#FF5C00] font-medium"
              />
            </div>

            {/* Cart Closing Deadline & Participant Limit */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-[#FF5C00]" />
                  <span>Cart Closing Time</span>
                </label>
                <select
                  value={cartClosingMinutes}
                  onChange={(e) => setCartClosingMinutes(Number(e.target.value))}
                  className="w-full px-4 py-2.5 text-sm rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 font-medium"
                >
                  <option value={15}>15 Minutes (Quick Order)</option>
                  <option value={30}>30 Minutes (Recommended)</option>
                  <option value={45}>45 Minutes</option>
                  <option value={60}>1 Hour</option>
                  <option value={120}>2 Hours</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-[#FF5C00]" />
                  <span>Max Participants</span>
                </label>
                <select
                  value={participantLimit}
                  onChange={(e) => setParticipantLimit(Number(e.target.value))}
                  className="w-full px-4 py-2.5 text-sm rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 font-medium"
                >
                  <option value={5}>Up to 5 friends</option>
                  <option value={10}>Up to 10 friends</option>
                  <option value={15}>Up to 15 friends</option>
                  <option value={25}>Up to 25 friends (Wing Order)</option>
                </select>
              </div>
            </div>

            {/* Fee Allocation Policy */}
            <div className="pt-2">
              <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Split className="w-3.5 h-3.5 text-[#FF5C00]" />
                <span>Delivery & Platform Fee Split Rule</span>
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                {[
                  {
                    id: "EQUAL_SPLIT",
                    title: "Equal Split",
                    desc: "Everyone pays their items + equal share of delivery fee (Default)",
                  },
                  {
                    id: "PROPORTIONAL",
                    title: "Proportional",
                    desc: "Delivery fee split proportionally to item spend",
                  },
                  {
                    id: "HOST_COVERS",
                    title: "Host Covers",
                    desc: "Host pays delivery; friends only pay their own items",
                  },
                ].map((pol) => (
                  <button
                    key={pol.id}
                    type="button"
                    onClick={() => setFeePolicy(pol.id)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      feePolicy === pol.id
                        ? "bg-[#FFF4ED] border-[#FF5C00] text-[#1A1A1A] shadow-xs"
                        : "bg-[#FAF8F5] border-[#EFE8DE] text-[#555555] hover:bg-white"
                    }`}
                  >
                    <span className="block font-bold text-xs text-[#1A1A1A] mb-0.5">
                      {pol.title}
                    </span>
                    <span className="block text-[10px] text-[#71717A] leading-tight">
                      {pol.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Optional Passcode */}
            <div>
              <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-[#71717A]" />
                <span>Optional Passcode (Leave blank for open link)</span>
              </label>
              <input
                type="password"
                value={passcode}
                onChange={(e) => setPasscode(e.target.value)}
                placeholder="Optional 4-digit code"
                className="w-full px-4 py-2.5 text-sm rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 font-medium"
              />
            </div>

            {/* Submit CTA */}
            <div className="pt-4">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-2 bg-[#FF5C00] hover:bg-[#E55200] disabled:bg-zinc-300 text-white py-3.5 rounded-xl font-bold text-sm shadow-lg shadow-[#FF5C00]/25 transition-all active:scale-95 cursor-pointer"
              >
                {isSubmitting ? (
                  <span>Generating Group Link...</span>
                ) : (
                  <>
                    <span>Generate Shareable Group Link</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
