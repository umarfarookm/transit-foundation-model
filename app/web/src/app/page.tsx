"use client";

import { useState, useRef, useEffect } from "react";

const HF_MODEL_ID = "umarfarookm/UmarTransit-1B";
const HF_API_URL = `https://api-inference.huggingface.co/models/${HF_MODEL_ID}`;

const SYSTEM_PROMPT =
  "You are UmarTransit-1B, a specialized AI assistant for public transit systems " +
  "and GTFS (General Transit Feed Specification) data. You provide accurate, " +
  "detailed answers about transit routes, stops, schedules, transfers, and GTFS concepts.";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const EXAMPLE_QUESTIONS = [
  "What does route_type 3 mean in GTFS?",
  "What are the required files in a GTFS feed?",
  "How many routes does the Chicago Transit Authority operate?",
  "What is the difference between calendar.txt and calendar_dates.txt?",
  "What transit modes does Auckland Transport operate?",
];

async function queryHuggingFace(question: string, hfToken: string): Promise<string> {
  const prompt = `<|im_start|>system\n${SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n${question}<|im_end|>\n<|im_start|>assistant\n`;

  const response = await fetch(HF_API_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${hfToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      inputs: prompt,
      parameters: {
        max_new_tokens: 256,
        temperature: 0.1,
        top_p: 0.9,
        do_sample: true,
        return_full_text: false,
      },
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    if (response.status === 503) {
      throw new Error("Model is loading. This takes ~2 minutes on first use. Please try again shortly.");
    }
    throw new Error(error.error || `API error: ${response.status}`);
  }

  const data = await response.json();
  let text = data[0]?.generated_text || "";

  // Clean up: remove any trailing special tokens
  text = text.replace(/<\|im_end\|>/g, "").replace(/<\|im_start\|>/g, "").trim();
  return text;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [hfToken, setHfToken] = useState("");
  const [showTokenInput, setShowTokenInput] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const saved = localStorage.getItem("hf_token");
    if (saved) {
      setHfToken(saved);
      setShowTokenInput(false);
    }
  }, []);

  const saveToken = () => {
    if (hfToken.trim()) {
      localStorage.setItem("hf_token", hfToken.trim());
      setShowTokenInput(false);
    }
  };

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMessage: Message = { role: "user", content: question.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const answer = await queryHuggingFace(question.trim(), hfToken);
      setMessages((prev) => [...prev, { role: "assistant", content: answer }]);
    } catch (error: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${error.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  // Token setup screen
  if (showTokenInput) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50 p-4">
        <div className="bg-white rounded-xl shadow-lg p-6 max-w-md w-full">
          <h1 className="text-2xl font-bold text-blue-600 mb-2">UmarTransit-1B</h1>
          <p className="text-gray-600 text-sm mb-4">
            Enter your HuggingFace API token to connect to the model.
            Get one free at{" "}
            <a
              href="https://huggingface.co/settings/tokens"
              target="_blank"
              className="text-blue-500 underline"
            >
              huggingface.co/settings/tokens
            </a>
          </p>
          <input
            type="password"
            value={hfToken}
            onChange={(e) => setHfToken(e.target.value)}
            placeholder="hf_xxxxxxxxxxxx"
            className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm mb-3 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={saveToken}
            disabled={!hfToken.trim()}
            className="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Connect
          </button>
        </div>
      </div>
    );
  }

  // Chat interface
  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {/* Header */}
      <header className="bg-blue-600 text-white p-4 shadow-md flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold">UmarTransit-1B</h1>
          <p className="text-blue-100 text-sm">
            AI assistant for public transit & GTFS data
          </p>
        </div>
        <button
          onClick={() => {
            localStorage.removeItem("hf_token");
            setShowTokenInput(true);
            setHfToken("");
          }}
          className="text-blue-200 hover:text-white text-xs"
        >
          Change token
        </button>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <h2 className="text-lg font-semibold text-gray-700 mb-4">
              Ask me about transit systems & GTFS
            </h2>
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
                <span className="text-xs text-gray-400 ml-2">Generating response...</span>
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
    </div>
  );
}
