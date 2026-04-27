export function triggerDownload(url: string): void {
  const a = document.createElement("a");
  a.href = url;
  a.rel = "noopener";
  a.click();
}

export function encodeFilters(filters: object): string {
  return encodeURIComponent(JSON.stringify(filters));
}
