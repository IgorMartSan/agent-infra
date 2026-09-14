## AGENTS.md

### Setup
- **Env**: `npm install -g @opencode/cli` (use `--force` if version conflicts)
- **Dev**: `npm run dev` (logs to `/tmp/agent.log`)
- **Fmt**: `npm run format` (ignores `node_modules`)
- **Test**: `npm run test -- --testPathPattern "integration"` (requires Docker)

### Commands
- **Lint**: `npx eslint . --ext .ts,.tsx` (fixes: `--fix`)
- **Typecheck**: `npx tsc --noEmit` (fails fast: `--noEmit`)
- **Build**: `npm run build` (outputs to `dist/agent`)
- **Deploy**: `npm run deploy` (requires AWS credentials in `~/.aws/credentials`)

### Architecture
- **Monorepo**: `packages/agent` (core) | `packages/redis` (backend) | `packages/web` (frontend)
- **Entry Points**: `index.ts` (main) | `api.js` (serverless) | `ui/index.html` (SPA)
- **Codegen**: `tools/generate.ts` (runs on `npm install`)

### Gotchas
- **Redis**: Always use `localhost:6379` in dev (prod uses cloud Redis)
- **Snapshots**: Jest uses `__snapshots__` directory (delete to reset)
- **CI**: `CI=true npm test` (skips Docker for faster runs)
- **Lockfile**: `package-lock.json` is immutable (manual edits may break builds)

### References
- [README.md](README.md) for full setup
- [.cursor/rules/](.cursor/rules/) for code formatting
- [.github/workflows](.github/workflows) for CI config

Last updated: `date +"\%Y-\%m-\%d"`