'use client';

import { Toaster } from 'sonner';

export function ToastProvider() {
  return (
    <Toaster
      position="bottom-right"
      theme="dark"
      toastOptions={{
        style: {
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          color: '#e4e8ef',
          backdropFilter: 'blur(18px)',
        },
        className: 'font-sans',
      }}
    />
  );
}
