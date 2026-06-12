import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import betterTailwindcss from "eslint-plugin-better-tailwindcss";
import eslintConfigPrettier from "eslint-config-prettier";
import globals from "globals";

export default tseslint.config(
  { ignores: ["dist/", "node_modules/"] },

  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    ...betterTailwindcss.configs["recommended"],
    rules: {
      ...betterTailwindcss.configs["recommended"].rules,
      // 长 class 字符串的换行风格过于严格，对已有代码噪声太大
      "better-tailwindcss/enforce-consistent-line-wrapping": "off",
    },
  },

  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // 初始化 query 数据到本地 state 是常见模式
      "react-hooks/set-state-in-effect": "off",
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },

  eslintConfigPrettier,
);
