"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Users,
  Clock,
  Share2,
  Copy,
  Check,
  Lock,
  Unlock,
  ShieldCheck,
  Plus,
  Minus,
  Trash2,
  ArrowRight,
  Sparkles,
  ShoppingBag,
  CreditCard,
  Layers,
  Search,
  ExternalLink,
  AlertCircle,
  RefreshCw,
  MessageCircle,
} from "lucide-react";
import {
  api,
  GroupDetail,
  CombinedCart,
  Product,
  ProductCategory,
  CartItem,
  getStoredGuestSession,
  saveStoredGuestSession,
  saveRecentGroup,
} from "@/lib/api";

function GroupCartContent() {
  const params = useParams();
  const router = useRouter();
  const code = (params?.code as string)?.toUpperCase();

  // State
  const [group, setGroup] = useState<GroupDetail | null>(null);
  const [cart, setCart] = useState<CombinedCart | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"menu" | "cart">("cart");
  const [loading, setLoading] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);
  const [timeLeft, setTimeLeft] = useState<string>("");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Current participant session
  const [currentParticipantId, setCurrentParticipantId] = useState<string | null>(null);
  const [currentDisplayName, setCurrentDisplayName] = useState<string>("");
  const [isHost, setIsHost] = useState<boolean>(false);

  // WebSocket reference
  const wsRef = useRef<WebSocket | null>(null);

  // Show Toast
  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // 1. Fetch group details and products
  const refreshCartData = async (groupId: string) => {
    try {
      const [cData, gData] = await Promise.all([
        api.getCombinedCart(groupId),
        api.getGroup(groupId),
      ]);
      setCart(cData);
      setGroup(gData);
    } catch (e) {
      console.error("Cart refresh failed:", e);
    }
  };

  useEffect(() => {
    if (!code) return;

    async function init() {
      try {
        setLoading(true);
        const groupData = await api.getGroup(code);
        setGroup(groupData);
        saveRecentGroup({
          code: groupData.invite_code,
          title: groupData.title,
          location: groupData.delivery_location,
          status: groupData.cart_status,
        });

        // Check if user has participant record
        const stored = getStoredGuestSession();
        const [cartData, prodsResp, catsResp, participants] = await Promise.all([
          api.getCombinedCart(groupData.id),
          api.getProducts(),
          api.getCategories(),
          api.getParticipants(groupData.id),
        ]);

        let myPart = participants.find((p) => p.id === stored?.id || p.display_name === stored?.display_name);

        if (!myPart && stored?.display_name && groupData.host_name === stored.display_name) {
          myPart = participants.find((p) => p.is_host);
        }

        if (myPart) {
          setCurrentParticipantId(myPart.id);
          setCurrentDisplayName(myPart.display_name);
          setIsHost(myPart.is_host);
        } else if (participants.length > 0 && !stored?.id) {
          router.push(`/join?code=${code}`);
          return;
        }

        setCart(cartData);
        setProducts(prodsResp.products || []);
        setCategories(catsResp || []);

        // Initialize WebSocket connection
        const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsHost = process.env.NEXT_PUBLIC_WS_URL || "127.0.0.1:8000/api/v1";
        const wsUrl = `${wsProto}//${wsHost}/ws/${groupData.id}`;

        try {
          const ws = new WebSocket(wsUrl);
          wsRef.current = ws;

          ws.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              if (data.event === "participant_joined") {
                triggerToast(`🎉 ${data.participant.display_name} joined the order!`);
                refreshCartData(groupData.id);
              } else if (data.event === "cart_item_added" || data.event === "cart_item_updated" || data.event === "cart_item_removed") {
                triggerToast(`🛒 Cart updated by ${data.participant_name || "roommate"}`);
                refreshCartData(groupData.id);
              } else if (data.event === "cart_locked") {
                triggerToast("🔒 Cart locked by host for checkout.");
                refreshCartData(groupData.id);
              } else if (data.event === "cart_reopened") {
                triggerToast("🔓 Cart reopened by host.");
                refreshCartData(groupData.id);
              } else if (data.event === "payment_status_changed") {
                triggerToast(`💰 Payment update: ${data.payment_status}`);
                refreshCartData(groupData.id);
              }
            } catch (err) {
              console.error("WS error:", err);
            }
          };

          ws.onerror = () => {
            console.log("WebSocket offline, falling back to local updates");
          };
        } catch (e) {
          console.warn("WebSocket connect failed:", e);
        }
      } catch (err: any) {
        console.error("Failed to load group:", err);
      } finally {
        setLoading(false);
      }
    }

    init();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [code]);

  // Countdown timer
  useEffect(() => {
    if (!group?.cart_closing_time) return;

    const interval = setInterval(() => {
      const now = new Date().getTime();
      const closing = new Date(group.cart_closing_time!).getTime();
      const diff = closing - now;

      if (diff <= 0) {
        setTimeLeft("Closed");
      } else {
        const mins = Math.floor(diff / (1000 * 60));
        const secs = Math.floor((diff % (1000 * 60)) / 1000);
        setTimeLeft(`${mins}m ${secs < 10 ? "0" : ""}${secs}s`);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [group?.cart_closing_time]);

  // Actions
  const handleCopyLink = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleWhatsAppInvite = () => {
    if (typeof window === "undefined" || !group) return;
    const shareUrl = window.location.href;
    const msg = `🍜 *MunchMate Group Order: ${group.title}*\nHost: *${group.host_name}* (Room: ${group.delivery_location})\n\nLate night cravings? Add your Maggi, drinks & snacks to our shared cart before it closes:\n👉 ${shareUrl}\n\nGroup Code: *${group.invite_code}*`;
    window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`, "_blank");
  };

  const handleAddItem = async (productId: string) => {
    if (!group) return;

    let partId = currentParticipantId;
    if (!partId) {
      const stored = getStoredGuestSession();
      if (stored?.id) {
        partId = stored.id;
        setCurrentParticipantId(stored.id);
      } else if (group.host_participant_id) {
        partId = group.host_participant_id;
        setCurrentParticipantId(partId);
      }
    }

    if (!partId) {
      triggerToast("Please join the group order to add your items!");
      router.push(`/join?code=${code}`);
      return;
    }

    if (group.cart_status !== "OPEN") {
      triggerToast("Cart is locked. No items can be added.");
      return;
    }

    try {
      await api.addItemToCart(group.id, partId, {
        product_id: productId,
        quantity: 1,
      });
      triggerToast("Item added to cart!");
      refreshCartData(group.id);
    } catch (err: any) {
      triggerToast(err.message || "Failed to add item");
    }
  };

  const handleUpdateItemQty = async (itemId: string, newQty: number) => {
    if (!group) return;
    try {
      if (newQty <= 0) {
        await api.deleteCartItem(group.id, itemId);
      } else {
        await api.updateCartItem(group.id, itemId, { quantity: newQty });
      }
      refreshCartData(group.id);
    } catch (err: any) {
      triggerToast(err.message || "Failed to update item");
    }
  };

  const handleToggleLock = async () => {
    if (!group) return;
    try {
      if (group.cart_status === "OPEN") {
        await api.lockCart(group.id);
        triggerToast("Cart locked!");
      } else {
        await api.reopenCart(group.id);
        triggerToast("Cart reopened!");
      }
      refreshCartData(group.id);
    } catch (err: any) {
      triggerToast(err.message || "Action failed");
    }
  };

  // Find current user's items in cart
  const myParticipantCart = cart?.participants.find((p) => p.participant_id === currentParticipantId);
  const mySubtotalInr = myParticipantCart ? myParticipantCart.items_subtotal_inr : 0;
  const myItemsCount = myParticipantCart ? myParticipantCart.items_count : 0;

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
        <h2 className="font-bold text-lg text-[#1A1A1A]">Loading Group Order...</h2>
        <p className="text-xs text-[#71717A]">Syncing collaborative cart with roommates</p>
      </div>
    );
  }

  if (!group) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-[#FF5C00] mx-auto" />
        <h2 className="font-bold text-xl text-[#1A1A1A]">Group Order Not Found</h2>
        <p className="text-xs text-[#71717A]">
          The group code &quot;{code}&quot; does not exist or may have expired.
        </p>
        <Link
          href="/create"
          className="inline-block bg-[#FF5C00] text-white px-6 py-2.5 rounded-xl font-bold text-xs shadow-md"
        >
          Create New Group
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 pb-28">
      {/* Toast Notification Container */}
      {toastMessage && (
        <div className="fixed top-20 right-4 z-50 bg-[#1A1A1A] text-white text-xs font-bold px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2 border border-zinc-700 animate-in fade-in slide-in-from-top-2">
          <Sparkles className="w-4 h-4 text-[#FF5C00]" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Group Header Card */}
      <div className="bg-white rounded-3xl border border-[#EFE8DE] p-5 sm:p-6 shadow-xs mb-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span className="font-mono font-black text-xs text-[#FF5C00] bg-[#FFF4ED] px-2.5 py-0.5 rounded-lg border border-[#FFD9C6]">
                Code: {group.invite_code}
              </span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider ${
                  group.cart_status === "OPEN"
                    ? "bg-[#ECFDF5] text-[#10B981] border border-emerald-200"
                    : "bg-amber-50 text-amber-700 border border-amber-200"
                }`}
              >
                ● {group.cart_status}
              </span>
              {timeLeft && (
                <span className="text-[11px] font-bold text-[#71717A] flex items-center gap-1 bg-[#FAF8F5] px-2 py-0.5 rounded-md border border-[#EFE8DE]">
                  <Clock className="w-3 h-3 text-[#FF5C00]" />
                  <span>Closing: {timeLeft}</span>
                </span>
              )}
            </div>

            <h1 className="text-xl sm:text-2xl font-black text-[#1A1A1A] font-['Outfit',sans-serif]">
              {group.title}
            </h1>
            <p className="text-xs text-[#71717A] mt-0.5">
              Host: <strong className="text-[#1A1A1A]">{group.host_name}</strong> • Delivering to:{" "}
              <strong className="text-[#1A1A1A]">{group.delivery_location}</strong>
            </p>
          </div>

          {/* Quick Actions (Share, Host Dashboard, Lock) */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleCopyLink}
              className="flex items-center gap-1.5 bg-[#FAF8F5] hover:bg-white text-[#1A1A1A] border border-[#EFE8DE] px-3 py-2 rounded-xl text-xs font-bold transition-colors shadow-xs cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-[#10B981]" /> : <Copy className="w-3.5 h-3.5 text-[#FF5C00]" />}
              <span>{copied ? "Copied" : "Copy Link"}</span>
            </button>

            <button
              onClick={handleWhatsAppInvite}
              className="flex items-center gap-1.5 bg-[#25D366] hover:bg-[#20BD5A] text-white px-3 py-2 rounded-xl text-xs font-bold transition-colors shadow-sm shadow-[#25D366]/20 cursor-pointer"
            >
              <MessageCircle className="w-3.5 h-3.5" />
              <span>Invite via WhatsApp</span>
            </button>

            {/* Host Dashboard Link */}
            <Link
              href={`/group/${group.invite_code}/dashboard`}
              className="flex items-center gap-1.5 bg-[#FFF4ED] hover:bg-[#FFE8DC] text-[#FF5C00] border border-[#FFD9C6] px-3.5 py-2 rounded-xl text-xs font-bold transition-colors shadow-xs"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Host Dashboard</span>
            </Link>

            {/* Lock / Reopen Cart Toggle (for Host) */}
            {isHost && (
              <button
                onClick={handleToggleLock}
                className="flex items-center gap-1.5 bg-zinc-100 hover:bg-zinc-200 text-[#1A1A1A] px-3 py-2 rounded-xl text-xs font-bold transition-colors"
              >
                {group.cart_status === "OPEN" ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
                <span>{group.cart_status === "OPEN" ? "Lock Cart" : "Reopen"}</span>
              </button>
            )}
          </div>
        </div>

        {/* Roommates Avatar Bar */}
        <div className="border-t border-[#EFE8DE] pt-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#71717A] text-[11px] uppercase tracking-wider">Roommates in Pool:</span>
            <div className="flex items-center -space-x-1.5">
              {cart?.participants.map((p) => (
                <div
                  key={p.participant_id}
                  title={`${p.participant_name} (${p.payment_status})`}
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-black text-white ring-2 ring-white shadow-xs cursor-help ${
                    p.payment_status === "PAID" ? "ring-emerald-400" : ""
                  }`}
                  style={{ backgroundColor: p.avatar_color || "#FF5C00" }}
                >
                  {p.participant_name.charAt(0).toUpperCase()}
                </div>
              ))}
            </div>
            <span className="text-[11px] text-[#71717A]">
              ({cart?.participants.length || 1} participant{cart?.participants.length === 1 ? "" : "s"})
            </span>
          </div>

          <div className="flex items-center gap-3 text-[11px]">
            <span className="text-[#71717A]">
              Total Cart Items: <strong className="text-[#1A1A1A]">{cart?.total_items_count || 0}</strong>
            </span>
            <span className="text-[#71717A]">
              Group Subtotal: <strong className="text-[#FF5C00]">₹{(cart?.items_subtotal_inr || 0).toFixed(0)}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Cart Locked Alert Banner if locked */}
      {group.cart_status === "LOCKED" && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl flex items-center justify-between text-xs sm:text-sm font-semibold">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-amber-700 shrink-0" />
            <span>The host has locked the cart for checkout. You can now split the bill and pay your share.</span>
          </div>
          <Link
            href={`/group/${group.invite_code}/checkout`}
            className="bg-amber-800 hover:bg-amber-900 text-white text-xs font-bold px-3 py-1.5 rounded-lg whitespace-nowrap ml-2"
          >
            Go to Checkout →
          </Link>
        </div>
      )}

      {/* Navigation Tabs (Menu vs Group Cart) */}
      <div className="flex items-center gap-2 mb-6 border-b border-[#EFE8DE] pb-3">
        <button
          onClick={() => setActiveTab("cart")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === "cart"
              ? "bg-[#1A1A1A] text-white shadow-sm"
              : "bg-white text-[#71717A] hover:text-[#1A1A1A] border border-[#EFE8DE]"
          }`}
        >
          <ShoppingBag className="w-4 h-4" />
          <span>Shared Group Cart ({cart?.total_items_count || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab("menu")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === "menu"
              ? "bg-[#1A1A1A] text-white shadow-sm"
              : "bg-white text-[#71717A] hover:text-[#1A1A1A] border border-[#EFE8DE]"
          }`}
        >
          <Plus className="w-4 h-4" />
          <span>Add More Snacks</span>
        </button>
      </div>

      {/* TAB CONTENT 1: Shared Group Cart */}
      {activeTab === "cart" && (
        <div className="space-y-6">
          {cart?.participants.length === 0 || cart?.total_items_count === 0 ? (
            <div className="bg-white rounded-3xl border border-[#EFE8DE] p-12 text-center max-w-md mx-auto space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-[#FFF4ED] text-[#FF5C00] flex items-center justify-center mx-auto">
                <ShoppingBag className="w-7 h-7" />
              </div>
              <h3 className="font-extrabold text-lg text-[#1A1A1A]">The cart is currently empty</h3>
              <p className="text-xs text-[#71717A] leading-relaxed">
                Be the first to add midnight snacks! Click &quot;Add More Snacks&quot; above to pick Maggi, Red Bull, chips, or cookies.
              </p>
              <button
                onClick={() => setActiveTab("menu")}
                className="bg-[#FF5C00] text-white text-xs font-bold px-6 py-2.5 rounded-xl shadow-md"
              >
                Browse Snack Menu
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {cart?.participants.map((participant) => {
                const isMe = participant.participant_id === currentParticipantId;

                return (
                  <div
                    key={participant.participant_id}
                    className={`bg-white rounded-3xl border p-5 shadow-xs transition-all ${
                      isMe ? "border-[#FF5C00]/40 ring-1 ring-[#FF5C00]/20 bg-gradient-to-b from-white to-[#FFFDFB]" : "border-[#EFE8DE]"
                    }`}
                  >
                    {/* Participant Header */}
                    <div className="flex items-center justify-between border-b border-[#EFE8DE] pb-3 mb-3">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-black text-white shadow-xs"
                          style={{ backgroundColor: participant.avatar_color || "#FF5C00" }}
                        >
                          {participant.participant_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="font-extrabold text-sm text-[#1A1A1A]">
                              {participant.participant_name}
                            </span>
                            {isMe && (
                              <span className="bg-[#FFF4ED] text-[#FF5C00] border border-[#FFD9C6] text-[9px] font-bold px-1.5 py-0.5 rounded-md">
                                You
                              </span>
                            )}
                            {participant.is_host && (
                              <span className="bg-zinc-100 text-[#71717A] text-[9px] font-bold px-1.5 py-0.5 rounded-md">
                                Host
                              </span>
                            )}
                          </div>
                          <span className="text-[11px] text-[#71717A]">
                            {participant.items_count} item{participant.items_count === 1 ? "" : "s"}
                          </span>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className="text-xs font-black text-[#1A1A1A] block">
                          ₹{participant.items_subtotal_inr.toFixed(0)}
                        </span>
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                            participant.payment_status === "PAID"
                              ? "bg-[#ECFDF5] text-[#10B981]"
                              : "bg-[#FFF4ED] text-[#FF5C00]"
                          }`}
                        >
                          {participant.payment_status}
                        </span>
                      </div>
                    </div>

                    {/* Participant's Items List */}
                    {participant.items.length === 0 ? (
                      <p className="text-xs text-[#71717A] italic py-2">
                        Hasn&apos;t added any items yet.
                      </p>
                    ) : (
                      <div className="space-y-2.5">
                        {participant.items.map((it) => (
                          <div
                            key={it.id}
                            className="flex items-center justify-between gap-3 bg-[#FAF8F5] p-2.5 rounded-2xl border border-[#EFE8DE]"
                          >
                            <div className="flex items-center gap-2.5">
                              <img
                                src={it.product.image_url}
                                alt={it.product.name}
                                className="w-10 h-10 rounded-xl object-cover"
                              />
                              <div>
                                <span className="font-bold text-xs text-[#1A1A1A] block line-clamp-1">
                                  {it.product.name}
                                </span>
                                <span className="text-[10px] text-[#71717A]">
                                  ₹{it.unit_price_inr} × {it.quantity}
                                </span>
                              </div>
                            </div>

                            <div className="flex items-center gap-3">
                              <span className="text-xs font-extrabold text-[#1A1A1A]">
                                ₹{it.item_subtotal_inr}
                              </span>

                              {/* Controls for item owner */}
                              {(isMe || isHost) && group.cart_status === "OPEN" && (
                                <div className="flex items-center gap-1 bg-white border border-[#EFE8DE] rounded-lg p-0.5 shadow-2xs">
                                  <button
                                    onClick={() => handleUpdateItemQty(it.id, it.quantity - 1)}
                                    className="w-5 h-5 rounded hover:bg-[#FAF8F5] flex items-center justify-center text-[#71717A] hover:text-[#1A1A1A]"
                                  >
                                    <Minus className="w-3 h-3" />
                                  </button>
                                  <span className="text-xs font-bold px-1 min-w-[14px] text-center">
                                    {it.quantity}
                                  </span>
                                  <button
                                    onClick={() => handleUpdateItemQty(it.id, it.quantity + 1)}
                                    className="w-5 h-5 rounded hover:bg-[#FAF8F5] flex items-center justify-center text-[#71717A] hover:text-[#1A1A1A]"
                                  >
                                    <Plus className="w-3 h-3" />
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT 2: In-Context Menu Picker */}
      {activeTab === "menu" && (
        <div className="space-y-4">
          {/* Quick search and category filter */}
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 text-[#71717A] absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search food items to add to this group cart..."
                className="w-full pl-10 pr-4 py-2 text-xs rounded-xl border border-[#EFE8DE] bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30"
              />
            </div>

            {/* Category Dropdown */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-2 rounded-xl text-xs font-semibold bg-white border border-[#EFE8DE] text-[#1A1A1A]"
            >
              <option value="all">All Categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Menu items */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {products
              .filter((p) => {
                if (selectedCategory !== "all" && p.category_id !== selectedCategory) return false;
                if (searchQuery.trim() && !p.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
                return true;
              })
              .map((p) => (
                <div
                  key={p.id}
                  className="bg-white rounded-2xl border border-[#EFE8DE] hover:border-[#FFD9C6] p-3 flex flex-col justify-between shadow-2xs group"
                >
                  <div className="relative h-28 w-full bg-[#FAF8F5] rounded-xl overflow-hidden mb-2">
                    <img
                      src={p.image_url}
                      alt={p.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                    <div className="absolute top-1.5 left-1.5">
                      <span className={`w-2 h-2 rounded-full inline-block ${p.is_veg ? "bg-emerald-500" : "bg-red-500"}`} />
                    </div>
                  </div>

                  <div>
                    <h4 className="font-extrabold text-xs text-[#1A1A1A] line-clamp-1 mb-0.5">
                      {p.name}
                    </h4>
                    <span className="text-[11px] font-black text-[#FF5C00] block mb-2">
                      ₹{p.price_inr.toFixed(0)}
                    </span>
                  </div>

                  <button
                    type="button"
                    id={`btn-add-${p.id}`}
                    data-testid={`add-to-cart-${p.id}`}
                    onClick={() => handleAddItem(p.id)}
                    disabled={group.cart_status !== "OPEN"}
                    className="w-full bg-[#FFF4ED] hover:bg-[#FF5C00] text-[#FF5C00] hover:text-white border border-[#FFD9C6] hover:border-[#FF5C00] py-1.5 rounded-xl text-xs font-bold transition-colors flex items-center justify-center gap-1 active:scale-95 disabled:opacity-50 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add to My Cart</span>
                  </button>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Sticky Bottom Action Bar */}
      <div className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-[#EFE8DE] p-3.5 shadow-xl">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
          <div>
            <span className="text-[10px] text-[#71717A] font-bold uppercase tracking-wider block">
              Your Share ({myItemsCount} items)
            </span>
            <div className="flex items-center gap-1.5">
              <span className="text-base sm:text-lg font-black text-[#1A1A1A]">
                ₹{mySubtotalInr.toFixed(0)}
              </span>
              <span className="text-[10px] text-[#71717A]">+ delivery & fees share</span>
            </div>
          </div>

          <Link
            href={`/group/${group.invite_code}/checkout`}
            className="flex items-center gap-2 bg-[#FF5C00] hover:bg-[#E55200] text-white px-5 sm:px-6 py-2.5 sm:py-3 rounded-xl font-bold text-xs sm:text-sm shadow-lg shadow-[#FF5C00]/25 transition-transform active:scale-95"
          >
            <CreditCard className="w-4 h-4" />
            <span>Proceed to Split & Pay</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function GroupCartPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-4">
          <div className="w-12 h-12 rounded-full border-4 border-[#FF5C00] border-t-transparent animate-spin mx-auto" />
          <h2 className="font-bold text-lg text-[#1A1A1A]">Loading Group Order...</h2>
          <p className="text-xs text-[#71717A]">Syncing collaborative cart with roommates</p>
        </div>
      }
    >
      <GroupCartContent />
    </Suspense>
  );
}
