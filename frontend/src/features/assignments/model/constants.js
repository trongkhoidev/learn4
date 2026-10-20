import { BookOpen, Headphones, Mic, PenTool } from 'lucide-react';

export const SKILLS = {
  reading: {
    id: 'reading',
    label: 'Reading',
    icon: BookOpen,
    color: 'bg-sky-100 text-sky-700 border-sky-200',
    colorClass: 'text-sky-500',
    bgClass: 'bg-sky-50',
    borderClass: 'border-sky-200',
    badgeClass: 'bg-sky-100 text-sky-700',
  },
  listening: {
    id: 'listening',
    label: 'Listening',
    icon: Headphones,
    color: 'bg-violet-100 text-violet-700 border-violet-200',
    colorClass: 'text-violet-500',
    bgClass: 'bg-violet-50',
    borderClass: 'border-violet-200',
    badgeClass: 'bg-violet-100 text-violet-700',
  },
  speaking: {
    id: 'speaking',
    label: 'Speaking',
    icon: Mic,
    color: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    colorClass: 'text-emerald-500',
    bgClass: 'bg-emerald-50',
    borderClass: 'border-emerald-200',
    badgeClass: 'bg-emerald-100 text-emerald-700',
  },
  writing: {
    id: 'writing',
    label: 'Writing',
    icon: PenTool,
    color: 'bg-amber-100 text-amber-700 border-amber-200',
    colorClass: 'text-amber-500',
    bgClass: 'bg-amber-50',
    borderClass: 'border-amber-200',
    badgeClass: 'bg-amber-100 text-amber-700',
  }
};

export function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('vi-VN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export function getDeadlineStatus(deadlineStr) {
  if (!deadlineStr) return null;
  const date = new Date(deadlineStr);
  const now = new Date();
  if (now > date) return { text: "Quá hạn", color: "bg-red-50 text-red-600 border-red-200" };
  
  const diff = date - now;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
  
  if (days > 0) return { text: `Còn ${days} ngày`, color: "bg-blue-50 text-blue-600 border-blue-200" };
  return { text: `Còn ${hours} giờ`, color: "bg-amber-50 text-amber-600 border-amber-200" };
}
