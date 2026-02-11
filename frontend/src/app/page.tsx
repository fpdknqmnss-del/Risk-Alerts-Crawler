"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { AlertDetailDialog } from "@/components/alerts/alert-detail-dialog";
import { SeverityChart } from "@/components/alerts/severity-chart";
import { Navbar } from "@/components/layout/navbar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatAlertDate, getCategoryLabel, getSeverityLabel } from "@/lib/alert-utils";
import { useAlertsRealtime } from "@/lib/use-alerts-realtime";
import type { Alert, AlertsStatsResponse } from "@/types";

const AlertsMap = dynamic(
  () => import("@/components/map/alerts-map").then((module) => module.AlertsMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[420px] items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
        Loading map...
      </div>
    ),
  }
);

export default function DashboardPage() {
  const [stats, setStats] = useState<AlertsStatsResponse | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadDashboardData = useCallback(async (backgroundRefresh: boolean) => {
    if (backgroundRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    try {
      const [statsResponse, alertsResponse] = await Promise.all([
        api.getAlertStats(),
        api.getAlerts({
          sort_by: "created_at",
          sort_order: "desc",
          page: 1,
          page_size: 100,
        }),
      ]);
      setStats(statsResponse);
      setAlerts(alertsResponse.items);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Failed to load dashboard data."
      );
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboardData(false);
  }, [loadDashboardData]);

  useAlertsRealtime(async () => {
    await loadDashboardData(true);
  });

  const recentAlerts = alerts.slice(0, 6);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container py-6">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Global travel risk overview and real-time alerts
            </p>
          </div>
          <span className="text-xs text-muted-foreground">
            {isRefreshing ? "Syncing live updates..." : "Live updates enabled"}
          </span>
        </div>

        {errorMessage ? (
          <div className="mb-6 rounded-md border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
            {errorMessage}
          </div>
        ) : null}

        <div className="mb-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Alerts</CardTitle>
              <Badge variant="secondary">All time</Badge>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {isLoading ? "--" : stats?.total_alerts ?? 0}
              </div>
              <p className="text-xs text-muted-foreground">Across all tracked sources</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Critical Alerts</CardTitle>
              <Badge variant="destructive">Severity 5</Badge>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {isLoading ? "--" : stats?.critical_alerts ?? 0}
              </div>
              <p className="text-xs text-muted-foreground">Immediate attention required</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Countries Affected</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {isLoading ? "--" : stats?.countries_affected ?? 0}
              </div>
              <p className="text-xs text-muted-foreground">Distinct impacted countries</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Plotted Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {isLoading
                  ? "--"
                  : alerts.filter(
                      (alert) => alert.latitude !== null && alert.longitude !== null
                    ).length}
              </div>
              <p className="text-xs text-muted-foreground">Alerts with map coordinates</p>
            </CardContent>
          </Card>
        </div>

        <div className="mb-6 grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <CardHeader>
              <CardTitle>Global Risk Map</CardTitle>
              <CardDescription>
                Interactive map with color-coded alert pins by severity
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AlertsMap alerts={alerts} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Severity Distribution</CardTitle>
              <CardDescription>Current spread of alert severities</CardDescription>
            </CardHeader>
            <CardContent>
              <SeverityChart distribution={stats?.severity_distribution ?? []} />
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Recent Alerts</CardTitle>
            <CardDescription>Latest travel risk alerts from all sources</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="rounded-md border p-6 text-sm text-muted-foreground">
                Loading alerts...
              </div>
            ) : recentAlerts.length === 0 ? (
              <div className="rounded-md border p-6 text-sm text-muted-foreground">
                No alerts available yet.
              </div>
            ) : (
              <div className="space-y-3">
                {recentAlerts.map((alert) => (
                  <button
                    key={alert.id}
                    type="button"
                    onClick={() => setSelectedAlert(alert)}
                    className="w-full rounded-md border p-3 text-left transition-colors hover:bg-muted/30"
                  >
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <h3 className="font-semibold">{alert.title}</h3>
                      <span className="text-xs text-muted-foreground">
                        {formatAlertDate(alert.created_at)}
                      </span>
                    </div>
                    <div className="mb-2 flex flex-wrap gap-2">
                      <Badge variant={alert.severity >= 4 ? "destructive" : "secondary"}>
                        {getSeverityLabel(alert.severity)}
                      </Badge>
                      <Badge variant="outline">{getCategoryLabel(alert.category)}</Badge>
                      <Badge variant="outline">
                        {alert.country}
                        {alert.region ? `, ${alert.region}` : ""}
                      </Badge>
                    </div>
                    <p className="line-clamp-2 text-sm text-muted-foreground">{alert.summary}</p>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>

      <AlertDetailDialog
        alert={selectedAlert}
        open={selectedAlert !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedAlert(null);
          }
        }}
      />
    </div>
  );
}
