import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Bot,
  Building2,
  Layers,
  MessageCircle,
  Mic,
  Network,
  Smartphone,
  Sparkles,
  Store,
  Workflow,
} from "lucide-react";
import { PRODUCT_CATALOG } from "@/constants/productCatalog";

const icons = {
  chat: Bot,
  voice: Mic,
  whatsapp: MessageCircle,
  omnichannel: Layers,
  automation: Workflow,
  "ai-studio": Sparkles,
  marketplace: Store,
  mobile: Smartphone,
  enterprise: Building2,
  "oraone-os": Network,
};

export default function ProductTiles() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {PRODUCT_CATALOG.map((product) => {
        const Icon = icons[product.slug];
        return (
          <Link
            key={product.id}
            to={
              product.id === 1
                ? "/products/ai-chat"
                : "/products/" + product.slug
            }
            className="flex flex-col rounded-lg border border-[#E2E8F0] bg-white p-6 transition-colors hover:border-[#2563EB]/40"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-[#64748B]">
                Product {product.id}
              </span>
              <span
                className={
                  "rounded-full px-2.5 py-1 text-xs font-medium " +
                  (product.id === 1
                    ? "bg-[#EFF6FF] text-[#2563EB]"
                    : "bg-[#F1F5F9] text-[#475569]")
                }
              >
                {product.status}
              </span>
            </div>
            <Icon
              size={25}
              className="mt-5 text-[#2563EB]"
              aria-hidden="true"
            />
            <h3 className="mt-4 text-lg font-semibold text-[#0F172A]">
              {product.shortName}
            </h3>
            <p className="mt-2 flex-1 text-sm leading-relaxed text-[#64748B]">
              {product.scope}
            </p>
            <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-[#2563EB]">
              Explore {product.shortName}
              <ArrowUpRight size={15} />
            </span>
          </Link>
        );
      })}
    </div>
  );
}
