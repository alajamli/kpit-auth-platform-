/**
 * Execution-log helpers.
 * The backend prefixes some messages with emoji (✅ ❌ ⚠️ …). We keep the messages
 * untouched and only change how they are *displayed*: the emoji is replaced by an icon.
 */
export type LogKind = 'pass' | 'fail' | 'warn' | 'info';

const LEADING_SYMBOLS = /^[\p{Extended_Pictographic}\u200d\ufe0f\u2714\u2716\s]+/u;

export function logKind(message: string): LogKind {
  const m = message || '';
  if (/^\s*[\u2705\u2714]/u.test(m) || /\bPASS\b/.test(m)) return 'pass';
  if (/^\s*[\u274c\u2716]/u.test(m) || /\bFAIL\b/.test(m)) return 'fail';
  if (/^\s*\u26a0/u.test(m)) return 'warn';
  return 'info';
}

export function logText(message: string): string {
  return (message || '').replace(LEADING_SYMBOLS, '');
}

export function logIcon(message: string): string {
  switch (logKind(message)) {
    case 'pass': return 'check_circle';
    case 'fail': return 'cancel';
    case 'warn': return 'warning';
    default: return 'chevron_right';
  }
}
