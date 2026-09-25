export function registerPageTool(tool) {
  const context = document.modelContext;
  if (!context?.registerTool) return () => {};
  const lifecycle = new AbortController();
  try {
    void Promise.resolve(
      context.registerTool(tool, { signal: lifecycle.signal }),
    ).catch(() => {});
  } catch {
    return () => {};
  }
  return () => lifecycle.abort();
}
