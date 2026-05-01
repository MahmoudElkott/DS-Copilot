import { Outlet } from 'react-router-dom';

/**
 * NotebookPane — The route outlet for the right-side workspace.
 * All 10 module routes render their content inside this container.
 */
export default function NotebookPane() {
  return (
    <div className="h-full overflow-y-auto no-scrollbar" style={{ background: 'var(--bg-primary)' }}>
      <Outlet />
    </div>
  );
}
