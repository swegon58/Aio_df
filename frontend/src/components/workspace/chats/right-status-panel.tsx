import type { Message } from "@langchain/langgraph-sdk";
import {
  Code2Icon,
  FilesIcon,
  MonitorIcon,
  PanelRightCloseIcon,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ConversationEmptyState } from "@/components/ai-elements/conversation";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { findToolCallResult } from "@/core/messages/utils";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";

import {
  ArtifactFileDetail,
  ArtifactFileList,
  useArtifacts,
} from "../artifacts";
import { EnergyPanelCard } from "../energy/energy-panel-card";
import { useThread } from "../messages/context";

// ponytail: take the latest successful `preview` tool call's result (a URL
// string) as the live dev-server preview. Plan/todos already render in
// message-group.tsx's chain-of-thought, no need to duplicate them here.
function extractLatestPreviewUrl(messages: Message[]): string | undefined {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i];
    if (message?.type !== "ai") continue;
    const toolCalls = message.tool_calls ?? [];
    for (let j = toolCalls.length - 1; j >= 0; j--) {
      const toolCall = toolCalls[j];
      if (toolCall?.name !== "preview" || !toolCall.id) continue;
      const result = findToolCallResult(toolCall.id, messages);
      if (result && !result.startsWith("Error")) return result;
    }
  }
  return undefined;
}

// ponytail: Aio_df only exposes isRunning (no done/error/needs-approval enum
// on this panel), so the mascot mapping covers idle/thinking + the 4
// tool-driven "working" activities. Add lucide-icon fallbacks here if a
// distinct done/error/needs-approval state ever gets surfaced to this panel.
type AgentActivity =
  | "idle"
  | "thinking"
  | "reading"
  | "writing"
  | "coding"
  | "research";

const TOOL_ACTIVITY: Record<string, AgentActivity> = {
  read_file: "reading",
  ls: "reading",
  write_file: "writing",
  str_replace: "writing",
  bash: "coding",
  web_search: "research",
  image_search: "research",
  web_fetch: "research",
};

const MASCOT_IMAGE: Record<AgentActivity, string> = {
  idle: "/mascot/coffee_break.png",
  thinking: "/mascot/thinking.png",
  reading: "/mascot/reading.png",
  writing: "/mascot/writing.png",
  coding: "/mascot/coding.png",
  research: "/mascot/research.png",
};

function extractCurrentActivity(
  messages: Message[],
  isRunning: boolean,
): AgentActivity {
  if (!isRunning) return "idle";
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i];
    if (message?.type !== "ai") continue;
    const toolCalls = message.tool_calls ?? [];
    for (let j = toolCalls.length - 1; j >= 0; j--) {
      const activity = TOOL_ACTIVITY[toolCalls[j]?.name ?? ""];
      if (activity) return activity;
    }
    break;
  }
  return "thinking";
}

