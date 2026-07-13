import { Skeleton } from '@/components/ui/skeleton';

const AppPending = () => {
  return (
    <main className="mx-auto flex w-full max-w-[1180px] flex-col gap-4 p-4 sm:p-6">
      <Skeleton className="h-36 w-full" />
      <Skeleton className="h-72 w-full" />
      <Skeleton className="h-40 w-full" />
    </main>
  );
};

export { AppPending };
