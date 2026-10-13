"use client";

import { useState, useEffect, Suspense } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle2,
  Printer,
  Share2,
  Receipt as ReceiptIcon,
  ShoppingBag,
  Clock,
  MapPin,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Truck,
  Check,
  Copy,
  Users,
  MessageCircle,
} from "lucide-react";
import { api, Receipt, FinalCombinedOrderSummary } from "@/lib/api";

function ReceiptContent() {
  const params = useParams();
  const token = params?.token as string;

  const [activeTab, setActiveTab] = useState<"INDIVIDUAL" | "CONSOLIDATED">("INDIVIDUAL");
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [groupSummary, setGroupSummary] = useState<FinalCombinedOrderSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!token) return;

    async function fetchReceipt() {
      try {
        setLoading(true);
        const data = await api.getReceipt(token);
        setReceipt(data);

        // Fetch group summary if available
        if (data?.group_order_id) {
          try {
            const sumData = await api.getGroupSummary(data.group_order_id);
            setGroupSummary(sumData);
          } catch (e) {
            console.warn("Could not load group summary:", e);
          }
        }
      } catch (err: any) {
        console.warn("Could not load receipt for token:", token, err?.message);
      } finally {
        setLoading(false);
      }
    }

    fetchReceipt();
  }, [token]);

  const handlePrint = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleWhatsAppShare = () => {
    if (typeof window === "undefined" || !receipt) return;
    const text = activeTab === "INDIVIDUAL"
      ? `🍜 *MunchMate Receipt Confirmed!*\nGroup: *${receipt.group_title}*\nParticipant: *${receipt.participant_name}*\nAmount Paid: *₹${receipt.total_paid_inr.toFixed(2)}*\nUTR: ${receipt.transaction_ref}\nView Receipt: ${window.location.href}`
      : `🍜 *MunchMate Consolidated Group Bill*\nGroup: *${receipt.group_title}*\nTotal Items: ${groupSummary?.total_items_count || 0}\nGrand Total: *₹${(groupSummary?.grand_total_inr || receipt.total_paid_inr).toFixed(2)}*\nPaid Roommates: ${groupSummary?.paid_participants_count || 1}/${groupSummary?.total_participants || 1}\nReceipt: ${window.location.href}`;
    window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`, "_blank");
  };

  if (loading) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
        <h2 className="font-bold text-lg text-[#1A1A1A]">Generating Digital Receipt...</h2>
        <p className="text-xs text-[#71717A]">Verifying transaction record</p>
      </div>
    );
  }

  if (!receipt) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center space-y-4">
        <ReceiptIcon className="w-12 h-12 text-[#FF5C00] mx-auto" />
        <h2 className="font-bold text-xl text-[#1A1A1A]">Receipt Not Found</h2>
        <p className="text-xs text-[#71717A]">
          Could not find an authenticated receipt for this token.
        </p>
        <Link
          href="/"
          className="inline-block bg-[#FF5C00] text-white px-5 py-2.5 rounded-xl font-bold text-xs"
        >
          Return Home
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
      {/* View Switcher: Individual vs Consolidated Receipt */}
      <div className="flex items-center gap-2 mb-4 bg-[#FAF8F5] p-1.5 rounded-2xl border border-[#EFE8DE] print:hidden">
        <button
          onClick={() => setActiveTab("INDIVIDUAL")}
          className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 ${
            activeTab === "INDIVIDUAL"
              ? "bg-white text-[#FF5C00] shadow-xs"
              : "text-[#71717A] hover:text-[#1A1A1A]"
          }`}
        >
          <ReceiptIcon className="w-3.5 h-3.5" />
          <span>My Individual Receipt</span>
        </button>

        <button
          onClick={() => setActiveTab("CONSOLIDATED")}
          className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 ${
            activeTab === "CONSOLIDATED"
              ? "bg-white text-[#FF5C00] shadow-xs"
              : "text-[#71717A] hover:text-[#1A1A1A]"
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Consolidated Group Receipt</span>
        </button>
      </div>

      {/* Main Printable Card */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] shadow-xl p-6 sm:p-8 space-y-6 relative overflow-hidden print:shadow-none print:border-none">
        {/* Header / Verified Badge */}
        <div className="text-center space-y-3">
          <div className="w-16 h-16 rounded-full bg-[#ECFDF5] text-[#10B981] flex items-center justify-center mx-auto shadow-md shadow-[#10B981]/25">
            <CheckCircle2 className="w-9 h-9 stroke-[2.5]" />
          </div>

          <div>
            <span className="text-[10px] font-bold text-[#10B981] uppercase tracking-wider bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
              {activeTab === "INDIVIDUAL" ? "Payment Verified & Recorded" : "Group Combined Order"}
            </span>
            <h1 className="text-2xl sm:text-3xl font-black text-[#1A1A1A] mt-2 font-['Outfit',sans-serif]">
              {activeTab === "INDIVIDUAL" ? "Digital Payment Receipt" : "Consolidated Group Receipt"}
            </h1>
            <p className="text-xs text-[#71717A] font-mono mt-0.5">
              Receipt No: <strong className="text-[#1A1A1A]">{receipt.receipt_number}</strong>
            </p>
          </div>
        </div>

        {/* Live Order Status Indicator */}
        <div className="bg-[#FAF8F5] p-3.5 rounded-2xl border border-[#EFE8DE] flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Truck className="w-4 h-4 text-[#FF5C00]" />
            <div>
              <span className="text-[10px] text-[#71717A] block">Merchant Order Status</span>
              <strong className="text-[#1A1A1A] font-bold">
                {receipt.merchant_order_status === "NOT_PLACED"
                  ? "Pooling with group (Awaiting host placement)"
                  : receipt.merchant_order_status}
              </strong>
            </div>
          </div>
          <span className="text-[10px] bg-[#FFF4ED] text-[#FF5C00] font-bold px-2 py-0.5 rounded-md border border-[#FFD9C6]">
            {receipt.merchant_order_status}
          </span>
        </div>

        {/* VIEW 1: INDIVIDUAL RECEIPT */}
        {activeTab === "INDIVIDUAL" && (
          <div className="space-y-6">
            {/* Details Grid */}
            <div className="grid grid-cols-2 gap-3.5 text-xs border-y border-[#EFE8DE] py-4">
              <div>
                <span className="text-[#71717A] text-[10px] block">Group Order</span>
                <strong className="text-[#1A1A1A] font-bold">{receipt.group_title}</strong>
              </div>
              <div>
                <span className="text-[#71717A] text-[10px] block">Participant</span>
                <strong className="text-[#1A1A1A] font-bold">{receipt.participant_name}</strong>
              </div>
              <div>
                <span className="text-[#71717A] text-[10px] block">Delivery Location</span>
                <strong className="text-[#1A1A1A] font-bold">{receipt.delivery_location}</strong>
              </div>
              <div>
                <span className="text-[#71717A] text-[10px] block">Transaction Reference</span>
                <strong className="text-[#1A1A1A] font-mono text-[11px] truncate block">{receipt.transaction_ref}</strong>
              </div>
            </div>

            {/* Itemized Line Items */}
            <div>
              <h3 className="text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-2.5">
                Your Ordered Items
              </h3>
              <div className="space-y-2">
                {receipt.items.map((it, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-xs py-1.5 border-b border-[#FAF8F5] last:border-none"
                  >
                    <div>
                      <span className="font-bold text-[#1A1A1A] block">{it.product_name}</span>
                      <span className="text-[10px] text-[#71717A]">
                        ₹{it.unit_price_inr} × {it.quantity}
                      </span>
                    </div>
                    <span className="font-black text-[#1A1A1A]">₹{it.total_price_inr.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Fee Breakdown & Total Paid */}
            <div className="border-t border-[#EFE8DE] pt-3.5 space-y-2 text-xs text-[#555555]">
              <div className="flex justify-between">
                <span>Items Subtotal</span>
                <span className="font-bold text-[#1A1A1A]">₹{receipt.items_subtotal_inr.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Shared Delivery & Tech Fee</span>
                <span className="font-bold text-[#1A1A1A]">₹{receipt.shared_fees_inr.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>GST / Taxes</span>
                <span className="font-bold text-[#1A1A1A]">₹{receipt.tax_inr.toFixed(2)}</span>
              </div>

              <div className="border-t border-[#EFE8DE] pt-3 flex justify-between items-center text-sm font-black text-[#1A1A1A]">
                <span>Total Paid (via {receipt.payment_method})</span>
                <span className="text-2xl text-[#10B981]">₹{receipt.total_paid_inr.toFixed(2)}</span>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 2: CONSOLIDATED GROUP RECEIPT */}
        {activeTab === "CONSOLIDATED" && (
          <div className="space-y-6">
            {/* Group Summary Metrics */}
            <div className="grid grid-cols-3 gap-2.5 bg-[#FAF8F5] p-3.5 rounded-2xl border border-[#EFE8DE] text-center">
              <div>
                <span className="text-[10px] text-[#71717A] block font-medium">Total Snacks</span>
                <strong className="text-lg font-black text-[#1A1A1A]">
                  {groupSummary?.total_items_count ?? receipt.items.reduce((s, i) => s + i.quantity, 0)}
                </strong>
              </div>
              <div>
                <span className="text-[10px] text-[#71717A] block font-medium">Roommates Paid</span>
                <strong className="text-lg font-black text-[#10B981]">
                  {groupSummary ? `${groupSummary.paid_participants_count}/${groupSummary.total_participants}` : "1/1"}
                </strong>
              </div>
              <div>
                <span className="text-[10px] text-[#71717A] block font-medium">Group Total</span>
                <strong className="text-lg font-black text-[#FF5C00]">
                  ₹{(groupSummary?.grand_total_inr ?? receipt.total_paid_inr).toFixed(2)}
                </strong>
              </div>
            </div>

            {/* Consolidated Product List */}
            <div>
              <h3 className="text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-2.5">
                Consolidated Shopping Items
              </h3>
              <div className="space-y-2">
                {groupSummary?.grouped_products && groupSummary.grouped_products.length > 0 ? (
                  groupSummary.grouped_products.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-[#FAF8F5] rounded-xl border border-[#EFE8DE] flex items-center justify-between text-xs"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-[#1A1A1A]">{item.product_name}</span>
                          <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-[#EFE8DE] font-bold text-[#FF5C00]">
                            × {item.total_quantity}
                          </span>
                        </div>
                        <span className="text-[10px] text-[#71717A]">
                          Ordered by: {item.ordered_by.join(", ")}
                        </span>
                      </div>
                      <span className="font-black text-[#1A1A1A]">₹{item.total_price_inr.toFixed(2)}</span>
                    </div>
                  ))
                ) : (
                  receipt.items.map((it, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-[#FAF8F5] rounded-xl border border-[#EFE8DE] flex items-center justify-between text-xs"
                    >
                      <span className="font-bold text-[#1A1A1A]">{it.product_name} × {it.quantity}</span>
                      <span className="font-black text-[#1A1A1A]">₹{it.total_price_inr.toFixed(2)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Grand Total Footer */}
            <div className="border-t border-[#EFE8DE] pt-3.5 space-y-1.5 text-xs text-[#555555]">
              <div className="flex justify-between">
                <span>Group Items Subtotal</span>
                <span className="font-bold text-[#1A1A1A]">
                  ₹{(groupSummary?.items_subtotal_inr ?? receipt.items_subtotal_inr).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Total Delivery & Tech Fees</span>
                <span className="font-bold text-[#1A1A1A]">
                  ₹{(groupSummary?.shared_fees_inr ?? receipt.shared_fees_inr).toFixed(2)}
                </span>
              </div>
              <div className="border-t border-[#EFE8DE] pt-2 flex justify-between items-center text-sm font-black text-[#1A1A1A]">
                <span>Grand Total Pool</span>
                <span className="text-2xl text-[#FF5C00]">
                  ₹{(groupSummary?.grand_total_inr ?? receipt.total_paid_inr).toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons (Print, WhatsApp, Copy Link, Return to Group) */}
        <div className="pt-2 flex flex-col sm:flex-row items-center gap-2 print:hidden">
          <button
            onClick={handlePrint}
            className="w-full sm:flex-1 flex items-center justify-center gap-1.5 bg-[#FAF8F5] hover:bg-white text-[#1A1A1A] border border-[#EFE8DE] py-2.5 rounded-xl text-xs font-bold transition-colors shadow-2xs cursor-pointer"
          >
            <Printer className="w-4 h-4" />
            <span>Print</span>
          </button>

          <button
            onClick={handleWhatsAppShare}
            className="w-full sm:flex-1 flex items-center justify-center gap-1.5 bg-[#25D366] hover:bg-[#20BD5A] text-white py-2.5 rounded-xl text-xs font-bold transition-colors shadow-md shadow-[#25D366]/25 cursor-pointer"
          >
            <MessageCircle className="w-4 h-4" />
            <span>WhatsApp</span>
          </button>

          <button
            onClick={handleShare}
            className="w-full sm:flex-1 flex items-center justify-center gap-1.5 bg-[#FAF8F5] hover:bg-white text-[#1A1A1A] border border-[#EFE8DE] py-2.5 rounded-xl text-xs font-bold transition-colors shadow-2xs cursor-pointer"
          >
            {copied ? <Check className="w-4 h-4 text-[#10B981]" /> : <Share2 className="w-4 h-4 text-[#FF5C00]" />}
            <span>{copied ? "Copied" : "Copy Link"}</span>
          </button>

          <Link
            href={`/group/${receipt.group_order_id}`}
            className="w-full sm:flex-1 flex items-center justify-center gap-1.5 bg-[#FF5C00] hover:bg-[#E55200] text-white py-2.5 rounded-xl text-xs font-bold transition-colors shadow-md shadow-[#FF5C00]/25 text-center"
          >
            <span>Back to Group</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ReceiptPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-md mx-auto px-4 py-16 text-center space-y-4">
          <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
          <h2 className="font-bold text-lg text-[#1A1A1A]">Generating Digital Receipt...</h2>
          <p className="text-xs text-[#71717A]">Verifying transaction record</p>
        </div>
      }
    >
      <ReceiptContent />
    </Suspense>
  );
}
