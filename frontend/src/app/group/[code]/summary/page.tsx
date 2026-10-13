"use client";

import { useState, useEffect, Suspense } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ShoppingBag,
  ArrowLeft,
  Copy,
  Check,
  CheckCircle2,
  Clock,
  Truck,
  Sparkles,
  Users,
  AlertCircle,
} from "lucide-react";
import { api, FinalCombinedOrderSummary, saveRecentGroup } from "@/lib/api";

function GroupSummaryContent() {
  const params = useParams();
  const code = (params?.code as string)?.toUpperCase();

  const [summary, setSummary] = useState<FinalCombinedOrderSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedList, setCopiedList] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;

    async function loadSummary() {
      try {
        setLoading(true);
        setErrorMessage(null);
        let data: FinalCombinedOrderSummary | null = null;
        try {
          // Attempt direct summary lookup (backend supports invite_code or UUID)
          data = await api.getGroupSummary(code);
        } catch {
          // Fallback to resolving group details first
          const grp = await api.getGroup(code);
          data = await api.getGroupSummary(grp.id);
        }

        setSummary(data);

        // Record in recent groups for convenience
        if (data) {
          saveRecentGroup({
            code: data.invite_code || code,
            title: data.group_title,
            location: data.delivery_location,
            status: data.cart_status,
            items: data.total_items_count,
          });
        }
      } catch (err: any) {
        console.warn(`Could not load group summary for "${code}":`, err?.message || err);
        setErrorMessage(err?.message || `Group order "${code}" was not found.`);
      } finally {
        setLoading(false);
      }
    }

    loadSummary();
  }, [code]);

  const copyShoppingListText = () => {
    if (!summary) return;
    const lines = [
      `🛒 MUNCHMATE FINAL ORDER: ${summary.group_title}`,
      `📍 Delivery: ${summary.delivery_location}`,
      `----------------------------------------`,
      ...summary.grouped_products.map(
        (p) => `• ${p.product_name} × ${p.total_quantity} (₹${p.total_price_inr.toFixed(0)})`
      ),
      `----------------------------------------`,
      `Items Subtotal: ₹${summary.items_subtotal_inr.toFixed(0)}`,
      `Shared Fees: ₹${summary.shared_fees_inr.toFixed(0)}`,
      `Grand Total: ₹${summary.grand_total_inr.toFixed(0)}`,
      `Status: ${summary.is_fully_paid ? "ALL PAID ✓" : "COLLECTING PAYMENTS"}`,
    ];

    navigator.clipboard.writeText(lines.join("\n"));
    setCopiedList(true);
    setTimeout(() => setCopiedList(false), 2000);
  };

  if (loading) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
        <h2 className="font-bold text-lg text-[#1A1A1A]">Generating Order Summary...</h2>
        <p className="text-xs text-[#71717A]">Consolidating product quantities and shares</p>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center space-y-6">
        <div className="w-16 h-16 rounded-3xl bg-[#FFF4ED] text-[#FF5C00] flex items-center justify-center mx-auto border border-[#FFD9C6] shadow-sm">
          <AlertCircle className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="font-black text-2xl text-[#1A1A1A] font-['Outfit',sans-serif]">
            Group Order Not Found
          </h2>
          <p className="text-xs text-[#71717A] max-w-sm mx-auto leading-relaxed">
            We couldn't find an order matching code{" "}
            <span className="font-mono font-bold text-[#FF5C00] bg-[#FFF4ED] px-1.5 py-0.5 rounded border border-[#FFD9C6]">
              {code || "UNKNOWN"}
            </span>
            . The session may have expired or the link might be mistyped.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-2.5 pt-2">
          <Link
            href={code ? `/join?code=${code}` : "/join"}
            className="w-full sm:w-auto bg-[#FF5C00] hover:bg-[#E55200] text-white px-5 py-2.5 rounded-xl font-bold text-xs shadow-md shadow-[#FF5C00]/25 transition-transform active:scale-95"
          >
            Try Joining With Code
          </Link>
          <Link
            href="/history"
            className="w-full sm:w-auto bg-white hover:bg-[#FAF8F5] text-[#1A1A1A] border border-[#EFE8DE] px-5 py-2.5 rounded-xl font-bold text-xs transition-colors"
          >
            Recent Groups
          </Link>
          <Link
            href="/"
            className="w-full sm:w-auto bg-white hover:bg-[#FAF8F5] text-[#71717A] border border-[#EFE8DE] px-5 py-2.5 rounded-xl font-bold text-xs transition-colors"
          >
            Return Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10 pb-20 space-y-6">
      {/* Back button */}
      <div>
        <Link
          href={`/group/${code}`}
          className="inline-flex items-center gap-1.5 text-xs font-bold text-[#71717A] hover:text-[#1A1A1A] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Group Cart</span>
        </Link>
      </div>

      {/* Header Card */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <span className="text-[10px] font-bold text-[#FF5C00] uppercase tracking-wider bg-[#FFF4ED] px-2.5 py-0.5 rounded-md border border-[#FFD9C6]">
              Consolidated Shopping List
            </span>
            <h1 className="text-2xl font-black text-[#1A1A1A] mt-1.5 font-['Outfit',sans-serif]">
              {summary.group_title}
            </h1>
            <p className="text-xs text-[#71717A]">
              Delivery Location: <strong className="text-[#1A1A1A]">{summary.delivery_location}</strong>
            </p>
          </div>

          <button
            onClick={copyShoppingListText}
            className="flex items-center gap-1.5 bg-[#FAF8F5] hover:bg-[#FFF4ED] text-[#FF5C00] border border-[#FFD9C6] px-3.5 py-2 rounded-xl text-xs font-bold transition-colors shadow-2xs self-start sm:self-auto"
          >
            {copiedList ? <Check className="w-3.5 h-3.5 text-[#10B981]" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedList ? "Shopping List Copied!" : "Copy Full Shopping List"}</span>
          </button>
        </div>

        {/* Status badges bar */}
        <div className="pt-2 flex flex-wrap items-center gap-2 text-xs">
          <span className="bg-[#FAF8F5] border border-[#EFE8DE] px-2.5 py-1 rounded-lg text-[#555555]">
            Total Items: <strong className="text-[#1A1A1A]">{summary.total_items_count}</strong>
          </span>
          <span className="bg-[#FAF8F5] border border-[#EFE8DE] px-2.5 py-1 rounded-lg text-[#555555]">
            Roommates: <strong className="text-[#1A1A1A]">{summary.total_participants}</strong>
          </span>
          <span
            className={`px-2.5 py-1 rounded-lg font-bold ${
              summary.is_fully_paid
                ? "bg-[#ECFDF5] text-[#10B981] border border-emerald-200"
                : "bg-[#FFF4ED] text-[#FF5C00] border border-[#FFD9C6]"
            }`}
          >
            {summary.is_fully_paid ? "All Payments Verified ✓" : `${summary.paid_participants_count}/${summary.total_participants} Paid`}
          </span>
        </div>
      </div>

      {/* Grouped Products Shopping List */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs space-y-4">
        <h2 className="text-sm font-extrabold text-[#1A1A1A] uppercase tracking-wider font-['Outfit',sans-serif]">
          Aggregated Quantities to Order
        </h2>

        <div className="divide-y divide-[#FAF8F5]">
          {summary.grouped_products.map((p) => (
            <div
              key={p.product_id}
              className="py-3.5 flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-[#FFF4ED] text-[#FF5C00] font-black text-sm flex items-center justify-center shrink-0 border border-[#FFD9C6]">
                  ×{p.total_quantity}
                </div>
                <div>
                  <span className="font-extrabold text-sm text-[#1A1A1A] block">
                    {p.product_name}
                  </span>
                  <span className="text-[11px] text-[#71717A]">
                    Ordered by: <strong className="text-[#555555]">{p.ordered_by.join(", ")}</strong>
                  </span>
                </div>
              </div>

              <div className="text-right shrink-0">
                <span className="font-black text-sm text-[#1A1A1A] block">
                  ₹{p.total_price_inr.toFixed(0)}
                </span>
                <span className="text-[10px] text-[#71717A]">
                  ₹{p.unit_price_inr} / {p.unit}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Financial Summary Breakdown */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs space-y-3 text-xs">
        <h2 className="text-sm font-extrabold text-[#1A1A1A] uppercase tracking-wider font-['Outfit',sans-serif] mb-2">
          Payment Breakdown & Balance
        </h2>

        <div className="flex justify-between text-[#555555]">
          <span>Combined Items Subtotal</span>
          <span className="font-bold text-[#1A1A1A]">₹{summary.items_subtotal_inr.toFixed(2)}</span>
        </div>

        <div className="flex justify-between text-[#555555]">
          <span>Shared Delivery, Platform & Packaging Fees</span>
          <span className="font-bold text-[#1A1A1A]">₹{summary.shared_fees_inr.toFixed(2)}</span>
        </div>

        <div className="flex justify-between text-[#555555]">
          <span>GST / Taxes</span>
          <span className="font-bold text-[#1A1A1A]">₹{summary.tax_inr.toFixed(2)}</span>
        </div>

        <div className="border-t border-[#EFE8DE] pt-3 flex justify-between items-center text-sm font-black text-[#1A1A1A]">
          <span>Grand Total Bill</span>
          <span className="text-2xl text-[#FF5C00]">₹{summary.grand_total_inr.toFixed(2)}</span>
        </div>

        <div className="flex justify-between text-[#10B981] font-bold pt-1">
          <span>Total Collected via UPI</span>
          <span>₹{summary.total_paid_inr.toFixed(2)}</span>
        </div>

        {summary.remaining_unpaid_paise > 0 && (
          <div className="flex justify-between text-red-600 font-bold">
            <span>Remaining Unpaid Balance</span>
            <span>₹{summary.remaining_unpaid_inr.toFixed(2)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function GroupSummaryPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-xl mx-auto px-4 py-16 text-center space-y-4">
          <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
          <h2 className="font-bold text-lg text-[#1A1A1A]">Generating Order Summary...</h2>
          <p className="text-xs text-[#71717A]">Consolidating product quantities and shares</p>
        </div>
      }
    >
      <GroupSummaryContent />
    </Suspense>
  );
}
