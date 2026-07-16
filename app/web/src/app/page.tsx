"use client";

import { useState } from "react";
import ChatTab from "@/components/ChatTab";
import ExplorerTab from "@/components/ExplorerTab";

type Tab = "chat" | "explorer";

export default function Home() {
  const [tab, setTab] = useState<Tab>("chat");

  return (
    <div className="flex flex-col h-screen">
      {/* ── Header ── */}
      <header className="flex items-center justify-between border-b px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground text-sm font-bold">
            T
          </div>
          <div>
            <h1 className="text-sm font-semibold leading-none">UmarTransit-1B</h1>
            <p className="text-xs text-muted-foreground mt-0.5">Transit & GTFS assistant</p>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center gap-1 rounded-lg border p-0.5">
          <button
            onClick={() => setTab("chat")}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              tab === "chat"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Chat
          </button>
          <button
            onClick={() => setTab("explorer")}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              tab === "explorer"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Feed Explorer
          </button>
        </div>
      </header>

      {/* ── Tab content ── */}
      {tab === "chat" ? <ChatTab /> : <ExplorerTab />}

      {/* ── Footer ── */}
      <div className="px-5 py-1.5 text-center text-[11px] text-muted-foreground border-t">
        <a
          href="https://huggingface.co/umarfarookm/UmarTransit-1B"
          target="_blank"
          className="hover:text-foreground transition-colors"
        >
          HuggingFace
        </a>
        <span className="mx-1.5">·</span>
        <a
          href="https://github.com/umarfarookm/transit-foundation-model"
          target="_blank"
          className="hover:text-foreground transition-colors"
        >
          GitHub
        </a>
        <span className="mx-1.5">·</span>
        <span>Apache 2.0</span>
      </div>
    </div>
  );
}
