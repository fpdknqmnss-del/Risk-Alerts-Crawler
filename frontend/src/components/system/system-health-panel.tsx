"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

type ApiHealth = {
  status: string;
  version: string;
  environment: string;
};

type DbHealth = {
  status: string;
  database?: string;
  detail?: string;
};

type HealthState = {
  api: ApiHealth | null;
  database: DbHealth | null;
};

export function SystemHealthPanel() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [healthState, setHealthState] = useState<HealthState>({
    api: null,
    database: null,
  });

  const loadHealth = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const [apiResult, dbResult] = await Promise.allSettled([
      api.get<ApiHealth>("/health"),
      api.get<DbHealth>("/health/db"),
    ]);

    if (apiResult.status === "rejected") {
      const message =
        apiResult.reason instanceof ApiError
          ? apiResult.reason.message
          : "Unable to check service health";
      setError(message);
      setHealthState({ api: null, database: null });
      setIsLoading(false);
      return;
    }

    const database =
      dbResult.status === "fulfilled"
        ? dbResult.value
        : {
            status: "unhealthy",
            detail:
              dbResult.reason instanceof ApiError
                ? dbResult.reason.message
                : "Database health check failed",
          };

    setHealthState({ api: apiResult.value, database });
    setIsLoading(false);
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadHealth();
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [loadHealth]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-5 w-52" />
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-4 w-32" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" size="sm" onClick={() => void loadHealth()}>
          Retry health checks
        </Button>
      </div>
    );
  }

  const apiHealthy = healthState.api?.status === "healthy";
  const dbHealthy = healthState.database?.status === "healthy";

  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">API</span>
        <Badge variant={apiHealthy ? "secondary" : "destructive"}>
          {apiHealthy ? "healthy" : "unhealthy"}
        </Badge>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">Database</span>
        <Badge variant={dbHealthy ? "secondary" : "destructive"}>
          {dbHealthy ? "healthy" : "unhealthy"}
        </Badge>
      </div>

      <p className="text-muted-foreground">
        {healthState.api?.environment} • v{healthState.api?.version}
      </p>

      {!dbHealthy && healthState.database?.detail ? (
        <p className="text-xs text-muted-foreground">{healthState.database.detail}</p>
      ) : null}

      <Button variant="outline" size="sm" onClick={() => void loadHealth()}>
        Refresh health checks
      </Button>
    </div>
  );
}
