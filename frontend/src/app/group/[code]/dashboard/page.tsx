"use client";

import { useState, useEffect, Suspense } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ShieldCheck,
  Users,
  CreditCard,
  CheckCircle2,
  AlertCircle,
  Clock,
  Lock,
  Unlock,
  Truck,
  Copy,
  Check,
  ShoppingBag,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  ExternalLink,
  PlusCircle,
  FileText,
  Sparkles,
  MessageCircle,
} from "lucide-react";
import {
  api,
  GroupDetail,
  HostDashboardSummary,
  FinalCombinedOrderSummary,
  getStoredGuestSession,
} from "@/lib/api";

function HostDashboardContent() {
  const params = useParams();
  const router = useRouter();
  const code = (params?.code as string)?.toUpperCase();

  const [group, setGroup] = useState<GroupDetail | null>(null);
  const [dashboard, setDashboard] = useState<HostDashboardSummary | null>(null);
  const [summary, setSummary] = useState<FinalCombinedOrderSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Manual UPI confirmation modal state
  const [manualConfirmTarget, setManualConfirmTarget] = useState<{
    id: string;
    name: string;
    amount: number;
  } | null>(null);
  const [manualUtr, setManualUtr] = useState("");
  const [manualNotes, setManualNotes] = useState("Host verified via GPay/PhonePe");

  // Merchant order placement state
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [orderPlatform, setOrderPlatform] = useState("Blinkit");
  const [orderExternalId, setOrderExternalId] = useState("");
  const [orderEtaMinutes, setOrderEtaMinutes] = useState(25);
  const [orderNotes, setOrderNotes] = useState("");

  const refreshData = async (groupId: string) => {
    try {
      const [dashData, sumData, grpData] = await Promise.all([
        api.getHostDashboard(groupId),
        api.getGroupSummary(groupId),
        api.getGroup(groupId),
      ]);
      setDashboard(dashData);
      setSummary(sumData);
      setGroup(grpData);
    } catch (err) {
      console.error("Dashboard refresh error:", err);
    }
  };

  useEffect(() => {
    if (!code) return;

    async function loadData() {
      try {
        setLoading(true);
        const grp = await api.getGroup(code);
        setGroup(grp);
        await refreshData(grp.id);
      } catch (err: any) {
        console.error("Failed to load dashboard:", err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [code]);

  const handleCopyLink = () => {
    if (!dashboard) return;
    navigator.clipboard.writeText(dashboard.share_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleWhatsAppRemind = () => {
    if (typeof window === "undefined" || !dashboard) return;
    const checkoutUrl = `${window.location.origin}/group/${dashboard.invite_code}/checkout`;
    const msg = `🍜 *MunchMate Payment Reminder: ${dashboard.group_title}*\nTotal Group Bill: *₹${dashboard.grand_total_inr.toFixed(2)}*\nCollected: *₹${dashboard.total_collected_inr.toFixed(2)}* (${dashboard.paid_count}/${dashboard.participants_count} paid)\n\nRoommates, please check your exact share & scan the UPI QR here:\n👉 ${checkoutUrl}`;
    window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`, "_blank");
  };

  const handleToggleLock = async () => {
    if (!group) return;
    try {
      setActionLoading(true);
      if (group.cart_status === "OPEN") {
        await api.lockCart(group.id);
        setStatusMessage("Cart locked! Roommates can now checkout and pay.");
      } else {
        await api.reopenCart(group.id);
        setStatusMessage("Cart reopened for roommate modifications.");
      }
      await refreshData(group.id);
    } catch (err: any) {
      setStatusMessage(`Error: ${err.message}`);
    } finally {
      setActionLoading(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleManualConfirm = async () => {
    if (!group || !manualConfirmTarget) return;

    try {
      setActionLoading(true);
      const stored = getStoredGuestSession();
      const hostPartId = group.host_participant_id || stored?.id || group.id;

      await api.hostManualConfirmPayment({
        participant_id: manualConfirmTarget.id,
        host_participant_id: hostPartId,
        session_token: stored?.session_token,
        upi_reference: manualUtr.trim() || undefined,
        notes: manualNotes.trim() || undefined,
      });

      setStatusMessage(`Payment confirmed for ${manualConfirmTarget.name}! Receipt generated.`);
      setManualConfirmTarget(null);
      setManualUtr("");
      await refreshData(group.id);
    } catch (err: any) {
      setStatusMessage(`Error confirming payment: ${err.message}`);
    } finally {
      setActionLoading(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handlePlaceMerchantOrder = async () => {
    if (!group) return;

    try {
      setActionLoading(true);
      await api.recordMerchantOrder(group.id, {
        platform_name: orderPlatform,
        external_order_id: orderExternalId.trim() || undefined,
        estimated_delivery_minutes: Number(orderEtaMinutes),
        notes: orderNotes.trim() || undefined,
      });

      setStatusMessage(`Merchant order recorded on ${orderPlatform}! Status set to PLACED.`);
      setShowOrderModal(false);
      await refreshData(group.id);
    } catch (err: any) {
      setStatusMessage(`Error placing merchant order: ${err.message}`);
    } finally {
      setActionLoading(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleUpdateMerchantStatus = async (newStatus: string) => {
    if (!group) return;
    try {
      setActionLoading(true);
      await api.updateMerchantOrderStatus(group.id, { status: newStatus });
      setStatusMessage(`Merchant order status updated to ${newStatus}!`);
      await refreshData(group.id);
    } catch (err: any) {
      setStatusMessage(`Error: ${err.message}`);
    } finally {
      setActionLoading(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
        <h2 className="font-bold text-lg text-[#1A1A1A]">Loading Host Dashboard...</h2>
        <p className="text-xs text-[#71717A]">Syncing real-time payment states and group metrics</p>
      </div>
    );
  }

  if (!dashboard || !group) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-[#FF5C00] mx-auto" />
        <h2 className="font-bold text-xl text-[#1A1A1A]">Dashboard Unavailable</h2>
        <Link href="/" className="inline-block bg-[#FF5C00] text-white px-5 py-2.5 rounded-xl font-bold text-xs">
          Return Home
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10 pb-28 space-y-6">
      {/* Back button */}
      <div>
        <Link
          href={`/group/${group.invite_code}`}
          className="inline-flex items-center gap-1.5 text-xs font-bold text-[#71717A] hover:text-[#1A1A1A] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Group Cart</span>
        </Link>
      </div>

      {/* Status Notice Toast */}
      {statusMessage && (
        <div className="p-3.5 bg-[#FFF4ED] border border-[#FFD9C6] text-[#FF5C00] text-xs font-bold rounded-2xl flex items-center gap-2 animate-in fade-in">
          <Sparkles className="w-4 h-4 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Header Card */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-bold text-[#FF5C00] uppercase tracking-wider bg-[#FFF4ED] px-2.5 py-0.5 rounded-md border border-[#FFD9C6] flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Host Control Center</span>
              </span>
              <span className="font-mono font-bold text-xs bg-zinc-100 text-[#1A1A1A] px-2 py-0.5 rounded">
                Code: {dashboard.invite_code}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-[#1A1A1A] font-['Outfit',sans-serif]">
              {dashboard.group_title}
            </h1>
            <p className="text-xs text-[#71717A] mt-0.5">
              Delivering to: <strong className="text-[#1A1A1A]">{dashboard.delivery_location}</strong>
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={handleCopyLink}
              className="flex items-center gap-1.5 bg-[#FAF8F5] hover:bg-white text-[#1A1A1A] border border-[#EFE8DE] px-3.5 py-2 rounded-xl text-xs font-bold transition-colors shadow-2xs cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-[#10B981]" /> : <Copy className="w-3.5 h-3.5 text-[#FF5C00]" />}
              <span>{copied ? "Link Copied" : "Copy Invite Link"}</span>
            </button>

            <button
              onClick={handleWhatsAppRemind}
              className="flex items-center gap-1.5 bg-[#25D366] hover:bg-[#20BD5A] text-white px-3.5 py-2 rounded-xl text-xs font-bold transition-colors shadow-sm shadow-[#25D366]/20 cursor-pointer"
            >
              <MessageCircle className="w-3.5 h-3.5" />
              <span>Remind via WhatsApp</span>
            </button>

            <button
              onClick={handleToggleLock}
              disabled={actionLoading}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-colors ${
                dashboard.cart_status === "OPEN"
                  ? "bg-amber-500 hover:bg-amber-600 text-white shadow-xs"
                  : "bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs"
              }`}
            >
              {dashboard.cart_status === "OPEN" ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
              <span>{dashboard.cart_status === "OPEN" ? "Lock Cart (Ready for Pay)" : "Reopen Cart"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4">
        {/* Grand Total */}
        <div className="bg-white p-4.5 rounded-2xl border border-[#EFE8DE] shadow-2xs">
          <span className="text-[11px] text-[#71717A] font-bold block mb-1">Combined Total</span>
          <span className="text-2xl font-black text-[#1A1A1A] font-['Outfit',sans-serif]">
            ₹{dashboard.grand_total_inr.toFixed(0)}
          </span>
          <span className="text-[10px] text-[#71717A] block mt-1">
            {dashboard.total_items_count} items across {dashboard.participants_count} roommates
          </span>
        </div>

        {/* Collected via UPI */}
        <div className="bg-white p-4.5 rounded-2xl border border-emerald-200/80 shadow-2xs bg-gradient-to-br from-white to-emerald-50/20">
          <span className="text-[11px] text-emerald-700 font-bold block mb-1">Collected via UPI</span>
          <span className="text-2xl font-black text-[#10B981] font-['Outfit',sans-serif]">
            ₹{dashboard.total_collected_inr.toFixed(0)}
          </span>
          <span className="text-[10px] text-emerald-600 font-medium block mt-1">
            {dashboard.paid_count} of {dashboard.participants_count} paid
          </span>
        </div>

        {/* Outstanding Unpaid */}
        <div className="bg-white p-4.5 rounded-2xl border border-[#EFE8DE] shadow-2xs">
          <span className="text-[11px] text-[#71717A] font-bold block mb-1">Unpaid Balance</span>
          <span className="text-2xl font-black text-[#FF5C00] font-['Outfit',sans-serif]">
            ₹{dashboard.outstanding_inr.toFixed(0)}
          </span>
          <span className="text-[10px] text-[#71717A] block mt-1">
            {dashboard.unpaid_count} roommate{dashboard.unpaid_count === 1 ? "" : "s"} pending
          </span>
        </div>

        {/* Completion % */}
        <div className="bg-white p-4.5 rounded-2xl border border-[#EFE8DE] shadow-2xs flex flex-col justify-between">
          <div>
            <span className="text-[11px] text-[#71717A] font-bold block mb-1">Payment Completion</span>
            <span className="text-2xl font-black text-[#1A1A1A] font-['Outfit',sans-serif]">
              {dashboard.payment_completion_pct}%
            </span>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-[#FAF8F5] h-2 rounded-full overflow-hidden border border-[#EFE8DE] mt-2">
            <div
              className="bg-[#10B981] h-full rounded-full transition-all duration-500"
              style={{ width: `${dashboard.payment_completion_pct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Roommates & Payment Status Tracker */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-extrabold text-[#1A1A1A] font-['Outfit',sans-serif]">
              Roommates Payment Tracker
            </h2>
            <p className="text-xs text-[#71717A]">
              Live status for every participant. Manually confirm UPI payments if a friend sent directly to your phone.
            </p>
          </div>
          <span className="text-xs font-bold text-[#71717A]">
            {dashboard.paid_count}/{dashboard.participants_count} Paid
          </span>
        </div>

        <div className="divide-y divide-[#FAF8F5]">
          {dashboard.participant_shares.map((share) => {
            const isPaid = share.payment_status === "PAID";

            return (
              <div
                key={share.participant_id}
                className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-black text-white shadow-xs shrink-0"
                    style={{ backgroundColor: share.avatar_color || "#FF5C00" }}
                  >
                    {share.participant_name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-extrabold text-xs sm:text-sm text-[#1A1A1A]">
                        {share.participant_name}
                      </span>
                      {share.is_host && (
                        <span className="bg-zinc-100 text-[#71717A] text-[9px] font-bold px-1.5 py-0.5 rounded">
                          Host
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-[#71717A]">
                      {share.items_count} items • Subtotal: ₹{share.items_subtotal_inr.toFixed(0)} + Fees Share: ₹
                      {share.shared_fees_total_inr.toFixed(0)}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-4 self-end sm:self-center">
                  <div className="text-right">
                    <span className="text-xs sm:text-sm font-black text-[#1A1A1A] block">
                      ₹{share.total_payable_inr.toFixed(2)}
                    </span>
                    <span
                      className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        isPaid
                          ? "bg-[#ECFDF5] text-[#10B981] border border-emerald-200"
                          : share.payment_status === "PAYMENT_CLAIMED"
                          ? "bg-amber-50 text-amber-700 border border-amber-300"
                          : "bg-[#FFF4ED] text-[#FF5C00] border border-[#FFD9C6]"
                      }`}
                    >
                      {isPaid
                        ? "PAID ✓"
                        : share.payment_status === "PAYMENT_CLAIMED"
                        ? "CLAIMED (VERIFY)"
                        : "PENDING"}
                    </span>
                  </div>

                  {/* Manual Confirmation Button if unpaid */}
                  {!isPaid && (
                    <button
                      onClick={() =>
                        setManualConfirmTarget({
                          id: share.participant_id,
                          name: share.participant_name,
                          amount: share.total_payable_inr,
                        })
                      }
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors shadow-2xs whitespace-nowrap ${
                        share.payment_status === "PAYMENT_CLAIMED"
                          ? "bg-[#FF5C00] hover:bg-[#E55200] text-white shadow-md shadow-[#FF5C00]/25"
                          : "bg-[#FAF8F5] hover:bg-[#FFF4ED] text-[#FF5C00] border border-[#FFD9C6]"
                      }`}
                    >
                      {share.payment_status === "PAYMENT_CLAIMED"
                        ? "Confirm Claim ✓"
                        : "Confirm UPI Manually"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Combined Group Order Shopping List (Grouped by Product) */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="inline-flex items-center gap-1.5 bg-[#FFF4ED] text-[#FF5C00] text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider mb-1 border border-[#FFD9C6]">
              <ShoppingBag className="w-3 h-3" />
              <span>Consolidated Merchant List</span>
            </div>
            <h2 className="text-base sm:text-lg font-black text-[#1A1A1A] font-['Outfit',sans-serif]">
              Final Shopping List (Grouped by Product)
            </h2>
            <p className="text-xs text-[#71717A]">
              Add these exact consolidated quantities to Blinkit, Zepto, Swiggy Instamart, or the Campus Canteen.
            </p>
          </div>

          <Link
            href={`/group/${group.invite_code}/summary`}
            className="text-xs font-bold text-[#FF5C00] hover:underline flex items-center gap-1 shrink-0"
          >
            <span>Public Summary View</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>

        {summary && summary.grouped_products.length > 0 ? (
          <div className="divide-y divide-[#FAF8F5] border border-[#EFE8DE] rounded-2xl overflow-hidden">
            {summary.grouped_products.map((p) => (
              <div
                key={p.product_id}
                className="p-3.5 flex items-center justify-between gap-4 bg-white hover:bg-[#FAF8F5] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-[#FFF4ED] text-[#FF5C00] font-black text-sm flex items-center justify-center shrink-0 border border-[#FFD9C6]">
                    ×{p.total_quantity}
                  </div>
                  <div>
                    <span className="font-extrabold text-xs sm:text-sm text-[#1A1A1A] block">
                      {p.product_name}
                    </span>
                    <span className="text-[11px] text-[#71717A]">
                      Ordered by: {p.ordered_by.join(", ")}
                    </span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="font-black text-xs sm:text-sm text-[#1A1A1A] block">
                    ₹{p.total_price_inr.toFixed(0)}
                  </span>
                  <span className="text-[10px] text-[#71717A]">
                    ₹{p.unit_price_inr} each
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-[#71717A] italic py-3 text-center">
            No items have been added to this order yet.
          </p>
        )}
      </div>

      {/* Merchant Order Placement & Status Section */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-extrabold text-[#1A1A1A] font-['Outfit',sans-serif]">
              Merchant Order Placement
            </h2>
            <p className="text-xs text-[#71717A]">
              Record placement with delivery service once group money is pooled.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider ${
                dashboard.merchant_order_status === "DELIVERED"
                  ? "bg-emerald-100 text-emerald-800"
                  : dashboard.merchant_order_status === "PLACED" || dashboard.merchant_order_status === "PREPARING"
                  ? "bg-blue-100 text-blue-800"
                  : "bg-zinc-100 text-[#71717A]"
              }`}
            >
              ● {dashboard.merchant_order_status}
            </span>

            {dashboard.merchant_order_status === "NOT_PLACED" ? (
              <button
                onClick={() => setShowOrderModal(true)}
                className="flex items-center gap-1.5 bg-[#FF5C00] hover:bg-[#E55200] text-white px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-md shadow-[#FF5C00]/25 active:scale-95"
              >
                <Truck className="w-3.5 h-3.5" />
                <span>Record Order Placement</span>
              </button>
            ) : (
              <div className="flex items-center gap-1">
                {dashboard.merchant_order_status !== "DELIVERED" && (
                  <button
                    onClick={() => handleUpdateMerchantStatus("DELIVERED")}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-xl text-xs font-bold transition-colors"
                  >
                    Mark Delivered ✓
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Activity Audit Log */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-6 shadow-xs space-y-3">
        <h2 className="text-xs font-bold text-[#71717A] uppercase tracking-wider">
          Recent Activity & Audit Trail
        </h2>
        <div className="space-y-2">
          {dashboard.recent_activities.map((act) => (
            <div
              key={act.id}
              className="flex items-center justify-between text-xs py-1.5 border-b border-[#FAF8F5] last:border-none"
            >
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-[#FF5C00] bg-[#FFF4ED] px-1.5 py-0.5 rounded font-bold">
                  {act.action}
                </span>
                <span className="text-[#1A1A1A] font-medium">by {act.actor_name}</span>
              </div>
              <span className="text-[10px] text-[#71717A]">
                {new Date(act.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* MODAL 1: Manual UPI Confirmation Modal */}
      {manualConfirmTarget && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl border border-[#EFE8DE] max-w-md w-full p-6 shadow-2xl space-y-4 animate-in zoom-in-95 duration-150">
            <div>
              <span className="text-[10px] font-bold text-[#FF5C00] uppercase tracking-wider bg-[#FFF4ED] px-2 py-0.5 rounded border border-[#FFD9C6]">
                Host Manual Verification
              </span>
              <h3 className="text-lg font-black text-[#1A1A1A] mt-2 font-['Outfit',sans-serif]">
                Confirm Payment from {manualConfirmTarget.name}
              </h3>
              <p className="text-xs text-[#71717A] mt-1">
                Confirming will issue an official digital receipt for ₹{manualConfirmTarget.amount.toFixed(2)} and log your host audit timestamp.
              </p>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[#1A1A1A] font-bold uppercase tracking-wider mb-1 text-[11px]">
                  Optional UPI UTR / Reference No.
                </label>
                <input
                  type="text"
                  value={manualUtr}
                  onChange={(e) => setManualUtr(e.target.value)}
                  placeholder="e.g. 429182390192"
                  className="w-full px-3.5 py-2 rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 font-mono"
                />
              </div>

              <div>
                <label className="block text-[#1A1A1A] font-bold uppercase tracking-wider mb-1 text-[11px]">
                  Verification Note
                </label>
                <input
                  type="text"
                  value={manualNotes}
                  onChange={(e) => setManualNotes(e.target.value)}
                  placeholder="e.g. Verified on GPay"
                  className="w-full px-3.5 py-2 rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2">
              <button
                onClick={() => setManualConfirmTarget(null)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-[#71717A] hover:bg-zinc-100"
              >
                Cancel
              </button>
              <button
                onClick={handleManualConfirm}
                disabled={actionLoading}
                className="bg-[#10B981] hover:bg-emerald-600 text-white px-5 py-2 rounded-xl text-xs font-bold shadow-md shadow-emerald-500/20 active:scale-95 transition-all"
              >
                {actionLoading ? "Confirming..." : "Confirm & Issue Receipt"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Record Merchant Order Placement Modal */}
      {showOrderModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl border border-[#EFE8DE] max-w-md w-full p-6 shadow-2xl space-y-4 animate-in zoom-in-95 duration-150">
            <div>
              <span className="text-[10px] font-bold text-[#FF5C00] uppercase tracking-wider bg-[#FFF4ED] px-2 py-0.5 rounded border border-[#FFD9C6]">
                Merchant Order Tracker
              </span>
              <h3 className="text-lg font-black text-[#1A1A1A] mt-2 font-['Outfit',sans-serif]">
                Record External Order Placement
              </h3>
              <p className="text-xs text-[#71717A] mt-1">
                Let your roommates know on which app the combined snacks have been ordered.
              </p>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[#1A1A1A] font-bold uppercase tracking-wider mb-1 text-[11px]">
                  Delivery App / Platform
                </label>
                <select
                  value={orderPlatform}
                  onChange={(e) => setOrderPlatform(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] font-semibold"
                >
                  <option value="Blinkit">Blinkit (10-15 mins)</option>
                  <option value="Zepto">Zepto</option>
                  <option value="Swiggy Instamart">Swiggy Instamart</option>
                  <option value="Zomato">Zomato Food</option>
                  <option value="Campus Night Canteen">Campus Night Canteen</option>
                </select>
              </div>

              <div>
                <label className="block text-[#1A1A1A] font-bold uppercase tracking-wider mb-1 text-[11px]">
                  External Order ID (Optional)
                </label>
                <input
                  type="text"
                  value={orderExternalId}
                  onChange={(e) => setOrderExternalId(e.target.value)}
                  placeholder="e.g. BLKT-983120"
                  className="w-full px-3.5 py-2 rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] font-mono"
                />
              </div>

              <div>
                <label className="block text-[#1A1A1A] font-bold uppercase tracking-wider mb-1 text-[11px]">
                  Estimated Delivery (Minutes)
                </label>
                <input
                  type="number"
                  min={5}
                  max={120}
                  value={orderEtaMinutes}
                  onChange={(e) => setOrderEtaMinutes(Number(e.target.value))}
                  className="w-full px-3.5 py-2 rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] font-semibold"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2">
              <button
                onClick={() => setShowOrderModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-[#71717A] hover:bg-zinc-100"
              >
                Cancel
              </button>
              <button
                onClick={handlePlaceMerchantOrder}
                disabled={actionLoading}
                className="bg-[#FF5C00] hover:bg-[#E55200] text-white px-5 py-2 rounded-xl text-xs font-bold shadow-md shadow-[#FF5C00]/25 active:scale-95 transition-all"
              >
                {actionLoading ? "Recording..." : "Record Order Placed"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function HostDashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-3xl mx-auto px-4 py-16 text-center space-y-4">
          <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
          <h2 className="font-bold text-lg text-[#1A1A1A]">Loading Host Dashboard...</h2>
          <p className="text-xs text-[#71717A]">Syncing real-time payment states and group metrics</p>
        </div>
      }
    >
      <HostDashboardContent />
    </Suspense>
  );
}
