import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';

const VARIANTS = {
  info: { icon: Info, classes: 'bg-primary/10 border-primary/20 text-primary' },
  warn: { icon: AlertTriangle, classes: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-500' },
  danger: { icon: ShieldAlert, classes: 'bg-red-500/10 border-red-500/20 text-red-500' },
};

export default function Callout({ variant = 'info', children }) {
  const { icon: Icon, classes } = VARIANTS[variant] || VARIANTS.info;
  return (
    <div className={`flex gap-3 border rounded-xl p-4 text-sm ${classes}`}>
      <Icon className="w-5 h-5 shrink-0 mt-0.5" />
      <div className="text-textSecondary [&_strong]:text-text [&_code]:text-current">{children}</div>
    </div>
  );
}
