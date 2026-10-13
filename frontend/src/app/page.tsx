"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowRight,
  Users,
  QrCode,
  ShieldCheck,
  Receipt,
  Sparkles,
  Zap,
  Clock,
  CheckCircle2,
  ChevronDown,
  Soup,
  Coffee,
  Cookie,
  Flame,
  HelpCircle,
  Copy,
  Check,
} from "lucide-react";

export default function LandingPage() {
  const [copied, setCopied] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const copyDemoLink = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(`${window.location.origin}/group/MUNCH9`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const faqs = [
    {
      q: "Do my hostel friends need to create an account to join?",
      a: "No! MunchMate is friction-free. Friends simply click the shared group link, enter their name, and immediately start adding their favorite snacks. No downloads or mandatory sign-ups.",
    },
    {
      q: "How does MunchMate handle delivery fees and taxes?",
      a: "Our smart bill-splitting engine uses integer paise precision and the Hamilton-Hare allocation method. You can choose equal split (default), proportional split by item cost, or have the host cover shared charges. The sum of all individual shares matches the final bill down to the exact single paise.",
    },
    {
      q: "How do participants pay for their food?",
      a: "Each participant gets a customized checkout screen with an exact-amount UPI QR code (Google Pay, PhonePe, Paytm, CRED) or deep link. They scan and pay their share directly. Once confirmed, a digital receipt is generated.",
    },
    {
      q: "Can the host see who has paid and who is pending?",
      a: "Yes! The host dashboard provides live payment tracking, showing exactly who has paid, who is pending, total collected amount, and a final combined shopping list grouped by product.",
    },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-8 pb-16 md:pt-16 md:pb-24 border-b border-[#EFE8DE]">
        {/* Subtle background glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[350px] bg-gradient-to-tr from-[#FF5C00]/10 via-[#FF8A00]/5 to-transparent rounded-full blur-3xl pointer-events-none -z-10" />

        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            {/* Left Column: Heading and CTAs */}
            <div className="lg:col-span-7 space-y-6 text-center lg:text-left">
              <div className="inline-flex items-center gap-2 bg-[#FFF4ED] border border-[#FFD9C6] text-[#FF5C00] px-3.5 py-1.5 rounded-full text-xs font-bold tracking-wide uppercase shadow-xs">
                <Sparkles className="w-3.5 h-3.5" />
                <span>The Late-Night Group Ordering Manager</span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-[#1A1A1A] tracking-tight leading-[1.08] font-['Outfit',sans-serif]">
                Your group. <br className="hidden sm:block" />
                Your cravings. <br />
                <span className="text-[#FF5C00] relative inline-block">
                  One easy order.
                  <svg
                    className="absolute -bottom-2 left-0 w-full h-3 text-[#FF5C00]/30"
                    viewBox="0 0 200 12"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M2 9C50 3 150 3 198 9"
                      stroke="currentColor"
                      strokeWidth="5"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
              </h1>

              <p className="text-base sm:text-lg text-[#555555] max-w-xl mx-auto lg:mx-0 font-medium leading-relaxed">
                Stop taking chaotic WhatsApp orders and chasing hostel roommates for UPI payments.
                Share one link, order together in real time, split bills down to the exact paise, and pay effortlessly.
              </p>

              {/* CTAs */}
              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3.5 pt-2">
                <Link
                  href="/create"
                  className="w-full sm:w-auto flex items-center justify-center gap-2 bg-[#FF5C00] hover:bg-[#E55200] text-white px-7 py-3.5 rounded-xl font-bold text-sm shadow-lg shadow-[#FF5C00]/30 transition-all hover:shadow-xl hover:shadow-[#FF5C00]/40 active:scale-95"
                >
                  <span>Create a Group Order</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>

                <Link
                  href="/join"
                  className="w-full sm:w-auto flex items-center justify-center gap-2 bg-white hover:bg-[#FAF8F5] text-[#1A1A1A] border border-[#EFE8DE] px-6 py-3.5 rounded-xl font-bold text-sm shadow-xs transition-colors"
                >
                  <Users className="w-4 h-4 text-[#FF5C00]" />
                  <span>Join with Code</span>
                </Link>
              </div>

              {/* Highlights badge bar */}
              <div className="pt-4 flex flex-wrap items-center justify-center lg:justify-start gap-4 sm:gap-6 text-xs text-[#71717A] font-semibold">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
                  <span>No Account Required for Friends</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
                  <span>Exact Paise UPI QR Codes</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
                  <span>Live Collaborative Cart</span>
                </div>
              </div>
            </div>

            {/* Right Column: Hero Visual - Live Group Cart Preview */}
            <div className="lg:col-span-5">
              <div className="bg-white rounded-2xl border border-[#EFE8DE] shadow-xl p-5 relative overflow-hidden">
                {/* Header of Simulated Cart */}
                <div className="flex items-center justify-between border-b border-[#EFE8DE] pb-3 mb-4">
                  <div className="flex items-center gap-2.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] animate-ping" />
                    <div>
                      <h2 className="font-bold text-sm text-[#1A1A1A]">Hostel Block B — Maggi & Drinks</h2>
                      <p className="text-[11px] text-[#71717A]">Code: <span className="font-mono font-bold text-[#FF5C00]">MUNCH9</span> • 4 friends joined</p>
                    </div>
                  </div>
                  <span className="text-[11px] bg-[#FFF4ED] text-[#FF5C00] font-bold px-2 py-0.5 rounded-md border border-[#FFD9C6]">
                    Cart Closes in 18m
                  </span>
                </div>

                {/* Simulated Participant Selections */}
                <div className="space-y-3 mb-4 text-xs">
                  {/* Bhavya (Host) */}
                  <div className="bg-[#FAF8F5] p-2.5 rounded-xl border border-[#EFE8DE]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-[#1A1A1A] flex items-center gap-1.5">
                        <span className="w-5 h-5 rounded-full bg-[#FF5C00] text-white flex items-center justify-center text-[10px] font-bold">B</span>
                        Bhavya <span className="text-[9px] bg-white border border-[#EFE8DE] px-1 rounded text-[#71717A]">Host</span>
                      </span>
                      <span className="font-bold text-[#10B981] bg-[#ECFDF5] px-1.5 py-0.5 rounded text-[10px]">PAID ₹63</span>
                    </div>
                    <p className="text-[#555555] text-[11px]">2× Maggi Masala Noodles (₹28) + Equal Delivery Share (₹35)</p>
                  </div>

                  {/* Sneha */}
                  <div className="bg-[#FAF8F5] p-2.5 rounded-xl border border-[#EFE8DE]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-[#1A1A1A] flex items-center gap-1.5">
                        <span className="w-5 h-5 rounded-full bg-[#6366F1] text-white flex items-center justify-center text-[10px] font-bold">S</span>
                        Sneha
                      </span>
                      <span className="font-bold text-[#10B981] bg-[#ECFDF5] px-1.5 py-0.5 rounded text-[10px]">PAID ₹160</span>
                    </div>
                    <p className="text-[#555555] text-[11px]">1× Red Bull Energy Can (₹125) + Equal Delivery Share (₹35)</p>
                  </div>

                  {/* Rohan */}
                  <div className="bg-[#FAF8F5] p-2.5 rounded-xl border border-[#EFE8DE]">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-[#1A1A1A] flex items-center gap-1.5">
                        <span className="w-5 h-5 rounded-full bg-[#10B981] text-white flex items-center justify-center text-[10px] font-bold">R</span>
                        Rohan
                      </span>
                      <span className="font-bold text-[#FF5C00] bg-[#FFF4ED] px-1.5 py-0.5 rounded text-[10px] animate-pulse">PENDING ₹95</span>
                    </div>
                    <p className="text-[#555555] text-[11px]">3× Kurkure Masala Munch (₹60) + Equal Delivery Share (₹35)</p>
                  </div>
                </div>

                {/* Bill Breakdown Summary */}
                <div className="border-t border-[#EFE8DE] pt-3 space-y-1.5 text-xs text-[#555555]">
                  <div className="flex justify-between">
                    <span>Items Subtotal</span>
                    <span className="font-medium text-[#1A1A1A]">₹213.00</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Shared Delivery & Platform Fee</span>
                    <span className="font-medium text-[#1A1A1A]">₹105.00</span>
                  </div>
                  <div className="flex justify-between font-bold text-sm text-[#1A1A1A] pt-1.5 border-t border-[#EFE8DE]">
                    <span>Total Group Bill</span>
                    <span className="text-[#FF5C00]">₹318.00</span>
                  </div>
                  <div className="flex justify-between text-[11px] text-[#10B981] font-semibold">
                    <span>Collected via UPI (2 of 3 paid)</span>
                    <span>₹223.00 / ₹318.00</span>
                  </div>
                </div>

                {/* Instant share action */}
                <div className="mt-4 pt-3 border-t border-[#EFE8DE] flex items-center justify-between">
                  <span className="text-[11px] text-[#71717A]">Invite Link for Roommates:</span>
                  <button
                    onClick={copyDemoLink}
                    className="flex items-center gap-1 text-xs font-bold text-[#FF5C00] hover:text-[#E55200] bg-[#FFF4ED] px-2.5 py-1 rounded-lg border border-[#FFD9C6] transition-colors"
                  >
                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? "Link Copied!" : "Copy Link"}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem vs Solution Comparison Section */}
      <section className="py-16 md:py-20 bg-white border-b border-[#EFE8DE]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-xs font-bold uppercase tracking-widest text-[#FF5C00] mb-2">Why MunchMate Exists</h2>
            <p className="text-3xl font-extrabold text-[#1A1A1A] font-['Outfit',sans-serif]">
              Hostel group ordering used to be a nightmare.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* The Old Painful Way */}
            <div className="bg-[#FAF8F5] rounded-2xl border border-red-200/70 p-6 relative">
              <div className="inline-block bg-red-100 text-red-700 font-bold text-xs px-2.5 py-1 rounded-md mb-4 uppercase tracking-wide">
                The Old Way (Chaos)
              </div>
              <ul className="space-y-3.5 text-sm text-[#555555]">
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-red-200 text-red-800 flex items-center justify-center text-xs font-bold shrink-0">✕</span>
                  <span>One unlucky person has to manually read 15 messy WhatsApp messages and notes.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-red-200 text-red-800 flex items-center justify-center text-xs font-bold shrink-0">✕</span>
                  <span>Opening the calculator app to divide ₹40 delivery fee by 7 people: 5.714 rupees?!</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-red-200 text-red-800 flex items-center justify-center text-xs font-bold shrink-0">✕</span>
                  <span>Host pays the entire bill out-of-pocket and has to beg friends on GPay for 3 days.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-red-200 text-red-800 flex items-center justify-center text-xs font-bold shrink-0">✕</span>
                  <span>Fake screenshots, forgotten payments, and awkward roommate tension.</span>
                </li>
              </ul>
            </div>

            {/* The MunchMate Way */}
            <div className="bg-[#FFF8F3] rounded-2xl border border-[#FFD9C6] p-6 relative shadow-sm">
              <div className="inline-block bg-[#FF5C00] text-white font-bold text-xs px-2.5 py-1 rounded-md mb-4 uppercase tracking-wide">
                The MunchMate Way (Effortless)
              </div>
              <ul className="space-y-3.5 text-sm text-[#1A1A1A]">
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-5 h-5 text-[#10B981] shrink-0" />
                  <span><strong>One shared link:</strong> Friends add their exact snacks without creating an account.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-5 h-5 text-[#10B981] shrink-0" />
                  <span><strong>Zero math:</strong> Integer paise engine splits delivery and taxes with deterministic rounding.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-5 h-5 text-[#10B981] shrink-0" />
                  <span><strong>Exact-amount UPI QR:</strong> Each roommate scans and pays their own share before order placement.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <CheckCircle2 className="w-5 h-5 text-[#10B981] shrink-0" />
                  <span><strong>Clear dashboard & digital receipts:</strong> The host sees exactly who paid, and gets a combined shopping list!</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* 3-Step Explanation */}
      <section className="py-16 md:py-20 border-b border-[#EFE8DE]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-xl mx-auto mb-14">
            <h2 className="text-xs font-bold uppercase tracking-widest text-[#FF5C00] mb-2">How It Works</h2>
            <p className="text-3xl font-extrabold text-[#1A1A1A] font-['Outfit',sans-serif]">
              Late-night ordering in 3 simple steps
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="bg-white p-6 rounded-2xl border border-[#EFE8DE] shadow-xs relative">
              <div className="w-12 h-12 rounded-xl bg-[#FFF4ED] text-[#FF5C00] font-black text-xl flex items-center justify-center mb-4">
                1
              </div>
              <h3 className="font-extrabold text-lg text-[#1A1A1A] mb-2 font-['Outfit',sans-serif]">
                Host Creates Order
              </h3>
              <p className="text-sm text-[#555555] leading-relaxed">
                Set group name, campus delivery room, and cart closing deadline. An unguessable link and join code is generated immediately.
              </p>
            </div>

            {/* Step 2 */}
            <div className="bg-white p-6 rounded-2xl border border-[#EFE8DE] shadow-xs relative">
              <div className="w-12 h-12 rounded-xl bg-[#FFF4ED] text-[#FF5C00] font-black text-xl flex items-center justify-center mb-4">
                2
              </div>
              <h3 className="font-extrabold text-lg text-[#1A1A1A] mb-2 font-['Outfit',sans-serif]">
                Roommates Pick Items
              </h3>
              <p className="text-sm text-[#555555] leading-relaxed">
                Friends open the link on mobile without downloading any app. Everyone adds noodles, chips, drinks, or coffee into the shared cart in real time.
              </p>
            </div>

            {/* Step 3 */}
            <div className="bg-white p-6 rounded-2xl border border-[#EFE8DE] shadow-xs relative">
              <div className="w-12 h-12 rounded-xl bg-[#FFF4ED] text-[#FF5C00] font-black text-xl flex items-center justify-center mb-4">
                3
              </div>
              <h3 className="font-extrabold text-lg text-[#1A1A1A] mb-2 font-['Outfit',sans-serif]">
                Split & Pay via UPI
              </h3>
              <p className="text-sm text-[#555555] leading-relaxed">
                Each participant scans their personalized UPI QR for their exact share. Verified payments automatically produce digital receipts.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Popular Late-Night Categories */}
      <section className="py-16 md:py-20 bg-white border-b border-[#EFE8DE]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-10 gap-4">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-widest text-[#FF5C00] mb-2">Hostel Favorites</h2>
              <p className="text-3xl font-extrabold text-[#1A1A1A] font-['Outfit',sans-serif]">
                Everything you need for late study sessions
              </p>
            </div>
            <Link
              href="/discover"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-[#FF5C00] hover:text-[#E55200]"
            >
              <span>Explore all snacks</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
            {[
              { name: "Instant Noodles", desc: "Maggi, Wai Wai, Buldak", icon: Soup, bg: "bg-amber-50 text-amber-600" },
              { name: "Chips & Munchies", desc: "Kurkure, Lays, Doritos", icon: Flame, bg: "bg-orange-50 text-[#FF5C00]" },
              { name: "Cold Drinks", desc: "Red Bull, Thums Up, Monster", icon: Zap, bg: "bg-blue-50 text-blue-600" },
              { name: "Sweets & Choco", desc: "Silk Oreo, KitKat, 5 Star", icon: Cookie, bg: "bg-pink-50 text-pink-600" },
              { name: "Cold Coffee & Tea", desc: "Sleepy Owl, Nescafe Can", icon: Coffee, bg: "bg-emerald-50 text-emerald-600" },
              { name: "Hostel Essentials", desc: "Milk, Bread, Tissues", icon: Sparkles, bg: "bg-purple-50 text-purple-600" },
            ].map((cat, i) => {
              const Icon = cat.icon;
              return (
                <Link
                  key={i}
                  href="/discover"
                  className="bg-[#FAF8F5] hover:bg-[#FFF4ED] p-4 rounded-xl border border-[#EFE8DE] hover:border-[#FFD9C6] transition-all group flex flex-col items-center text-center"
                >
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 ${cat.bg} group-hover:scale-110 transition-transform`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <h4 className="font-bold text-xs text-[#1A1A1A] mb-1">{cat.name}</h4>
                  <p className="text-[10px] text-[#71717A]">{cat.desc}</p>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-16 md:py-20 border-b border-[#EFE8DE]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-10">
            <h2 className="text-xs font-bold uppercase tracking-widest text-[#FF5C00] mb-2">Got Questions?</h2>
            <p className="text-3xl font-extrabold text-[#1A1A1A] font-['Outfit',sans-serif]">
              Frequently Asked Questions
            </p>
          </div>

          <div className="space-y-3">
            {faqs.map((faq, idx) => {
              const isOpen = openFaq === idx;
              return (
                <div key={idx} className="bg-white rounded-xl border border-[#EFE8DE] overflow-hidden">
                  <button
                    onClick={() => setOpenFaq(isOpen ? null : idx)}
                    className="w-full text-left p-4.5 flex items-center justify-between font-bold text-sm text-[#1A1A1A] hover:bg-[#FAF8F5] transition-colors"
                  >
                    <span>{faq.q}</span>
                    <ChevronDown className={`w-4 h-4 text-[#71717A] transition-transform ${isOpen ? "rotate-180 text-[#FF5C00]" : ""}`} />
                  </button>
                  {isOpen && (
                    <div className="px-4.5 pb-4 text-xs text-[#555555] leading-relaxed border-t border-[#EFE8DE] pt-3">
                      {faq.a}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Bottom CTA Banner */}
      <section className="py-16 bg-[#1A1A1A] text-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center space-y-5">
          <h2 className="text-3xl sm:text-4xl font-extrabold font-['Outfit',sans-serif]">
            Craving a midnight snack right now?
          </h2>
          <p className="text-zinc-400 text-sm max-w-lg mx-auto">
            Gather your wingmates, create a group order in 10 seconds, and let MunchMate handle the math and payments.
          </p>
          <div className="pt-2">
            <Link
              href="/create"
              className="inline-flex items-center gap-2 bg-[#FF5C00] hover:bg-[#E55200] text-white px-8 py-4 rounded-xl font-bold text-sm shadow-xl shadow-[#FF5C00]/25 transition-all hover:scale-105 active:scale-95"
            >
              <span>Start Group Order</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 bg-white text-[#71717A] text-xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#1A1A1A]">MunchMate</span>
            <span>— Group Ordering Made Effortless</span>
          </div>
          <div className="flex items-center gap-4 text-[11px]">
            <span>Integer Paise Accuracy</span>
            <span>•</span>
            <span>Direct UPI Flow</span>
            <span>•</span>
            <span>College Hostel Ready</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
