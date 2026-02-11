"use client";

import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  formatAlertDate,
  getCategoryLabel,
  getSeverityColor,
  getSeverityLabel,
} from "@/lib/alert-utils";
import type { Alert } from "@/types";

interface AlertDetailDialogProps {
  alert: Alert | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AlertDetailDialog({
  alert,
  open,
  onOpenChange,
}: AlertDetailDialogProps) {
  if (!alert) {
    return null;
  }

  const sourceCount = Array.isArray(alert.sources)
    ? alert.sources.length
    : alert.sources
      ? 1
      : 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{alert.title}</DialogTitle>
          <DialogDescription>{formatAlertDate(alert.created_at)}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
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

          <p>{alert.summary}</p>

          {alert.full_content ? (
            <div className="space-y-1">
              <div className="text-xs font-semibold uppercase text-muted-foreground">
                Full details
              </div>
              <p className="whitespace-pre-wrap">{alert.full_content}</p>
            </div>
          ) : null}

          <div className="grid gap-2 rounded-md bg-muted p-3 text-xs text-muted-foreground md:grid-cols-2">
            <div>Sources: {sourceCount}</div>
            <div>
              Verification score:{" "}
              {alert.verification_score !== null
                ? alert.verification_score.toFixed(2)
                : "N/A"}
            </div>
            <div>
              Coordinates:{" "}
              {alert.latitude !== null && alert.longitude !== null
                ? `${alert.latitude.toFixed(2)}, ${alert.longitude.toFixed(2)}`
                : "N/A"}
            </div>
            <div>Last updated: {formatAlertDate(alert.updated_at)}</div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
