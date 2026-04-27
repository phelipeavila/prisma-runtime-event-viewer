import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { auth } from "@/api/auth";
import { InfoTip } from "@/components/InfoTip";

function normalizeConsoleUrl(input: string): string {
  let url = input.trim();
  if (!url) return url;
  // Add scheme if missing — easy mistake, would otherwise blow up in httpx.
  if (!/^https?:\/\//i.test(url)) url = `https://${url}`;
  // Strip a stray "/api" or trailing slashes — the client appends the path itself.
  url = url.replace(/\/+$/, "");
  url = url.replace(/\/api(\/.*)?$/i, "");
  return url;
}

export function LoginGate() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  // Read whatever the backend already knows (env-provided console URL or a value
  // remembered from a previous login). We never receive the token here.
  const status = useQuery({ queryKey: ["auth", "status"], queryFn: auth.status });
  const knownConsoleUrl = status.data?.console_url ?? null;

  const [mode, setMode] = useState<"keysecret" | "token">("keysecret");
  const [consoleUrl, setConsoleUrl] = useState("");
  const [consoleUrlTouched, setConsoleUrlTouched] = useState(false);
  const [key, setKey] = useState("");
  const [secret, setSecret] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!consoleUrlTouched && knownConsoleUrl) {
      setConsoleUrl(knownConsoleUrl);
    }
  }, [knownConsoleUrl, consoleUrlTouched]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const normalized = normalizeConsoleUrl(consoleUrl);
    if (normalized !== consoleUrl) setConsoleUrl(normalized);
    try {
      if (mode === "token") {
        await auth.login({ mode: "token", console_url: normalized, token });
      } else {
        await auth.login({
          mode: "keysecret",
          console_url: normalized,
          key,
          secret,
        });
      }
      await qc.invalidateQueries({ queryKey: ["auth", "status"] });
      navigate("/events");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="center">
      <form className="login-card col" onSubmit={submit}>
        <h2 style={{ margin: 0 }}>Connect to Prisma Cloud</h2>
        <div className="row" style={{ gap: 4 }}>
          <button
            type="button"
            className={mode === "keysecret" ? "primary" : ""}
            onClick={() => setMode("keysecret")}
          >
            Access Key
          </button>
          <button
            type="button"
            className={mode === "token" ? "primary" : ""}
            onClick={() => setMode("token")}
          >
            Bearer Token
          </button>
        </div>
        <label className="col">
          <span className="label">
            Console URL
            <InfoTip>
              Just the host (e.g. <code>console.example.com</code>). Don't include
              <code>/api</code>. Scheme is optional — <code>https://</code> is
              added if missing.
            </InfoTip>
            {knownConsoleUrl && consoleUrl === knownConsoleUrl && (
              <span className="meta" style={{ marginLeft: 6, textTransform: "none" }}>
                · prefilled from server
              </span>
            )}
          </span>
          <input
            value={consoleUrl}
            onChange={(e) => {
              setConsoleUrl(e.target.value);
              setConsoleUrlTouched(true);
            }}
            placeholder="https://console.example.com"
            required
          />
        </label>
        {mode === "keysecret" ? (
          <>
            <label className="col">
              <span className="label">
                Access Key ID
                <InfoTip>
                  Created in the Prisma Cloud Console under
                  <code>Settings → Access Keys</code>. Not your console
                  username/password.
                </InfoTip>
              </span>
              <input
                value={key}
                onChange={(e) => setKey(e.target.value)}
                autoComplete="username"
                required
              />
            </label>
            <label className="col">
              <span className="label">
                Secret Key
                <InfoTip>
                  The secret value shown once when the access key was
                  created. If you didn't save it, generate a new key.
                </InfoTip>
              </span>
              <input
                type="password"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                autoComplete="current-password"
                required
              />
            </label>
          </>
        ) : (
          <label className="col">
            <span className="label">
              Token (JWT)
              <InfoTip>
                Paste a pre-issued JWT (e.g. exported from another tool).
                The app won't verify it until the first API call.
              </InfoTip>
            </span>
            <textarea
              rows={4}
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
            />
          </label>
        )}
        {error && (
          <div
            className="panel"
            style={{
              padding: "8px 12px",
              borderColor: "var(--danger)",
              color: "var(--danger)",
              fontSize: 13,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {error}
          </div>
        )}
        <button type="submit" className="primary" disabled={busy}>
          {busy ? "Connecting…" : "Connect"}
        </button>
      </form>
    </div>
  );
}
