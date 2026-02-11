import type { Alert, AlertCategory } from "@/types";

const SEVERITY_COLORS: Record<number, string> = {
  1: "#16a34a",
  2: "#65a30d",
  3: "#d97706",
  4: "#ea580c",
  5: "#dc2626",
};

const CATEGORY_LABELS: Record<AlertCategory, string> = {
  natural_disaster: "Natural Disaster",
  political: "Political",
  crime: "Crime",
  health: "Health",
  terrorism: "Terrorism",
  civil_unrest: "Civil Unrest",
};

export function getSeverityColor(severity: number): string {
  return SEVERITY_COLORS[severity] ?? "#6b7280";
}

export function getSeverityLabel(severity: number): string {
  return `Severity ${severity}`;
}

export function getCategoryLabel(category: AlertCategory): string {
  return CATEGORY_LABELS[category] ?? category;
}

export function formatAlertDate(dateString: string): string {
  return new Date(dateString).toLocaleString();
}

export function hasCoordinates(alert: Alert): boolean {
  return alert.latitude !== null && alert.longitude !== null;
}
