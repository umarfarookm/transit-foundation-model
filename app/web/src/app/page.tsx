"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

// Pre-computed demo answers from the actual model
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

const EXAMPLE_QUESTIONS = Object.keys(DEMO_QA).slice(0, 5);

type Mode = "demo" | "local";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<Mode>("demo");
  const [apiUrl, setApiUrl] = useState("http://localhost:8000");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMessage: Message = { role: "user", content: question.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      let answer: string;

      if (mode === "demo") {
        // Check for exact match or find closest
        await new Promise((r) => setTimeout(r, 500)); // Simulate delay
        const key = Object.keys(DEMO_QA).find(
          (k) => k.toLowerCase() === question.trim().toLowerCase()
        );
        answer = key
          ? DEMO_QA[key]
          : "This is a demo mode with pre-computed answers. Try one of the example questions, or switch to 'Live Mode' to connect to the local API server for real-time responses.";
      } else {
        // Call local FastAPI backend
        const response = await fetch(`${apiUrl}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: question.trim() }),
        });
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        const data = await response.json();
        answer = data.answer;
      }

      setMessages((prev) => [...prev, { role: "assistant", content: answer }]);
    } catch (error: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            mode === "local"
              ? `Could not connect to ${apiUrl}. Make sure the backend is running:\n\n.venv/bin/uvicorn app.api.main:app --port 8000`
              : `Error: ${error.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {/* Header */}
      <header className="bg-blue-600 text-white p-4 shadow-md">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">UmarTransit-1B</h1>
            <p className="text-blue-100 text-sm">
              AI assistant for public transit & GTFS data
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={mode}
              onChange={(e) => {
                setMode(e.target.value as Mode);
                setMessages([]);
              }}
              className="bg-blue-700 text-white text-xs rounded px-2 py-1 border border-blue-400"
            >
              <option value="demo">Demo Mode</option>
              <option value="local">Live Mode (local API)</option>
            </select>
          </div>
        </div>
        {mode === "demo" && (
          <p className="text-blue-200 text-xs mt-1">
            Showing pre-computed answers. Switch to Live Mode to run the actual model.
          </p>
        )}
        {mode === "local" && (
          <p className="text-blue-200 text-xs mt-1">
            Connected to {apiUrl}
          </p>
        )}
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <h2 className="text-lg font-semibold text-gray-700 mb-2">
              Ask me about transit systems & GTFS
            </h2>
            <p className="text-gray-500 text-sm mb-4">
              {mode === "demo"
                ? "Click an example question to see a pre-computed answer from UmarTransit-1B."
                : "Make sure the backend is running locally, then ask any transit question."}
            </p>
            <div className="space-y-2">
              {EXAMPLE_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(q)}
                  className="block w-full text-left p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-colors text-sm text-gray-700"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-white border border-gray-200 text-gray-800"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
              <div className="flex space-x-1 items-center">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                <span className="text-xs text-gray-400 ml-2">
                  {mode === "demo" ? "Loading..." : "Generating response..."}
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t border-gray-200">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about transit routes, GTFS, schedules..."
            className="flex-1 border border-gray-300 rounded-full px-4 py-2 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded-full text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
      </form>

      {/* Footer */}
      <div className="bg-gray-100 px-4 py-2 text-center">
        <p className="text-xs text-gray-500">
          Powered by{" "}
          <a
            href="https://huggingface.co/umarfarookm/UmarTransit-1B"
            target="_blank"
            className="text-blue-500 hover:underline"
          >
            UmarTransit-1B
          </a>
          {" | "}
          <a
            href="https://github.com/umarfarookm/transit-foundation-model"
            target="_blank"
            className="text-blue-500 hover:underline"
          >
            GitHub
          </a>
        </p>
      </div>
    </div>
  );
}
