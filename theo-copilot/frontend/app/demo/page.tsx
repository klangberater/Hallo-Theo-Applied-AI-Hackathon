'use client';

/**
 * Demo control panel — standalone page.
 *
 * Lives at /inbox/demo/ so it can be opened in a second browser tab (or on a
 * second laptop) while the main inbox is mirrored to the projector. The jury
 * sees a clean inbox; the operator works from here.
 *
 * Three things happen during a demo:
 *   1. Köhler — the operator sends a REAL WhatsApp from their phone to the
 *      paired number. No button needed for the happy path. The "Köhler
 *      simulieren" button only exists as a fallback if the Baileys bridge
 *      is offline.
 *   2. Demir — email-from-phone is not in scope, so this is a real button
 *      that injects the pre-canned formal email.
 *   3. Reset — wipes Postgres state + re-seeds between dry runs.
 */
import { useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { ArrowLeft, Mail, MessageSquare, RotateCcw, AlertTriangle } from 'lucide-react';

type Action = 'koehler' | 'demir' | 'reset';

interface LogEntry {
  ts: string;
  action: Action;
  result: string;
  ok: boolean;
}

export default function DemoPage() {
  const [busy, setBusy] = useState<Action | null>(null);
  const [log, setLog] = useState<LogEntry[]>([]);

  const fire = async (which: Action) => {
    setBusy(which);
    const ts = new Date().toLocaleTimeString('de-DE');
    try {
      const fn = which === 'koehler' ? api.fireKoehler
               : which === 'demir'   ? api.fireDemir
               :                       api.resetDemo;
      const res: any = await fn();
      const result = res?.ticket_id || res?.status || 'ok';
      setLog((prev) => [{ ts, action: which, result, ok: true }, ...prev].slice(0, 10));
    } catch (e: any) {
      setLog((prev) => [{ ts, action: which, result: e.message, ok: false }, ...prev].slice(0, 10));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="min-h-screen bg-paper-50">
      {/* Header */}
      <header className="border-b border-paper-200 bg-white px-8 py-4">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <div className="flex items-baseline gap-3">
            <h1 className="font-serif text-xl italic font-medium text-teal-700">Fletcher</h1>
            <span className="text-sm font-medium text-paper-500">· Demo-Steuerung</span>
          </div>
          <Link
            href="/"
            className="flex items-center gap-2 text-sm font-medium text-paper-600 hover:text-teal-700"
          >
            <ArrowLeft size={14} /> Zurück zum Posteingang
          </Link>
        </div>
      </header>

      {/* Body */}
      <main className="mx-auto max-w-3xl px-8 py-8">
        <p className="mb-6 text-sm text-paper-600">
          In einem zweiten Browser-Tab öffnen — der Jury im Haupttab nur den
          Posteingang zeigen. Aktionen wirken sich sofort auf den Posteingang
          aus; dort „Aktualisieren" klicken oder kurz warten.
        </p>

        {/* Primary path: real WhatsApp */}
        <section className="mb-8 rounded-lg border border-teal-200 bg-teal-50 p-5">
          <div className="flex items-start gap-3">
            <div className="rounded-md bg-teal-600 p-2 text-white">
              <MessageSquare size={18} />
            </div>
            <div className="flex-1">
              <h2 className="mb-1 font-semibold text-paper-900">
                Köhler — echte WhatsApp
              </h2>
              <p className="text-sm text-paper-700">
                Sende eine WhatsApp an die mit dem System gepairte Nummer.
                Die Nachricht landet automatisch über die Baileys-Brücke im
                Posteingang — kein Knopfdruck nötig. Beispiel-Text:
              </p>
              <pre className="mt-3 rounded-md border border-teal-200 bg-white px-3 py-2 text-xs text-paper-700 whitespace-pre-wrap font-mono">
{`Die Heizung im Wohnzimmer ist seit heute Nachmittag wieder kalt.
Das ist jetzt das sechste Mal mit demselben Heizkörper.
Für Donnerstag und Freitag ist Frost angekündigt.`}
              </pre>
            </div>
          </div>
        </section>

        {/* Real buttons: email + reset */}
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-paper-500">
          Andere Aktionen
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <ActionCard
            icon={<Mail size={20} />}
            title="Demir — NK-Beanstandung"
            description="Formelle E-Mail von y.demir@gmx.de auslösen (E-Mail-Eingang ist nicht an einen echten Provider angebunden)."
            buttonLabel={busy === 'demir' ? 'Sende…' : 'Demir abfeuern'}
            onClick={() => fire('demir')}
            disabled={busy !== null}
            variant="primary"
          />
          <ActionCard
            icon={<RotateCcw size={20} />}
            title="Zurücksetzen"
            description="Datenbank wipen + Seed neu laden (inkl. Schornsteinfeger-Autonom-Ticket)."
            buttonLabel={busy === 'reset' ? 'Setze zurück…' : 'Zurücksetzen'}
            onClick={() => fire('reset')}
            disabled={busy !== null}
            variant="outline"
          />
        </div>

        {/* Fallback */}
        <section className="mt-10">
          <details className="rounded-md border border-paper-200 bg-white">
            <summary className="cursor-pointer px-4 py-2 text-sm font-medium text-paper-600 hover:bg-paper-50 flex items-center gap-2">
              <AlertTriangle size={14} className="text-amber-500" />
              Fallback: Köhler-WhatsApp simulieren (Brücke offline)
            </summary>
            <div className="border-t border-paper-200 px-4 py-3">
              <p className="mb-3 text-xs text-paper-500">
                Nur klicken, wenn die WhatsApp-Brücke nicht antwortet oder das
                gepairte Telefon nicht erreichbar ist. Erzeugt das gleiche
                Ticket, als käme es per echter WhatsApp herein.
              </p>
              <button
                onClick={() => fire('koehler')}
                disabled={busy !== null}
                className="rounded-md border border-paper-300 bg-white px-3 py-2 text-sm font-medium hover:bg-paper-50 disabled:opacity-50"
              >
                {busy === 'koehler' ? 'Sende…' : 'Köhler simulieren'}
              </button>
            </div>
          </details>
        </section>

        {/* Log */}
        <section className="mt-10">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-paper-500">
            Letzte Aktionen
          </h2>
          {log.length === 0 ? (
            <p className="rounded-md border border-dashed border-paper-300 bg-white px-4 py-6 text-center text-sm italic text-paper-400">
              Noch nichts ausgelöst.
            </p>
          ) : (
            <ul className="divide-y divide-paper-200 rounded-md border border-paper-200 bg-white">
              {log.map((e, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between gap-4 px-4 py-2 text-sm"
                >
                  <span className="font-mono text-xs text-paper-500">{e.ts}</span>
                  <span className="font-medium text-paper-700">{e.action}</span>
                  <span
                    className={
                      e.ok
                        ? 'font-mono text-xs text-teal-700'
                        : 'font-mono text-xs text-red-700'
                    }
                  >
                    {e.result}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

function ActionCard({
  icon, title, description, buttonLabel, onClick, disabled, variant,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  buttonLabel: string;
  onClick: () => void;
  disabled: boolean;
  variant: 'primary' | 'outline';
}) {
  return (
    <div className="flex flex-col rounded-lg border border-paper-200 bg-white p-4">
      <div className="mb-2 flex items-center gap-2 text-teal-700">
        {icon}
        <h3 className="text-sm font-semibold text-paper-900">{title}</h3>
      </div>
      <p className="mb-4 flex-1 text-xs text-paper-500">{description}</p>
      <button
        onClick={onClick}
        disabled={disabled}
        className={
          variant === 'primary'
            ? 'w-full rounded-md bg-teal-600 px-3 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50'
            : 'w-full rounded-md border border-paper-300 bg-white px-3 py-2 text-sm font-medium hover:bg-paper-50 disabled:opacity-50'
        }
      >
        {buttonLabel}
      </button>
    </div>
  );
}
