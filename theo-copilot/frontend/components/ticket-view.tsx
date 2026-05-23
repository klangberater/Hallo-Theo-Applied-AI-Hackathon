'use client';

import { useEffect, useState } from 'react';
import { api, type ThreadMessage, type TicketDetail, type TraceEvent } from '@/lib/api';
import { EnrichmentCards } from '@/components/enrichment-cards';
import { ActionPanel } from '@/components/action-panel';

function fmt(iso: string): string {
  return new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  });
}

function PriorityChip({ priority }: { priority: string | null }) {
  if (priority === 'DRINGEND')
    return <span className="inline-flex rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[11px] font-semibold uppercase text-red-700">Dringend</span>;
  if (priority === 'Hoch')
    return <span className="inline-flex rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold uppercase text-amber-700">Hoch</span>;
  return <span className="inline-flex rounded-full border border-paper-200 bg-paper-100 px-2 py-0.5 text-[11px] font-semibold uppercase text-paper-700">Standard</span>;
}

export function TicketView({
  ticket, onAfter,
}: { ticket: TicketDetail; onAfter: () => Promise<void> | void }) {
  const [messages, setMessages] = useState<ThreadMessage[]>([]);

  useEffect(() => {
    api.getThread(ticket.id).then(setMessages).catch(() => setMessages([]));
  }, [ticket.id]);

  return (
    <div className="px-8 py-6 max-w-4xl mx-auto">
      {/* Header */}
      <header className="border-b border-paper-200 pb-4 mb-6">
        <h2 className="font-serif text-2xl font-medium leading-tight tracking-tight mb-2 text-paper-900">
          {ticket.tenant_name} — {ticket.unit_label}
        </h2>
        <div className="flex flex-wrap items-center gap-2 text-sm text-paper-500">
          <span>{ticket.property_address}</span>
          <span className="text-paper-400">·</span>
          <span>Ticket <code className="font-mono text-xs">{ticket.id}</code></span>
          <span className="text-paper-400">·</span>
          <PriorityChip priority={ticket.priority} />
          <span className="inline-flex rounded-full border border-blue-100 bg-blue-50 px-2 py-0.5 text-[11px] font-semibold uppercase text-blue-600">
            {(ticket.status || '').replace(/_/g, ' ')}
          </span>
        </div>
      </header>

      {/* Conversation */}
      <section className="mb-6">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-paper-500 mb-3">
          Konversation
        </h3>
        {messages.length === 0 ? (
          <div className="rounded-lg bg-paper-100 px-5 py-4">
            <div className="text-xs text-paper-500 mb-1">
              <strong className="font-semibold text-paper-900">{ticket.tenant_name}</strong>
            </div>
            <p className="whitespace-pre-wrap text-paper-900">{ticket.full_text}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((m) => (
              <div
                key={m.id}
                className={m.direction === 'outbound'
                  ? 'rounded-lg border-l-2 border-teal-600 bg-teal-50 px-5 py-4'
                  : 'rounded-lg bg-paper-100 px-5 py-4'}
              >
                <div className="text-xs text-paper-500 mb-1 flex gap-2">
                  <strong className="font-semibold text-paper-900">{m.sender}</strong>
                  <span>·</span>
                  <span>{fmt(m.sent_at)}</span>
                </div>
                <p className="whitespace-pre-wrap text-paper-900 leading-relaxed">{m.body}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Action panel — three modes */}
      <ActionPanel ticket={ticket} onAfter={onAfter} />

      {/* Enrichment cards */}
      <section className="mt-8">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-paper-500 mb-3">
          Anreicherung
        </h3>
        <EnrichmentCards ticket={ticket} />
      </section>
    </div>
  );
}
