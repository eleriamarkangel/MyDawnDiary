import { useState, type FormEvent } from "react";
import { api, type Theme, type User } from "./api";

const themes: { id: Theme; name: string; description: string }[] = [
  { id: "orange-yellow", name: "Golden dawn", description: "Orange & yellow · Default" },
  { id: "blue-yellow", name: "Morning sky", description: "Blue & yellow" },
  { id: "green-yellow", name: "Sunlit garden", description: "Green & yellow" },
];

export function SettingsPanel({ user, token, onUserChange, onDeleted }: {
  user: User; token: string; onUserChange: (user: User) => void; onDeleted: () => void;
}) {
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");

  async function changeTheme(theme: Theme) {
    setPending(true); setError(""); setMessage("");
    try {
      const updated = await api<User>("/auth/me", { method: "PATCH", token, body: { theme } });
      onUserChange(updated);
      setMessage("Theme saved to your account.");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not save theme."); }
    finally { setPending(false); }
  }

  async function deleteAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (confirmation !== "DELETE") return;
    setPending(true); setError(""); setMessage("");
    try {
      await api<null>("/auth/me", { method: "DELETE", token, body: { current_password: password } });
      onDeleted();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not delete account."); }
    finally { setPending(false); }
  }

  return <>
    <div className="page-intro"><div><div className="eyebrow">Make yourself at home</div><h1 className="page-title">Settings</h1><p className="page-subtitle">Your space, your colors.</p></div></div>
    <section className="settings-card" aria-labelledby="theme-heading">
      <h2 id="theme-heading">Color theme</h2><p>Choose the colors for your diary. Your choice follows your account across devices.</p>
      <div className="theme-options" role="group" aria-label="Color theme">
        {themes.map((theme) => <button key={theme.id} type="button" className="theme-option" data-theme={theme.id} aria-pressed={user.theme === theme.id} disabled={pending} onClick={() => changeTheme(theme.id)}>
          <span className="theme-swatch" aria-hidden="true"><i/><i/><i/></span>
          <strong>{theme.name}</strong><span>{theme.description}</span><span className="theme-selection">{user.theme === theme.id ? "Selected" : "Choose theme"}</span>
        </button>)}
      </div>
    </section>
    <p role="status">{message}</p><p className="form-error" role="alert">{error}</p>
    <section className="settings-card danger-zone" aria-labelledby="delete-heading">
      <h2 id="delete-heading">Delete account</h2><p>Permanently delete <strong>{user.email}</strong> and all your diaries, notes, conversations, and social drafts, including items in trash. This cannot be undone. You can register again with the same email afterward.</p>
      {!confirming ? <button className="button button-danger" type="button" disabled={pending} onClick={() => setConfirming(true)}>Delete Account</button> :
        <form onSubmit={deleteAccount}>
          <div className="field"><label htmlFor="delete-password">Current password</label><input id="delete-password" type="password" autoComplete="current-password" required maxLength={128} value={password} disabled={pending} onChange={(event) => setPassword(event.target.value)}/></div>
          <div className="field"><label htmlFor="delete-confirmation">Type DELETE to confirm permanent deletion</label><input id="delete-confirmation" autoComplete="off" required pattern="DELETE" value={confirmation} disabled={pending} onChange={(event) => setConfirmation(event.target.value)}/></div>
          <div className="actions"><button className="button button-danger" type="submit" disabled={pending || confirmation !== "DELETE" || !password}>{pending ? "Please wait…" : "Permanently delete account"}</button>
            <button className="button button-secondary" type="button" disabled={pending} onClick={() => { setConfirming(false); setPassword(""); setConfirmation(""); setError(""); }}>Cancel</button></div>
        </form>}
    </section>
  </>;
}

// Illustrative only. Replace this data with the AI integration's results later.
const sampleTraits = [
  { name: "Curiosity", value: 80 }, { name: "Creativity", value: 65 },
  { name: "Connection", value: 70 }, { name: "Reflection", value: 90 },
  { name: "Persistence", value: 60 }, { name: "Openness", value: 75 },
];
function point(index: number, radius: number): [number, number] {
  const angle = index * Math.PI / 3 - Math.PI / 2;
  return [220 + Math.cos(angle) * radius, 200 + Math.sin(angle) * radius];
}
function polygon(radius: number) {
  return sampleTraits.map((_, index) => point(index, radius).join(",")).join(" ");
}

export function PersonalityPanel() {
  return <>
    <div className="page-intro"><div><div className="eyebrow">A space for self-discovery</div><h1 className="page-title">Personality</h1><p className="page-subtitle">A future view of the patterns in your diary.</p></div></div>
    <section className="settings-card personality-card">
      <div><span className="preview-badge">Preview · Sample data</span><h2>Your personality web</h2><p>After AI integration, this dashboard will summarize patterns from your diary activity. The graph below uses fixed example values, not an assessment of you.</p></div>
      <div className="personality-layout"><figure className="personality-figure">
        <svg className="personality-graph" viewBox="0 0 440 400" role="img" aria-labelledby="personality-title personality-description">
          <title id="personality-title">Example personality radar graph</title><desc id="personality-description">Six illustrative traits on a scale from zero to one hundred. Sample values are listed alongside the graph. No diary analysis has been performed.</desc>
          {[.25, .5, .75, 1].map((level) => <polygon key={level} points={polygon(level * 130)} className="radar-grid"/>)}
          {sampleTraits.map((trait, index) => { const [x, y] = point(index, 130); const [lx, ly] = point(index, 165); return <g key={trait.name}><line x1="220" y1="200" x2={x} y2={y} className="radar-grid"/><text x={lx} y={ly} textAnchor="middle" dominantBaseline="middle">{trait.name}</text></g>; })}
          <polygon className="radar-shape" points={sampleTraits.map((trait, index) => point(index, trait.value * 1.3).join(",")).join(" ")}/>
          {sampleTraits.map((trait, index) => { const [cx, cy] = point(index, trait.value * 1.3); return <circle key={trait.name} cx={cx} cy={cy} r="4" className="radar-dot"/>; })}
        </svg><figcaption>Illustrative scores · 0–100 · AI analysis coming later</figcaption>
      </figure><dl className="trait-list">{sampleTraits.map((trait) => <div key={trait.name}><dt>{trait.name}</dt><dd>{trait.value}<span> / 100</span></dd></div>)}</dl></div>
      <p className="helper">All accounts see the same preview. Writing or deleting notes does not change these sample scores.</p>
    </section>
  </>;
}
