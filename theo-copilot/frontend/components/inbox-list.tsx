import { cx, type Ticket } from '@/lib/api';

const CHANNEL_ICON: Record<string, string> = {
  whatsapp: '💬', email: '✉', voicemail: '📞', portal: '🖥',
};

function ago(opened_at: string | null): string {
  if (!opened_at) return '';
  const then = new Date(opened_at).getTime();
  const sec = (Date.now() - then) / 1000;
  if (sec < 60) return 'jetzt';
  if (sec < 3600) return `vor ${Math.floor(sec / 60)} min`;
  if (sec < 86400) return `vor ${Math.floor(sec / 3600)} h`;
  return `vor ${Math.floor(sec / 86400)} d`;
}

function ModeChip({ mode }: { mode: string | null }) {
  if (mode === 'autonomous_done')
    return <span className="inline-flex items-center rounded-full border border-teal-200 bg-teal-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-teal-800">✓ Autonom</span>;
  if (mode === 'bundle_approve')
    return <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-amber-700">Einmal bestätigen</span>;
  return null;
}

function PriorityPill({ priority }: { priority: string | null }) {
  if (priority === 'DRINGEND')
    return <span className="inline-flex rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[11px] font-semibold uppercase text-red-700">Dringend</span>;
  if (priority === 'Hoch')
    return <span className="inline-flex rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold uppercase text-amber-700">Hoch</span>;
  return null;
}

export function InboxList({
  tickets, selectedId, openedIds, onSelect,
}: {
  tickets: Ticket[] | null;
  selectedId: string | null;
  openedIds: Set<string>;
  onSelect: (id: string) => void;
}) {
  if (tickets === null) {
    return <div className="px-4 py-8 text-sm text-paper-500">Lade Tickets…</div>;
  }
  if (tickets.length === 0) {
    return <div className="px-4 py-8 text-sm text-paper-500">Keine Tickets.</div>;
  }

  return (
    <ul className="flex flex-col">
      {tickets.map((t) => {
        const isSelected = t.id === selectedId;
        const isUnread = !openedIds.has(t.id);
        const channelIcon = CHANNEL_ICON[(t.channel || 'whatsapp').toLowerCase()] || '📨';
        const intent = (t.classified_intent || t.category || 'Allgemein')
          .replace(/_/g, ' ')
          .replace(/^./, (c) => c.toUpperCase());
        const patternCount = t.pattern_count ? parseInt(t.pattern_count) : 0;
        const preview = (t.full_text || '').replace(/\s+/g, ' ').trim().slice(0, 110);

        return (
          <li
            key={t.id}
            onClick={() => onSelect(t.id)}
            className={cx(
              'cursor-pointer border-b border-paper-200 px-4 py-3 transition',
              isSelected ? 'bg-teal-50' : 'hover:bg-paper-50',
            )}
          >
            <div className="flex items-baseline justify-between gap-2 mb-0.5">
              <span className={cx(
                'truncate text-base',
                isUnread ? 'font-semibold text-paper-900' : 'font-medium text-paper-700',
              )}>
                {t.tenant_name}
              </span>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-paper-500" title={t.channel || ''}>{channelIcon}</span>
                <PriorityPill priority={t.priority} />
                <span className="text-xs text-paper-500 tabular-nums whitespace-nowrap">
                  {ago(t.opened_at)}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2 mb-1 text-sm">
              <span className="font-semibold text-paper-900">{intent}</span>
              {t.unit_label && (
                <>
                  <span className="text-paper-400">·</span>
                  <span className="text-paper-700 truncate">{t.unit_label} · Zossener Str. 47</span>
                </>
              )}
              {patternCount >= 3 && (
                <span className="inline-flex items-center rounded-full border border-red-100 bg-red-50 px-1.5 py-0.5 text-[11px] font-semibold text-red-700 shrink-0">
                  🔁 {patternCount}
                </span>
              )}
              <ModeChip mode={t.autonomy_mode} />
            </div>
            <p className="truncate text-sm text-paper-500">{preview}</p>
          </li>
        );
      })}
    </ul>
  );
}
