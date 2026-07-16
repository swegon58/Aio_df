"use client";

import { Menu, MessageSquarePlusIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { WorkspaceChannelsList } from "@/components/workspace/channels/workspace-channels-list";
import { RecentChatList } from "@/components/workspace/recent-chat-list";
import { SettingsDialog } from "@/components/workspace/settings";
import { useI18n } from "@/core/i18n/hooks";

import { IconRail } from "./icon-rail";
import { useIconRailItems, type IconRailKey } from "./use-icon-rail-items";

export function WorkspaceIconRail() {
  const { t } = useI18n();
  const router = useRouter();
  const items = useIconRailItems();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [chatsOpen, setChatsOpen] = useState(false);
  const [channelsOpen, setChannelsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const handleItemClick = (key: string) => {
    setMobileOpen(false);
    switch (key as IconRailKey) {
      case "chats":
        setChatsOpen(true);
        break;
      case "channels":
        setChannelsOpen(true);
        break;
      case "settings":
        setSettingsOpen(true);
        break;
      case "agents":
        router.push("/workspace/agents");
        break;
    }
  };

  return (
    <>
      <div className="icon-rail-slot">
        <nav className="icon-rail icon-rail--compact">
          <div className="icon-rail-main">
            <IconRail
              variant="compact"
              items={items}
              onItemClick={handleItemClick}
            />
          </div>
        </nav>
      </div>

      <button
        type="button"
        className="icon-rail-mobile-toggle"
        style={mobileOpen ? { display: "none" } : undefined}
        onClick={() => setMobileOpen(true)}
        aria-label="Open navigation"
      >
        <Menu className="w-4.5 h-4.5" />
      </button>

      <div className={`icon-rail-mobile-sheet${mobileOpen ? " open" : ""}`}>
        <div
          className="icon-rail-mobile-sheet-backdrop"
          onClick={() => setMobileOpen(false)}
        />
        <nav className="icon-rail" style={{ width: "80vw", maxWidth: 320 }}>
          <IconRail
            variant="mobile"
            items={items}
            onItemClick={handleItemClick}
          />
        </nav>
      </div>

      <Dialog open={chatsOpen} onOpenChange={setChatsOpen}>
        <DialogContent
          className="flex max-h-[75vh] flex-col sm:max-w-md"
          aria-describedby={undefined}
        >
          <DialogHeader>
            <DialogTitle>{t.sidebar.chats}</DialogTitle>
          </DialogHeader>
          <Button asChild className="w-full" onClick={() => setChatsOpen(false)}>
            <Link href="/workspace/chats/new">
              <MessageSquarePlusIcon className="mr-2 size-4" />
              {t.sidebar.newChat}
            </Link>
          </Button>
          <ScrollArea className="min-h-0 flex-1">
            <RecentChatList />
          </ScrollArea>
        </DialogContent>
      </Dialog>

      <Dialog open={channelsOpen} onOpenChange={setChannelsOpen}>
        <DialogContent
          className="flex max-h-[75vh] flex-col sm:max-w-md"
          aria-describedby={undefined}
        >
          <DialogHeader>
            <DialogTitle>{t.sidebar.channels}</DialogTitle>
          </DialogHeader>
          <ScrollArea className="min-h-0 flex-1">
            <WorkspaceChannelsList />
          </ScrollArea>
        </DialogContent>
      </Dialog>

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
