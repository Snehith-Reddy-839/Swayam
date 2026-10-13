/**
 * MunchMate API Client
 * Connects frontend to FastAPI backend, with localStorage session persistence
 * and resilient fallbacks.
 */

function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    return `${protocol}//${hostname}:8000/api/v1`;
  }
  return "http://localhost:8000/api/v1";
}

// Helper for local storage guest session
const GUEST_STORAGE_KEY = "munchmate_guest_session";

export interface GuestSession {
  id: string;
  session_token: string;
  display_name: string;
  avatar_color: string;
}

export function getStoredGuestSession(): GuestSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(GUEST_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveStoredGuestSession(session: GuestSession) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(session));
  } catch (e) {
    console.error("Failed to store guest session:", e);
  }
}

// Helper for recently viewed / joined / created groups
const RECENT_GROUPS_KEY = "munchmate_recent_groups";

export interface RecentGroupItem {
  code: string;
  title: string;
  location: string;
  status: string;
  items?: number;
}

export function getRecentGroups(): RecentGroupItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(RECENT_GROUPS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveRecentGroup(group: RecentGroupItem) {
  if (typeof window === "undefined" || !group.code) return;
  try {
    const existing = getRecentGroups().filter((g) => g.code.toUpperCase() !== group.code.toUpperCase());
    const updated = [group, ...existing].slice(0, 8);
    localStorage.setItem(RECENT_GROUPS_KEY, JSON.stringify(updated));
  } catch (e) {
    console.warn("Failed to store recent group:", e);
  }
}

export interface ProductCategory {
  id: string;
  name: string;
  slug: string;
  icon: string;
  display_order: number;
}

export interface Product {
  id: string;
  category_id: string;
  name: string;
  description?: string;
  price_paise: number;
  price_inr: number;
  image_url: string;
  is_available: boolean;
  is_veg: boolean;
  unit: string;
  popularity_score: number;
}

export interface GroupDetail {
  id: string;
  invite_code: string;
  title: string;
  host_name: string;
  store_mode: string;
  delivery_location: string;
  cart_closing_time?: string;
  participant_limit: number;
  cart_status: "OPEN" | "LOCKED" | "READY_FOR_CHECKOUT" | "FINALIZED" | "CANCELLED";
  fee_policy: "EQUAL_SPLIT" | "PROPORTIONAL" | "HOST_COVERS" | "CUSTOM";
  delivery_fee_paise: number;
  platform_fee_paise: number;
  packaging_fee_paise: number;
  discount_paise: number;
  tax_percentage: number;
  is_payment_required_before_finalize: boolean;
  host_approval_required: boolean;
  allow_participant_edit: boolean;
  has_passcode: boolean;
  created_at: string;
  participants_count: number;
  share_url: string;
  host_participant_id?: string;
  host_session_token?: string;
}

export interface GroupParticipant {
  id: string;
  display_name: string;
  avatar_color: string;
  is_host: boolean;
  payment_status: "PENDING" | "PROCESSING" | "PAID" | "FAILED" | "CANCELLED";
  amount_paid_paise: number;
  amount_paid_inr: number;
  joined_at: string;
  session_token?: string;
}

export interface CartItem {
  id: string;
  group_order_id: string;
  participant_id: string;
  participant_name: string;
  product_id: string;
  product: Product;
  quantity: number;
  unit_price_paise: number;
  unit_price_inr: number;
  item_subtotal_paise: number;
  item_subtotal_inr: number;
  item_notes?: string;
}

export interface ParticipantCart {
  participant_id: string;
  participant_name: string;
  avatar_color: string;
  is_host: boolean;
  payment_status: string;
  items: CartItem[];
  items_count: number;
  items_subtotal_paise: number;
  items_subtotal_inr: number;
}

export interface CombinedCart {
  group_id: string;
  group_title: string;
  cart_status: string;
  total_items_count: number;
  total_unique_products_count: number;
  items_subtotal_paise: number;
  items_subtotal_inr: number;
  participants: ParticipantCart[];
}

export interface ParticipantBillShare {
  participant_id: string;
  participant_name: string;
  avatar_color: string;
  is_host: boolean;
  payment_status: string;
  items_count: number;
  items_subtotal_paise: number;
  items_subtotal_inr: number;
  delivery_share_paise: number;
  platform_share_paise: number;
  packaging_share_paise: number;
  shared_fees_total_paise: number;
  shared_fees_total_inr: number;
  tax_share_paise: number;
  tax_share_inr: number;
  discount_share_paise: number;
  discount_share_inr: number;
  rounding_adjustment_paise: number;
  total_payable_paise: number;
  total_payable_inr: number;
  amount_paid_paise: number;
  amount_paid_inr: number;
  outstanding_paise: number;
  outstanding_inr: number;
}

export interface BillCalculation {
  group_id: string;
  fee_policy: string;
  participants_count: number;
  total_items_subtotal_paise: number;
  total_items_subtotal_inr: number;
  delivery_fee_paise: number;
  delivery_fee_inr: number;
  platform_fee_paise: number;
  platform_fee_inr: number;
  packaging_fee_paise: number;
  packaging_fee_inr: number;
  total_shared_fees_paise: number;
  total_shared_fees_inr: number;
  tax_percentage: number;
  total_tax_paise: number;
  total_tax_inr: number;
  total_discount_paise: number;
  total_discount_inr: number;
  grand_total_paise: number;
  grand_total_inr: number;
  total_paid_paise: number;
  total_paid_inr: number;
  total_outstanding_paise: number;
  total_outstanding_inr: number;
  is_fully_paid: boolean;
  sum_of_participant_shares_paise: number;
  is_deterministic_exact_match: boolean;
  participant_shares: ParticipantBillShare[];
}

export interface ReceiptItemLine {
  product_name: string;
  quantity: number;
  unit_price_paise: number;
  unit_price_inr: number;
  total_price_paise: number;
  total_price_inr: number;
  item_notes?: string;
}

export interface Receipt {
  id: string;
  receipt_number: string;
  group_order_id: string;
  group_title: string;
  delivery_location: string;
  participant_id: string;
  participant_name: string;
  access_token: string;
  items: ReceiptItemLine[];
  items_subtotal_paise: number;
  items_subtotal_inr: number;
  shared_fees_paise: number;
  shared_fees_inr: number;
  tax_paise: number;
  tax_inr: number;
  discount_paise: number;
  discount_inr: number;
  total_paid_paise: number;
  total_paid_inr: number;
  payment_method: string;
  transaction_ref: string;
  issued_at: string;
  merchant_order_status: string;
}

export interface FinalCombinedProductGroup {
  product_id: string;
  product_name: string;
  category_name: string;
  unit: string;
  total_quantity: number;
  unit_price_paise: number;
  unit_price_inr: number;
  total_price_paise: number;
  total_price_inr: number;
  ordered_by: string[];
}

export interface FinalCombinedOrderSummary {
  group_id: string;
  group_title: string;
  invite_code: string;
  delivery_location: string;
  cart_status: string;
  merchant_order_status: string;
  platform_name?: string;
  external_order_id?: string;
  total_participants: number;
  paid_participants_count: number;
  total_items_count: number;
  grouped_products: FinalCombinedProductGroup[];
  items_subtotal_paise: number;
  items_subtotal_inr: number;
  shared_fees_paise: number;
  shared_fees_inr: number;
  tax_paise: number;
  tax_inr: number;
  grand_total_paise: number;
  grand_total_inr: number;
  total_paid_paise: number;
  total_paid_inr: number;
  remaining_unpaid_paise: number;
  remaining_unpaid_inr: number;
  is_fully_paid: boolean;
}

export interface HostDashboardSummary {
  group_id: string;
  group_title: string;
  invite_code: string;
  share_url: string;
  delivery_location: string;
  cart_status: string;
  cart_closing_time?: string;
  participants_count: number;
  paid_count: number;
  unpaid_count: number;
  total_items_count: number;
  grand_total_paise: number;
  grand_total_inr: number;
  total_collected_paise: number;
  total_collected_inr: number;
  outstanding_paise: number;
  outstanding_inr: number;
  payment_completion_pct: number;
  is_ready_to_order: boolean;
  merchant_order_status: string;
  participant_shares: ParticipantBillShare[];
  recent_activities: {
    id: string;
    action: string;
    actor_type: string;
    actor_name: string;
    details?: string;
    created_at: string;
  }[];
}

// ======================== API CALLS ======================== //

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  // Automatically attach stored session token if available
  const stored = getStoredGuestSession();
  if (stored?.session_token && !headers.has("Authorization") && !headers.has("X-Session-Token")) {
    headers.set("Authorization", `Guest ${stored.session_token}`);
    headers.set("X-Session-Token", stored.session_token);
  }

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "Connection refused";
    // If connection to localhost failed, attempt 127.0.0.1 fallback (or vice-versa)
    let fallbackUrl: string | null = null;
    if (url.includes("localhost:8000")) {
      fallbackUrl = url.replace("localhost:8000", "127.0.0.1:8000");
    } else if (url.includes("127.0.0.1:8000")) {
      fallbackUrl = url.replace("127.0.0.1:8000", "localhost:8000");
    }

    if (fallbackUrl) {
      try {
        res = await fetch(fallbackUrl, {
          ...options,
          headers,
        });
      } catch {
        throw new Error(`Unable to reach MunchMate API (${errorMsg}). Please verify backend is running on port 8000.`);
      }
    } else {
      throw new Error(`Unable to reach MunchMate API (${errorMsg}). Please verify backend is running on port 8000.`);
    }
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || `Request failed with status ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Products
  getCategories: () => request<ProductCategory[]>("/products/categories"),
  getProducts: (params?: { category_id?: string; q?: string; is_veg?: boolean; sort_by?: string }) => {
    const qry = new URLSearchParams();
    if (params?.category_id) qry.set("category_id", params.category_id);
    if (params?.q) qry.set("q", params.q);
    if (params?.is_veg !== undefined) qry.set("is_veg", String(params.is_veg));
    if (params?.sort_by) qry.set("sort_by", params.sort_by);
    return request<{ categories: ProductCategory[]; products: Product[]; total: number }>(`/products?${qry.toString()}`);
  },

  // Auth & Guest
  createGuestSession: (display_name: string, avatar_color?: string) =>
    request<GuestSession>("/auth/guest-session", {
      method: "POST",
      body: JSON.stringify({ display_name, avatar_color }),
    }),

  // Groups
  createGroup: (payload: {
    title: string;
    store_mode?: string;
    delivery_location: string;
    cart_closing_minutes?: number;
    participant_limit?: number;
    fee_policy?: string;
    host_name?: string;
    guest_session_token?: string;
    passcode?: string;
  }) =>
    request<GroupDetail>("/groups", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getGroup: (codeOrId: string) => request<GroupDetail>(`/groups/${codeOrId}`),

  getParticipants: (groupId: string) => request<GroupParticipant[]>(`/groups/${groupId}/participants`),

  joinGroup: (code: string, payload: { display_name: string; avatar_color?: string; passcode?: string; guest_session_token?: string }) =>
    request<GroupParticipant>(`/groups/${code}/join`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  lockCart: (groupId: string) => request<{ message: string; cart_status: string }>(`/groups/${groupId}/lock`, { method: "POST" }),
  reopenCart: (groupId: string) => request<{ message: string; cart_status: string }>(`/groups/${groupId}/reopen`, { method: "POST" }),

  // Cart
  getCombinedCart: (groupId: string) => request<CombinedCart>(`/groups/${groupId}/cart/combined`),

  addItemToCart: (groupId: string, participantId: string, payload: { product_id: string; quantity: number; item_notes?: string }) =>
    request<CartItem>(`/groups/${groupId}/cart/items?participant_id=${participantId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateCartItem: (groupId: string, itemId: string, payload: { quantity: number; item_notes?: string }) =>
    request<CartItem>(`/groups/${groupId}/cart/items/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteCartItem: (groupId: string, itemId: string) =>
    request<{ message: string }>(`/groups/${groupId}/cart/items/${itemId}`, {
      method: "DELETE",
    }),

  // Billing
  getBilling: (groupId: string) => request<BillCalculation>(`/groups/${groupId}/billing`),

  updateBillingPolicy: (groupId: string, payload: { fee_policy: string; delivery_fee_paise?: number; platform_fee_paise?: number; packaging_fee_paise?: number; discount_paise?: number }) =>
    request<BillCalculation>(`/groups/${groupId}/billing/policy`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Payments
  initiatePayment: (payload: { participant_id: string; payment_mode: "UPI_QR" | "DEMO" | "RAZORPAY"; idempotency_key?: string }) =>
    request<{
      mode: string;
      attempt_id: string;
      amount_paise?: number;
      amount_inr?: number;
      demo_notice?: string;
      data: {
        payment_attempt_id: string;
        upi_uri?: string;
        qr_data_url?: string;
        vpa?: string;
        payee_name?: string;
        amount_paise: number;
        amount_inr: number;
        transaction_ref?: string;
        instructions?: string[];
        key_id?: string;
        razorpay_order_id?: string;
      };
    }>("/payments/initiate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  verifyPayment: (payload: {
    payment_attempt_id: string;
    payment_mode: string;
    participant_id?: string;
    session_token?: string;
    demo_outcome?: "SUCCESS" | "FAILURE" | "PENDING";
    razorpay_order_id?: string;
    razorpay_payment_id?: string;
    razorpay_signature?: string;
    upi_reference?: string;
  }) =>
    request<{
      payment_attempt_id: string;
      participant_id: string;
      status: string;
      payment_mode: string;
      amount_paise: number;
      amount_inr: number;
      receipt_id?: string;
      receipt_token?: string;
      failure_reason?: string;
      is_simulated?: boolean;
      message?: string;
    }>("/payments/verify", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  hostManualConfirmPayment: (payload: {
    participant_id: string;
    host_participant_id: string;
    session_token?: string;
    upi_reference?: string;
    notes?: string;
  }) =>
    request<{
      payment_attempt_id: string;
      participant_id: string;
      status: string;
      amount_paise: number;
      amount_inr: number;
      receipt_id: string;
      receipt_token: string;
      is_simulated?: boolean;
      message?: string;
    }>("/payments/host-manual-confirm", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getPaymentStatus: (attemptId: string) =>
    request<{
      payment_attempt_id: string;
      status: string;
      amount_paise: number;
      amount_inr: number;
      receipt_id?: string;
      receipt_token?: string;
    }>(`/payments/attempt/${attemptId}/status`),

  // Receipts & Summaries
  getReceipt: (tokenOrId: string) => request<Receipt>(`/receipts/${tokenOrId}`),
  getGroupSummary: (groupId: string) => request<FinalCombinedOrderSummary>(`/groups/${groupId}/summary`),

  // Host Dashboard
  getHostDashboard: (groupId: string) => request<HostDashboardSummary>(`/groups/${groupId}/dashboard`),

  // Merchant Orders
  recordMerchantOrder: (groupId: string, payload: { platform_name: string; external_order_id?: string; estimated_delivery_minutes?: number; notes?: string }) =>
    request<{ id: string; status: string; platform_name: string }>(`/groups/${groupId}/merchant-order`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateMerchantOrderStatus: (groupId: string, payload: { status: string; notes?: string; external_order_id?: string }) =>
    request<{ id: string; status: string }>(`/groups/${groupId}/merchant-order/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
};
