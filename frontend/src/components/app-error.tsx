import type { ErrorComponentProps } from '@tanstack/react-router';
import { CircleAlert } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

const AppError = ({ error, reset }: ErrorComponentProps) => {
  return (
    <main className="mx-auto w-full max-w-[1180px] p-4 sm:p-6">
      <Alert variant="destructive">
        <CircleAlert />
        <AlertTitle>Unable to load fixture data</AlertTitle>
        <AlertDescription>{error.message}</AlertDescription>
        <Button className="mt-3 w-fit" size="sm" variant="outline" onClick={reset}>
          Try again
        </Button>
      </Alert>
    </main>
  );
};

export { AppError };
