import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GroupImperativeHandle } from "react-resizable-panels";

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { env } from "@/env";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";

import { useArtifacts } from "../artifacts";
import { useThread } from "../messages/context";

import { RightStatusPanel } from "./right-status-panel";

const CLOSE_MODE = { chat: 100, right: 0 };
const OPEN_MODE = { chat: 60, right: 40 };
const CLOSE_MODE_WITH_STATUS = { chat: 70, right: 30 };
const OPEN_MODE_WITH_STATUS = { chat: 40, right: 60 };

const ChatBox: React.FC<{ children: React.ReactNode; threadId: string }> = ({
  children,
  threadId,
}) => {
  const { thread } = useThread();
  const pathname = usePathname();
  const threadIdRef = useRef(threadId);
  const layoutRef = useRef<GroupImperativeHandle>(null);
  const isMobile = useIsMobile();

  const {
    artifacts,
    open: artifactsOpen,
    setArtifacts,
    select: selectArtifact,
    deselect,
    selectedArtifact,
  } = useArtifacts();

  const [autoSelectFirstArtifact, setAutoSelectFirstArtifact] = useState(true);
  useEffect(() => {
    const threadArtifacts = Array.isArray(thread.values.artifacts)
      ? thread.values.artifacts
      : undefined;

    if (threadIdRef.current !== threadId) {
      threadIdRef.current = threadId;
      deselect();
      setArtifacts([]);
    }

    // Update artifacts from the current thread
    if (threadArtifacts) {
      setArtifacts(threadArtifacts);
    }

    // DO NOT automatically deselect the artifact when switching threads, because the artifacts auto discovering is not work now.
    // if (
    //   selectedArtifact &&
    //   !thread.values.artifacts?.includes(selectedArtifact)
    // ) {
    //   deselect();
    // }

    if (
      env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" &&
      autoSelectFirstArtifact
    ) {
      if (threadArtifacts && threadArtifacts.length > 0) {
        setAutoSelectFirstArtifact(false);
        selectArtifact(threadArtifacts[0]!);
      }
    }
  }, [
    threadId,
    autoSelectFirstArtifact,
    deselect,
    selectArtifact,
    selectedArtifact,
    setArtifacts,
    thread.values.artifacts,
  ]);

  const artifactPanelOpen = useMemo(() => {
    if (env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true") {
      return artifactsOpen && artifacts?.length > 0;
    }
    return artifactsOpen;
  }, [artifactsOpen, artifacts]);

  const resizableIdBase = useMemo(() => {
    return pathname.replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
  }, [pathname]);

  useEffect(() => {
    if (layoutRef.current) {
      if (isMobile) {
        layoutRef.current.setLayout(artifactPanelOpen ? OPEN_MODE : CLOSE_MODE);
      } else {
        layoutRef.current.setLayout(
          artifactPanelOpen ? OPEN_MODE_WITH_STATUS : CLOSE_MODE_WITH_STATUS,
        );
      }
    }
  }, [artifactPanelOpen, isMobile]);

  return (
    <ResizablePanelGroup
      id={`${resizableIdBase}-panels`}
      orientation="horizontal"
      defaultLayout={CLOSE_MODE_WITH_STATUS}
      groupRef={layoutRef}
    >
      <ResizablePanel className="relative" defaultSize={100} id="chat">
        {children}
      </ResizablePanel>
      <ResizableHandle
        id={`${resizableIdBase}-separator`}
        className={cn(
          "opacity-33 hover:opacity-100",
          isMobile && !artifactPanelOpen && "pointer-events-none opacity-0",
        )}
      />
      <ResizablePanel
        className="border-border/60 border-l"
        defaultSize={30}
        minSize={artifactPanelOpen ? 20 : 0}
        id="right"
      >
        <RightStatusPanel
          threadId={threadId}
          artifactPanelOpen={artifactPanelOpen}
        />
      </ResizablePanel>
    </ResizablePanelGroup>
  );
};

export { ChatBox };
