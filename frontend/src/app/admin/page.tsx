"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Navbar } from "@/components/layout/navbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, api } from "@/lib/api";
import type { MailingList, Report, ReportDispatchResponse } from "@/types";
import { SystemHealthPanel } from "@/components/system/system-health-panel";

export default function AdminPage() {
  const [pendingReports, setPendingReports] = useState<Report[]>([]);
  const [allReports, setAllReports] = useState<Report[]>([]);
  const [mailingLists, setMailingLists] = useState<MailingList[]>([]);
  const [reviewComments, setReviewComments] = useState<Record<number, string>>({});
  const [dispatchSelection, setDispatchSelection] = useState<Record<number, number[]>>(
    {}
  );
  const [useGeoMatch, setUseGeoMatch] = useState<Record<number, boolean>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  const approvedReports = useMemo(
    () => allReports.filter((report) => report.status === "approved"),
    [allReports]
  );

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [pending, reports, lists] = await Promise.all([
        api.get<Report[]>("/admin/reports/pending"),
        api.get<Report[]>("/reports?limit=100"),
        api.get<MailingList[]>("/mailing/lists"),
      ]);
      setPendingReports(pending);
      setAllReports(reports);
      setMailingLists(lists);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Failed to load admin data");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleReview = async (reportId: number, action: "approve" | "reject") => {
    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const comment = reviewComments[reportId] ?? "";
      await api.post<Report>(`/admin/reports/${reportId}/${action}`, {
        comment: comment.trim() || null,
      });
      setSuccessMessage(
        action === "approve" ? "Report approved" : "Report moved back to draft"
      );
      await loadData();
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : `Failed to ${action} report`
      );
    } finally {
      setIsSaving(false);
    }
  };

  const toggleMailingListSelection = (reportId: number, mailingListId: number) => {
    setDispatchSelection((previous) => {
      const current = previous[reportId] ?? [];
      const exists = current.includes(mailingListId);
      return {
        ...previous,
        [reportId]: exists
          ? current.filter((id) => id !== mailingListId)
          : [...current, mailingListId],
      };
    });
  };

  const handleDispatch = async (reportId: number) => {
    setIsSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const response = await api.post<ReportDispatchResponse>(
        `/admin/reports/${reportId}/dispatch`,
        {
          mailing_list_ids: dispatchSelection[reportId] ?? [],
          use_geographic_match: useGeoMatch[reportId] ?? true,
        }
      );
      setSuccessMessage(
        `Dispatch queued (${response.status})${response.task_id ? ` task ${response.task_id}` : ""}`
      );
      await loadData();
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "Failed to queue dispatch"
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container py-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold tracking-tight">Admin Panel</h1>
          <p className="text-muted-foreground">
            Review report approvals and dispatch approved reports to mailing lists.
          </p>
        </div>

        {errorMessage ? (
          <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            {errorMessage}
          </div>
        ) : null}
        {successMessage ? (
          <div className="mb-4 rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-700 dark:text-emerald-300">
            {successMessage}
          </div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Pending Approvals</CardTitle>
              <CardDescription>
                Approve or reject reports submitted for admin review.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading pending reports...</p>
              ) : pendingReports.length === 0 ? (
                <p className="text-sm text-muted-foreground">No pending reports right now.</p>
              ) : (
                pendingReports.map((report) => (
                  <div key={report.id} className="rounded-md border p-3">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium">{report.title}</p>
                        <p className="text-xs text-muted-foreground">
                          Scope: {report.geographic_scope || "Global"}
                        </p>
                      </div>
                      <Badge variant="outline">{report.status}</Badge>
                    </div>
                    <Input
                      placeholder="Review comment (optional)"
                      value={reviewComments[report.id] ?? ""}
                      onChange={(event) =>
                        setReviewComments((previous) => ({
                          ...previous,
                          [report.id]: event.target.value,
                        }))
                      }
                    />
                    <div className="mt-2 flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleReview(report.id, "approve")}
                        disabled={isSaving}
                      >
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleReview(report.id, "reject")}
                        disabled={isSaving}
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Approved Reports Dispatch</CardTitle>
              <CardDescription>
                Queue email delivery to selected mailing lists or use geographic matching.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <p className="text-sm text-muted-foreground">Loading approved reports...</p>
              ) : approvedReports.length === 0 ? (
                <p className="text-sm text-muted-foreground">No approved reports available.</p>
              ) : (
                <div className="space-y-3">
                  {approvedReports.map((report) => (
                    <div key={report.id} className="rounded-md border p-3">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <div>
                          <p className="font-medium">{report.title}</p>
                          <p className="text-xs text-muted-foreground">
                            Scope: {report.geographic_scope || "Global"}
                          </p>
                        </div>
                        <Badge variant="secondary">{report.status}</Badge>
                      </div>

                      <label className="mb-2 flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={useGeoMatch[report.id] ?? true}
                          onChange={(event) =>
                            setUseGeoMatch((previous) => ({
                              ...previous,
                              [report.id]: event.target.checked,
                            }))
                          }
                        />
                        Use geographic matching
                      </label>

                      <div className="mb-3 grid gap-1 rounded-md border p-2">
                        <p className="text-xs font-medium text-muted-foreground">
                          Optional explicit mailing list selection
                        </p>
                        {mailingLists.length === 0 ? (
                          <p className="text-xs text-muted-foreground">
                            No mailing lists found.
                          </p>
                        ) : (
                          mailingLists.map((mailingList) => (
                            <label
                              key={mailingList.id}
                              className="flex items-center gap-2 text-xs"
                            >
                              <input
                                type="checkbox"
                                checked={
                                  dispatchSelection[report.id]?.includes(mailingList.id) ?? false
                                }
                                onChange={() =>
                                  toggleMailingListSelection(report.id, mailingList.id)
                                }
                              />
                              {mailingList.name} ({mailingList.subscriber_count})
                            </label>
                          ))
                        )}
                      </div>

                      <Button
                        size="sm"
                        onClick={() => handleDispatch(report.id)}
                        disabled={isSaving}
                      >
                        Queue Dispatch
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="mt-4">
          <CardHeader>
            <CardTitle>Recent Reports</CardTitle>
            <CardDescription>
              Current report statuses across the workflow.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Scope</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-muted-foreground">
                      Loading reports...
                    </TableCell>
                  </TableRow>
                ) : allReports.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-muted-foreground">
                      No reports found.
                    </TableCell>
                  </TableRow>
                ) : (
                  allReports.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell>{report.title}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{report.status}</Badge>
                      </TableCell>
                      <TableCell>{report.geographic_scope || "Global"}</TableCell>
                      <TableCell>{new Date(report.created_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="mt-4">
          <CardHeader>
            <CardTitle>System Health</CardTitle>
            <CardDescription>
              Backend service and database connectivity status.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SystemHealthPanel />
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
