"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Navbar } from "@/components/layout/navbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, api } from "@/lib/api";
import type {
  AlertCategory,
  Report,
  ReportGenerationRequest,
  ReportGenerationResponse,
} from "@/types";

type BuilderFormState = {
  title: string;
  geographicScope: string;
  dateRangeStart: string;
  dateRangeEnd: string;
  maxAlerts: number;
  includeUnverified: boolean;
  generatePdf: boolean;
  categories: AlertCategory[];
};

const CATEGORY_OPTIONS: Array<{ value: AlertCategory; label: string }> = [
  { value: "natural_disaster", label: "Natural Disaster" },
  { value: "political", label: "Political" },
  { value: "crime", label: "Crime" },
  { value: "health", label: "Health" },
  { value: "terrorism", label: "Terrorism" },
  { value: "civil_unrest", label: "Civil Unrest" },
];

function getStatusVariant(status: Report["status"]): "default" | "secondary" | "outline" {
  if (status === "approved") {
    return "secondary";
  }
  if (status === "sent") {
    return "default";
  }
  return "outline";
}

function formatDate(dateString: string | null): string {
  if (!dateString) {
    return "N/A";
  }
  const parsed = new Date(dateString);
  return Number.isNaN(parsed.getTime()) ? "N/A" : parsed.toLocaleDateString();
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [isLoadingReports, setIsLoadingReports] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [formState, setFormState] = useState<BuilderFormState>({
    title: "",
    geographicScope: "",
    dateRangeStart: "",
    dateRangeEnd: "",
    maxAlerts: 50,
    includeUnverified: false,
    generatePdf: true,
    categories: [],
  });

  const loadReports = useCallback(async () => {
    setIsLoadingReports(true);
    try {
      const response = await api.get<Report[]>("/reports?limit=50&offset=0");
      setReports(response);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Failed to load reports";
      toast.error(message);
    } finally {
      setIsLoadingReports(false);
    }
  }, []);

  useEffect(() => {
    void loadReports();
  }, [loadReports]);

  const selectedReportContent = selectedReport?.content_json;
  const previewTopAlerts = useMemo(
    () => selectedReportContent?.top_alerts ?? [],
    [selectedReportContent]
  );

  const toggleCategory = (category: AlertCategory) => {
    setFormState((previousState) => {
      const isSelected = previousState.categories.includes(category);
      return {
        ...previousState,
        categories: isSelected
          ? previousState.categories.filter((value) => value !== category)
          : [...previousState.categories, category],
      };
    });
  };

  const handleGenerateReport = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsGenerating(true);

    const payload: ReportGenerationRequest = {
      title: formState.title.trim() || null,
      geographic_scope: formState.geographicScope.trim() || null,
      date_range_start: formState.dateRangeStart || null,
      date_range_end: formState.dateRangeEnd || null,
      categories: formState.categories,
      max_alerts: formState.maxAlerts,
      include_unverified: formState.includeUnverified,
      generate_pdf: formState.generatePdf,
    };

    try {
      const response = await api.post<ReportGenerationResponse>(
        "/reports/generate",
        payload
      );
      toast.success(`Report generated using ${response.alerts_used} alerts`);
      setReports((previousReports) => [response.report, ...previousReports]);
      setSelectedReport(response.report);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Failed to generate report";
      toast.error(message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownloadPdf = async (report: Report) => {
    try {
      const pdfBlob = await api.downloadReportPdf(report.id);
      const blobUrl = window.URL.createObjectURL(pdfBlob);
      const anchor = document.createElement("a");
      anchor.href = blobUrl;
      anchor.download = report.pdf_path ?? `report-${report.id}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Failed to download report PDF";
      toast.error(message);
    }
  };

  const handleSubmitForApproval = async (reportId: number) => {
    try {
      const updated = await api.post<Report>(`/reports/${reportId}/submit`);
      toast.success("Report submitted for admin approval");
      setReports((previousReports) =>
        previousReports.map((report) =>
          report.id === updated.id ? updated : report
        )
      );
      if (selectedReport?.id === updated.id) {
        setSelectedReport(updated);
      }
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Failed to submit report";
      toast.error(message);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container py-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground">
            Generate, preview, and manage travel risk reports
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Report Builder</CardTitle>
            <CardDescription>
              Select date range, region, and categories to generate AI-powered
              reports
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-5" onSubmit={handleGenerateReport}>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="title">Report Title (Optional)</Label>
                  <Input
                    id="title"
                    value={formState.title}
                    onChange={(event) =>
                      setFormState((previousState) => ({
                        ...previousState,
                        title: event.target.value,
                      }))
                    }
                    placeholder="APAC Weekly Risk Brief"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="geographicScope">Geographic Scope</Label>
                  <Input
                    id="geographicScope"
                    value={formState.geographicScope}
                    onChange={(event) =>
                      setFormState((previousState) => ({
                        ...previousState,
                        geographicScope: event.target.value,
                      }))
                    }
                    placeholder="Global, Southeast Asia, Thailand..."
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dateRangeStart">Date Range Start</Label>
                  <Input
                    id="dateRangeStart"
                    type="date"
                    value={formState.dateRangeStart}
                    onChange={(event) =>
                      setFormState((previousState) => ({
                        ...previousState,
                        dateRangeStart: event.target.value,
                      }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dateRangeEnd">Date Range End</Label>
                  <Input
                    id="dateRangeEnd"
                    type="date"
                    value={formState.dateRangeEnd}
                    onChange={(event) =>
                      setFormState((previousState) => ({
                        ...previousState,
                        dateRangeEnd: event.target.value,
                      }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="maxAlerts">Max Alerts</Label>
                  <Input
                    id="maxAlerts"
                    type="number"
                    min={1}
                    max={200}
                    value={formState.maxAlerts}
                    onChange={(event) =>
                      setFormState((previousState) => ({
                        ...previousState,
                        maxAlerts: Number(event.target.value) || 1,
                      }))
                    }
                  />
                </div>
                <div className="space-y-3">
                  <Label>Options</Label>
                  <div className="space-y-2 text-sm">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formState.includeUnverified}
                        onChange={(event) =>
                          setFormState((previousState) => ({
                            ...previousState,
                            includeUnverified: event.target.checked,
                          }))
                        }
                      />
                      Include unverified alerts
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formState.generatePdf}
                        onChange={(event) =>
                          setFormState((previousState) => ({
                            ...previousState,
                            generatePdf: event.target.checked,
                          }))
                        }
                      />
                      Generate PDF output
                    </label>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Risk Categories</Label>
                <div className="flex flex-wrap gap-2">
                  {CATEGORY_OPTIONS.map((option) => {
                    const isSelected = formState.categories.includes(option.value);
                    return (
                      <Button
                        key={option.value}
                        type="button"
                        variant={isSelected ? "default" : "outline"}
                        size="sm"
                        onClick={() => toggleCategory(option.value)}
                      >
                        {option.label}
                      </Button>
                    );
                  })}
                </div>
              </div>

              <CardFooter className="px-0 pb-0">
                <Button type="submit" disabled={isGenerating}>
                  {isGenerating ? "Generating report..." : "Generate report"}
                </Button>
              </CardFooter>
            </form>
          </CardContent>
        </Card>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Generated Reports</CardTitle>
            <CardDescription>
              Review generated reports, open previews, and download PDFs
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingReports ? (
              <div className="flex h-40 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
                Loading reports...
              </div>
            ) : reports.length === 0 ? (
              <div className="flex h-40 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
                No reports yet. Generate your first report above.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Scope</TableHead>
                    <TableHead>Date Range</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reports.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell className="max-w-[260px] truncate">
                        {report.title}
                      </TableCell>
                      <TableCell>{report.geographic_scope || "Global"}</TableCell>
                      <TableCell>
                        {formatDate(report.date_range_start)} -{" "}
                        {formatDate(report.date_range_end)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusVariant(report.status)}>
                          {report.status.replace("_", " ")}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDate(report.created_at)}</TableCell>
                      <TableCell className="space-x-2">
                        {report.status === "draft" ? (
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => void handleSubmitForApproval(report.id)}
                          >
                            Submit
                          </Button>
                        ) : null}
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => setSelectedReport(report)}
                        >
                          Preview
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          disabled={!report.pdf_path}
                          onClick={() => void handleDownloadPdf(report)}
                        >
                          Download PDF
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>

      <Dialog
        open={selectedReport !== null}
        onOpenChange={(isOpen) => {
          if (!isOpen) {
            setSelectedReport(null);
          }
        }}
      >
        <DialogContent className="max-h-[80vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedReport?.title}</DialogTitle>
            <DialogDescription>
              {selectedReport?.geographic_scope || "Global"} |{" "}
              {formatDate(selectedReport?.date_range_start || null)} -{" "}
              {formatDate(selectedReport?.date_range_end || null)}
            </DialogDescription>
          </DialogHeader>

          {selectedReportContent ? (
            <div className="space-y-4 text-sm">
              <div>
                <h3 className="mb-2 font-semibold">Executive Summary</h3>
                <p className="text-muted-foreground">
                  {selectedReportContent.executive_summary}
                </p>
              </div>

              <div>
                <h3 className="mb-2 font-semibold">Key Findings</h3>
                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                  {selectedReportContent.key_findings?.map((finding, index) => (
                    <li key={`${finding}-${index}`}>{finding}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h3 className="mb-2 font-semibold">Recommendations</h3>
                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                  {selectedReportContent.recommendations?.map(
                    (recommendation, index) => (
                      <li key={`${recommendation}-${index}`}>{recommendation}</li>
                    )
                  )}
                </ul>
              </div>

              <div>
                <h3 className="mb-2 font-semibold">Top Alerts</h3>
                {previewTopAlerts.length === 0 ? (
                  <p className="text-muted-foreground">No top alerts in this report.</p>
                ) : (
                  <div className="space-y-2">
                    {previewTopAlerts.map((alert) => (
                      <div
                        key={alert.id}
                        className="rounded-md border p-3 text-muted-foreground"
                      >
                        <div className="mb-1 flex items-center justify-between gap-3">
                          <span className="font-medium text-foreground">
                            {alert.title}
                          </span>
                          <Badge variant="outline">Severity {alert.severity}</Badge>
                        </div>
                        <p>{alert.summary}</p>
                        <p className="mt-1 text-xs">
                          {alert.country} {alert.region ? `- ${alert.region}` : ""} |{" "}
                          {alert.category.replace("_", " ")}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              This report does not have preview content.
            </p>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
