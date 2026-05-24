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
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import Script from 'next/script';
import { api } from '@/lib/api';
import { ArrowLeft, Mail, MessageSquare, Mic, MicOff, Phone, RotateCcw, AlertTriangle } from 'lucide-react';

// ElevenLabs Conversational AI agent + the demo persona's seeded phone.
// Hardcoded for hackathon speed; move to NEXT_PUBLIC_* envs later.
const ELEVENLABS_AGENT_ID = 'agent_5501ksckr2ppejj8ah5n354qq0n5';
const DEMO_CALLER_PHONE = '+491793960546';  // Köhler's seeded phone
const DEMO_CALLER_NAME = 'Frau Köhler';     // greeted in the first message

// React doesn't know about ElevenLabs' custom element — declare it loosely
// so TS doesn't complain about the attributes.
declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      'elevenlabs-convai': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          'agent-id'?: string;
          'dynamic-variables'?: string;
        },
        HTMLElement
      >;
    }
  }
}

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
  // Mic muting: ElevenLabs widget is sensitive to background noise, so we
  // intercept getUserMedia, capture every audio stream the widget opens,
  // and flip track.enabled on demand. This works regardless of the widget
  // version / internal API.
  const [muted, setMuted] = useState(false);
  const activeStreamsRef = useRef<MediaStream[]>([]);

  useEffect(() => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) return;
    // Patch once — re-patching on hot-reload would shadow the previous patch.
    const md = navigator.mediaDevices as MediaDevices & { __fletcherPatched?: boolean };
    if (md.__fletcherPatched) return;
    const orig = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async (constraints) => {
      const stream = await orig(constraints);
      activeStreamsRef.current.push(stream);
      // Apply current mute state to the new stream immediately.
      stream.getAudioTracks().forEach((t) => { t.enabled = !muted; });
      // Drop ended streams so the list doesn't grow forever.
      stream.getTracks().forEach((t) => t.addEventListener('ended', () => {
        activeStreamsRef.current = activeStreamsRef.current.filter((s) => s !== stream);
      }));
      return stream;
    };
    md.__fletcherPatched = true;
    /* eslint-disable-next-line */
  }, []);

  // Toggle mic on existing streams whenever `muted` changes.
  useEffect(() => {
    activeStreamsRef.current.forEach((s) =>
      s.getAudioTracks().forEach((t) => { t.enabled = !muted; }),
    );
  }, [muted]);

  // Space-bar as push-to-talk shortcut. Only acts when the operator is
  // currently muted — held space momentarily unmutes; releasing remutes.
  // If the mic is already active, spacebar is a no-op (so we don't surprise-
  // mute on release).
  const mutedRef = useRef(false);
  useEffect(() => { mutedRef.current = muted; }, [muted]);
  const pttActiveRef = useRef(false);
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const isTypingTarget = (t: EventTarget | null): boolean => {
      if (!(t instanceof HTMLElement)) return false;
      const tag = t.tagName;
      return tag === 'INPUT' || tag === 'TEXTAREA' || t.isContentEditable;
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code !== 'Space' || e.repeat || isTypingTarget(e.target)) return;
      if (!mutedRef.current) return; // already unmuted — no-op
      e.preventDefault();
      pttActiveRef.current = true;
      setMuted(false);
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code !== 'Space' || isTypingTarget(e.target)) return;
      if (!pttActiveRef.current) return;
      e.preventDefault();
      pttActiveRef.current = false;
      setMuted(true);
    };
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
    };
  }, []);

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
        <section className="mb-6 rounded-lg border border-teal-200 bg-teal-50 p-5">
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

        {/* Voice — browser-based ElevenLabs call (no phone number needed) */}
        <section className="mb-8 rounded-lg border border-teal-200 bg-teal-50 p-5">
          <div className="flex items-start gap-3">
            <div className="rounded-md bg-teal-600 p-2 text-white">
              <Phone size={18} />
            </div>
            <div className="flex-1">
              <h2 className="mb-1 font-semibold text-paper-900">
                Köhler — Anruf im Browser
              </h2>
              <p className="text-sm text-paper-700">
                Klicken Sie auf das schwebende Mikrofon-Symbol unten rechts
                auf dieser Seite, um Fletcher direkt im Browser anzurufen.
                Clara (deutsche Stimme) nimmt den Anruf entgegen, lässt
                Sie Ihr Anliegen schildern und beendet das Gespräch. Sobald
                Sie auflegen, erscheint ein Voicemail-Ticket im Posteingang.
              </p>
              <div className="mt-3 rounded-md border border-teal-200 bg-white px-3 py-2 text-xs text-paper-700">
                <span className="font-semibold">Anrufer-Identität:</span>{' '}
                <span className="font-mono">{DEMO_CALLER_NAME} · {DEMO_CALLER_PHONE}</span>
                <span className="text-paper-500"> (per dynamic-variable an Fletcher übermittelt — Clara begrüßt namentlich)</span>
              </div>
              <div className="mt-2 rounded-md border border-paper-200 bg-paper-50 px-3 py-2 text-xs text-paper-700">
                <span className="font-semibold">Mikrofon-Steuerung:</span>{' '}
                <kbd className="rounded border border-paper-300 bg-white px-1 py-0.5 font-mono text-[10px]">Leertaste</kbd>{' '}
                gedrückt halten zum Sprechen (Push-to-Talk). Klick auf den
                Button unten links wechselt dauerhaft zwischen stumm / aktiv.
              </div>
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

      {/* Floating mute button — fixed bottom-left, opposite the widget's
          bottom-right bubble. Reachable during the call without scrolling. */}
      <button
        onClick={() => setMuted((m) => !m)}
        aria-pressed={muted}
        aria-label={muted ? 'Mikrofon einschalten' : 'Mikrofon stumm schalten'}
        title={muted ? 'Mikrofon stumm — klicken zum Aktivieren (oder Leertaste)' : 'Mikrofon aktiv — klicken zum Stummschalten (oder Leertaste)'}
        className={
          'fixed bottom-6 left-6 z-50 flex items-center gap-2 rounded-full px-4 py-3 shadow-lg transition ' +
          (muted
            ? 'bg-red-600 text-white hover:bg-red-700'
            : 'bg-teal-600 text-white hover:bg-teal-700')
        }
      >
        {muted ? <MicOff size={20} /> : <Mic size={20} />}
        <span className="text-sm font-semibold">
          {muted ? 'Stumm' : 'Mikro aktiv'}
        </span>
      </button>

      {/* ElevenLabs Conversational AI widget. Loads the custom element + the
          floating mic bubble in the bottom-right of every page render. The
          dynamic-variable `caller_phone` flows back to Fletcher via the
          post-call webhook so the tenant lookup matches Köhler. */}
      <Script
        src="https://unpkg.com/@elevenlabs/convai-widget-embed"
        strategy="afterInteractive"
        type="text/javascript"
      />
      <elevenlabs-convai
        agent-id={ELEVENLABS_AGENT_ID}
        dynamic-variables={JSON.stringify({
          caller_phone: DEMO_CALLER_PHONE,
          caller_name: DEMO_CALLER_NAME,
        })}
      />
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
