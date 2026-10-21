import js from "@eslint/js"
import globals from "globals"
import reactHooks from "eslint-plugin-react-hooks"
import reactRefresh from "eslint-plugin-react-refresh"

const featureNames = [
  "beneficiary_selection",
  "evidence_trust",
  "livelihood_planning",
  "market_risk",
]

const crossFeatureRules = featureNames.map((featureName) => ({
  files: [`src/features/${featureName}/**/*.{js,jsx}`],
  rules: {
    "no-restricted-imports": [
      "error",
      {
        patterns: [
          "@/features/*",
          ...featureNames
            .filter((name) => name !== featureName)
            .flatMap((name) => [
              `../${name}/*`,
              `../../${name}/*`,
              `../../../${name}/*`,
            ]),
        ],
      },
    ],
  },
}))

export default [
  { ignores: ["dist", "node_modules"] },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      globals: globals.browser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
        sourceType: "module",
      },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },
  {
    files: ["src/components/ui/**/*.{js,jsx}"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
  ...crossFeatureRules,
]
