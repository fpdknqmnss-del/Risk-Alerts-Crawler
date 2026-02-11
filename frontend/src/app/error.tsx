"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function GlobalError({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error("Unhandled client error:", error);
  }, [error]);

  return (
    <main className="container py-10">
      <Card className="mx-auto w-full max-w-lg">
        <CardHeader>
          <CardTitle>Something went wrong</CardTitle>
          <CardDescription>
            The page failed to load. Try again, or refresh the browser.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={reset}>Try Again</Button>
        </CardContent>
      </Card>
    </main>
  );
}
