'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { ChevronDown, ChevronUp } from 'lucide-react';

export function DemoControls({ onAfter }: { onAfter: () => Promise<void> | void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [last, setLast] = useState<string | null>(null);

  const fire = async (which: 'koehler' | 'demir' | 'reset') => {
    setBusy(which);
    try {
      const fn = which === 'koehler' ? api.fireKoehler
               : which === 'demir'   ? api.fireDemir
               :                       api.resetDemo;
      const res = await fn();
      setLast(res?.ticket_id || `${which}: ok`);
      await onAfter();
    } catch (e: any) {
      setLast(`error: ${e.message}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="border-b border-paper-200 bg-white">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-6 py-2 text-sm font-medium text-paper-700 hover:bg-paper-50"
      >
        <span>🎭 Demo-Steuerung</span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {open && (
        <div className="px-6 pb-4 grid grid-cols-3 gap-4">
          <div>
            <p className="text-sm font-semibold mb-1">📱 Köhler — Heizung</p>
            <p className="text-xs text-paper-500 mb-2">Fallback. Live: WhatsApp vom echten Telefon.</p>
            <button
              onClick={() => fire('koehler')}
              disabled={busy !== null}
              className="w-full rounded-md border border-paper-300 bg-white px-3 py-2 text-sm font-medium hover:bg-paper-50 disabled:opacity-50"
            >
              {busy === 'koehler' ? 'Sende…' : 'Köhler simulieren'}
            </button>
          </div>

          <div>
            <p className="text-sm font-semibold mb-1">✉ Demir — NK-Beanstandung</p>
            <p className="text-xs text-paper-500 mb-2">Formelle E-Mail von y.demir@gmx.de.</p>
            <button
              onClick={() => fire('demir')}
              disabled={busy !== null}
              className="w-full rounded-md bg-teal-600 px-3 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50"
            >
              {busy === 'demir' ? 'Sende…' : 'Demir abfeuern'}
            </button>
          </div>

          <div>
            <p className="text-sm font-semibold mb-1">↻ Zurücksetzen</p>
            <p className="text-xs text-paper-500 mb-2">Wipe + re-seed inkl. Schornsteinfeger.</p>
            <button
              onClick={() => fire('reset')}
              disabled={busy !== null}
              className="w-full rounded-md border border-paper-300 bg-white px-3 py-2 text-sm font-medium hover:bg-paper-50 disabled:opacity-50"
            >
              {busy === 'reset' ? 'Setze zurück…' : 'Zurücksetzen'}
            </button>
          </div>

          {last && (
            <div className="col-span-3 text-xs text-paper-500 font-mono">
              Letzter Trigger: {last}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
