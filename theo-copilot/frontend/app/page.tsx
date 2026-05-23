'use client';

import { useEffect, useState } from 'react';
import { api, type Ticket, type TicketDetail } from '@/lib/api';
import { InboxList } from '@/components/inbox-list';
import { TicketView } from '@/components/ticket-view';
import { EnrichmentCards } from '@/components/enrichment-cards';
import { DemoControls } from '@/components/demo-controls';
import { RefreshCw } from 'lucide-react';

export default function Page() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [openedIds, setOpenedIds] = useState<Set<string>>(new Set());

  const refresh = async () => {
    try {
      const data = await api.listTickets();
      setTickets(data);
      if (!selectedId && data.length > 0) setSelectedId(data[0].id);
    } catch (e: any) {
      console.error(e);
      setTickets([]);
    }
  };

  useEffect(() => { refresh(); }, []);

  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    setOpenedIds((prev) => new Set(prev).add(selectedId));
    api.getTicket(selectedId).then(setDetail).catch((e) => {
      console.error(e);
      setDetail(null);
    });
  }, [selectedId]);

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-paper-200 bg-white px-6 py-3">
        <div className="flex items-baseline gap-3">
          <h1 className="font-serif text-xl italic font-medium text-teal-700">Fletcher</h1>
          <span className="text-sm font-medium text-paper-500">· Sarah Weber</span>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-2 rounded-md border border-paper-300 bg-white px-3 py-1.5 text-sm font-medium text-paper-900 hover:bg-paper-50 transition"
        >
          <RefreshCw size={14} /> Aktualisieren
        </button>
      </header>

      {/* Demo controls (collapsible) */}
      <DemoControls onAfter={refresh} />

      {/* Main: 3-column inbox layout — list / detail / context */}
      <div className="flex flex-1 overflow-hidden">
        {/* Column 1: ticket list */}
        <aside className="w-[360px] shrink-0 border-r border-paper-200 bg-white overflow-y-auto">
          <h2 className="px-4 pt-4 pb-2 text-xs font-semibold uppercase tracking-wider text-paper-500">
            Inbox
          </h2>
          <InboxList
            tickets={tickets}
            selectedId={selectedId}
            openedIds={openedIds}
            onSelect={setSelectedId}
          />
        </aside>

        {/* Column 2: ticket detail (conversation + actions) */}
        <main className="flex-1 min-w-0 overflow-y-auto bg-paper-50">
          {detail ? (
            <TicketView ticket={detail} onAfter={async () => {
              await refresh();
              if (selectedId) {
                const d = await api.getTicket(selectedId);
                setDetail(d);
              }
            }} />
          ) : (
            <div className="flex h-full items-center justify-center text-paper-400 font-serif italic">
              Wählen Sie ein Ticket aus der Liste.
            </div>
          )}
        </main>

        {/* Column 3: enrichment context (stays in view while reading) */}
        {detail && (
          <aside className="w-[400px] shrink-0 border-l border-paper-200 bg-paper-100 overflow-y-auto">
            <h2 className="px-5 pt-4 pb-2 text-xs font-semibold uppercase tracking-wider text-paper-500">
              Anreicherung
            </h2>
            <div className="px-5 pb-6">
              <EnrichmentCards ticket={detail} />
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
