import { useEffect } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { auth } from "@/api/auth";
import { meta as metaApi } from "@/api/meta";
import { useToastStore } from "@/state/toastStore";

export function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);

  const status = useQuery({ queryKey: ["auth", "status"], queryFn: auth.status });
  const meta = useQuery({ queryKey: ["meta"], queryFn: metaApi.get, refetchInterval: 5000 });

  useEffect(() => {
    if (status.data && !status.data.authenticated && location.pathname !== "/login") {
      navigate("/login", { replace: true });
    }
    if (status.data?.authenticated && location.pathname === "/login") {
      navigate("/events", { replace: true });
    }
  }, [status.data, location.pathname, navigate]);

  return (
    <div className="app">
      <div className="topbar">
        <span className="brand">RUNTIME EVENT VIEWER</span>
        <span className="meta">Prisma Cloud · Container Audits</span>
        <span className="grow" />
        {meta.data && (
          <span className="meta">
            Console: {meta.data.console_url || "—"} · Cached rows:{" "}
            <strong>{meta.data.row_count.toLocaleString()}</strong>
          </span>
        )}
        {status.data?.authenticated && (
          <button
            onClick={async () => {
              await auth.logout();
              navigate("/login");
            }}
          >
            Logout
          </button>
        )}
      </div>
      <Outlet />
      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.level}`} onClick={() => dismiss(t.id)}>
            {t.message}
          </div>
        ))}
      </div>
    </div>
  );
}
