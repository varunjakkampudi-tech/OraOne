import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api } from "@/lib/api";

/**
 * Branding context — Phase 12 Module 15 white-label.
 *
 * Loads the org's branding once and shares it across the dashboard so the
 * sidebar, header, and any surface can render the customer's brand. The
 * brand primary colour is also exposed as the `--brand-primary` CSS
 * variable on the wrapped subtree. Call `refresh()` after saving to update
 * the UI live.
 */
const BrandingContext = createContext({
  branding: null,
  loading: true,
  refresh: async () => {},
});

export function BrandingProvider({ children }) {
  const [branding, setBranding] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/branding");
      setBranding(data);
    } catch {
      setBranding(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({ branding, loading, refresh }),
    [branding, loading, refresh]
  );

  const style = branding?.primary_color
    ? {
        "--brand-primary": branding.primary_color,
        "--brand-accent": branding.accent_color || branding.primary_color,
      }
    : undefined;

  return (
    <BrandingContext.Provider value={value}>
      <div style={style} className="contents">
        {children}
      </div>
    </BrandingContext.Provider>
  );
}

export function useBranding() {
  return useContext(BrandingContext);
}
