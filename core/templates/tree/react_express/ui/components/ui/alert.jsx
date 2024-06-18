import React from 'react';
import { AlertCircle } from 'lucide-react';

export function AlertDestructive({ title, description }) {
  return (
    <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4" role="alert">
      <p className="font-bold"><AlertCircle className="inline-block mr-2 h-5 w-5" />{title}</p>
      <p>{description}</p>
    </div>
  );
}