import { Moon, Sun } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useTheme } from '@/lib/theme';

const ThemeToggle = () => {
  const { setTheme, theme } = useTheme();
  const nextTheme = theme === 'dark' ? 'light' : 'dark';
  const label = `Use ${nextTheme} theme`;

  return (
    <Button type="button" variant="outline" size="icon" aria-label={label} title={label} onClick={() => setTheme(nextTheme)}>
      {theme === 'dark' ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
      <span className="sr-only">{label}</span>
    </Button>
  );
};

export { ThemeToggle };
