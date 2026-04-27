import type { ReactNode } from "react";

export function InfoTip({ children }: { children: ReactNode }) {
  return (
    <span className="info-tip" tabIndex={0} aria-label="More info">
      <span className="info-icon">i</span>
      <span className="info-bubble">{children}</span>
    </span>
  );
}
