import React from 'react';
import { AlertCircle, CheckCircle } from 'lucide-react';

function Toast({ toast }) {
  if (!toast) return null;

  return (
    <div className={`toast ${toast.type}`}>
      {toast.type === 'error' ? <AlertCircle size={18} /> : <CheckCircle size={18} />}
      <span>{toast.message}</span>
    </div>
  );
}

export default Toast;
