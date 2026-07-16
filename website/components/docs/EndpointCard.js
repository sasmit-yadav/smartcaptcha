const METHOD_COLORS = {
  POST: 'bg-successSoft text-success',
  GET: 'bg-primarySoft text-primary',
  DELETE: 'bg-dangerSoft text-danger',
};

export default function EndpointCard({ method = 'POST', path, auth, children }) {
  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <span className={`font-bold px-3 py-1 rounded-full text-xs ${METHOD_COLORS[method] || METHOD_COLORS.POST}`}>
          {method}
        </span>
        <code className="text-ink/70 font-mono text-sm">{path}</code>
        {auth && <span className="text-xs text-stone ml-auto">Auth: {auth}</span>}
      </div>
      {children}
    </div>
  );
}
