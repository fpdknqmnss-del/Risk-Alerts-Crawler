"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useAlertsRealtime } from "@/lib/use-alerts-realtime";
import {
  formatAlertDate,
  getCategoryLabel,
  getSeverityColor,
  getSeverityLabel,
} from "@/lib/alert-utils";
import type { Alert, AlertCategory, AlertListResponse, AlertQueryParams } from "@/types";
import { AlertDetailDialog } from "@/components/alerts/alert-detail-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const CATEGORY_OPTIONS: Array<{ value: AlertCategory; label: string }> = [
  { value: "natural_disaster", label: "Natural Disaster" },
  { value: "political", label: "Political" },
  { value: "crime", label: "Crime" },
  { value: "health", label: "Health" },
  { value: "terrorism", label: "Terrorism" },
  { value: "civil_unrest", label: "Civil Unrest" },
];

const DEFAULT_PAGE_SIZE = 20;

interface AlertFeedFilterDraft {
  category: AlertCategory | "all";
  severityMin: "all" | "1" | "2" | "3" | "4" | "5";
  country: string;
  region: string;
  search: string;
  startDate: string;
  endDate: string;
  sortBy: "created_at" | "severity";
  sortOrder: "asc" | "desc";
}

const INITIAL_DRAFT: AlertFeedFilterDraft = {
  category: "all",
  severityMin: "all",
  country: "",
  region: "",
  search: "",
  startDate: "",
  endDate: "",
  sortBy: "created_at",
  sortOrder: "desc",
};

function toStartDateIso(dateValue: string): string | undefined {
  if (!dateValue) {
    return undefined;
  }
  return `${dateValue}T00:00:00`;
}

function toEndDateIso(dateValue: string): string | undefined {
  if (!dateValue) {
    return undefined;
  }
  return `${dateValue}T23:59:59`;
}

function buildAlertQueryParams(
  draft: AlertFeedFilterDraft,
  page: number,
  pageSize: number
): AlertQueryParams {
  return {
    category: draft.category === "all" ? undefined : draft.category,
    severity_min: draft.severityMin === "all" ? undefined : Number(draft.severityMin),
    country: draft.country || undefined,
    region: draft.region || undefined,
    search: draft.search || undefined,
    start_date: toStartDateIso(draft.startDate),
    end_date: toEndDateIso(draft.endDate),
    sort_by: draft.sortBy,
    sort_order: draft.sortOrder,
    page,
    page_size: pageSize,
  };
}

