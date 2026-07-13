import { useCallback, useEffect, useState } from 'react';

import { resolveTheme, type TTheme } from '@/lib/theme-preference';

const THEME_STORAGE_KEY = 'release-assurance-theme';

const getPreferredTheme = (): TTheme => {
  return resolveTheme(localStorage.getItem(THEME_STORAGE_KEY), window.matchMedia('(prefers-color-scheme: dark)').matches);
};

const applyTheme = (theme: TTheme): void => {
  document.documentElement.dataset.theme = theme;
};

const initializeTheme = (): TTheme => {
  const theme = getPreferredTheme();
  applyTheme(theme);
  return theme;
};

const useTheme = () => {
  const [theme, setThemeState] = useState<TTheme>(getPreferredTheme);

  useEffect(() => {
    const colorScheme = window.matchMedia('(prefers-color-scheme: dark)');

    const syncTheme = (): void => {
      const nextTheme = resolveTheme(localStorage.getItem(THEME_STORAGE_KEY), colorScheme.matches);
      applyTheme(nextTheme);
      setThemeState(nextTheme);
    };

    const handleStorage = (event: StorageEvent): void => {
      if (event.key === THEME_STORAGE_KEY) {
        syncTheme();
      }
    };

    colorScheme.addEventListener('change', syncTheme);
    window.addEventListener('storage', handleStorage);

    return () => {
      colorScheme.removeEventListener('change', syncTheme);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const setTheme = useCallback((nextTheme: TTheme): void => {
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    applyTheme(nextTheme);
    setThemeState(nextTheme);
  }, []);

  return { setTheme, theme };
};

export { initializeTheme, useTheme };
