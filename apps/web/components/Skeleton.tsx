export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-neutral-800/60 ${className}`} />;
}

export function ClauseSkeleton() {
  return (
    <div className="rounded-md border border-neutral-800 bg-neutral-950 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-4/5" />
        </div>
        <Skeleton className="h-6 w-16" />
      </div>
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <header className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-7 w-64" />
          <Skeleton className="h-4 w-48" />
        </div>
        <Skeleton className="h-12 w-32" />
      </header>
      <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-[1fr_400px]">
        <section className="space-y-2">
          <Skeleton className="h-5 w-32" />
          <div className="mt-4 space-y-2">
            {Array.from({ length: 6 }).map((_, i) => <ClauseSkeleton key={i} />)}
          </div>
        </section>
        <aside>
          <Skeleton className="h-[60vh] w-full" />
        </aside>
      </div>
    </main>
  );
}
