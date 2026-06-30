import React from 'react';
import { motion } from 'framer-motion';

export function StreamingCursor() {
  return (
    <motion.span
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{
        repeat: Infinity,
        duration: 0.8,
        ease: "easeInOut",
      }}
      className="inline-block w-2 h-4 ml-1 align-middle bg-primary"
    />
  );
}
