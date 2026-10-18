import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { api, ApiError, diaryDateLabel, displayDate, shiftDate, userDate, type Diary, type Note, type Trash, type User } from "./api";

type IconName = "home" | "note" | "plus" | "mic" | "search" | "logout" | "trash";
type View = "today" | "notes" | "trash";
type Editor = Note | "new" | null;

function Icon({ name }: { name: IconName }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  return <svg className="icon" viewBox="0 0 24 24" aria-hidden="true" {...common}>
    {name === "home" && <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M9 21v-7h6v7"/></>}
    {name === "note" && <><path d="M6 2h9l5 5v14a1 1 0 0 1-1 1H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M14 2v6h6M8 13h8M8 17h8"/></>}
    {name === "plus" && <path d="M12 4v16M4 12h16"/>}
    {name === "mic" && <><rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v4M8 22h8"/></>}
    {name === "search" && <><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></>}
    {name === "logout" && <><path d="M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h5M15 17l5-5-5-5M20 12H9"/></>}
    {name === "trash" && <><path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6"/></>}
  </svg>;
}

function Brand() {
  return <a className="brand" href="/app/" aria-label="MyDawnDiary home">
    <img src="/app/favicon.svg" alt=""/><span>MyDawn<em>Diary</em></span>
  </a>;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

function AuthScreen({ onAuthenticated, notify }: {
  onAuthenticated: (token: string) => void;
  notify: (message: string) => void;
}) {
  const [mode, setMode] = useState<"login" | "register" | "verify">("login");
  const [email, setEmail] = useState(sessionStorage.getItem("mdd_verification_email") || "");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [resendUntil, setResendUntil] = useState(Number(sessionStorage.getItem("mdd_otp_wait_until") || 0));
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Taipei";

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    const data = new FormData(event.currentTarget);
    const address = String(data.get("email") || "").trim();
    try {
      if (mode === "register") {
        await api<User>("/auth/register", { method: "POST", body: {
          email: address,
          password: String(data.get("password")),
          time_zone: String(data.get("time_zone") || "").trim(),
          display_name: String(data.get("display_name") || "").trim() || null,
        }});
        setEmail(address);
        sessionStorage.setItem("mdd_verification_email", address);
        const until = Date.now() + 300_000;
        sessionStorage.setItem("mdd_otp_wait_until", String(until));
        setResendUntil(until);
        setMode("verify");
        notify("Check your email for the verification code.");
      } else if (mode === "verify") {
        await api<null>("/auth/verify-email", { method: "POST", body: {
          email: address, code: String(data.get("code") || "").trim(),
        }});
        sessionStorage.removeItem("mdd_verification_email");
        setMode("login");
        notify("Email verified. You can sign in now.");
      } else {
        const result = await api<{ access_token: string }>("/auth/login", { method: "POST", body: {
          email: address, password: String(data.get("password")),
        }});
        onAuthenticated(result.access_token);
      }
    } catch (caught) {
      if (mode === "login" && caught instanceof ApiError && caught.status === 403) {
        setEmail(address);
        setMode("verify");
        notify("Verify your email before signing in.");
      } else setError(errorMessage(caught));
    } finally { setPending(false); }
  }

  async function resend() {
    if (!email.trim()) { setError("Enter your email first."); return; }
    setError("");
    setPending(true);
    try {
      await api<null>("/auth/resend-verification", { method: "POST", body: { email: email.trim() } });
      const until = Date.now() + 300_000;
      sessionStorage.setItem("mdd_otp_wait_until", String(until));
      setResendUntil(until);
      notify("If this account is awaiting verification, a new code will arrive shortly.");
    } catch (caught) { setError(errorMessage(caught)); }
    finally { setPending(false); }
  }

  const heading = mode === "verify" ? "Verify your email" : mode === "register" ? "Create your account" : "Welcome back";
  const description = mode === "verify" ? "Enter the six-digit code we sent to your inbox." :
    mode === "register" ? "Start your own private space for notes and reflection." :
    "Sign in to return to your diary.";
  const minutes = Math.ceil(Math.max(0, resendUntil - now) / 60_000);

  return <main className="auth-layout">
    <section className="auth-story" aria-label="MyDawnDiary introduction">
      <Brand/>
      <div className="auth-copy"><div className="eyebrow">A little space for every new day</div>
        <h1>Every day has a story.</h1>
        <p>Keep your thoughts, moments, and notes together in a quiet place that feels like yours.</p>
      </div>
      <div className="auth-footer">MyDawnDiary · Your day, in your words.</div>
    </section>
    <section className="auth-panel-wrap"><div className="auth-panel">
      <div className="eyebrow">{mode === "verify" ? "One more step" : mode === "register" ? "Begin your diary" : "Your private space"}</div>
      <h2>{heading}</h2><p>{description}</p>
      <form onSubmit={submit}>
        {mode === "register" && <div className="field"><label htmlFor="display-name">Display name <span className="helper">(optional)</span></label><input id="display-name" name="display_name" autoComplete="name" maxLength={120}/></div>}
        <div className="field"><label htmlFor="email">Email</label><input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required/></div>
        {mode === "verify" ? <div className="field"><label htmlFor="code">Verification code</label><input id="code" className="otp-code" name="code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} placeholder="000000" required/></div> :
          <div className="field"><label htmlFor="password">Password</label><input id="password" name="password" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} minLength={mode === "register" ? 12 : 1} required/>{mode === "register" && <span className="helper">At least 12 characters.</span>}</div>}
        {mode === "register" && <div className="field"><label htmlFor="time-zone">Time zone</label><input id="time-zone" name="time_zone" defaultValue={timeZone} required/><span className="helper">Uses your device setting. This decides which day a note belongs to.</span></div>}
        <div className="form-error" role="alert">{error}</div>
        <button className="button button-primary" type="submit" disabled={pending}>{mode === "verify" ? "Verify email" : mode === "register" ? "Create account" : "Sign in"}</button>
      </form>
      {mode === "verify" ? <div className="auth-switch">
        <button className="text-button" type="button" onClick={resend} disabled={pending || minutes > 0}>{minutes > 0 ? `Resend code in ${minutes} min` : "Resend code"}</button><br/>
        <button className="text-button" type="button" onClick={() => { setError(""); setMode("login"); }}>Back to sign in</button>
      </div> : <div className="auth-switch">{mode === "register" ? "Already have an account?" : "New here?"} <button className="text-button" type="button" onClick={() => { setError(""); setMode(mode === "register" ? "login" : "register"); }}>{mode === "register" ? "Sign in" : "Create an account"}</button></div>}
    </div></section>
  </main>;
}

function NavButton({ view, current, icon, label, onSelect }: {
  view: View; current: View; icon: IconName; label: string; onSelect: (view: View) => void;
}) {
  return <button className={`nav-item ${current === view ? "active" : ""}`} type="button" onClick={() => onSelect(view)} aria-current={current === view ? "page" : undefined}><Icon name={icon}/><span>{label}</span></button>;
}

function NoteCard({ note, onOpen }: { note: Note; onOpen: (note: Note) => void }) {
  return <button className="note-card notebook-paper" type="button" onClick={() => onOpen(note)} aria-label={`Open ${note.title || "Untitled note"}`}>
    <span className="note-body">
      <span className="note-meta">{displayDate(note.diary_date)}</span>
      <span className="note-title">{note.title || "Untitled note"}</span>
      <span className="note-preview">{note.content}</span>
    </span>
  </button>;
}

function EmptyNotes({ date, onNew }: { date?: string; onNew: () => void }) {
  return <div className="empty-state"><div className="eyebrow">A fresh page</div>
    <h3>{date ? `Nothing written for ${displayDate(date)} yet` : "Your notes start here"}</h3>
    <p>Capture a thought, a memory, or something small you want to keep.</p>
    <button className="button button-primary" type="button" onClick={onNew}><Icon name="plus"/> New Note</button>
  </div>;
}

function NoteEditor({ note, today, defaultDate, onClose, onSave, onDelete, onSeeDiary }: {
  note: Editor;
  today: string;
  defaultDate: string;
  onClose: () => void;
  onSave: (title: string | null, content: string, diaryDate: string) => Promise<void>;
  onDelete: () => Promise<void>;
  onSeeDiary: (date: string) => void;
}) {
  const existing = note && note !== "new" ? note : null;
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [customDate, setCustomDate] = useState(defaultDate !== today);
  const [noteDate, setNoteDate] = useState(defaultDate);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const title = String(data.get("title") || "").trim() || null;
    const content = String(data.get("content") || "").trim();
    if (!content) { setError("Write something before saving your note."); return; }
    if (!existing && (noteDate > today || !noteDate)) { setError("Choose today or a previous date."); return; }
    setPending(true); setError("");
    try { await onSave(title, content, existing?.diary_date || noteDate); }
    catch (caught) { setError(errorMessage(caught)); }
    finally { setPending(false); }
  }

  async function remove() {
    if (!window.confirm("Move this note to the recycle bin?")) return;
    setPending(true); setError("");
    try { await onDelete(); }
    catch (caught) { setError(errorMessage(caught)); }
    finally { setPending(false); }
  }

  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="modal notebook-paper" role="dialog" aria-modal="true" aria-labelledby="editor-heading">
      <div className="modal-top"><div><div className="eyebrow">{existing ? "A moment to revisit" : "A fresh thought"}</div><h2 id="editor-heading">{existing ? "Note Details" : "New note"}</h2></div>
        <button className="close-button" type="button" onClick={onClose} aria-label="Close note editor">×</button></div>
      <div className="note-date-summary"><p className="helper">{existing ? `Saved for ${displayDate(existing.diary_date)}.` : noteDate ? `This note will be saved for ${displayDate(noteDate)}.` : "Choose a date for this note."}</p>
        {existing && <button className="text-button" type="button" onClick={() => onSeeDiary(existing.diary_date)}>See Diary</button>}
      </div>
      {!existing && <div className="note-date-choice"><button className={`date-toggle ${customDate ? "active" : ""}`} type="button" aria-pressed={customDate}
        onClick={() => { setCustomDate(!customDate); setNoteDate(customDate ? today : defaultDate !== today ? defaultDate : today); }}>
        <span aria-hidden="true" className="toggle-track"/> Set a previous date
      </button>
        {customDate && <div className="field"><label htmlFor="note-date">Note date</label><input id="note-date" type="date" value={noteDate} max={today} required onChange={(event) => setNoteDate(event.target.value)}/>
          <span className="helper">Past notes stay available in All Notes, even beyond the 30-day diary navigation.</span></div>}
      </div>}
      <form onSubmit={submit}><div className="field"><label htmlFor="note-title">Title <span className="helper">(optional)</span></label>
        <input id="note-title" name="title" maxLength={200} defaultValue={existing?.title || ""} placeholder="Give this moment a name" autoFocus/></div>
        <div className="field"><label htmlFor="note-content">Your note</label><textarea className="notebook-input" id="note-content" name="content" maxLength={200000} defaultValue={existing?.content || ""} placeholder="What's on your mind?" required/></div>
        <div className="form-error" role="alert">{error}</div>
        <div className="modal-actions">{existing && <button className="button button-danger" type="button" onClick={remove} disabled={pending}>Move to trash</button>}
          <div className="modal-actions-right"><button className="button button-secondary" type="button" onClick={onClose}>Cancel</button>
            <button className="button button-primary" type="submit" disabled={pending}>{existing ? "Save changes" : "Save note"}</button></div></div>
      </form>
    </section>
  </div>;
}

function TrashPanel({ trash, loading, error, restoringId, onRestore }: {
  trash: Trash | null;
  loading: boolean;
  error: string;
  restoringId: string | null;
  onRestore: (kind: "notes" | "records", id: string) => Promise<void>;
}) {
  return <><div className="page-intro"><div><div className="eyebrow">Room for second thoughts</div>
    <h1 className="page-title">Trash</h1><p className="page-subtitle">Deleted notes and conversations can be restored for three days.</p></div></div>
    {loading ? <div className="empty-state">Opening the trash…</div> : error ? <div className="empty-state" role="alert">{error}</div> :
      !trash || (!trash.notes.length && !trash.records.length) ? <div className="empty-state notebook-paper"><h2>Nothing in the trash</h2><p>Deleted items will appear here while they can still be restored.</p></div> :
      <div className="trash-groups">
        <section aria-label="Deleted notes"><h2 className="section-title">Deleted notes <span className="item-count">{trash.notes.length}</span></h2>
          {trash.notes.length ? <div className="trash-grid">{trash.notes.map((note) => <article className="trash-card notebook-paper" key={note.id}>
            <div className="trash-card-content"><span className="note-meta">{displayDate(note.diary_date)}</span><h3>{note.title || "Untitled note"}</h3><p>{note.content}</p>
              <button className="button button-secondary" type="button" disabled={restoringId !== null} onClick={() => onRestore("notes", note.id)}>{restoringId === note.id ? "Restoring…" : "Restore note"}</button></div>
          </article>)}</div> : <p className="helper">No deleted notes.</p>}</section>
        <section aria-label="Deleted conversations"><h2 className="section-title">Deleted conversations <span className="item-count">{trash.records.length}</span></h2>
          {trash.records.length ? <div className="trash-grid">{trash.records.map((record) => <article className="trash-card notebook-paper" key={record.id}>
            <div className="trash-card-content"><span className="note-meta">{displayDate(record.diary_date)}</span><h3>{record.title || "Untitled conversation"}</h3><p>{record.edited_summary || record.ai_summary || "No summary was saved for this conversation."}</p>
              {record.entries.length > 0 && <details className="trash-transcript"><summary>Read conversation ({record.entries.length} turns)</summary>
                <div>{record.entries.map((entry) => <p key={entry.id}><strong>{entry.speaker === "user" ? "You" : "Assistant"}:</strong> {entry.content}</p>)}</div>
              </details>}
              <button className="button button-secondary" type="button" disabled={restoringId !== null} onClick={() => onRestore("records", record.id)}>{restoringId === record.id ? "Restoring…" : "Restore conversation"}</button></div>
          </article>)}</div> : <p className="helper">No deleted conversations.</p>}</section>
      </div>}
  </>;
}

function Dashboard({ user, token, notes, hasMore, onSignOut, onLoadMore, onReloadNotes, onSaveNote, onDeleteNote, notify }: {
  user: User;
  token: string;
  notes: Note[];
  hasMore: boolean;
  onSignOut: () => void;
  onLoadMore: () => Promise<void>;
  onReloadNotes: () => Promise<void>;
  onSaveNote: (note: Editor, title: string | null, content: string, diaryDate: string) => Promise<void>;
  onDeleteNote: (note: Note) => Promise<void>;
  notify: (message: string) => void;
}) {
  const [view, setView] = useState<View>("today");
  const [search, setSearch] = useState("");
  const [editor, setEditor] = useState<Editor>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const today = userDate(user.time_zone);
  const oldestDate = shiftDate(today, -30);
  const [selectedDate, setSelectedDate] = useState(today);
  const [diaryState, setDiaryState] = useState<{ date: string; value: Diary | null; error: string } | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [trashState, setTrashState] = useState<{ value: Trash | null; loading: boolean; error: string }>({ value: null, loading: false, error: "" });
  const [trashRefresh, setTrashRefresh] = useState(0);
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const diary = diaryState?.date === selectedDate ? diaryState.value : null;
  const diaryLoading = diaryState?.date !== selectedDate;
  const olderLinkedDate = selectedDate < oldestDate;
  const dayOptions = useMemo(() => {
    const recent = Array.from({ length: 31 }, (_, index) => shiftDate(today, -index));
    return selectedDate < shiftDate(today, -30) ? [selectedDate, ...recent] : recent;
  }, [selectedDate, today]);
  const displayName = user.display_name || user.email.split("@")[0];
  const firstName = displayName.trim().split(/\s+/)[0] || "friend";
  const diaryText = diary?.edited_combined_entry || diary?.ai_combined_entry;
  const shownNotes = useMemo(() => {
    if (view === "today") return diary?.notes || [];
    const query = search.trim().toLocaleLowerCase();
    return query ? notes.filter((note) => `${note.title || ""} ${note.content}`.toLocaleLowerCase().includes(query)) : notes;
  }, [diary, notes, search, view]);

  useEffect(() => {
    if (selectedDate > today) setSelectedDate(today);
  }, [selectedDate, today]);

  useEffect(() => {
    let active = true;
    setDiaryState(null);
    api<Diary>(`/diaries/${selectedDate}`, { token }).then((value) => {
      if (active) setDiaryState({ date: selectedDate, value, error: "" });
    }).catch((error: unknown) => {
      if (!active) return;
      if (error instanceof ApiError && error.status === 404) setDiaryState({ date: selectedDate, value: null, error: "" });
      else setDiaryState({ date: selectedDate, value: null, error: errorMessage(error) });
    });
    return () => { active = false; };
  }, [selectedDate, token, refreshKey]);

  useEffect(() => {
    if (view !== "trash") return;
    let active = true;
    setTrashState({ value: null, loading: true, error: "" });
    api<Trash>("/trash", { token }).then((value) => {
      if (active) setTrashState({ value, loading: false, error: "" });
    }).catch((error: unknown) => {
      if (active) setTrashState({ value: null, loading: false, error: errorMessage(error) });
    });
    return () => { active = false; };
  }, [view, token, trashRefresh]);

  useEffect(() => {
    if (editor === null) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setEditor(null); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editor]);

  async function loadMore() {
    setLoadingMore(true);
    try { await onLoadMore(); }
    catch (caught) { notify(errorMessage(caught)); }
    finally { setLoadingMore(false); }
  }

  async function save(title: string | null, content: string, diaryDate: string) {
    await onSaveNote(editor, title, content, diaryDate);
    setRefreshKey((value) => value + 1);
    if (editor === "new" && view === "today") {
      if (diaryDate >= oldestDate && diaryDate <= today) setSelectedDate(diaryDate);
      else setView("notes");
    }
    setEditor(null);
  }

  async function remove() {
    if (editor && editor !== "new") {
      await onDeleteNote(editor);
      setRefreshKey((value) => value + 1);
      setEditor(null);
    }
  }

  function seeDiary(date: string) {
    setSelectedDate(date);
    setView("today");
    setEditor(null);
    window.scrollTo(0, 0);
  }

  async function restore(kind: "notes" | "records", id: string) {
    setRestoringId(id);
    try {
      await api(`/${kind}/${encodeURIComponent(id)}/restore`, { method: "POST", token });
      await onReloadNotes();
      setRefreshKey((value) => value + 1);
      setTrashRefresh((value) => value + 1);
      notify(kind === "notes" ? "Note restored." : "Conversation restored.");
    } catch (error) { notify(errorMessage(error)); }
    finally { setRestoringId(null); }
  }

  const nav = (place: "side" | "mobile") => <nav className={place === "side" ? "side-nav" : "mobile-nav"} aria-label={`${place === "side" ? "Main" : "Mobile"} navigation`}>
    <NavButton view="today" current={view} icon="home" label="Diary" onSelect={setView}/>
    <NavButton view="notes" current={view} icon="note" label="Notes" onSelect={setView}/>
    <NavButton view="trash" current={view} icon="trash" label="Trash" onSelect={setView}/>
  </nav>;

  return <div className="shell">
    <aside className="sidebar"><Brand/>{nav("side")}<div className="side-foot"><button className="button button-quiet" type="button" onClick={onSignOut}><Icon name="logout"/> Sign out</button></div></aside>
    <header className="mobile-header"><Brand/><button className="button button-quiet button-small" type="button" onClick={onSignOut} aria-label="Sign out"><Icon name="logout"/></button></header>
    <main className="main"><div className="topbar"><span className="topbar-name">{displayName}</span><span className="topbar-avatar" aria-hidden="true">{firstName[0].toLocaleUpperCase()}</span></div>
      {view === "today" ? <><div className="page-intro"><div><div className="eyebrow">A page for every day</div><h1 className="page-title">Daily Diary</h1><p className="page-subtitle">{selectedDate === today ? `Today · Hello, ${firstName}.` : `Looking back at ${displayDate(selectedDate)}.`}</p></div></div>
        <div className="date-navigation" aria-label="Navigate diary dates">
          <button className="date-arrow" type="button" aria-label="Previous day" disabled={selectedDate <= oldestDate} onClick={() => setSelectedDate(shiftDate(selectedDate, -1))}>‹ <span>Previous</span></button>
          <label className="date-select-wrap"><span className="sr-only">Jump to a diary date</span><select value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} aria-label="Jump to a diary date">
            {dayOptions.map((date) => <option key={date} value={date}>{diaryDateLabel(date)}</option>)}
          </select></label>
          <button className={`date-arrow ${olderLinkedDate ? "return-today" : ""}`} type="button" aria-label={olderLinkedDate ? "Return to today" : "Next day"} disabled={selectedDate >= today} onClick={() => setSelectedDate(olderLinkedDate ? today : shiftDate(selectedDate, 1))}><span>{olderLinkedDate ? "Today" : "Next"}</span>{olderLinkedDate ? "" : " ›"}</button>
        </div>
        {olderLinkedDate && <p className="historical-hint">Opened from a note outside the 30-day picker. Choose a recent date above to return.</p>}
        <section className="diary-card notebook-paper" aria-label="Daily diary"><div className="diary-content"><div className="diary-date">{diaryDateLabel(selectedDate)}</div><h2 className="diary-heading">Dear diary,</h2><p className={diaryText ? "" : "diary-placeholder"}>{diaryLoading ? "Opening this page…" : diaryState?.error ? diaryState.error : diaryText || "Your daily entry will appear here when one is ready. Notes for this day are just below."}</p></div></section></> :
        view === "notes" ? <div className="page-intro"><div><div className="eyebrow">Little moments worth keeping</div><h1 className="page-title">Your Notes</h1><p className="page-subtitle">All the thoughts you have saved so far.</p></div></div> :
        <TrashPanel trash={trashState.value} loading={trashState.loading} error={trashState.error} restoringId={restoringId} onRestore={restore}/>}
      {view !== "trash" && <><div className="section-head"><div><h2 className="section-title">{view === "today" ? "Notes" : "All notes"}</h2></div>
        <div className="actions">{view === "notes" && <label className="search-wrap"><Icon name="search"/><span className="sr-only">Search notes</span><input className="search-input" type="search" placeholder="Search notes" value={search} onChange={(event) => setSearch(event.target.value)}/></label>}
          <button className="button button-primary" type="button" onClick={() => setEditor("new")}><Icon name="plus"/> New Note</button>
          <button className="button button-secondary" type="button" disabled title="Voice notes are coming later"><Icon name="mic"/> Voice Note</button>
        </div></div>
      <div className="notes-grid">{view === "today" && diaryLoading ? <div className="empty-state">Opening notes for this day…</div> : view === "today" && diaryState?.error ? <div className="empty-state" role="alert">{diaryState.error}</div> : shownNotes.length ? shownNotes.map((note) => <NoteCard key={note.id} note={note} onOpen={setEditor}/>) : <EmptyNotes date={view === "today" ? selectedDate : undefined} onNew={() => setEditor("new")}/>}</div>
      {view === "notes" && hasMore && <button className="button button-secondary load-more" type="button" onClick={loadMore} disabled={loadingMore}>Load more notes</button>}
      </>}
    </main>
    {nav("mobile")}
    {editor !== null && <NoteEditor key={editor === "new" ? "new" : editor.id} note={editor} today={today} defaultDate={view === "today" ? selectedDate : today} onClose={() => setEditor(null)} onSave={save} onDelete={remove} onSeeDiary={seeDiary}/>}
  </div>;
}

