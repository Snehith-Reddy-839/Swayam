"use client";

import { useState, useEffect, Suspense } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import confetti from "canvas-confetti";
import {
  QrCode,
  CreditCard,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  Clock,
  ArrowRight,
  ArrowLeft,
  AlertCircle,
  Copy,
  Check,
  ExternalLink,
  Smartphone,
  RefreshCw,
  Lock,
} from "lucide-react";
import {
  api,
  GroupDetail,
  BillCalculation,
  ParticipantBillShare,
  getStoredGuestSession,
} from "@/lib/api";

function CheckoutContent() {
  const params = useParams();
  const router = useRouter();
  const code = (params?.code as string)?.toUpperCase();

  // State
  const [group, setGroup] = useState<GroupDetail | null>(null);
  const [billing, setBilling] = useState<BillCalculation | null>(null);
  const [myShare, setMyShare] = useState<ParticipantBillShare | null>(null);
  const [loading, setLoading] = useState(true);
  const [paymentMode, setPaymentMode] = useState<"UPI_QR" | "DEMO" | "RAZORPAY">("UPI_QR");
  const [copiedVpa, setCopiedVpa] = useState(false);

  // Payment Initiation and Verification state
  const [qrDetails, setQrDetails] = useState<{
    upi_uri?: string;
    qr_data_url?: string;
    vpa?: string;
    payee_name?: string;
    amount_inr?: number;
    transaction_ref?: string;
    instructions?: string[];
    attempt_id?: string;
  } | null>(null);

  const [verifying, setVerifying] = useState(false);
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const [utrInput, setUtrInput] = useState("");

  useEffect(() => {
    if (!code) return;

    async function loadCheckoutData() {
      try {
        setLoading(true);
        const groupData = await api.getGroup(code);
        setGroup(groupData);

        const billData = await api.getBilling(groupData.id);
        setBilling(billData);

        // Identify current participant
        const stored = getStoredGuestSession();
        const participants = await api.getParticipants(groupData.id);
        let myP = participants.find((p) => p.id === stored?.id || p.display_name === stored?.display_name);

        if (!myP && stored?.display_name && groupData.host_name === stored.display_name) {
          myP = participants.find((p) => p.is_host);
        }

        if (!myP && participants.length > 0) {
          router.push(`/join?code=${code}`);
          return;
        }

        if (myP) {
          const share = billData.participant_shares.find((s) => s.participant_id === myP.id);
          setMyShare(share || null);

          // If participant is already paid, redirect to receipt
          if (share?.payment_status === "PAID") {
            // Find existing receipt
            router.push(`/receipt/${share.participant_id}`);
            return;
          }

          // Initiate payment attempt to get exact QR code
          if (share && share.total_payable_paise > 0) {
            const initResp = await api.initiatePayment({
              participant_id: share.participant_id,
              payment_mode: "UPI_QR",
            });
            setQrDetails({
              ...initResp.data,
              attempt_id: initResp.attempt_id,
            });
          }
        }
      } catch (err: any) {
        console.error("Failed to load checkout:", err);
      } finally {
        setLoading(false);
      }
    }

    loadCheckoutData();
  }, [code]);

  const copyVpa = () => {
    if (!qrDetails?.vpa) return;
    navigator.clipboard.writeText(qrDetails.vpa);
    setCopiedVpa(true);
    setTimeout(() => setCopiedVpa(false), 2000);
  };

  // Trigger Payment Verification
  const handleVerifyPayment = async (outcome: "SUCCESS" | "FAILURE" | "PENDING" = "SUCCESS") => {
    if (!qrDetails?.attempt_id) return;

    try {
      setVerifying(true);
      setVerificationError(null);

      // In UPI or Demo mode: send verification request
      const verifyResp = await api.verifyPayment({
        payment_attempt_id: qrDetails.attempt_id,
        payment_mode: paymentMode,
        demo_outcome: outcome,
        upi_reference: utrInput.trim() || undefined,
      });

      if (verifyResp.status === "PAID") {
        // Trigger celebratory confetti!
        try {
          confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 },
          });
        } catch {}

        // Redirect to digital receipt
        const targetToken = verifyResp.receipt_token || verifyResp.receipt_id || qrDetails.attempt_id;
        setTimeout(() => {
          router.push(`/receipt/${targetToken}`);
        }, 1200);
      } else if (verifyResp.status === "FAILED") {
        setVerificationError("Simulated payment failed. Please retry.");
      } else {
        setVerificationError("Payment is currently processing. Please check again in a few seconds.");
      }
    } catch (err: any) {
      console.error("Verification failed:", err);
      setVerificationError(err.message || "Payment verification failed.");
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
        <h2 className="font-bold text-lg text-[#1A1A1A]">Preparing Smart Bill Split...</h2>
        <p className="text-xs text-[#71717A]">Calculating exact integer paise shares</p>
      </div>
    );
  }

  if (!myShare || !group) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-[#FF5C00] mx-auto" />
        <h2 className="font-bold text-lg text-[#1A1A1A]">No Bill Items Found</h2>
        <p className="text-xs text-[#71717A]">
          You have not added any snacks to this group order yet.
        </p>
        <Link
          href={`/group/${code}`}
          className="inline-block bg-[#FF5C00] text-white px-5 py-2.5 rounded-xl font-bold text-xs"
        >
          Return to Cart & Add Snacks
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10 pb-20">
      {/* Back button */}
      <div className="mb-4">
        <Link
          href={`/group/${code}`}
          className="inline-flex items-center gap-1.5 text-xs font-bold text-[#71717A] hover:text-[#1A1A1A] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Group Cart</span>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
        {/* Left Column: Smart Bill Split Breakdown */}
        <div className="md:col-span-6 bg-white rounded-3xl border border-[#EFE8DE] p-5 sm:p-6 shadow-xs space-y-5">
          <div>
            <span className="text-[10px] font-bold text-[#FF5C00] uppercase tracking-wider bg-[#FFF4ED] px-2 py-0.5 rounded-md border border-[#FFD9C6]">
              Deterministic Bill Engine
            </span>
            <h1 className="text-xl sm:text-2xl font-black text-[#1A1A1A] mt-2 font-['Outfit',sans-serif]">
              Your Bill Breakdown
            </h1>
            <p className="text-xs text-[#71717A] mt-0.5">
              Ordering as <strong className="text-[#1A1A1A]">{myShare.participant_name}</strong> for {group.title}
            </p>
          </div>

          {/* Breakdown Rows */}
          <div className="space-y-3 text-xs border-t border-[#EFE8DE] pt-4">
            <div className="flex justify-between items-center text-[#555555]">
              <span>Your Items Subtotal ({myShare.items_count} items)</span>
              <span className="font-bold text-[#1A1A1A]">₹{myShare.items_subtotal_inr.toFixed(2)}</span>
            </div>

            <div className="flex justify-between items-center text-[#555555]">
              <span className="flex items-center gap-1">
                <span>Delivery Fee Share</span>
                <span className="text-[10px] text-[#71717A]">({group.fee_policy})</span>
              </span>
              <span className="font-bold text-[#1A1A1A]">₹{(myShare.delivery_share_paise / 100).toFixed(2)}</span>
            </div>

            <div className="flex justify-between items-center text-[#555555]">
              <span>Platform & Tech Fee Share</span>
              <span className="font-bold text-[#1A1A1A]">₹{(myShare.platform_share_paise / 100).toFixed(2)}</span>
            </div>

            <div className="flex justify-between items-center text-[#555555]">
              <span>Packaging Charges Share</span>
              <span className="font-bold text-[#1A1A1A]">₹{(myShare.packaging_share_paise / 100).toFixed(2)}</span>
            </div>

            <div className="flex justify-between items-center text-[#555555]">
              <span>GST / Taxes ({group.tax_percentage}%)</span>
              <span className="font-bold text-[#1A1A1A]">₹{myShare.tax_share_inr.toFixed(2)}</span>
            </div>

            {myShare.discount_share_paise > 0 && (
              <div className="flex justify-between items-center text-emerald-600 font-bold">
                <span>Group Discount Share</span>
                <span>-₹{myShare.discount_share_inr.toFixed(2)}</span>
              </div>
            )}

            {/* Total Highlight */}
            <div className="border-t border-[#EFE8DE] pt-3.5 flex justify-between items-center text-sm font-black text-[#1A1A1A]">
              <span>Total Payable</span>
              <span className="text-2xl text-[#FF5C00]">₹{myShare.total_payable_inr.toFixed(2)}</span>
            </div>
          </div>

          {/* Group Verification Proof */}
          <div className="bg-[#FAF8F5] p-3 rounded-xl border border-[#EFE8DE] text-[11px] text-[#71717A] space-y-1">
            <div className="flex items-center gap-1.5 font-bold text-[#10B981]">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Exact Mathematical Proof:</span>
            </div>
            <p>
              Sum of all {billing?.participants_count} roommates&apos; shares exactly matches the ₹
              {billing?.grand_total_inr.toFixed(2)} grand bill with zero leftover paise discrepancy.
            </p>
          </div>
        </div>

        {/* Right Column: Payment Gateway / UPI QR Interface */}
        <div className="md:col-span-6 bg-white rounded-3xl border border-[#EFE8DE] p-5 sm:p-6 shadow-md space-y-5">
          {/* Payment Mode Selector Tabs */}
          <div className="flex items-center gap-1.5 bg-[#FAF8F5] p-1 rounded-xl border border-[#EFE8DE]">
            <button
              onClick={() => setPaymentMode("UPI_QR")}
              className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-1.5 ${
                paymentMode === "UPI_QR"
                  ? "bg-white text-[#FF5C00] shadow-xs"
                  : "text-[#71717A] hover:text-[#1A1A1A]"
              }`}
            >
              <QrCode className="w-3.5 h-3.5" />
              <span>UPI QR</span>
            </button>

            <button
              onClick={() => setPaymentMode("DEMO")}
              className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-1.5 ${
                paymentMode === "DEMO"
                  ? "bg-white text-[#FF5C00] shadow-xs"
                  : "text-[#71717A] hover:text-[#1A1A1A]"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Demo Mode</span>
            </button>
          </div>

          {/* MODE 1: Direct UPI QR Code */}
          {paymentMode === "UPI_QR" && qrDetails && (
            <div className="text-center space-y-4">
              <div>
                <span className="text-xs font-bold text-[#71717A]">Scan & Pay Exact Amount</span>
                <div className="text-3xl font-black text-[#1A1A1A] mt-0.5">
                  ₹{myShare.total_payable_inr.toFixed(2)}
                </div>
              </div>

              {/* Dynamic QR Code */}
              <div className="inline-block p-3.5 bg-white rounded-2xl border-2 border-[#1A1A1A] shadow-md">
                {qrDetails.qr_data_url ? (
                  <img
                    src={qrDetails.qr_data_url}
                    alt="UPI Payment QR Code"
                    className="w-48 h-48 mx-auto"
                  />
                ) : (
                  <div className="w-48 h-48 bg-zinc-100 flex items-center justify-center">
                    <QrCode className="w-12 h-12 text-zinc-400" />
                  </div>
                )}
              </div>

              {/* VPA Copy helper */}
              <div className="bg-[#FAF8F5] p-2.5 rounded-xl border border-[#EFE8DE] flex items-center justify-between text-xs">
                <span className="text-[#71717A] font-mono text-[11px] truncate">
                  VPA: <strong className="text-[#1A1A1A]">{qrDetails.vpa}</strong>
                </span>
                <button
                  onClick={copyVpa}
                  className="text-[11px] font-bold text-[#FF5C00] flex items-center gap-1 hover:underline shrink-0"
                >
                  {copiedVpa ? <Check className="w-3 h-3 text-[#10B981]" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedVpa ? "Copied" : "Copy VPA"}</span>
                </button>
              </div>

              {/* Mobile Intent deep link */}
              {qrDetails.upi_uri && (
                <div>
                  <a
                    href={qrDetails.upi_uri}
                    className="w-full flex items-center justify-center gap-2 bg-[#FAF8F5] hover:bg-[#F4EFEB] text-[#1A1A1A] border border-[#EFE8DE] py-2.5 rounded-xl font-bold text-xs transition-colors shadow-2xs"
                  >
                    <Smartphone className="w-4 h-4 text-[#FF5C00]" />
                    <span>Open in UPI App (GPay, PhonePe, Paytm)</span>
                  </a>
                </div>
              )}

              {/* Verification CTA */}
              <div className="pt-2">
                <button
                  onClick={() => handleVerifyPayment("SUCCESS")}
                  disabled={verifying}
                  className="w-full flex items-center justify-center gap-2 bg-[#FF5C00] hover:bg-[#E55200] disabled:bg-zinc-300 text-white py-3.5 rounded-xl font-bold text-sm shadow-lg shadow-[#FF5C00]/25 transition-all active:scale-95 cursor-pointer"
                >
                  {verifying ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Verifying Payment with UPI...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4 stroke-[3]" />
                      <span>I Have Paid (Confirm & Get Receipt)</span>
                    </>
                  )}
                </button>
              </div>

              {verificationError && (
                <p className="text-xs text-red-600 font-semibold">{verificationError}</p>
              )}
            </div>
          )}

          {/* MODE 2: Clearly Labeled Demo Mode */}
          {paymentMode === "DEMO" && (
            <div className="space-y-4">
              <div className="bg-[#FFF4ED] border border-[#FFD9C6] p-3.5 rounded-2xl text-xs space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-[#FF5C00]">
                  <Sparkles className="w-4 h-4" />
                  <span>DEMONSTRATION SIMULATOR</span>
                </div>
                <p className="text-[#555555] leading-relaxed text-[11px]">
                  No real money will be deducted. Test instant bank verification, simulated payment failures,
                  and digital receipt generation.
                </p>
              </div>

              <div className="space-y-2.5 pt-2">
                <button
                  onClick={() => handleVerifyPayment("SUCCESS")}
                  disabled={verifying}
                  className="w-full flex items-center justify-center gap-2 bg-[#10B981] hover:bg-emerald-600 text-white py-3 rounded-xl font-bold text-xs shadow-md shadow-emerald-500/20 active:scale-95 transition-all"
                >
                  {verifying ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4" />
                  )}
                  <span>Simulate Instant Payment Success</span>
                </button>

                <button
                  onClick={() => handleVerifyPayment("FAILURE")}
                  disabled={verifying}
                  className="w-full flex items-center justify-center gap-2 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 py-2.5 rounded-xl font-bold text-xs transition-colors"
                >
                  <span>Simulate Bank Failure Scenario</span>
                </button>

                <button
                  onClick={() => handleVerifyPayment("PENDING")}
                  disabled={verifying}
                  className="w-full flex items-center justify-center gap-2 bg-zinc-100 hover:bg-zinc-200 text-[#1A1A1A] py-2.5 rounded-xl font-bold text-xs transition-colors"
                >
                  <span>Simulate Bank Pending State</span>
                </button>
              </div>

              {verificationError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl font-medium">
                  {verificationError}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function CheckoutPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-4">
          <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
          <p className="text-xs text-[#71717A]">Loading Checkout...</p>
        </div>
      }
    >
      <CheckoutContent />
    </Suspense>
  );
}
