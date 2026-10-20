module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: ['eslint:recommended', 'plugin:@typescript-eslint/recommended', 'plugin:react-hooks/recommended'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-hooks'],
  ignorePatterns: ['dist', 'node_modules'],
  rules: { 'react-hooks/exhaustive-deps': 'error' },
};
