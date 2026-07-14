const METHOD_COLORS = {
  POST: 'bg-green-500/10 text-green-500',
  GET: 'bg-blue-500/10 text-blue-400',
  DELETE: 'bg-red-500/10 text-red-500',
};

export default function EndpointCard({ method = 'POST', path, auth, children }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-6 space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <span className={`font-bold px-3 py-1 rounded-lg text-xs ${METHOD_COLORS[method] || METHOD_COLORS.POST}`}>
          {method}
        </span>
        <code className="text-textSecondary font-mono text-sm">{path}</code>
        {auth && <span className="text-xs text-textSecondary ml-auto">Auth: {auth}</span>}
      </div>
      {children}
    </div>
  );
}
