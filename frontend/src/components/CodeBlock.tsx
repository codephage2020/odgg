// Syntax-highlighted code block using highlight.js
import { useEffect, useRef } from 'react';
import hljs from 'highlight.js/lib/core';
import sql from 'highlight.js/lib/languages/sql';
import yaml from 'highlight.js/lib/languages/yaml';
import 'highlight.js/styles/github-dark.min.css';

hljs.registerLanguage('sql', sql);
hljs.registerLanguage('yaml', yaml);

interface CodeBlockProps {
  code: string;
  language?: string;
}

/** Detect language from code content. */
function detectLang(code: string): string {
  if (/^(CREATE|ALTER|INSERT|SELECT|DROP|WITH)\b/im.test(code)) return 'sql';
  if (/^(version|models|sources|columns):/m.test(code)) return 'yaml';
  return 'sql';
}

export function CodeBlock({ code, language }: CodeBlockProps) {
  const codeRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (codeRef.current) {
      codeRef.current.removeAttribute('data-highlighted');
      hljs.highlightElement(codeRef.current);
    }
  }, [code, language]);

  const lang = language || detectLang(code);

  return (
    <pre className="brief-code-pre">
      <code ref={codeRef} className={`language-${lang}`}>
        {code}
      </code>
    </pre>
  );
}
