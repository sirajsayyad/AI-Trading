"use client";

import { useEffect, useState } from "react";
import { api, type RiskProfile } from "@/lib/api";

const sections = ["General", "Appearance", "Trading", "Chart", "Replay", "Backtesting", "Notifications", "AI Coach", "Security", "Account & data"];
type Settings = { timezone: string; currency: string; refresh: string; compact: boolean; sound: boolean; confirmOrders: boolean; candles: string; autoPlay: boolean; alerts: boolean; coach: boolean };
const defaults: Settings = { timezone: "Asia/Kolkata", currency: "USD", refresh: "15", compact: true, sound: false, confirmOrders: true, candles: "1D", autoPlay: false, alerts: true, coach: true };

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return <button type="button" className={`settings-toggle ${checked ? "on" : ""}`} aria-label={label} aria-pressed={checked} onClick={() => onChange(!checked)}><span /></button>;
}

export default function SettingsPage() {
  const [section, setSection] = useState("General");
  const [settings, setSettings] = useState<Settings>(defaults);
  const [saved, setSaved] = useState(false);
  const [risk, setRisk] = useState<RiskProfile | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try { const stored = localStorage.getItem("aitrade.settings"); if (stored) setSettings({ ...defaults, ...JSON.parse(stored) }); } catch { /* use defaults */ }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  useEffect(() => { api.getRiskProfile().then(setRisk).catch(() => undefined); }, []);

  const update = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettings((current) => ({ ...current, [key]: value }));
    setSaved(false);
  };
  const save = async () => {
    setError("");
    localStorage.setItem("aitrade.settings", JSON.stringify(settings));
    try { if (risk) setRisk(await api.updateRiskProfile(risk)); setSaved(true); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save settings"); }
    window.setTimeout(() => setSaved(false), 2200);
  };
  const updateRisk = <K extends keyof RiskProfile>(key: K, value: RiskProfile[K]) => setRisk((current) => current ? { ...current, [key]: value } : current);

  return <div className="settings-page">
    <div className="page-heading settings-heading"><div><div className="eyebrow">CONTROL CENTER</div><h1>Settings</h1><p>Configure your trading workspace, market data, and learning preferences.</p></div><button className="primary-button" onClick={save}>{saved ? "Saved" : "Save changes"}</button></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="settings-layout">
      <aside className="settings-nav" aria-label="Settings sections"><span className="settings-nav-title">Preferences</span>{sections.map((item) => <button key={item} className={section === item ? "active" : ""} onClick={() => setSection(item)}>{item}<span>›</span></button>)}</aside>
      <section className="settings-content" aria-live="polite">
        {section === "General" && <><SettingsTitle title="General preferences" copy="Defaults used across your AI Trade workspace." /><div className="settings-form-grid"><label>Timezone<select value={settings.timezone} onChange={(event) => update("timezone", event.target.value)}><option>Asia/Kolkata</option><option>UTC</option><option>America/New_York</option><option>Europe/London</option></select></label><label>Display currency<select value={settings.currency} onChange={(event) => update("currency", event.target.value)}><option>USD</option><option>INR</option><option>EUR</option><option>GBP</option></select></label><label>Live quote refresh<select value={settings.refresh} onChange={(event) => update("refresh", event.target.value)}><option value="15">Every 15 seconds</option><option value="30">Every 30 seconds</option><option value="60">Every minute</option></select></label></div><SettingRow title="Compact data density" copy="Show more rows and metrics in terminal panels." control={<Toggle label="Compact data density" checked={settings.compact} onChange={(value) => update("compact", value)} />} /><SettingRow title="Order confirmations" copy="Ask for confirmation before placing a paper order." control={<Toggle label="Order confirmations" checked={settings.confirmOrders} onChange={(value) => update("confirmOrders", value)} />} /></>}
        {section === "Appearance" && <><SettingsTitle title="Appearance" copy="Tune the visual density and feedback of the terminal." /><SettingRow title="Sound effects" copy="Play a subtle sound for fills and replay events." control={<Toggle label="Sound effects" checked={settings.sound} onChange={(value) => update("sound", value)} />} /><SettingRow title="Theme" copy="AI Trade is optimized for the dark OLED terminal theme." control={<span className="settings-badge">Dark OLED</span>} /><SettingRow title="Reduced motion" copy="Respects your operating system accessibility preference automatically." control={<span className="settings-badge muted">System</span>} /></>}
        {section === "Trading" && <><SettingsTitle title="Paper-trading risk profile" copy="Orders that break these limits are rejected before simulation." />{risk ? <div className="settings-form-grid"><RiskNumber label="Starting balance" value={risk.starting_balance} onChange={(value) => updateRisk("starting_balance", value)} /><RiskNumber label="Risk per trade (%)" value={risk.max_risk_percent} onChange={(value) => updateRisk("max_risk_percent", value)} /><RiskNumber label="Daily loss limit (%)" value={risk.max_daily_loss_percent} onChange={(value) => updateRisk("max_daily_loss_percent", value)} /><RiskNumber label="Maximum positions" value={risk.max_open_positions} onChange={(value) => updateRisk("max_open_positions", value)} /><RiskNumber label="Maximum position (%)" value={risk.max_position_value_percent} onChange={(value) => updateRisk("max_position_value_percent", value)} /><RiskNumber label="Minimum reward:risk" value={risk.min_reward_risk_ratio} onChange={(value) => updateRisk("min_reward_risk_ratio", value)} /></div> : <p className="history-copy">Sign in to configure your risk profile.</p>} {risk && <SettingRow title="Mandatory stop-loss" copy="Reject new paper positions without a defined stop." control={<Toggle label="Mandatory stop-loss" checked={risk.require_stop_loss} onChange={(value) => updateRisk("require_stop_loss", value)} />} />}</>}
        {section === "Chart" && <><SettingsTitle title="Chart defaults" copy="Set the starting view for market and replay charts." /><label className="settings-wide-label">Default candle interval<select value={settings.candles} onChange={(event) => update("candles", event.target.value)}><option>1D</option><option>4h</option><option>1h</option><option>15m</option><option>5m</option><option>1m</option></select></label><SettingRow title="Show volume by default" copy="Keep volume visible beneath the primary candle chart." control={<Toggle label="Show volume by default" checked={true} onChange={() => undefined} />} /></>}
        {section === "Replay" && <><SettingsTitle title="Replay preferences" copy="Control how historical market sessions are played back." /><SettingRow title="Auto-play sessions" copy="Start replay playback after the historical candles load." control={<Toggle label="Auto-play sessions" checked={settings.autoPlay} onChange={(value) => update("autoPlay", value)} />} /><SettingRow title="Pause on trade" copy="Pause playback when a simulated order is placed." control={<Toggle label="Pause on trade" checked={true} onChange={() => undefined} />} /></>}
        {section === "Backtesting" && <><SettingsTitle title="Backtesting defaults" copy="Keep research runs reproducible and easy to compare." /><SettingRow title="Save run snapshots" copy="Persist parameters and equity curves with every run." control={<Toggle label="Save run snapshots" checked={true} onChange={() => undefined} />} /><SettingRow title="Include transaction costs" copy="Apply a default fee model to strategy results." control={<Toggle label="Include transaction costs" checked={true} onChange={() => undefined} />} /></>}
        {section === "Notifications" && <><SettingsTitle title="Notifications" copy="Choose which events should appear in your workspace." /><SettingRow title="Market alerts" copy="Notify when a watched symbol moves beyond your threshold." control={<Toggle label="Market alerts" checked={settings.alerts} onChange={(value) => update("alerts", value)} />} /><SettingRow title="Training reminders" copy="Keep your learning streak visible with gentle reminders." control={<Toggle label="Training reminders" checked={true} onChange={() => undefined} />} /></>}
        {section === "AI Coach" && <><SettingsTitle title="AI coach" copy="Personalize explanations and feedback during training." /><SettingRow title="Show coaching prompts" copy="Offer context when a replay or paper trade completes." control={<Toggle label="Show coaching prompts" checked={settings.coach} onChange={(value) => update("coach", value)} />} /><SettingRow title="Explain technical terms" copy="Add short plain-language explanations beside indicators." control={<Toggle label="Explain technical terms" checked={true} onChange={() => undefined} />} /></>}
        {section === "Security" && <><SettingsTitle title="Security" copy="Review session and account protection controls." /><SettingRow title="Session status" copy="Authentication is handled by the secure API session." control={<span className="settings-badge success">Protected</span>} /><SettingRow title="API keys" copy="Your market data provider key remains server-side and is never exposed here." control={<span className="settings-badge muted">Server only</span>} /></>}
        {section === "Account & data" && <><SettingsTitle title="Account & data" copy="Manage local preferences and your workspace data." /><SettingRow title="Local preferences" copy="Saved on this device for a faster return to your setup." control={<span className="settings-badge success">Enabled</span>} /><button className="danger-outline" onClick={() => { localStorage.removeItem("aitrade.settings"); setSettings(defaults); setSaved(false); }}>Reset local preferences</button></>}
      </section>
    </div>
  </div>;
}

function SettingsTitle({ title, copy }: { title: string; copy: string }) { return <div className="settings-title"><h2>{title}</h2><p>{copy}</p></div>; }
function SettingRow({ title, copy, control }: { title: string; copy: string; control: React.ReactNode }) { return <div className="setting-row"><div><strong>{title}</strong><p>{copy}</p></div>{control}</div>; }
function RiskNumber({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) { return <label>{label}<input className="terminal-input" type="number" min="0" step="0.1" value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>; }
