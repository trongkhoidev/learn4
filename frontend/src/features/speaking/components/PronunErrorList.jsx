import React from 'react';
import { Ear } from 'lucide-react';

export default function PronunErrorList({ problems = [] }) {
  if (!problems || problems.length === 0) {
    return null;
  }

  const displayProblems = problems;
  
  if (displayProblems.length === 0) {
    return null;
  }

  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
        <Ear className="w-5 h-5 text-indigo-500" />
        Lỗi phát âm cần chú ý ({displayProblems.length})
      </h3>
      <div className="space-y-4">
        {displayProblems.map((error, idx) => (
          <div key={idx} className="p-4 rounded-xl bg-indigo-50 border border-indigo-100">
            <div className="flex flex-col">
              <p className="text-gray-800 font-medium">
                <span className="text-gray-500 text-sm">Bạn định nói:</span> <span className="text-indigo-700 font-bold">{error.intended}</span>
                {error.type === 'asr_uncertain' && (
                  <span className="ml-2 inline-block px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs font-bold uppercase">Cần nghe lại</span>
                )}
              </p>
              <p className="text-gray-800 font-medium mt-1">
                <span className="text-gray-500 text-sm">Hệ thống nghe thành:</span> <span className="text-red-500 line-through">{error.heard}</span>
              </p>
              <div className="mt-2 text-sm text-gray-600">
                <span className="inline-block px-2 py-1 bg-white rounded border border-indigo-100 text-indigo-600 mr-2">
                  Độ giống âm: {error.phonetic_sim || 'N/A'}
                </span>
                <span className="inline-block px-2 py-1 bg-white rounded border border-indigo-100 text-indigo-600">
                  Hợp ngữ cảnh: {error.semantic_fit || 'N/A'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
