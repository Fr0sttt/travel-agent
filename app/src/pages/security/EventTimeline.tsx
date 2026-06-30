import { ScrollArea } from '@/components/ui/scroll-area';
import EventCard from './EventCard';
import type { SecurityEvent } from './data';
import type { Status } from './data';

interface EventTimelineProps {
  events: SecurityEvent[];
  selectedEvent: SecurityEvent | null;
  onSelectEvent: (event: SecurityEvent) => void;
  onStatusChange: (id: string, newStatus: Status) => void;
}

export default function EventTimeline({
  events,
  selectedEvent,
  onSelectEvent,
  onStatusChange,
}: EventTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
          style={{ background: 'rgba(255,255,255,0.05)' }}
        >
          <span className="text-2xl" style={{ color: 'rgba(255,255,255,0.15)' }}>
            No events
          </span>
        </div>
        <p className="text-sm" style={{ color: 'rgba(255,255,255,0.3)' }}>
          No security events match your filters
        </p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-[640px] pr-2">
      <div className="space-y-2">
        {events.map((event, i) => (
          <EventCard
            key={event.id}
            event={event}
            index={i}
            isSelected={selectedEvent?.id === event.id}
            onSelect={onSelectEvent}
            onStatusChange={onStatusChange}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
