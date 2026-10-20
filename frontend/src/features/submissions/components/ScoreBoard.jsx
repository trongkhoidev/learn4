export default function ScoreBoard({ submissions, onSelect }) {
  if (!submissions?.length) return <p className="text-sm text-slate-500">Chưa có bài nộp.</p>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs text-slate-500">
          <th className="py-1">Học viên</th>
          <th>Điểm</th>
          <th>Trạng thái</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {submissions.map((s) => (
          <tr key={s.id} className="border-t">
            <td className="py-2">{s.student_name}</td>
            <td>{s.score ?? "-"}</td>
            <td>{s.status === "graded" ? "✅" : "⏳"}</td>
            <td>
              <button className="text-blue-600" onClick={() => onSelect && onSelect(s)}>
                Xem
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
