import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // 프로젝트 전반 기술부채가 큰 규칙은 우선 경고/비활성으로 전환
      "@typescript-eslint/no-explicit-any": "warn",
      "react-hooks/set-state-in-effect": "off",
      "react/no-unescaped-entities": "warn",
      "prefer-const": "warn",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Local backup/temporary files:
    "**/*_backup.*",
    "**/*.backup",
    "**/*.bak",
    "**/*.old",
  ]),
]);

export default eslintConfig;
