"use client";

import { MapContainer, Popup, TileLayer, CircleMarker } from "react-leaflet";
import type { Alert } from "@/types";
import {
  formatAlertDate,
  getCategoryLabel,
  getSeverityColor,
  getSeverityLabel,
  hasCoordinates,
} from "@/lib/alert-utils";

interface AlertsMapProps {
  alerts: Alert[];
  heightClassName?: string;
}

const DEFAULT_CENTER: [number, number] = [20, 0];

export function AlertsMap({ alerts, heightClassName = "h-[420px]" }: AlertsMapProps) {
  const plottedAlerts = alerts.filter(hasCoordinates);

  return (
    <div className={`w-full overflow-hidden rounded-md border ${heightClassName}`}>
      <MapContainer center={DEFAULT_CENTER} zoom={2} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {plottedAlerts.map((alert) => (
          <CircleMarker
            key={alert.id}
            center={[alert.latitude as number, alert.longitude as number]}
            radius={6 + alert.severity}
            pathOptions={{
              color: getSeverityColor(alert.severity),
              fillColor: getSeverityColor(alert.severity),
              fillOpacity: 0.75,
            }}
          >
            <Popup>
              <div className="space-y-1">
                <div className="font-semibold">{alert.title}</div>
                <div className="text-xs text-muted-foreground">
                  {getCategoryLabel(alert.category)} - {getSeverityLabel(alert.severity)}
                </div>
                <div className="text-xs text-muted-foreground">
                  {alert.country}
                  {alert.region ? `, ${alert.region}` : ""}
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatAlertDate(alert.created_at)}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
