import React, { useState, useEffect, useRef } from 'react';
import {
  Terminal,
  Copy,
  Check,
  Maximize2,
  Minimize2,
  ArrowDownCircle,
  FileText,
} from 'lucide-react';
import { ControlRoomLogs } from '../../api/types';

interface ControlRoomLogsViewerProps {
  logs: ControlRoomLogs;
  isRunning: boolean;
}

export const ControlRoomLogsViewer: React.FC<ControlRoomLogsViewerProps> = ({ logs, isRunning }) => {
  const [activeStream, setActiveStream] = useState<'ALL' | 'STDOUT' | 'STDERR'>('ALL');
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when logs change during active run
  useEffect(() => {
    if (autoScroll && isRunning) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll, isRunning]);

  const getLogContent = () => {
    if (activeStream === 'STDOUT') return logs.stdout;
    if (activeStream === 'STDERR') return logs.stderr;
    // Combined
    if (!logs.stdout && !logs.stderr) return '';
    if (!logs.stdout) return logs.stderr;
    if (!logs.stderr) return logs.stdout;
    return `${logs.stdout}\n--- [STDERR] ---\n${logs.stderr}`;
  };

  const currentText = getLogContent();

  const handleCopy = () => {
    if (currentText) {
      navigator.clipboard.writeText(currentText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className={`cr-logs-viewer-card ${isExpanded ? 'is-maximized' : ''}`}>
      <div className="cr-logs-header">
        <div className="cr-logs-header-left">
          <Terminal size={15} />
          <span className="cr-logs-title">Execution & Process Output</span>
          <span className="cr-logs-line-count">
            <FileText size={11} /> {logs.total_lines} lines
          </span>
        </div>

        <div className="cr-logs-header-right">
          {/* Stream toggles */}
          <div className="cr-logs-stream-pills">
            {(['ALL', 'STDOUT', 'STDERR'] as const).map((stream) => (
              <button
                key={stream}
                className={`stream-pill ${activeStream === stream ? 'active' : ''}`}
                onClick={() => setActiveStream(stream)}
              >
                {stream}
              </button>
            ))}
          </div>

          {/* Auto-scroll button */}
          <button
            className={`btn btn-secondary btn-xs ${autoScroll ? 'btn-active-toggle' : ''}`}
            onClick={() => setAutoScroll((prev) => !prev)}
            title="Toggle auto-scroll on new output"
          >
            <ArrowDownCircle size={12} />
            <span>Scroll: {autoScroll ? 'ON' : 'OFF'}</span>
          </button>

          {/* Copy button */}
          <button
            className="btn btn-secondary btn-xs"
            onClick={handleCopy}
            disabled={!currentText}
            title="Copy logs to clipboard"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {/* Maximize toggle */}
          <button
            className="btn btn-secondary btn-xs"
            onClick={() => setIsExpanded((prev) => !prev)}
            title={isExpanded ? 'Restore size' : 'Expand log viewer'}
          >
            {isExpanded ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          </button>
        </div>
      </div>

      <div className="cr-logs-terminal-viewport">
        {currentText ? (
          <pre className="cr-terminal-pre">
            <code>{currentText}</code>
            <div ref={logsEndRef} />
          </pre>
        ) : (
          <div className="cr-terminal-empty">
            <Terminal size={24} className="text-muted" />
            <span>No execution output recorded yet.</span>
          </div>
        )}
      </div>
    </div>
  );
};
