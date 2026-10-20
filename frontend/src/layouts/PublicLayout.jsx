import { Outlet } from "react-router-dom";

export default function PublicLayout() {
  return (
    <div className="min-h-screen w-full bg-slate-50 text-slate-800 font-sans">
      <main className="relative h-full w-full">
        <Outlet />
      </main>
    </div>
  );
}
