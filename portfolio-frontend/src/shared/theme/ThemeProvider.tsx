'use client';

import { createContext, useCallback, useContext, useEffect, useState } from 'react';

export type ThemeColor = 'blue' | 'purple';
export type ThemeMode = 'dark' | 'light';

const COLOR_KEY = 'theme';
const MODE_KEY = 'theme-mode';
const DEFAULT_COLOR: ThemeColor = 'blue';
const DEFAULT_MODE: ThemeMode = 'dark';

interface ThemeContextValue {
  color: ThemeColor;
  mode: ThemeMode;
  setColor: (color: ThemeColor) => void;
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
  toggleColor: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readStored<T extends string>(key: string, valid: readonly T[], fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const saved = window.localStorage.getItem(key);
    if (saved && (valid as readonly string[]).includes(saved)) return saved as T;
  } catch {
    /* noop */
  }
  return fallback;
}

function applyAttr(name: string, value: string) {
  if (typeof document === 'undefined') return;
  document.documentElement.setAttribute(name, value);
}

function setCookie(key: string, value: string) {
  try {
    document.cookie = `${key}=${value}; path=/; max-age=31536000; SameSite=Lax`;
  } catch {
    /* noop */
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [color, setColorState] = useState<ThemeColor>(DEFAULT_COLOR);
  const [mode, setModeState] = useState<ThemeMode>(DEFAULT_MODE);

  useEffect(() => {
    const initialColor = readStored<ThemeColor>(COLOR_KEY, ['blue', 'purple'] as const, DEFAULT_COLOR);
    const initialMode = readStored<ThemeMode>(MODE_KEY, ['dark', 'light'] as const, DEFAULT_MODE);
    applyAttr('data-theme', initialColor);
    applyAttr('data-theme-mode', initialMode);
    setCookie(COLOR_KEY, initialColor);
    setCookie(MODE_KEY, initialMode);
    const id = setTimeout(() => {
      setColorState(initialColor);
      setModeState(initialMode);
    }, 0);
    return () => clearTimeout(id);
  }, []);

  const setColor = useCallback((next: ThemeColor) => {
    setColorState(next);
    applyAttr('data-theme', next);
    setCookie(COLOR_KEY, next);
    try {
      window.localStorage.setItem(COLOR_KEY, next);
    } catch {
      /* noop */
    }
  }, []);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    applyAttr('data-theme-mode', next);
    setCookie(MODE_KEY, next);
    try {
      window.localStorage.setItem(MODE_KEY, next);
    } catch {
      /* noop */
    }
  }, []);

  const toggleColor = useCallback(() => {
    setColor(color === 'blue' ? 'purple' : 'blue');
  }, [color, setColor]);

  const toggleMode = useCallback(() => {
    setMode(mode === 'dark' ? 'light' : 'dark');
  }, [mode, setMode]);

  return (
    <ThemeContext.Provider value={{ color, mode, setColor, setMode, toggleColor, toggleMode }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used inside ThemeProvider');
  }
  return ctx;
}
