import React from 'react';
import { ControlRoomEvent } from '../../api/types';
import { Clock, Activity, Bot, Scale, AlertCircle, RefreshCw } from 'lucide-react';

interface OrchestrationEventsTimelineProps {
  events: ControlRoomEvent[];
}

export const OrchestrationEventsTimeline: React.FC<OrchestrationEventsTimelineProps> = ({ events }) => {
  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour12: false });
    } catch {
      return ts;
    }
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'AGENT_START':
      case 'AGENT_COMPLETE':
        return <Bot size={13} />;
      case 'DECISION':
        return <Scale size={13} />;
      case 'ITERATION_START':
      case 'RETRY':
        return <RefreshCw size={13} />;
      case 'ERROR':
      case 'FAILURE':
        return <AlertCircle size={13} />;
      default:
        return <Activity size={13} />;
    }
  };

  if (!events || events.length === 0) {
    return (
      <div className="cr-empty-card">
        <Activity size={20} className="text-muted" />
        <span>No orchestration events recorded yet.</span>
      </div>
    );
  }

  return (
    <div className="cr-events-timeline">
      <div className="cr-timeline-list">
        {events.map((evt, idx) => (
          <div key={idx} className="cr-timeline-item">
            <div className="cr-timeline-time">
              <Clock size={11} />
              <span>{formatTime(evt.timestamp)}</span>
            </div>

            <div className="cr-timeline-marker">
              <div className="marker-dot">{getEventIcon(evt.event_type)}</div>
              {idx < events.length - 1 && <div className="marker-line" />}
            </div>

            <div className="cr-timeline-content">
              <div className="cr-timeline-header">
                <span className="cr-timeline-type">{evt.event_type}</span>
                <span className="cr-timeline-iter">Iter {evt.iteration}</span>
                {evt.agent && <span className="cr-timeline-agent">{evt.agent}</span>}
              </div>

              {evt.decision && (
                <div className="cr-timeline-decision">
                  <strong>Decision:</strong> {evt.decision}
                </div>
              )}

              {evt.reason && <div className="cr-timeline-reason">&ldquo;{evt.reason}&rdquo;</div>}

              {evt.details && Object.keys(evt.details).length > 0 && (
                <div className="cr-timeline-details">
                  {Object.entries(evt.details).map(([k, v]) => (
                    <span key={k} className="detail-tag">
                      {k}: {String(v)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
