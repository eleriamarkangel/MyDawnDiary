import { useEffect, useState, type FormEvent } from "react";
import { api } from "./api";

export function PasswordRecovery({ initialEmail, onBack, onSuccess }: {
  initialEmail: string; onBack: () => void; onSuccess: (email: string) => void;
}) {
  const [email, setEmail] = useState(initialEmail);
  const [sent, setSent] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [waitUntil, setWaitUntil] = useState(0);
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(timer); }, []);
  const seconds = Math.max(0, Math.ceil((waitUntil - now) / 1000));

  async function sendCode() {
    setPending(true); setError("");
    try {
      await api("/auth/forgot-password", { method: "POST", body: { email: email.trim() } });
      setSent(true); setWaitUntil(Date.now() + 300_000);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not request a code."); }
    finally { setPending(false); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sent) { await sendCode(); return; }
    const data = new FormData(event.currentTarget);
    if (data.get("password") !== data.get("confirm")) { setError("Passwords do not match."); return; }
    setPending(true); setError("");
    try {
      await api("/auth/reset-password", { method: "POST", body: {
        email: email.trim(), code: String(data.get("code")).trim(), new_password: String(data.get("password")),
      } });
      onSuccess(email.trim());
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not reset password."); }
    finally { setPending(false); }
  }
  return <>
    <div className="eyebrow">Let’s get you back in</div><h2>{sent ? "Reset your password" : "Forgot password?"}</h2>
    <p>{sent ? "If this email belongs to a verified account, a reset code will arrive shortly. Check your inbox and spam folder. Codes expire after 10 minutes." : "Enter your account email to request a password reset code."}</p>
    <form onSubmit={submit}>
      <div className="field"><label htmlFor="reset-email">Email</label><input id="reset-email" type="email" autoComplete="email" required value={email} readOnly={sent} disabled={pending} onChange={(event) => setEmail(event.target.value)}/></div>
      {sent && <>
        <div className="field"><label htmlFor="reset-code">Reset code</label><input id="reset-code" name="code" className="otp-code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required disabled={pending}/></div>
        <div className="field"><label htmlFor="reset-password">New password</label><input id="reset-password" name="password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required disabled={pending}/><span className="helper">12–128 characters. Resetting signs out all existing sessions.</span></div>
        <div className="field"><label htmlFor="reset-confirm">Confirm new password</label><input id="reset-confirm" name="confirm" type="password" autoComplete="new-password" minLength={12} maxLength={128} required disabled={pending}/></div>
      </>}
      <div className="form-error" role="alert">{error}</div>
      <button className="button button-primary" disabled={pending} type="submit">{pending ? "Please wait…" : sent ? "Reset password" : "Send reset code"}</button>
    </form>
    <div className="auth-switch">
      {sent && <><button className="text-button" type="button" disabled={pending || seconds > 0} onClick={sendCode}>{seconds > 0 ? `Resend code in ${Math.ceil(seconds / 60)} min` : "Resend reset code"}</button><br/><button className="text-button" type="button" disabled={pending} onClick={() => { setSent(false); setError(""); }}>Use another email</button><br/></>}
      <button className="text-button" type="button" disabled={pending} onClick={onBack}>Back to sign in</button>
    </div>
  </>;
}
