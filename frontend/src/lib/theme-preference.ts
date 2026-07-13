type TTheme = 'light' | 'dark';

const isTheme = (value: string | null): value is TTheme => {
  return value === 'light' || value === 'dark';
};

const resolveTheme = (storedTheme: string | null, prefersDark: boolean): TTheme => {
  if (isTheme(storedTheme)) {
    return storedTheme;
  }

  return prefersDark ? 'dark' : 'light';
};

export type { TTheme };
export { resolveTheme };
