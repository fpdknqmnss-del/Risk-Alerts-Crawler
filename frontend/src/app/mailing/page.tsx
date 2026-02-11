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
import { useAuth } from "@/lib/auth";
import type { CsvImportResult, MailingList, Subscriber } from "@/types";

type ListFormState = {
  id: number | null;
  name: string;
  geographicRegions: string;
  description: string;
};

export default function MailingPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [lists, setLists] = useState<MailingList[]>([]);
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [subscribers, setSubscribers] = useState<Subscriber[]>([]);
  const [isLoadingLists, setIsLoadingLists] = useState(true);
  const [isLoadingSubscribers, setIsLoadingSubscribers] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [subscriberEmail, setSubscriberEmail] = useState("");
  const [subscriberName, setSubscriberName] = useState("");
  const [subscriberOrganization, setSubscriberOrganization] = useState("");
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [listForm, setListForm] = useState<ListFormState>({
    id: null,
    name: "",
    geographicRegions: "",
    description: "",
  });

  const selectedList = useMemo(
    () => lists.find((mailingList) => mailingList.id === selectedListId) ?? null,
    [lists, selectedListId]
  );

  const clearMessages = () => {
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  const refreshLists = useCallback(async () => {
    setIsLoadingLists(true);
    try {
      const data = await api.get<MailingList[]>("/mailing/lists");
      setLists(data);
      if (data.length === 0) {
        setSelectedListId(null);
      } else if (selectedListId === null || !data.some((item) => item.id === selectedListId)) {
        setSelectedListId(data[0].id);
      }
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "Failed to load mailing lists"
      );
    } finally {
      setIsLoadingLists(false);
    }
  }, [selectedListId]);

  const refreshSubscribers = useCallback(async (mailingListId: number) => {
    setIsLoadingSubscribers(true);
    try {
      const data = await api.get<Subscriber[]>(
        `/mailing/lists/${mailingListId}/subscribers`
      );
      setSubscribers(data);
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "Failed to load subscribers"
      );
    } finally {
      setIsLoadingSubscribers(false);
    }
  }, []);

  useEffect(() => {
    void refreshLists();
  }, [refreshLists]);

  useEffect(() => {
    if (selectedListId) {
      void refreshSubscribers(selectedListId);
    } else {
      setSubscribers([]);
    }
  }, [refreshSubscribers, selectedListId]);

  const handleCreateOrUpdateList = async () => {
    clearMessages();
    if (!listForm.name.trim()) {
      setErrorMessage("List name is required");
      return;
    }

    const geographicRegions = listForm.geographicRegions
      .split(",")
      .map((region) => region.trim())
      .filter(Boolean);

    const payload = {
      name: listForm.name.trim(),
      geographic_regions: geographicRegions,
      description: listForm.description.trim() || null,
    };

    setIsSaving(true);
    try {
      if (listForm.id) {
        await api.put<MailingList>(`/mailing/lists/${listForm.id}`, payload);
        setSuccessMessage("Mailing list updated");
      } else {
        await api.post<MailingList>("/mailing/lists", payload);
        setSuccessMessage("Mailing list created");
      }
      setListForm({ id: null, name: "", geographicRegions: "", description: "" });
      await refreshLists();
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "Unable to save mailing list"
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleEditList = (mailingList: MailingList) => {
    clearMessages();
    setListForm({
      id: mailingList.id,
      name: mailingList.name,
      geographicRegions: mailingList.geographic_regions.join(", "),
      description: mailingList.description ?? "",
    });
  };

  const handleDeleteList = async (mailingListId: number) => {
    clearMessages();
    setIsSaving(true);
    try {
      await api.delete<void>(`/mailing/lists/${mailingListId}`);
      setSuccessMessage("Mailing list deleted");
      if (selectedListId === mailingListId) {
        setSelectedListId(null);
      }
      await refreshLists();
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "Unable to delete mailing list"
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddSubscriber = async () => {
    if (!selectedListId) {
      setErrorMessage("Choose a mailing list first");
      return;
    }
    clearMessages();
    if (!subscriberEmail.trim()) {
      setErrorMessage("Subscriber email is required");
      return;
    }

    setIsSaving(true);
    try {
      await api.post<Subscriber>(`/mailing/lists/${selectedListId}/subscribers`, {
        email: subscriberEmail.trim(),
        name: subscriberName.trim() || null,
        organization: subscriberOrganization.trim() || null,
      });
      setSuccessMessage("Subscriber added");
      setSubscriberEmail("");
      setSubscriberName("");
      setSubscriberOrganization("");
      await refreshSubscribers(selectedListId);
      await refreshLists();
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "Unable to add subscriber"
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteSubscriber = async (subscriberId: number) => {
    if (!selectedListId) {
      return;
    }
    clearMessages();
    setIsSaving(true);
    try {
      await api.delete<void>(
        `/mailing/lists/${selectedListId}/subscribers/${subscriberId}`
      );
      setSuccessMessage("Subscriber removed");
      await refreshSubscribers(selectedListId);
      await refreshLists();
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "Unable to remove subscriber"
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleCsvImport = async () => {
    if (!selectedListId) {
      setErrorMessage("Choose a mailing list first");
      return;
    }
    if (!csvFile) {
      setErrorMessage("Select a CSV file first");
      return;
    }

    clearMessages();
    setIsSaving(true);
    try {
      const formData = new FormData();
      formData.append("file", csvFile);
      const result = await api.postForm<CsvImportResult>(
        `/mailing/lists/${selectedListId}/subscribers/import-csv`,
        formData
      );
      setSuccessMessage(
        `CSV import complete: ${result.imported_count} added, ${result.skipped_count} skipped, ${result.invalid_rows} invalid`
      );
      setCsvFile(null);
      await refreshSubscribers(selectedListId);
      await refreshLists();
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "CSV import failed"
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
          <h1 className="text-3xl font-bold tracking-tight">Mailing Lists</h1>
          <p className="text-muted-foreground">
            Create geographic lists, manage subscribers, and import CSV data.
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

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Mailing Lists</CardTitle>
              <CardDescription>
                Geographic region matching drives auto dispatch suggestions.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isAdmin ? (
                <div className="grid gap-2">
                  <Input
                    placeholder="List name"
                    value={listForm.name}
                    onChange={(event) =>
                      setListForm((prev) => ({ ...prev, name: event.target.value }))
                    }
                  />
                  <Input
                    placeholder="Geographic regions (comma-separated)"
                    value={listForm.geographicRegions}
                    onChange={(event) =>
                      setListForm((prev) => ({
                        ...prev,
                        geographicRegions: event.target.value,
                      }))
                    }
                  />
                  <Input
                    placeholder="Description"
                    value={listForm.description}
                    onChange={(event) =>
                      setListForm((prev) => ({
                        ...prev,
                        description: event.target.value,
                      }))
                    }
                  />
                  <div className="flex gap-2">
                    <Button onClick={handleCreateOrUpdateList} disabled={isSaving}>
                      {listForm.id ? "Update List" : "Create List"}
                    </Button>
                    {listForm.id ? (
                      <Button
                        variant="outline"
                        onClick={() =>
                          setListForm({
                            id: null,
                            name: "",
                            geographicRegions: "",
                            description: "",
                          })
                        }
                        disabled={isSaving}
                      >
                        Cancel Edit
                      </Button>
                    ) : null}
                  </div>
                </div>
              ) : null}

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Regions</TableHead>
                    <TableHead>Subscribers</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoadingLists ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-muted-foreground">
                        Loading mailing lists...
                      </TableCell>
                    </TableRow>
                  ) : lists.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-muted-foreground">
                        No mailing lists yet.
                      </TableCell>
                    </TableRow>
                  ) : (
                    lists.map((mailingList) => (
                      <TableRow
                        key={mailingList.id}
                        className={
                          selectedListId === mailingList.id
                            ? "bg-accent/40"
                            : undefined
                        }
                      >
                        <TableCell>
                          <button
                            className="cursor-pointer text-left font-medium hover:underline"
                            onClick={() => setSelectedListId(mailingList.id)}
                            type="button"
                          >
                            {mailingList.name}
                          </button>
                        </TableCell>
                        <TableCell className="max-w-56 text-wrap">
                          {mailingList.geographic_regions.join(", ") || "All regions"}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{mailingList.subscriber_count}</Badge>
                        </TableCell>
                        <TableCell>
                          {isAdmin ? (
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleEditList(mailingList)}
                                disabled={isSaving}
                              >
                                Edit
                              </Button>
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={() => handleDeleteList(mailingList.id)}
                                disabled={isSaving}
                              >
                                Delete
                              </Button>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">View only</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Subscribers</CardTitle>
              <CardDescription>
                {selectedList
                  ? `Managing subscribers for ${selectedList.name}`
                  : "Select a mailing list to manage subscribers"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedList && isAdmin ? (
                <>
                  <div className="grid gap-2">
                    <Input
                      type="email"
                      placeholder="Subscriber email"
                      value={subscriberEmail}
                      onChange={(event) => setSubscriberEmail(event.target.value)}
                    />
                    <Input
                      placeholder="Name (optional)"
                      value={subscriberName}
                      onChange={(event) => setSubscriberName(event.target.value)}
                    />
                    <Input
                      placeholder="Organization (optional)"
                      value={subscriberOrganization}
                      onChange={(event) => setSubscriberOrganization(event.target.value)}
                    />
                    <Button onClick={handleAddSubscriber} disabled={isSaving}>
                      Add Subscriber
                    </Button>
                  </div>
                  <div className="grid gap-2 rounded-md border p-3">
                    <p className="text-sm font-medium">CSV Import</p>
                    <Input
                      type="file"
                      accept=".csv"
                      onChange={(event) => setCsvFile(event.target.files?.[0] ?? null)}
                    />
                    <Button variant="outline" onClick={handleCsvImport} disabled={isSaving}>
                      Import CSV
                    </Button>
                  </div>
                </>
              ) : null}

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Organization</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {!selectedList ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-muted-foreground">
                        Select a list to view subscribers.
                      </TableCell>
                    </TableRow>
                  ) : isLoadingSubscribers ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-muted-foreground">
                        Loading subscribers...
                      </TableCell>
                    </TableRow>
                  ) : subscribers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-muted-foreground">
                        No subscribers in this list.
                      </TableCell>
                    </TableRow>
                  ) : (
                    subscribers.map((subscriber) => (
                      <TableRow key={subscriber.id}>
                        <TableCell>{subscriber.email}</TableCell>
                        <TableCell>{subscriber.name || "-"}</TableCell>
                        <TableCell>{subscriber.organization || "-"}</TableCell>
                        <TableCell>
                          {isAdmin ? (
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleDeleteSubscriber(subscriber.id)}
                              disabled={isSaving}
                            >
                              Remove
                            </Button>
                          ) : (
                            <span className="text-xs text-muted-foreground">View only</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
