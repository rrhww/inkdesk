export default function RootLoading() {
  return (
    <main className="mx-auto max-w-reading px-6 py-16">
      <div className="h-4 w-24 animate-pulse rounded-sm bg-ink-low" />
      <div className="mt-6 h-12 w-3/4 animate-pulse rounded-sm bg-ink-low" />
      <div className="mt-8 space-y-4">
        <div className="h-4 w-full animate-pulse rounded-sm bg-ink-low" />
        <div className="h-4 w-5/6 animate-pulse rounded-sm bg-ink-low" />
        <div className="h-4 w-2/3 animate-pulse rounded-sm bg-ink-low" />
      </div>
    </main>
  );
}
