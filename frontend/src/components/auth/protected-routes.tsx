"use client";

import { useEffect } from "react";
import type { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const PUBLIC_ROUTES = ["/login", "/register"];
const ADMIN_ONLY_ROUTES = ["/admin"];

function isPublicRoute(pathname: string) {
  return PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
}

function isAdminRoute(pathname: string) {
  return ADMIN_ONLY_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
}

export function ProtectedRoutes({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAuth();

  useEffect(() => {
    if (isLoading) {
      return;
    }

    if (isPublicRoute(pathname)) {
      if (isAuthenticated) {
        router.replace("/");
      }
      return;
    }

    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }

    if (isAdminRoute(pathname) && user?.role !== "admin") {
      router.replace("/");
    }
  }, [isAuthenticated, isLoading, pathname, router, user?.role]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        Checking your session...
      </div>
    );
  }

  if (!isPublicRoute(pathname) && !isAuthenticated) {
    return null;
  }

  if (isAdminRoute(pathname) && user?.role !== "admin") {
    return null;
  }

  return <>{children}</>;
}
