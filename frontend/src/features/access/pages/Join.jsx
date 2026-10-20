import * as classApi from "../../classes/api.js";
import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Card } from "../../../shared/ui/Card";
import { Button } from "../../../shared/ui/Button";
import { Input } from "../../../shared/ui/Input";
import { useToast } from "../../../shared/ui/Toast";
import { GraduationCap, ArrowRight } from "lucide-react";
import { Spinner } from "../../../shared/ui/Spinner";

export default function Join() {
  const [params] = useSearchParams();
  const initialCode = useRef(params.get("code") || "");
  const [code, setCode] = useState(initialCode.current);
  const [name, setName] = useState("");
  const [cls, setCls] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  const loadClass = useCallback(async value => {
    if (!value.trim()) return;
    setLoading(true);
    try {
      const foundCls = await classApi.join(value.trim());
      setCls(foundCls);
    } catch (e) {
      toast.error(e.message);
      setCls(null);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (initialCode.current.length >= 6) loadClass(initialCode.current);
  }, [loadClass]);

  function checkCode() {
    return loadClass(code);
  }

  async function join() {
    if (!name.trim()) {
      toast.error("Vui lòng nhập tên của bạn");
      return;
    }
    localStorage.setItem(`student_name_${cls.id}`, name.trim());
    toast.success(`Đã tham gia lớp ${cls.name}!`);
    navigate(`/student/${cls.id}`);
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] p-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card className="w-full max-w-md p-8 shadow-xl border-slate-100 relative overflow-hidden">
        {/* Background accent */}
        <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-blue-500 to-emerald-400" />
        
        <div className="mb-8 text-center pt-2">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 shadow-inner">
            <GraduationCap size={32} />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">Tham gia lớp học</h1>
          <p className="mt-2 text-sm text-slate-500">
            {cls ? "Xác nhận tên để vào lớp" : "Nhập mã lớp do giáo viên cung cấp"}
          </p>
        </div>

        <div className="space-y-5">
          {!cls ? (
            <>
              <Input
                label="Mã lớp học"
                className="uppercase tracking-wider font-mono text-center text-lg"
                placeholder="VD: ABC123"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && checkCode()}
                maxLength={6}
              />
              <Button 
                className="w-full text-base h-12" 
                onClick={checkCode}
                disabled={loading || code.length < 6}
              >
                {loading ? <Spinner size="sm" className="text-white" /> : "Kiểm tra mã lớp"}
              </Button>
            </>
          ) : (
            <div className="space-y-6 animate-in slide-in-from-right-4">
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-center">
                <p className="text-sm font-medium text-slate-500 mb-1">Bạn đang vào lớp:</p>
                <p className="text-lg font-bold text-slate-800">{cls.name}</p>
                {cls.teacher_note && <p className="text-sm text-slate-500 mt-2">{cls.teacher_note}</p>}
                <button 
                  className="mt-3 text-sm text-blue-600 hover:underline"
                  onClick={() => setCls(null)}
                >
                  Đổi mã lớp khác
                </button>
              </div>

              <Input
                label="Tên của bạn"
                placeholder="Nhập họ và tên..."
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && join()}
                autoFocus
              />

              <Button 
                className="w-full text-base h-12 gap-2" 
                onClick={join}
              >
                Vào lớp <ArrowRight size={18} />
              </Button>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