export function AlertFeed() {
  const [draftFilters, setDraftFilters] = useState<AlertFeedFilterDraft>(INITIAL_DRAFT);
  const [appliedFilters, setAppliedFilters] =
    useState<AlertFeedFilterDraft>(INITIAL_DRAFT);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [response, setResponse] = useState<AlertListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const queryParams = useMemo(
    () => buildAlertQueryParams(appliedFilters, page, pageSize),
    [appliedFilters, page, pageSize]
  );

  const fetchAlerts = useCallback(
    async (backgroundRefresh: boolean) => {
      if (backgroundRefresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }

      try {
        const data = await api.getAlerts(queryParams);
        setResponse(data);
        setErrorMessage(null);
      } catch (error) {
        setErrorMessage(
          error instanceof Error ? error.message : "Failed to load alerts."
        );
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [queryParams]
  );

  useEffect(() => {
    void fetchAlerts(false);
  }, [fetchAlerts]);

  useAlertsRealtime(async () => {
    await fetchAlerts(true);
  });

  const totalPages = Math.max(1, Math.ceil((response?.total ?? 0) / pageSize));

  const applyFilters = () => {
    setPage(1);
    setAppliedFilters(draftFilters);
  };

  const resetFilters = () => {
    setDraftFilters(INITIAL_DRAFT);
    setAppliedFilters(INITIAL_DRAFT);
    setPage(1);
    setPageSize(DEFAULT_PAGE_SIZE);
  };

  const alerts = response?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="rounded-md border bg-muted/20 p-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Input
            placeholder="Search alerts..."
            value={draftFilters.search}
            onChange={(event) =>
              setDraftFilters((previous) => ({
                ...previous,
                search: event.target.value,
              }))
            }
          />
          <Select
            value={draftFilters.category}
            onValueChange={(value) =>
              setDraftFilters((previous) => ({
                ...previous,
                category: value as AlertCategory | "all",
              }))
            }
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {CATEGORY_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={draftFilters.severityMin}
            onValueChange={(value) =>
              setDraftFilters((previous) => ({
                ...previous,
                severityMin: value as AlertFeedFilterDraft["severityMin"],
              }))
            }
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Minimum Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Any Severity</SelectItem>
              {[1, 2, 3, 4, 5].map((severity) => (
                <SelectItem key={severity} value={String(severity)}>
                  Severity {severity}+
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            placeholder="Country"
            value={draftFilters.country}
            onChange={(event) =>
              setDraftFilters((previous) => ({
                ...previous,
                country: event.target.value,
              }))
            }
          />
          <Input
            placeholder="Region"
            value={draftFilters.region}
            onChange={(event) =>
              setDraftFilters((previous) => ({
                ...previous,
                region: event.target.value,
              }))
            }
          />
          <Input
            type="date"
            value={draftFilters.startDate}
            onChange={(event) =>
              setDraftFilters((previous) => ({
                ...previous,
                startDate: event.target.value,
              }))
            }
          />
          <Input
            type="date"
            value={draftFilters.endDate}
            onChange={(event) =>
              setDraftFilters((previous) => ({
                ...previous,
                endDate: event.target.value,
              }))
            }
          />
          <div className="grid grid-cols-2 gap-2">
            <Select
              value={draftFilters.sortBy}
              onValueChange={(value) =>
                setDraftFilters((previous) => ({
                  ...previous,
                  sortBy: value as "created_at" | "severity",
                }))
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="created_at">Sort: Time</SelectItem>
                <SelectItem value="severity">Sort: Severity</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={draftFilters.sortOrder}
              onValueChange={(value) =>
                setDraftFilters((previous) => ({
                  ...previous,
                  sortOrder: value as "asc" | "desc",
                }))
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="desc">Desc</SelectItem>
                <SelectItem value="asc">Asc</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button onClick={applyFilters}>Apply filters</Button>
          <Button variant="outline" onClick={resetFilters}>
            Reset
          </Button>
          <span className="text-xs text-muted-foreground">
            {isRefreshing ? "Live update syncing..." : "Live updates enabled"}
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">
          Loading alerts...
        </div>
      ) : errorMessage ? (
        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
          {errorMessage}
        </div>
      ) : alerts.length === 0 ? (
        <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">
          No alerts found for the selected filters.
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <Card key={alert.id}>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <h3 className="text-base font-semibold">{alert.title}</h3>
                    <p className="text-xs text-muted-foreground">
                      {formatAlertDate(alert.created_at)}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedAlert(alert)}
                  >
                    View details
                  </Button>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Badge
                    variant={alert.severity >= 4 ? "destructive" : "secondary"}
                    style={{
                      backgroundColor: getSeverityColor(alert.severity),
                      color: "white",
                    }}
                  >
                    {getSeverityLabel(alert.severity)}
                  </Badge>
                  <Badge variant="outline">{getCategoryLabel(alert.category)}</Badge>
                  <Badge variant="outline">
                    {alert.country}
                    {alert.region ? `, ${alert.region}` : ""}
                  </Badge>
                  <Badge variant={alert.verified ? "default" : "secondary"}>
                    {alert.verified ? "Verified" : "Unverified"}
                  </Badge>
                </div>

                <p className="text-sm text-muted-foreground">{alert.summary}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-3 text-sm">
        <div className="text-muted-foreground">
          Showing {(response?.items.length ?? 0) > 0 ? (page - 1) * pageSize + 1 : 0}-
          {(page - 1) * pageSize + (response?.items.length ?? 0)} of {response?.total ?? 0}
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={String(pageSize)}
            onValueChange={(value) => {
              setPageSize(Number(value));
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[130px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[10, 20, 50].map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size} / page
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((previous) => Math.max(1, previous - 1))}
          >
            Previous
          </Button>
          <span className="text-muted-foreground">
            Page {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() =>
              setPage((previous) => Math.min(totalPages, previous + 1))
            }
          >
            Next
          </Button>
        </div>
      </div>

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
