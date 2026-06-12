import React, { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  className?: string;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, className }) => {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
      <div 
        className={cn(
          "relative bg-white border-4 border-black shadow-[16px_16px_0px_#FF4500] w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]",
          className
        )}
      >
        <div className="bg-black text-white p-4 flex justify-between items-center shrink-0">
          <h2 className="font-mono font-bold tracking-widest text-lg uppercase">{title}</h2>
          <button 
            onClick={onClose}
            className="text-white hover:text-orange-500 transition-colors focus:outline-none"
          >
            <X size={24} />
          </button>
        </div>
        <div className="p-6 overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
};
