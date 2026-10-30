/** Small shared status elements: errors, progress, empty states. */
export function ErrorNote({ error }) {
  if (!error) return null;
  return (
    <p className="note note-error" role="alert">
      {error}
    </p>
  );
}

export function Working({ children }) {
  return (
    <p className="working" role="status">
      <span className="scanline" aria-hidden="true" />
      {children}
    </p>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      <p className="muted">{children}</p>
    </div>
  );
}
