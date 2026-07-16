"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import FeedDashboard from "./FeedDashboard";
import { uploadFeed, askFeedQuestion } from "@/lib/api";
import {
  DEMO_FEED_SUMMARY,
  DEMO_FEED_VALIDATION,
  DEMO_FEED_QA,
  DEMO_FEED_EXAMPLES,
} from "@/lib/demo-feed";
import type { FeedSummary, FeedValidation } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  time?: number;
}

type Mode = "demo" | "local";

export default function ExplorerTab() {
  const [mode, setMode] = useState<Mode>("demo");
  const [status, setStatus] = useState<"idle" | "uploading" | "loaded" | "error">("idle");
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [summary, setSummary] = useState<FeedSummary | null>(null);
  const [validation, setValidation] = useState<FeedValidation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load demo feed on mount or mode switch
  useEffect(() => {
    if (mode === "demo") {
      setSummary(DEMO_FEED_SUMMARY);
      setValidation(DEMO_FEED_VALIDATION);
      setStatus("loaded");
      setUploadId(null);
      setMessages([]);
      setError(null);
    } else {
      setSummary(null);
      setValidation(null);
      setStatus("idle");
      setUploadId(null);
      setMessages([]);
      setError(null);
    }
  }, [mode]);

  const handleUpload = async (file: File) => {
    if (file.size > 100 * 1024 * 1024) {
      setError("File too large. Maximum size is 100 MB.");
      setStatus("error");
      return;
    }
    if (!file.name.endsWith(".zip")) {
      setError("Please upload a .zip file.");
      setStatus("error");
      return;
    }

    setStatus("uploading");
    setError(null);
    setMessages([]);

    try {
      const result = await uploadFeed(file);
      setValidation(result.validation);

      if (result.summary && result.upload_id) {
        setSummary(result.summary);
        setUploadId(result.upload_id);
        setStatus("loaded");
      } else {
        setError(
          result.validation.errors.length > 0
            ? result.validation.errors.join(". ")
            : "Could not process feed."
        );
        setStatus("error");
      }
    } catch (e) {
      setError(`Upload failed. Is the backend running?\n\nuvicorn app.api.main:app --port 8000`);
      setStatus("error");
    }
  };

  const askQuestion = async (question: string) => {
    if (!question.trim() || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: question.trim() }]);
    setInput("");
    setLoading(true);

    try {
      let answer: string;
      let time: number | undefined;

      if (mode === "demo") {
        await new Promise((r) => setTimeout(r, 500));
        const key = Object.keys(DEMO_FEED_QA).find(
          (k) => k.toLowerCase() === question.trim().toLowerCase()
        );
        answer = key
          ? DEMO_FEED_QA[key]
          : "This question isn\u2019t in the demo set. Try one of the suggested questions, or switch to Live Mode to upload your own feed.";
        time = 0.5;
      } else if (uploadId) {
        const res = await askFeedQuestion(uploadId, question.trim());
        answer = res.answer;
        time = res.time_seconds;
      } else {
        answer = "No feed loaded. Please upload a GTFS ZIP first.";
      }

      setMessages((prev) => [...prev, { role: "assistant", content: answer, time }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Failed to get answer. Is the backend running?" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setSummary(null);
    setValidation(null);
    setUploadId(null);
    setMessages([]);
    setError(null);
    setStatus(mode === "demo" ? "loaded" : "idle");
    if (mode === "demo") {
      setSummary(DEMO_FEED_SUMMARY);
      setValidation(DEMO_FEED_VALIDATION);
    }
  };

  const examples = mode === "demo" ? DEMO_FEED_EXAMPLES : [
    "How many routes does this agency operate?",
    "What is the busiest route?",
    "What transit modes are available?",
    "How many stops are in the network?",
  ];

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Mode selector */}
      <div className="flex items-center justify-between px-5 py-2 border-b">
        <div className="flex items-center gap-3">
          {status === "loaded" && mode === "local" && (
            <Button
              variant="ghost"
              size="sm"
              onClick={reset}
              className="h-7 px-2 text-xs text-muted-foreground"
            >
              Upload new feed
            </Button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              mode === "demo" ? "bg-amber-500" : "bg-emerald-500"
            }`}
          />
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as Mode)}
            className="bg-transparent text-xs text-muted-foreground cursor-pointer focus:outline-none"
          >
            <option value="demo">Demo</option>
            <option value="local">Live</option>
          </select>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="mx-auto max-w-3xl px-5 py-6">
          {/* Upload area (live mode, no feed loaded) */}
          {status === "idle" && mode === "local" && (
            <div className="space-y-6 pt-4">
              <div>
                <h2 className="text-lg font-semibold">Upload a GTFS Feed</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Upload a GTFS ZIP file to explore routes, stops, schedules, and ask AI-powered questions about your data.
                </p>
              </div>

              <div
                onClick={() => fileRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  const file = e.dataTransfer.files[0];
                  if (file) handleUpload(file);
                }}
                className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 hover:border-primary/40 p-12 cursor-pointer transition-colors"
              >
                <p className="text-sm text-muted-foreground">Drop a GTFS ZIP here or click to browse</p>
                <p className="text-xs text-muted-foreground/60 mt-1">Max 100 MB</p>
              </div>

              <input
                ref={fileRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUpload(file);
                }}
              />
            </div>
          )}

          {/* Uploading state */}
          {status === "uploading" && (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="flex items-center gap-2">
                {[0, 1, 2].map((d) => (
                  <span
                    key={d}
                    className="h-2 w-2 rounded-full bg-primary animate-bounce"
                    style={{ animationDelay: `${d * 150}ms` }}
                  />
                ))}
              </div>
              <p className="text-sm text-muted-foreground mt-4">Processing feed...</p>
              <p className="text-xs text-muted-foreground/60 mt-1">This may take 10-30 seconds</p>
            </div>
          )}

          {/* Error state */}
          {status === "error" && (
            <div className="space-y-4 pt-4">
              <Card className="border-red-200 bg-red-50/50">
                <CardContent className="p-4">
                  <p className="text-sm text-red-700 whitespace-pre-wrap">{error}</p>
                </CardContent>
              </Card>
              <Button variant="outline" size="sm" onClick={reset}>
                Try again
              </Button>
            </div>
          )}

          {/* Dashboard + Q&A */}
          {status === "loaded" && summary && validation && (
            <div className="space-y-6">
              <FeedDashboard summary={summary} validation={validation} />

              {/* Q&A section */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium">Ask about this feed</h3>

                {messages.length === 0 && (
                  <div className="grid gap-2">
                    {examples.map((q) => (
                      <button
                        key={q}
                        onClick={() => askQuestion(q)}
                        className="text-left rounded-lg border px-3.5 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}

                {messages.map((msg, i) => (
                  <div key={i} className="msg-enter mb-3">
                    <div
                      className={`flex gap-3 ${
                        msg.role === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      {msg.role === "assistant" && (
                        <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary text-[11px] font-bold text-primary-foreground">
                          T
                        </div>
                      )}
                      <Card
                        className={`max-w-[80%] ${
                          msg.role === "user" ? "bg-secondary border-transparent" : "bg-card"
                        }`}
                      >
                        <CardContent className="p-3">
                          <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                        </CardContent>
                      </Card>
                      {msg.role === "user" && (
                        <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-secondary text-[11px] font-bold text-secondary-foreground">
                          U
                        </div>
                      )}
                    </div>
                    {msg.role === "assistant" && msg.time != null && (
                      <p className="ml-9 mt-1 text-[11px] text-muted-foreground">{msg.time}s</p>
                    )}
                  </div>
                ))}

                {loading && (
                  <div className="msg-enter flex gap-3 mb-3">
                    <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary text-[11px] font-bold text-primary-foreground">
                      T
                    </div>
                    <Card className="bg-card">
                      <CardContent className="p-3 flex items-center gap-1">
                        {[0, 1, 2].map((d) => (
                          <span
                            key={d}
                            className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce"
                            style={{ animationDelay: `${d * 150}ms` }}
                          />
                        ))}
                        <span className="ml-2 text-xs text-muted-foreground">
                          {mode === "demo" ? "Loading..." : "Generating..."}
                        </span>
                      </CardContent>
                    </Card>
                  </div>
                )}

                <div ref={bottomRef} />
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input (only when feed is loaded) */}
      {status === "loaded" && (
        <div className="border-t px-5 py-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              askQuestion(input);
            }}
            className="mx-auto flex max-w-3xl gap-2"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about this feed..."
              disabled={loading}
              className="flex-1"
            />
            <Button type="submit" disabled={loading || !input.trim()} size="sm">
              Ask
            </Button>
          </form>
        </div>
      )}
    </div>
  );
}
