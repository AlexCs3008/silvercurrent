"use client";

import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";

const STORAGE_KEY = "silvercurrent.pinned_listing_ids";
const CHANGE_EVENT = "silvercurrent:pinned-changed";
const MAX_PINNED = 3;

type CompareEvent = CustomEvent<{ ids: string[] }>;

function readPinned(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === "string")
      : [];
  } catch {
    return [];
  }
}

function writePinned(ids: string[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  window.dispatchEvent(
    new CustomEvent(CHANGE_EVENT, { detail: { ids } }) as CompareEvent,
  );
}

// `useSyncExternalStore` requires a stable snapshot reference on every call —
// returning a fresh array each time triggers React's "should be cached to
// avoid an infinite loop" warning. We cache the last known list and only
// return a new array when the JSON differs. EMPTY is a singleton for the
// SSR / pre-hydration case.
const EMPTY: readonly string[] = [];
let cachedSnapshot: string[] = [];
let cachedJson = "";

function getSnapshot(): string[] {
  const json = window.localStorage.getItem(STORAGE_KEY) ?? "";
  if (json !== cachedJson) {
    cachedJson = json;
    cachedSnapshot = readPinned();
  }
  return cachedSnapshot;
}

function getServerSnapshot(): string[] {
  return EMPTY as string[];
}

function subscribe(callback: () => void): () => void {
  const onChanged = () => callback();
  const onStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) callback();
  };
  window.addEventListener(CHANGE_EVENT, onChanged);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(CHANGE_EVENT, onChanged);
    window.removeEventListener("storage", onStorage);
  };
}

function usePinned(): [string[], (ids: string[]) => void] {
  const ids = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  return [ids, writePinned];
}

type ComparePinProps = {
  listingId: string;
  /** "compact" is the small pin used in the inventory card. "full" shows a labeled button. */
  variant?: "compact" | "full";
};

/**
 * Toggle pin state for a listing. Persists to localStorage with a cap of 3 —
 * if already at the cap, pinning a fourth evicts the oldest pinned id.
 */
export function ComparePin({ listingId, variant = "compact" }: ComparePinProps) {
  const [pinned, setPinned] = usePinned();
  const isPinned = pinned.includes(listingId);

  function toggle(e?: React.MouseEvent) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (isPinned) {
      setPinned(pinned.filter((id) => id !== listingId));
      return;
    }
    let next = [...pinned, listingId];
    if (next.length > MAX_PINNED) {
      next = next.slice(next.length - MAX_PINNED);
    }
    setPinned(next);
  }

  if (variant === "compact") {
    return (
      <button
        type="button"
        aria-pressed={isPinned}
        aria-label={isPinned ? "Unpin from compare" : "Pin to compare"}
        onClick={toggle}
        className={
          "inline-flex h-6 w-6 items-center justify-center rounded-full text-sm transition " +
          (isPinned
            ? "bg-foreground text-background"
            : "bg-muted text-muted-foreground hover:bg-muted/70")
        }
      >
        {isPinned ? "•" : "+"}
      </button>
    );
  }

  return (
    <Button variant={isPinned ? "default" : "outline"} size="sm" onClick={toggle}>
      {isPinned ? "Pinned for compare" : "Pin for compare"}
    </Button>
  );
}

/** Inventory-toolbar button that appears when ≥2 listings are pinned. */
export function CompareLauncher() {
  const [pinned] = usePinned();
  if (pinned.length < 2) return null;
  const href = `/listings/compare?ids=${encodeURIComponent(pinned.join(","))}`;
  return (
    <a
      href={href}
      className="inline-flex h-8 items-center rounded-md bg-foreground px-3 text-xs font-medium text-background transition hover:opacity-90"
    >
      Compare ({pinned.length})
    </a>
  );
}
