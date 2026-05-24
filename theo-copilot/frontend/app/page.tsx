'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, cx, type Ticket, type TicketDetail } from '@/lib/api';
import { InboxList } from '@/components/inbox-list';
import { TicketView } from '@/components/ticket-view';
import { EnrichmentCards } from '@/components/enrichment-cards';
import { ExternalLink, RefreshCw, Search } from 'lucide-react';

type View = 'inbox' | 'archive';

export default function Page() {
  const [view, setView] = useState<View>('inbox');
  const [search, setSearch] = useState('');
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [openedIds, setOpenedIds] = useState<Set<string>>(new Set());
  const [openCount, setOpenCount] = useState<number | null>(null);

  const refresh = async () => {
    try {
      const [data, count] = await Promise.all([
        api.listTickets(view, view === 'archive' ? search : undefined),
        api.countOpen().catch(() => ({ count: 0 })),
      ]);
      setTickets(data);
      setOpenCount(count.count);
      // If the previously-selected ticket isn't in the new list, clear it.
      if (selectedId && !data.find((t) => t.id === selectedId)) {
        setSelectedId(data.length > 0 ? data[0].id : null);
      } else if (!selectedId && data.length > 0) {
        setSelectedId(data[0].id);
      }
    } catch (e: any) {
      console.error(e);
      setTickets([]);
    }
  };

  // Re-fetch when view changes; for search, debounce a touch.
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [view]);
  useEffect(() => {
    if (view !== 'archive') return;
    const t = setTimeout(refresh, 250);
    return () => clearTimeout(t);
    /* eslint-disable-next-line */
  }, [search]);

  // Initial open-count fetch (covers the page-load case).
  useEffect(() => {
    api.countOpen().then((r) => setOpenCount(r.count)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    setOpenedIds((prev) => new Set(prev).add(selectedId));
    api.getTicket(selectedId).then(setDetail).catch((e) => {
      console.error(e);
      setDetail(null);
    });
  }, [selectedId]);

  const onAfterMutation = async () => {
    await refresh();
    if (selectedId) {
      try {
        const d = await api.getTicket(selectedId);
        setDetail(d);
      } catch {
        setDetail(null);
      }
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-paper-200 bg-white px-6 py-3">
        <div className="flex items-baseline gap-3">
          <h1 className="font-serif text-xl italic font-medium text-teal-700">Fletcher</h1>
          <span className="text-sm font-medium text-paper-500">· Sarah Weber</span>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/demo"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 rounded-md border border-paper-300 bg-white px-3 py-1.5 text-sm font-medium text-paper-600 hover:bg-paper-50 transition"
            title="Demo-Steuerung in neuem Tab öffnen"
          >
            Demo <ExternalLink size={12} />
          </Link>
          <button
            onClick={refresh}
            className="flex items-center gap-2 rounded-md border border-paper-300 bg-white px-3 py-1.5 text-sm font-medium text-paper-900 hover:bg-paper-50 transition"
          >
            <RefreshCw size={14} /> Aktualisieren
          </button>
        </div>
      </header>

      {/* Inbox / Archiv tabs */}
      <div className="flex items-center border-b border-paper-200 bg-white px-6">
        {(['inbox', 'archive'] as View[]).map((v) => {
          const isActive = view === v;
          const label = v === 'inbox' ? 'Posteingang' : 'Archiv';
          // Only the Inbox tab carries a count badge (spec §8.1).
          const badge = v === 'inbox' && openCount !== null ? ` · ${openCount}` : '';
          return (
            <button
              key={v}
              onClick={() => setView(v)}
              className={cx(
                'relative px-4 py-3 text-sm font-semibold uppercase tracking-wide transition',
                isActive
                  ? 'text-teal-700'
                  : 'text-paper-500 hover:text-paper-700',
              )}
            >
              {label}{badge}
              {isActive && (
                <span className="absolute left-0 right-0 -bottom-px h-0.5 bg-teal-600" />
              )}
            </button>
          );
        })}
      </div>

      {/* Main: 3-column inbox layout — list / detail / context */}
      <div className="flex flex-1 overflow-hidden">
        {/* Column 1: ticket list */}
        <aside className="w-[360px] shrink-0 border-r border-paper-200 bg-white overflow-y-auto flex flex-col">
          {view === 'archive' && (
            <div className="px-4 pt-3 pb-2 border-b border-paper-200">
              <div className="relative">
                <Search
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-paper-400"
                />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Archiv durchsuchen…"
                  className="w-full rounded-md border border-paper-300 bg-white pl-8 pr-3 py-1.5 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-100"
                />
              </div>
            </div>
          )}
          <div className="flex-1 overflow-y-auto">
            <InboxList
              tickets={tickets}
              selectedId={selectedId}
              openedIds={openedIds}
              onSelect={setSelectedId}
            />
          </div>
        </aside>

        {/* Column 2: ticket detail (conversation + actions) */}
        <main className="flex-1 min-w-0 overflow-y-auto bg-paper-50">
          {detail ? (
            <TicketView ticket={detail} onAfter={onAfterMutation} />
          ) : (
            <div className="flex h-full items-center justify-center text-paper-400 font-serif italic">
              {view === 'archive'
                ? 'Wählen Sie ein archiviertes Ticket aus.'
                : 'Wählen Sie ein Ticket aus der Liste.'}
            </div>
          )}
        </main>

        {/* Column 3: enrichment context */}
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
