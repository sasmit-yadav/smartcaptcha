import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';

const VARIANTS = {
  info: { icon: Info, classes: 'bg-primarySoft border-primary/25 text-primary' },
  warn: { icon: AlertTriangle, classes: 'bg-warningSoft border-warning/25 text-warning' },
  danger: { icon: ShieldAlert, classes: 'bg-dangerSoft border-danger/25 text-danger' },
};

export default function Callout({ variant = 'info', children }) {
  const { icon: Icon, classes } = VARIANTS[variant] || VARIANTS.info;
  return (
    <div className={`flex gap-3 border rounded-xl p-4 text-sm ${classes}`}>
      <Icon className="w-5 h-5 shrink-0 mt-0.5" />
      <div className="text-ink/80 [&_strong]:text-ink [&_code]:text-current">{children}</div>
    </div>
  );
}
