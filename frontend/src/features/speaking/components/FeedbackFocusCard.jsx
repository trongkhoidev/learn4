import React from 'react';
import { CheckCircle2, AlertTriangle, Lightbulb } from 'lucide-react';

export default function FeedbackFocusCard({ comment }) {
  if (!comment) return null;

  let pros = '';
  let cons = '';
  let action = '';

  if (typeof comment === 'object') {
    pros = comment.pros;
    cons = comment.cons;
    action = comment.action;
  } else {
    // Extract pros, cons, action based on keywords
    const extractPart = (text, startKeywords, endKeywords = []) => {
      let startIndex = -1;
      for (const kw of startKeywords) {
        const idx = text.indexOf(kw);
        if (idx !== -1) {
          startIndex = idx;
          break;
        }
      }
      
      if (startIndex === -1) return null;
      
      // Find the end of this part
      let endIndex = text.length;
      for (const kw of endKeywords) {
        const idx = text.indexOf(kw, startIndex + 5); 
        if (idx !== -1 && idx < endIndex) {
          endIndex = idx;
        }
      }
      
      // Also stop at the | character if it's there
      const pipeIndex = text.indexOf('|', startIndex + 5);
      if (pipeIndex !== -1 && pipeIndex < endIndex) {
        endIndex = pipeIndex;
      }
      
      let result = text.substring(startIndex, endIndex).trim();
      // Remove the prefix (e.g., "🟢 Ưu điểm (Pros):" or "Điểm mạnh:")
      result = result.replace(/^[^:]+:\s*/, '').trim();
      return result;
    };

    pros = extractPart(comment, ['🟢 Ưu điểm', 'Ưu điểm', 'Điểm mạnh'], ['🟠 Hạn chế', 'Hạn chế', 'Điểm yếu', '💡 Cải thiện', 'Cải thiện', 'Gợi ý']);
    cons = extractPart(comment, ['🟠 Hạn chế', 'Hạn chế', 'Điểm yếu'], ['💡 Cải thiện', 'Cải thiện', 'Gợi ý', 'Lý do']);
    action = extractPart(comment, ['💡 Cải thiện', 'Cải thiện', 'Gợi ý'], []);
  }

  // If we couldn't parse the structure, fallback to displaying the text directly
  if (!pros && !cons && !action) {
    return (
      <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700 whitespace-pre-line">
        {typeof comment === 'string' ? comment : JSON.stringify(comment)}
      </div>
    );
  }

  return (
    <div className="space-y-3 mt-3 w-full">
      {/* Thẻ Xanh lục - Ưu điểm */}
      <div className="bg-green-50/80 border border-green-200 rounded-lg p-3 flex items-start gap-3 transition-colors hover:bg-green-50">
        <div className="bg-green-100 p-1.5 rounded-full mt-0.5 shrink-0">
          <CheckCircle2 className="w-4 h-4 text-green-600" />
        </div>
        <div>
          <h5 className="text-xs font-bold text-green-800 uppercase tracking-wide mb-1">Ưu điểm (Pros)</h5>
          <p className="text-sm text-green-700 leading-snug">{pros || 'Đang cập nhật...'}</p>
        </div>
      </div>

      {/* Thẻ Màu hổ phách - Hạn chế */}
      <div className="bg-amber-50/80 border border-amber-200 rounded-lg p-3 flex items-start gap-3 transition-colors hover:bg-amber-50">
        <div className="bg-amber-100 p-1.5 rounded-full mt-0.5 shrink-0">
          <AlertTriangle className="w-4 h-4 text-amber-600" />
        </div>
        <div>
          <h5 className="text-xs font-bold text-amber-800 uppercase tracking-wide mb-1">Hạn chế cốt lõi (Cons)</h5>
          <p className="text-sm text-amber-700 leading-snug">{cons || 'Đang cập nhật...'}</p>
        </div>
      </div>

      {/* Thẻ Xanh dương - Trọng tâm nâng Band */}
      <div className="bg-blue-50/80 border border-blue-200 rounded-lg p-3 flex items-start gap-3 transition-colors hover:bg-blue-50">
        <div className="bg-blue-100 p-1.5 rounded-full mt-0.5 shrink-0">
          <Lightbulb className="w-4 h-4 text-blue-600" />
        </div>
        <div>
          <h5 className="text-xs font-bold text-blue-800 uppercase tracking-wide mb-1">Trọng tâm nâng Band (Action Fix)</h5>
          <p className="text-sm text-blue-700 leading-snug">{action || 'Đang cập nhật...'}</p>
        </div>
      </div>
    </div>
  );
}
