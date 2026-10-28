"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

type IconName = "grid" | "book" | "play" | "chart" | "market" | "settings" | "chevron" | "logout" | "menu" | "close";

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const paths: Record<IconName, React.ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    book: <><path d="M3 4.5A2.5 2.5 0 0 1 5.5 2H12v18H5.5A2.5 2.5 0 0 0 3 22z" /><path d="M21 4.5A2.5 2.5 0 0 0 18.5 2H12v18h6.5a2.5 2.5 0 0 1 2.5 2z" /></>,
    play: <><circle cx="12" cy="12" r="9" /><path d="m10 8 6 4-6 4z" /></>,
    chart: <><path d="M3 20V4" /><path d="M3 20h18" /><path d="m7 15 3-4 3 2 5-7" /></>,
    market: <><path d="M4 19V5" /><path d="M4 19h16" /><path d="M7 15V9M12 17V6M17 14V4" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.7 1.7-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5v.2h-2.4v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1L8 17l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H6.7v-2.4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9L8 8.6l1.7-1.7.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.5v-.2h2.4v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1 1.7 1.7-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.5 1h.2V14h-.2a1.7 1.7 0 0 0-1.5 1z" /></>,
    chevron: <path d="m8 10 4 4 4-4" />,
    logout: <><path d="M10 17l5-5-5-5" /><path d="M15 12H3" /><path d="M21 19V5a2 2 0 0 0-2-2h-5" /></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  };
  return <svg {...common} aria-hidden="true">{paths[name]}</svg>;
}

const primaryItems = [
  { label: "Dashboard", href: "/dashboard", icon: "grid" as IconName },
  { label: "Training", href: "/training", icon: "book" as IconName },
  { label: "Replay", href: "/replay", icon: "play" as IconName },
  { label: "Backtest", href: "/backtest", icon: "chart" as IconName },
  { label: "Markets", href: "/markets", icon: "market" as IconName },
  { label: "Journal", href: "/journal", icon: "book" as IconName },
];

export default function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMore, setMobileMore] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [confirmLogout, setConfirmLogout] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setCollapsed(localStorage.getItem("aitrade.sidebar.collapsed") === "true"), 0);
    return () => window.clearTimeout(timer);
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((value) => {
      const next = !value;
      localStorage.setItem("aitrade.sidebar.collapsed", String(next));
      return next;
    });
  };

  const pageTitle = primaryItems.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))?.label ?? (pathname.startsWith("/settings") ? "Settings" : "AI Trade");

  return <>
    <aside className={`app-sidebar ${collapsed ? "is-collapsed" : ""}`} aria-label="Primary navigation">
      <Link href="/dashboard" className="brand-lockup" aria-label="AI Trade dashboard">
        <span className="brand-mark"><span /></span>
        <span className="brand-word"><b>AI</b>Trade</span>
      </Link>
      <div className="sidebar-label">Workspace</div>
      <nav className="sidebar-nav">
        {primaryItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return <Link key={item.href} href={item.href} className={`sidebar-link ${active ? "active" : ""}`} title={collapsed ? item.label : undefined}>
            <Icon name={item.icon} /><span>{item.label}</span>
          </Link>;
        })}
      </nav>
      <div className="sidebar-spacer" />
      <Link href="/settings" className={`sidebar-link ${pathname.startsWith("/settings") ? "active" : ""}`} title={collapsed ? "Settings" : undefined}><Icon name="settings" /><span>Settings</span></Link>
      <button className="sidebar-collapse" onClick={toggleCollapsed} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}><Icon name="chevron" /><span>{collapsed ? "Expand" : "Collapse"}</span></button>
      <div className="sidebar-status"><i /> <span>Market data connected</span></div>
    </aside>

    <header className="app-topbar">
      <div className="topbar-heading"><span className="topbar-eyebrow">AI TRADING WORKSPACE</span><strong>{pageTitle}</strong></div>
      <div className="topbar-actions">
        <span className="connection-pill"><i /> Live data</span>
        <button className="icon-button" aria-label="Notifications"><span className="notification-dot" /><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></svg></button>
        <div className="profile-wrap">
          <button className="profile-button" onClick={() => setProfileOpen((value) => !value)} aria-expanded={profileOpen}>
            <span className="avatar">{(user?.username || "T").slice(0, 1).toUpperCase()}</span><span className="profile-name">{user?.username || "Trader"}</span><Icon name="chevron" size={15} />
          </button>
          {profileOpen && <div className="profile-menu">
            <Link href="/settings" onClick={() => setProfileOpen(false)}><Icon name="settings" size={16} /> Account settings</Link>
            <button onClick={() => { setProfileOpen(false); setConfirmLogout(true); }}><Icon name="logout" size={16} /> Log out</button>
          </div>}
        </div>
      </div>
    </header>

    <nav className="mobile-bottom-nav" aria-label="Mobile navigation">
      {primaryItems.slice(0, 4).map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return <Link key={item.href} href={item.href} className={active ? "active" : ""}><Icon name={item.icon} size={19} /><span>{item.label}</span></Link>;
      })}
      <button className={mobileMore || pathname.startsWith("/settings") ? "active" : ""} onClick={() => setMobileMore((value) => !value)}><Icon name="menu" size={19} /><span>More</span></button>
    </nav>
    {mobileMore && <div className="mobile-more-sheet"><Link href="/markets" onClick={() => setMobileMore(false)}><Icon name="market" /> Markets</Link><Link href="/journal" onClick={() => setMobileMore(false)}><Icon name="book" /> Journal</Link><Link href="/settings" onClick={() => setMobileMore(false)}><Icon name="settings" /> Settings</Link></div>}

    {confirmLogout && <div className="modal-backdrop" role="presentation" onClick={() => setConfirmLogout(false)}><div className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="logout-title" onClick={(event) => event.stopPropagation()}><h2 id="logout-title">Log out of AI Trade?</h2><p>Your local session will be cleared and you can sign in again at any time.</p><div className="modal-actions"><button className="button-quiet" onClick={() => setConfirmLogout(false)}>Cancel</button><button className="button-danger" onClick={() => { logout(); setConfirmLogout(false); }}>Log out</button></div></div></div>}
  </>;
}
