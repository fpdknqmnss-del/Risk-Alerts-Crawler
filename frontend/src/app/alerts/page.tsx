import { Navbar } from "@/components/layout/navbar";
import { AlertFeed } from "@/components/alerts/alert-feed";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function AlertsPage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container py-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold tracking-tight">Alert Feed</h1>
          <p className="text-muted-foreground">
            Browse, filter, and review travel risk alerts
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Alerts</CardTitle>
            <CardDescription>
              Filterable by category, severity, region, and date range
            </CardDescription>
          </CardHeader>
          <CardContent>
            <AlertFeed />
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
