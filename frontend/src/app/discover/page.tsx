"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Search,
  Filter,
  Flame,
  Plus,
  Minus,
  Check,
  ShoppingBag,
  Sparkles,
  ArrowRight,
  Layers,
  Info,
} from "lucide-react";
import { api, Product, ProductCategory } from "@/lib/api";

export default function DiscoverPage() {
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [vegOnly, setVegOnly] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<string>("popularity");
  const [loading, setLoading] = useState<boolean>(true);

  // Cart helper for quick simulation
  const [localQuantities, setLocalQuantities] = useState<Record<string, number>>({});
  const [addedNotice, setAddedNotice] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [cats, prodsResp] = await Promise.all([
          api.getCategories().catch(() => []),
          api.getProducts().catch(() => ({ products: [], categories: [], total: 0 })),
        ]);
        if (cats.length) setCategories(cats);
        if (prodsResp.products) setProducts(prodsResp.products);
      } catch (e) {
        console.error("Failed to load products:", e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const filteredProducts = products.filter((p) => {
    if (selectedCategory !== "all" && p.category_id !== selectedCategory) return false;
    if (vegOnly && !p.is_veg) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = p.name.toLowerCase().includes(q);
      const matchDesc = p.description?.toLowerCase().includes(q);
      if (!matchName && !matchDesc) return false;
    }
    return true;
  }).sort((a, b) => {
    if (sortBy === "price_asc") return a.price_paise - b.price_paise;
    if (sortBy === "price_desc") return b.price_paise - a.price_paise;
    return b.popularity_score - a.popularity_score;
  });

  const handleQtyChange = (productId: string, delta: number) => {
    setLocalQuantities((prev) => {
      const current = prev[productId] || 0;
      const next = Math.max(0, current + delta);
      return { ...prev, [productId]: next };
    });
  };

  const totalSelectedItems = Object.values(localQuantities).reduce((a, b) => a + b, 0);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      {/* Top Banner & Header */}
      <div className="mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 bg-[#FFF4ED] text-[#FF5C00] text-[11px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider mb-2 border border-[#FFD9C6]">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Campus Snacks & Midnight Pantry</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-[#1A1A1A] font-['Outfit',sans-serif]">
              Late-Night Snack Menu
            </h1>
            <p className="text-xs sm:text-sm text-[#71717A] mt-1">
              Browse 25+ curated noodles, chips, cold coffees, and energy drinks for hostel cravings.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/create"
              className="flex items-center gap-1.5 bg-[#FF5C00] hover:bg-[#E55200] text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-md shadow-[#FF5C00]/25 transition-all"
            >
              <ShoppingBag className="w-4 h-4" />
              <span>Start Group Order</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white p-3.5 sm:p-4 rounded-2xl border border-[#EFE8DE] shadow-xs mb-6 space-y-3">
        <div className="flex flex-col sm:flex-row items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-[#71717A] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search Maggi, Red Bull, Kurkure, cold coffee..."
              className="w-full pl-10 pr-4 py-2 text-xs sm:text-sm rounded-xl border border-[#EFE8DE] bg-[#FAF8F5] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30 focus:border-[#FF5C00] transition-all"
            />
          </div>

          {/* Controls: Veg filter and Sort dropdown */}
          <div className="flex items-center gap-2.5 w-full sm:w-auto justify-between sm:justify-start">
            {/* Veg Only Toggle */}
            <button
              onClick={() => setVegOnly(!vegOnly)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold border transition-colors ${
                vegOnly
                  ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                  : "bg-[#FAF8F5] text-[#555555] border-[#EFE8DE] hover:bg-white"
              }`}
            >
              <span className={`w-2.5 h-2.5 rounded-full ${vegOnly ? "bg-emerald-600" : "bg-zinc-400"}`} />
              <span>Veg Only</span>
            </button>

            {/* Sort Dropdown */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-2 rounded-xl text-xs font-semibold bg-[#FAF8F5] border border-[#EFE8DE] text-[#1A1A1A] focus:outline-none focus:ring-2 focus:ring-[#FF5C00]/30"
            >
              <option value="popularity">Most Popular</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
            </select>
          </div>
        </div>

        {/* Category Pills Carousel */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 no-scrollbar">
          <button
            onClick={() => setSelectedCategory("all")}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-colors shrink-0 ${
              selectedCategory === "all"
                ? "bg-[#FF5C00] text-white shadow-xs"
                : "bg-[#FAF8F5] text-[#555555] hover:text-[#1A1A1A] border border-[#EFE8DE]"
            }`}
          >
            All Items
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-colors shrink-0 ${
                selectedCategory === cat.id
                  ? "bg-[#FF5C00] text-white shadow-xs"
                  : "bg-[#FAF8F5] text-[#555555] hover:text-[#1A1A1A] border border-[#EFE8DE]"
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      {/* Product Grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="bg-white rounded-2xl border border-[#EFE8DE] p-4 space-y-3 animate-pulse">
              <div className="w-full h-36 bg-zinc-200 rounded-xl" />
              <div className="h-4 bg-zinc-200 rounded w-3/4" />
              <div className="h-3 bg-zinc-100 rounded w-1/2" />
              <div className="h-8 bg-zinc-200 rounded-xl mt-4" />
            </div>
          ))}
        </div>
      ) : filteredProducts.length === 0 ? (
        <div className="bg-white rounded-2xl border border-[#EFE8DE] p-12 text-center max-w-md mx-auto space-y-3">
          <div className="w-12 h-12 rounded-full bg-[#FFF4ED] text-[#FF5C00] flex items-center justify-center mx-auto">
            <Search className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-[#1A1A1A]">No snacks found</h3>
          <p className="text-xs text-[#71717A]">
            Try clearing search filters or selecting &quot;All Items&quot;.
          </p>
          <button
            onClick={() => {
              setSearchQuery("");
              setSelectedCategory("all");
              setVegOnly(false);
            }}
            className="text-xs font-bold text-[#FF5C00] underline"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3.5 sm:gap-4">
          {filteredProducts.map((p) => {
            const qty = localQuantities[p.id] || 0;

            return (
              <div
                key={p.id}
                className="bg-white rounded-2xl border border-[#EFE8DE] hover:border-[#FFD9C6] transition-all shadow-xs hover:shadow-md flex flex-col justify-between overflow-hidden group"
              >
                {/* Image Section */}
                <div className="relative h-36 sm:h-44 w-full bg-[#FAF8F5] overflow-hidden">
                  <img
                    src={p.image_url}
                    alt={p.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                  {/* Veg / Non-Veg badge */}
                  <div className="absolute top-2.5 left-2.5">
                    <span
                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wider backdrop-blur-md shadow-xs ${
                        p.is_veg
                          ? "bg-emerald-500/90 text-white"
                          : "bg-red-500/90 text-white"
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-white" />
                      {p.is_veg ? "Veg" : "Non-Veg"}
                    </span>
                  </div>

                  {/* Unit badge */}
                  <div className="absolute bottom-2.5 right-2.5 bg-black/60 backdrop-blur-md text-white text-[10px] font-medium px-2 py-0.5 rounded-md">
                    {p.unit}
                  </div>
                </div>

                {/* Content Section */}
                <div className="p-3.5 sm:p-4 flex-1 flex flex-col justify-between">
                  <div>
                    <h3 className="font-extrabold text-xs sm:text-sm text-[#1A1A1A] line-clamp-1 mb-1 font-['Outfit',sans-serif]">
                      {p.name}
                    </h3>
                    <p className="text-[11px] text-[#71717A] line-clamp-2 leading-relaxed mb-3">
                      {p.description}
                    </p>
                  </div>

                  {/* Price & Quantity Controls */}
                  <div className="pt-2 border-t border-[#EFE8DE] flex items-center justify-between gap-2">
                    <div>
                      <span className="text-[10px] text-[#71717A] block -mb-0.5">Price</span>
                      <span className="text-sm sm:text-base font-black text-[#1A1A1A]">
                        ₹{p.price_inr.toFixed(0)}
                      </span>
                    </div>

                    {/* Quantity Selector */}
                    {qty === 0 ? (
                      <button
                        onClick={() => handleQtyChange(p.id, 1)}
                        className="bg-[#FFF4ED] hover:bg-[#FF5C00] text-[#FF5C00] hover:text-white border border-[#FFD9C6] hover:border-[#FF5C00] px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-xs active:scale-95 flex items-center gap-1"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add</span>
                      </button>
                    ) : (
                      <div className="flex items-center gap-1.5 bg-[#FF5C00] text-white rounded-xl px-1.5 py-1 shadow-xs">
                        <button
                          onClick={() => handleQtyChange(p.id, -1)}
                          className="w-5 h-5 rounded-lg hover:bg-black/15 flex items-center justify-center transition-colors"
                        >
                          <Minus className="w-3 h-3" />
                        </button>
                        <span className="text-xs font-extrabold px-1 min-w-[16px] text-center">
                          {qty}
                        </span>
                        <button
                          onClick={() => handleQtyChange(p.id, 1)}
                          className="w-5 h-5 rounded-lg hover:bg-black/15 flex items-center justify-center transition-colors"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Floating Action Bar when snacks are selected */}
      {totalSelectedItems > 0 && (
        <div className="fixed bottom-18 md:bottom-6 left-1/2 -translate-x-1/2 z-50 w-[92%] max-w-lg bg-[#1A1A1A] text-white p-3.5 rounded-2xl shadow-2xl flex items-center justify-between border border-zinc-700 animate-in fade-in slide-in-from-bottom-4 duration-200">
          <div>
            <span className="text-xs text-zinc-300 font-medium block">
              {totalSelectedItems} snack{totalSelectedItems > 1 ? "s" : ""} selected
            </span>
            <span className="text-sm font-bold text-[#FF5C00]">
              Ready to order with roommates?
            </span>
          </div>
          <Link
            href="/create"
            className="bg-[#FF5C00] hover:bg-[#E55200] text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-md flex items-center gap-1.5 transition-transform active:scale-95"
          >
            <span>Create Order</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}
    </div>
  );
}
