export default function AppLoading() {
  return (
    <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
      <div className="h-4 w-28 animate-pulse rounded-sm bg-ink-low" />
      <div className="mt-6 h-12 w-2/3 animate-pulse rounded-sm bg-ink-low" />
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <div className="h-40 animate-pulse rounded-[28px] bg-ink-low" />
        <div className="h-40 animate-pulse rounded-[28px] bg-ink-low" />
        <div className="h-40 animate-pulse rounded-[28px] bg-ink-low" />
      </div>
    </main>
  );
}
