"use client";
import { useEffect, useRef, useState } from "react";

type Player = { getCurrentTime(): number; getDuration(): number; getPlayerState(): number; seekTo(time: number, allowSeekAhead: boolean): void; destroy(): void };
type YouTube = { Player: new (element: HTMLElement, config: Record<string, unknown>) => Player };
declare global { interface Window { YT?: YouTube; onYouTubeIframeAPIReady?: () => void } }
let apiReady: Promise<void> | undefined;
function loadAPI() {
  if (window.YT?.Player) return Promise.resolve();
  if (!apiReady) apiReady = new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => { apiReady = undefined; reject(new Error("Video service did not respond")); }, 20000);
    window.onYouTubeIframeAPIReady = () => { clearTimeout(timeout); resolve(); };
    const script = document.createElement("script"); script.src = "https://www.youtube.com/iframe_api";
    script.onerror = () => { clearTimeout(timeout); apiReady = undefined; reject(new Error("Video service is blocked or offline")); };
    document.head.appendChild(script);
  });
  return apiReady;
}

export default function LessonVideo({ videoId, initialPosition, seekPosition, onProgress, onPosition }: { videoId: string; initialPosition: number; seekPosition: number | null; onProgress: (position: number, completed: boolean) => void; onPosition: (position: number) => void }) {
  const container = useRef<HTMLDivElement>(null);
  const player = useRef<Player | null>(null);
  const callback = useRef(onProgress);
  const tick = useRef(onPosition);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  useEffect(() => { callback.current = onProgress; }, [onProgress]);
  useEffect(() => { tick.current = onPosition; }, [onPosition]);
  useEffect(() => {
    let disposed = false; let played = false; let interval: ReturnType<typeof setInterval> | undefined;
    const report = (complete = false) => {
      const p = player.current;
      if (played && p?.getCurrentTime) callback.current(p.getCurrentTime(), complete);
    };
    loadAPI().then(() => {
      if (disposed || !container.current || !/^[\w-]{11}$/.test(videoId)) return;
      const target = document.createElement("div"); container.current.replaceChildren(target);
      player.current = new window.YT!.Player(target, {
        videoId, host: "https://www.youtube-nocookie.com", width: "100%", height: "100%",
        playerVars: { origin: window.location.origin, start: Math.floor(initialPosition), playsinline: 1, rel: 0, cc_load_policy: 1 },
        events: {
          onReady: () => { if (!disposed) setReady(true); },
          onError: () => { if (!disposed) setError("This video is unavailable here. Try the original provider link below."); },
          onStateChange: (event: { data: number }) => {
            if (disposed) return;
            if (event.data === 1) played = true;
            if ([0, 2].includes(event.data)) report(event.data === 0);
          },
        },
      });
      let seconds = 0;
      interval = setInterval(() => {
        if (player.current?.getPlayerState?.() === 1) {
          tick.current(player.current.getCurrentTime());
          if (++seconds % 10 === 0) report();
        }
      }, 1000);
    }).catch(e => { if (!disposed) setError(e.message); });
    return () => { disposed = true; clearInterval(interval); report(); player.current?.destroy(); player.current = null; };
  }, [videoId, initialPosition]);
  useEffect(() => { if (seekPosition !== null && ready) player.current?.seekTo(seekPosition, true); }, [seekPosition, ready]);
  return <section aria-label="Lesson video">{!ready && !error && <p role="status">Connecting to YouTube…</p>}<div className="learn-video" ref={container} />{error && <p className="learn-error" role="alert">{error}</p>}<p className="learn-meta">Use the player’s controls for captions, speed, volume and fullscreen.</p><a className="learn-link" target="_blank" rel="noreferrer" href={`https://www.youtube.com/watch?v=${videoId}`}>Watch on YouTube ↗</a></section>;
}