export default function App(): ReactNode {
  const [token, setToken] = useState(sessionStorage.getItem("mdd_access_token") || "");
  const [user, setUser] = useState<User | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(Boolean(token));
  const [notice, setNotice] = useState("");

  const notify = useCallback((message: string) => setNotice(message), []);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 4300);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const loadContent = useCallback(async (currentToken: string) => {
    const nextNotes = await api<Note[]>("/notes?limit=50&offset=0", { token: currentToken });
    setNotes(nextNotes);
    setHasMore(nextNotes.length === 50);
  }, []);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    let active = true;
    setLoading(true);
    (async () => {
      try {
        const currentUser = await api<User>("/auth/me", { token });
        if (!active) return;
        setUser(currentUser);
        await loadContent(token);
      } catch (error) {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401) {
          sessionStorage.removeItem("mdd_access_token");
          setToken("");
          setUser(null);
          notify("Your session expired. Please sign in again.");
        } else notify(errorMessage(error));
      } finally { if (active) setLoading(false); }
    })();
    return () => { active = false; };
  }, [token, loadContent, notify]);

  function authenticated(value: string) {
    sessionStorage.setItem("mdd_access_token", value);
    setToken(value);
  }

  function signOut() {
    sessionStorage.removeItem("mdd_access_token");
    setToken(""); setUser(null); setNotes([]);
    notify("Signed out of this browser session.");
  }

  async function saveNote(editor: Editor, title: string | null, content: string, diaryDate: string) {
    if (!user) return;
    if (editor && editor !== "new") {
      await api<Note>(`/notes/${encodeURIComponent(editor.id)}`, { method: "PATCH", body: { title, content }, token });
    } else {
      await api<Note>("/notes", { method: "POST", body: { title, content, diary_date: diaryDate }, token });
    }
    await loadContent(token);
    notify(editor && editor !== "new" ? "Note updated." : "Note saved.");
  }

  async function deleteNote(note: Note) {
    if (!user) return;
    await api<null>(`/notes/${encodeURIComponent(note.id)}`, { method: "DELETE", token });
    await loadContent(token);
    notify("Note moved to trash.");
  }

  async function loadMore() {
    const next = await api<Note[]>(`/notes?limit=50&offset=${notes.length}`, { token });
    setNotes((current) => [...current, ...next]);
    setHasMore(next.length === 50);
  }

  return <>
    {loading ? <div className="auth-layout"><div className="auth-story"><Brand/></div><div className="auth-panel-wrap"><p>Opening your diary…</p></div></div> :
      token && user ? <Dashboard user={user} token={token} notes={notes} hasMore={hasMore} onSignOut={signOut} onLoadMore={loadMore} onReloadNotes={() => loadContent(token)} onSaveNote={saveNote} onDeleteNote={deleteNote} notify={notify}/> :
        <AuthScreen onAuthenticated={authenticated} notify={notify}/>}
    <div className={`toast ${notice ? "show" : ""}`} role="status" aria-live="polite">{notice}</div>
  </>;
}
