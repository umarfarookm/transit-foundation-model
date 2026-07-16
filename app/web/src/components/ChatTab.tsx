"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Message {
  role: "user" | "assistant";
  content: string;
  time?: number;
  tokens?: number;
}

const DEMO_QA: Record<string, string> = {
  "What does route_type 3 mean in GTFS?":
    "In the GTFS specification, route_type 3 indicates Bus service. This is the most common route type and covers short- and long-distance bus routes.",
  "What are the required files in a GTFS feed?":
    "A valid GTFS feed must include the following required files: agency.txt (transit agency information), routes.txt (transit routes), trips.txt (trips for each route), stops.txt (individual stop locations), stop_times.txt (times a vehicle arrives at and departs from stops), and either calendar.txt or calendar_dates.txt (service dates). Optional files include shapes.txt, transfers.txt, frequencies.txt, and feed_info.txt.",
  "How many routes does the Chicago Transit Authority operate?":
    "The Chicago Transit Authority (CTA) operates 133 routes. 8 are Subway/Metro routes and 125 are Bus routes.",
  "What is the difference between calendar.txt and calendar_dates.txt?":
    "calendar.txt defines regular weekly service patterns using day-of-week flags (monday through sunday) with a start and end date range. calendar_dates.txt defines exceptions to the regular schedule — adding service on specific dates (exception_type=1) or removing service (exception_type=2). A feed can use calendar.txt alone, calendar_dates.txt alone, or both together.",
  "What transit modes does Auckland Transport operate?":
    "Auckland Transport operates the following transit services: 5 Rail/Commuter rail routes, 206 Bus routes, 15 Ferry routes. In total, the agency has 226 routes.",
  "Can GTFS times exceed 24:00:00?":
    "Yes, GTFS allows times greater than 24:00:00 in stop_times.txt. This is used for trips that extend past midnight relative to the service day. For example, a departure time of 25:30:00 means 1:30 AM the day after the service day starts.",
  "What is GTFS?":
    "GTFS (General Transit Feed Specification) is an open standard for sharing public transit schedule, route, and stop information. Originally developed by Google and TriMet (Portland, OR) in 2005, it defines a common format using CSV files packaged in a ZIP archive. GTFS enables transit agencies to publish their data and allows developers to build applications like trip planners.",
  "What transfer types are defined in GTFS?":
    "GTFS defines four transfer types in transfers.txt: Type 0 is a recommended transfer point between routes. Type 1 is a timed transfer where the departing vehicle waits for the arriving vehicle. Type 2 requires a minimum transfer time (specified in min_transfer_time). Type 3 means transfers are not possible between the stops.",
};

const EXAMPLES = [
  "What is GTFS?",
  "What does route_type 3 mean in GTFS?",
  "How many routes does the Chicago Transit Authority operate?",
  "What are the required files in a GTFS feed?",
  "Can GTFS times exceed 24:00:00?",
];

type Mode = "demo" | "local";

export default function ChatTab() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<Mode>("demo");
  const [apiUrl] = useState("http://localhost:8000");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (question: string) => {
    if (!question.trim() || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: question.trim() }]);
    setInput("");
    setLoading(true);

    try {
      let answer: string;
      let time: number | undefined;
      let tokens: number | undefined;

      if (mode === "demo") {
        await new Promise((r) => setTimeout(r, 500));
        const key = Object.keys(DEMO_QA).find(
          (k) => k.toLowerCase() === question.trim().toLowerCase()
        );
        answer = key
          ? DEMO_QA[key]
          : "This question isn\u2019t in the demo set. Try one of the examples above, or switch to Live Mode for real-time answers.";
        time = 0.5;
        tokens = answer.split(" ").length;
      } else {
        const res = await fetch(`${apiUrl}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: question.trim() }),
        });
        if (!res.ok) throw new Error(`API ${res.status}`);
        const data = await res.json();
        answer = data.answer;
        time = data.time_seconds;
        tokens = data.tokens;
      }

      setMessages((prev) => [...prev, { role: "assistant", content: answer, time, tokens }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            mode === "local"
              ? `Could not reach ${apiUrl}. Is the backend running?\n\nuvicorn app.api.main:app --port 8000`
              : "Something went wrong.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Mode selector */}
      <div className="flex items-center justify-end gap-3 px-5 py-2 border-b">
        <div className="flex items-center gap-2">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              mode === "demo" ? "bg-amber-500" : "bg-emerald-500"
            }`}
          />
          <select
            value={mode}
            onChange={(e) => {
              setMode(e.target.value as Mode);
              setMessages([]);
            }}
            className="bg-transparent text-xs text-muted-foreground cursor-pointer focus:outline-none"
          >
            <option value="demo">Demo</option>
            <option value="local">Live</option>
          </select>
        </div>

        {messages.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setMessages([])}
            className="h-7 px-2 text-xs text-muted-foreground"
          >
            Clear
          </Button>
        )}
      </div>

      {/* Chat area */}
      <ScrollArea className="flex-1">
        <div className="mx-auto max-w-2xl px-5 py-6">
          {messages.length === 0 && (
            <div className="space-y-6 pt-4">
              <div>
                <h2 className="text-lg font-semibold">What do you want to know?</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  {mode === "demo"
                    ? "Pick a question below or type one of the examples."
                    : "Ask anything about transit systems and GTFS data."}
                </p>
              </div>

              <div className="grid gap-2">
                {EXAMPLES.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="text-left rounded-lg border px-3.5 py-2.5 text-sm text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>

              <Separator />

              <div className="flex flex-wrap gap-2">
                {["15 agencies", "10 countries", "11K routes", "ROUGE-L 0.82"].map((s) => (
                  <Badge key={s} variant="secondary" className="font-normal">
                    {s}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className="msg-enter mb-4">
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
                    msg.role === "user"
                      ? "bg-secondary border-transparent"
                      : "bg-card"
                  }`}
                >
                  <CardContent className="p-3">
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </p>
                  </CardContent>
                </Card>

                {msg.role === "user" && (
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-secondary text-[11px] font-bold text-secondary-foreground">
                    U
                  </div>
                )}
              </div>

              {msg.role === "assistant" && msg.time != null && (
                <p className="ml-9 mt-1 text-[11px] text-muted-foreground">
                  {msg.time}s
                  {msg.tokens != null && <span className="ml-2">{msg.tokens} tokens</span>}
                </p>
              )}
            </div>
          ))}

          {loading && (
            <div className="msg-enter flex gap-3 mb-4">
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
      </ScrollArea>

      {/* Input */}
      <div className="border-t px-5 py-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="mx-auto flex max-w-2xl gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about routes, stops, GTFS spec..."
            disabled={loading}
            className="flex-1"
          />
          <Button type="submit" disabled={loading || !input.trim()} size="sm">
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}