export function RightStatusPanel({
  className,
  threadId,
  artifactPanelOpen,
  onCollapse,
}: {
  className?: string;
  threadId: string;
  artifactPanelOpen: boolean;
  onCollapse?: () => void;
}) {
  const { thread } = useThread();
  const isRunning = thread.isLoading;
  const isMobile = useIsMobile();
  const { artifacts, selectedArtifact } = useArtifacts();

  const activity = useMemo(
    () => extractCurrentActivity(thread.messages, isRunning),
    [thread.messages, isRunning],
  );

  const previewUrl = useMemo(
    () => extractLatestPreviewUrl(thread.messages),
    [thread.messages],
  );

  const [tab, setTab] = useState("code");
  useEffect(() => {
    if (selectedArtifact) setTab("code");
  }, [selectedArtifact]);

  // ponytail: Radix unmounts the inactive TabsContent, so switching back into
  // "code" remounts ArtifactFileDetail and its auto-view-mode effect fires
  // again — without this guard it immediately snaps back to "preview" and
  // the Code tab becomes unreachable. Only auto-open preview once per
  // artifact, not on every remount.
  const autoPreviewedArtifactRef = useRef<string | null>(null);
  const handleAutoViewMode = useCallback(
    (mode: "code" | "preview") => {
      if (mode !== "preview") return;
      if (autoPreviewedArtifactRef.current === selectedArtifact) return;
      autoPreviewedArtifactRef.current = selectedArtifact ?? null;
      setTab("preview");
    },
    [selectedArtifact],
  );

  const codeTab = selectedArtifact ? (
    <ArtifactFileDetail
      className="size-full"
      filepath={selectedArtifact}
      threadId={threadId}
      viewMode="code"
      onAutoViewMode={handleAutoViewMode}
    />
  ) : (
    <div className="relative flex size-full justify-center">
      {artifacts.length === 0 ? (
        <ConversationEmptyState
          icon={<FilesIcon />}
          title="No artifact selected"
          description="Select an artifact to view its details"
        />
      ) : (
        <div className="flex size-full max-w-(--container-width-sm) flex-col justify-center p-4 pt-8">
          <header className="shrink-0">
            <h2 className="text-lg font-medium">Artifacts</h2>
          </header>
          <main className="min-h-0 grow">
            <ArtifactFileList
              className="max-w-(--container-width-sm) p-4 pt-12"
              files={artifacts}
              threadId={threadId}
            />
          </main>
        </div>
      )}
    </div>
  );

  // ponytail: mobile keeps the old artifacts-only surface (no Preview chrome)
  // — same slide transition it always had, just relocated here.
  if (isMobile) {
    return (
      <div
        className={cn(
          "h-full p-4 transition-transform duration-300 ease-in-out",
          artifactPanelOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        {codeTab}
      </div>
    );
  }

  const previewTab = previewUrl ? (
    <iframe className="size-full" src={previewUrl} title="Live preview" />
  ) : selectedArtifact ? (
    <ArtifactFileDetail
      className="size-full"
      filepath={selectedArtifact}
      threadId={threadId}
      viewMode="preview"
    />
  ) : (
    <ConversationEmptyState
      className="text-muted-foreground size-full p-4 text-xs [&_h3]:text-xs [&_p]:text-xs"
      icon={<MonitorIcon className="size-5" />}
      title="No preview yet"
      description="Live preview appears here once the agent starts a dev server in the sandbox."
    />
  );

  return (
    // ponytail: `relative` isn't cosmetic — the fixed DotGrid canvas behind
    // workspace content paints in the CSS z-index:0 stacking step, which sits
    // ABOVE non-positioned static content. Without this, the dot canvas
    // renders on top of Code/Preview at 60% opacity, looking like a
    // transparent panel with a background showing through.
    <div className={cn("relative flex h-full flex-col gap-4 p-4", className)}>
      <div className="glass-surface flex items-center gap-3 rounded-lg p-4">
        <div className="icon-badge-glass flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full">
          <img
            src={MASCOT_IMAGE[activity]}
            alt={activity}
            className="size-full object-cover"
          />
        </div>
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="text-sm font-medium">Agent</span>
          <span className="text-muted-foreground flex items-center gap-1.5 text-xs">
            <span
              className={cn(
                "size-1.5 rounded-full",
                isRunning
                  ? "bg-primary animate-pulse"
                  : "bg-muted-foreground/50",
              )}
            />
            {isRunning ? "Running" : "Idle"}
          </span>
        </div>
      </div>

      <EnergyPanelCard />

      <Tabs value={tab} onValueChange={setTab} className="min-h-0 flex-1 gap-2">
        <div className="flex items-center justify-between gap-2">
          <TabsList variant="line" className="shrink-0">
            <TabsTrigger value="code" className="gap-1.5 font-mono">
              <Code2Icon className="size-4" />
              Code
            </TabsTrigger>
            <TabsTrigger value="preview" className="gap-1.5 font-mono">
              <MonitorIcon className="size-4" />
              Preview
            </TabsTrigger>
          </TabsList>
          {onCollapse && (
            <Button
              aria-label="Collapse panel"
              className="shrink-0"
              onClick={onCollapse}
              size="icon-sm"
              variant="ghost"
            >
              <PanelRightCloseIcon />
            </Button>
          )}
        </div>

        <TabsContent
          value="code"
          className="border-border bg-card min-h-0 overflow-hidden rounded-lg border"
        >
          {codeTab}
        </TabsContent>

        <TabsContent
          value="preview"
          className="border-border bg-card min-h-0 overflow-hidden rounded-lg border"
        >
          {previewTab}
        </TabsContent>
      </Tabs>
    </div>
  );
}
