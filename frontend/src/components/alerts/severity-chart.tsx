"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SeverityDistributionItem } from "@/types";
import { getSeverityColor } from "@/lib/alert-utils";

interface SeverityChartProps {
  distribution: SeverityDistributionItem[];
}

export function SeverityChart({ distribution }: SeverityChartProps) {
  const data = [1, 2, 3, 4, 5].map((severity) => {
    const item = distribution.find((entry) => entry.severity === severity);
    return {
      severity: `S${severity}`,
      count: item?.count ?? 0,
      fill: getSeverityColor(severity),
    };
  });

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="severity" />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="count" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
