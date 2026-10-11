import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import App from "@/App";

// Recharts 3.x emits a transient "width(-1) and height(-1) of chart should be
// greater than 0" warning on a ResponsiveContainer's first synchronous render,
// before its ResizeObserver measures the (already fixed-size) parent. It is
// purely cosmetic console noise and does not affect rendering. Filter only this
// exact message so all other warnings still surface.
const __origWarn = console.warn;
console.warn = (...args) => {
  if (typeof args[0] === "string" && args[0].includes("of chart should be greater than 0")) {
    return;
  }
  __origWarn(...args);
};

// Safety net: an unhandled promise rejection (e.g. an API call in an effect
// with no try/catch) would otherwise fail completely silently for the user.
// Surface it in the console so it's at least visible/debuggable in prod.
window.addEventListener("unhandledrejection", (event) => {
  // eslint-disable-next-line no-console
  console.error("[unhandled promise rejection]", event.reason);
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
