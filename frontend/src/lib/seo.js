import { useEffect } from "react";

const SITE_NAME = "OraOne - One AI. Every Conversation.";
const SITE_BASE = "https://oraone.in";
const DEFAULT_OG_IMAGE = "/assets/og-image.png";

const LD_ID = "oraone-page-jsonld";

/**
 * useSEO — keeps document title, meta description, canonical URL, OG/Twitter
 * tags and (optionally) a per-page JSON-LD block in sync with the current route.
 *
 * @param {{
 *   title?: string,
 *   description?: string,
 *   ogImage?: string,
 *   noindex?: boolean,
 *   breadcrumbs?: { name: string, url: string }[],
 *   faq?: { question: string, answer: string }[],
 *   jsonLd?: object | object[]
 * }} opts
 */
export function useSEO({ title, description, ogImage, noindex, breadcrumbs, faq, jsonLd } = {}) {
  useEffect(() => {
    if (title) document.title = `${title} | ${SITE_NAME}`;

    const upsert = (selector, create, attrs) => {
      let tag = document.head.querySelector(selector);
      if (!tag) {
        tag = create();
        document.head.appendChild(tag);
      }
      Object.entries(attrs).forEach(([k, v]) => tag.setAttribute(k, v));
      return tag;
    };

    const setMeta = (name, content) => {
      if (!content) return;
      upsert(`meta[name="${name}"]`, () => document.createElement("meta"), { name, content });
    };

    const setOg = (property, content) => {
      if (!content) return;
      upsert(`meta[property="${property}"]`, () => document.createElement("meta"), { property, content });
    };

    const image = ogImage || DEFAULT_OG_IMAGE;
    const canonicalUrl = `${SITE_BASE}${window.location.pathname}`;

    setMeta("description", description);
    setMeta("robots", noindex ? "noindex, nofollow" : "index, follow, max-image-preview:large");

    setOg("og:title", title ? `${title} | OraOne` : SITE_NAME);
    setOg("og:description", description);
    setOg("og:image", image);
    setOg("og:url", canonicalUrl);
    setOg("og:type", "website");

    setMeta("twitter:card", "summary_large_image");
    setMeta("twitter:title", title ? `${title} | OraOne` : SITE_NAME);
    setMeta("twitter:description", description);
    setMeta("twitter:image", image);

    upsert('link[rel="canonical"]', () => document.createElement("link"), {
      rel: "canonical",
      href: canonicalUrl,
    });

    // Build per-page JSON-LD payload
    const blocks = [];
    if (Array.isArray(breadcrumbs) && breadcrumbs.length) {
      blocks.push({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: breadcrumbs.map((b, i) => ({
          "@type": "ListItem",
          position: i + 1,
          name: b.name,
          item: b.url.startsWith("http") ? b.url : `${SITE_BASE}${b.url}`,
        })),
      });
    }
    if (Array.isArray(faq) && faq.length) {
      blocks.push({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: faq.map((f) => ({
          "@type": "Question",
          name: f.question,
          acceptedAnswer: { "@type": "Answer", text: f.answer },
        })),
      });
    }
    if (jsonLd) blocks.push(...(Array.isArray(jsonLd) ? jsonLd : [jsonLd]));

    // Inject/replace single LD container
    let ld = document.getElementById(LD_ID);
    if (blocks.length) {
      if (!ld) {
        ld = document.createElement("script");
        ld.type = "application/ld+json";
        ld.id = LD_ID;
        document.head.appendChild(ld);
      }
      ld.textContent = JSON.stringify(blocks.length === 1 ? blocks[0] : blocks);
    } else if (ld) {
      ld.remove();
    }
  }, [title, description, ogImage, noindex, breadcrumbs, faq, jsonLd]);
}
