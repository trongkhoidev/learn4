import React from 'react';
import { AlertCircle } from 'lucide-react';

export default function GrammarErrorList({ errors = [], status = 'scored' }) {
  if (!errors || errors.length === 0) {
    return (
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col items-center justify-center h-full">
        {status === 'scored' ? (
          <>
            <div className="w-12 h-12 rounded-full bg-green-50 flex items-center justify-center text-green-500 mb-2">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
            </div>
            <h3 className="font-medium text-gray-800">Không có lỗi được xác nhận</h3>
            <p className="text-gray-500 text-sm">Chỉ là quan sát từ transcript ASR, chưa được giáo viên xác minh bằng audio.</p>
          </>
        ) : (
          <>
            <h3 className="font-medium text-gray-800">Chưa đủ bằng chứng ngữ pháp</h3>
            <p className="text-gray-500 text-sm">Không kết luận “không có lỗi” khi mẫu chưa đủ hoặc cần nghe lại.</p>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
      <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
        <AlertCircle className="w-5 h-5 text-orange-500" />
        Góp ý về ngữ pháp
      </h3>
      <div className="space-y-4">
        {errors.map((error, idx) => (
          <div key={idx} className={`p-4 rounded-xl border ${error.error_or_improvement === 'optional_improvement' ? 'bg-blue-50 border-blue-100' : 'bg-red-50 border-red-100'}`}>
            <div className="flex items-start justify-between">
              <div>
                <span className={`inline-block mb-2 px-2 py-0.5 rounded text-xs font-bold ${error.error_or_improvement === 'optional_improvement' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'}`}>
                  {error.error_or_improvement === 'optional_improvement' ? 'Gợi ý phong cách' : 'Lỗi cần chú ý'}
                </span>
                <p className="text-gray-800 font-medium">
                  <span className="line-through text-red-500 mr-2">{error.error || error.wrong}</span>
                  <span className="text-green-600">{error.correct}</span>
                </p>
                <p className="text-sm text-gray-600 mt-1">{error.explain || error.explanation}</p>
                <p className="text-xs text-gray-500 mt-2">Transcript-grounded; chưa được người nghe xác minh bằng audio.</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
