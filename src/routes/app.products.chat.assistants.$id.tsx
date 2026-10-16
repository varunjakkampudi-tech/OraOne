import { createFileRoute, Outlet } from "@tanstack/react-router";
export const Route = createFileRoute("/app/products/chat/assistants/$id")({ component: Outlet });
