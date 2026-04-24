# TradeNodeX AI Copy Trading Control Center

![License](https://img.shields.io/github/license/TradeNodeX/TradeNodeX-AI-Copy-Trading)
![Stars](https://img.shields.io/github/stars/TradeNodeX/TradeNodeX-AI-Copy-Trading?style=social)
![Forks](https://img.shields.io/github/forks/TradeNodeX/TradeNodeX-AI-Copy-Trading?style=social)
![Last Commit](https://img.shields.io/github/last-commit/TradeNodeX/TradeNodeX-AI-Copy-Trading)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-Control%20Plane-61DAFB)

TradeNodeX is a self-hosted, single-tenant copy-trading control center for private operator use. The current repository ships a FastAPI backend, a React control plane, execution workers, audit logs, equity analytics, multi-language UI support, and multi-exchange connectivity.

This edition is designed for:

- self-hosted deployment
- operator-managed API keys
- cloud server operation
- controlled testing, staged rollout, and small-to-medium scale validation

It is not a managed SaaS product and it does not custody funds.

If this project is useful to you, a GitHub star helps more builders discover it.

## Core capabilities

- `Signals`: register and monitor master accounts that produce standardized trading signals
- `Copy Routing`: bind signal sources to follower accounts and configure exact or scaled copy mode
- `API Registry`: manage master and follower credentials with readiness breakdown
- `Studio`: generate and execute manual commands, inspect live execution queue, and open execution audit timelines
- `Audit Logs`: inspect signal, execution, reconcile, manual, warning, and error logs
- `Equity List`: review recent position snapshots, exposure, unrealized pnl, leverage, margin mode, freshness, and display-currency analytics

## Exchange support matrix

The project currently supports seven exchange connectors, but not all exchanges are at the same automation level. The matrix below is the authoritative support statement for the open-source free edition.

| Exchange | Credential validation | Manual execute / cancel / fetch position | Master auto-listener | Listener mode | Product scope |
| --- | --- | --- | --- | --- | --- |
| Binance Futures | Yes | Yes | Yes | Private WebSocket | USD-M perpetual / futures path |
| Bybit Linear | Yes | Yes | Yes | Private WebSocket | USDT linear perpetual path |
| OKX Swap | Yes | Yes | Yes | Private WebSocket with REST fallback | Swap / derivatives path |
| Kraken Futures | Yes | Yes | Yes | Private WebSocket with REST fallback | Futures / derivatives path |
| BitMEX | Yes | Yes | Yes | Private WebSocket with REST fallback | Perpetual / derivatives path |
| Gate.io Futures | Yes | Yes | Yes | Private WebSocket with REST fallback | USDT futures path |
| Coinbase Advanced | Yes | Yes | Yes | Private WebSocket with REST fallback | Advanced / derivatives-compatible path |

### Important support notes

- `Private WebSocket` means the master account can be monitored from exchange push events directly.
- `Private WebSocket with REST fallback` means the system now attempts exchange private-stream monitoring first and falls back to private position reconciliation if the exchange environment or subscription flow is unavailable.
- The open-source edition prioritizes the derivatives path. Spot auto-copy is not the default supported workflow.
- Some exchanges require additional credential fields:
  - `OKX`: API passphrase is required
  - `Coinbase Advanced`: key id + ES256 private key format must be correct

## Quick start

### 1. Install

```bash
pip install -e .[dev]
```

### 2. Start the API

```bash
uvicorn copytrading_app.main:app --reload
```

### 3. Start the worker and master listeners

```bash
python -m copytrading_app.workers.runtime
```

### 4. Open the UI

- Main UI: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## Runtime requirements

- Python 3.12+
- Node.js is only required when rebuilding the React frontend locally
- SQLite is used by default for local development
- PostgreSQL + Redis + SQS are recommended for cloud deployment

## Core API surface

- `GET /v1/dashboard`
- `GET /v1/positions`
- `GET /v1/logs/query`
- `POST /v1/signal-sources`
- `POST /v1/followers`
- `POST /v1/copy-trades`
- `POST /v1/commands/generate`
- `POST /v1/commands/execute`
- `GET /v1/executions/{task_id}/audit`
- `WS /v1/ws/stream`

## Recommended security model

- enable trading permissions only
- do not enable withdrawals
- use IP allowlists where the exchange supports them
- store API secrets and passphrases encrypted at rest
- prefer running this project on a fixed-IP cloud server for 24/7 operation

## Known limits in the current open-source edition

- Binance and Bybit currently remain the most mature private-stream paths.
- OKX, Kraken, BitMEX, Gate.io, and Coinbase Advanced now include private-stream connection logic plus REST reconciliation fallback, but they should still be treated as newer exchange paths until validated in your own environment.
- The repository includes automated tests and control-plane coverage, but it does not yet claim validated 1000-account production readiness.
- Exchange testnet capabilities are not uniform. Some exchanges may require demo or small-size mainnet verification for complete end-to-end validation.

## Development and test

Backend test suite:

```bash
python -m pytest -q
```

Frontend typecheck and build from the `frontend/` workspace:

```bash
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vite/bin/vite.js build
```

Real private-stream validation for configured master accounts:

```bash
python scripts/validate_private_streams.py --exchange OKX --exchange KRAKEN --exchange BITMEX --exchange GATEIO --exchange COINBASE
```

The validator only checks exchanges that already have configured `Signal Source` records with stored credentials in the local database.

Release safety gate:

```bash
python scripts/release_gate.py
```

The release gate scans project-owned source and documentation files for blocked secret patterns and disallowed product-reference residue. Dependency folders and generated frontend artifacts are intentionally excluded.

## Open-source free edition packaging

The source release should include:

- `src/`
- `frontend/src/`
- `tests/`
- `deployments/`
- `scripts/`
- `sql/`
- `README.md`
- `USER_GUIDE_CN.md`
- `NOTICE.md`
- `LICENSE`
- `.env.example`

## Documentation

- Chinese user guide: [USER_GUIDE_CN.md](./USER_GUIDE_CN.md)
- Architecture overview: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- Roadmap: [ROADMAP.md](./ROADMAP.md)
- Contributing guide: [CONTRIBUTING.md](./CONTRIBUTING.md)
- Security policy: [SECURITY.md](./SECURITY.md)
- Community guide: [docs/COMMUNITY.md](./docs/COMMUNITY.md)
- Repository marketing checklist: [docs/REPOSITORY_MARKETING.md](./docs/REPOSITORY_MARKETING.md)
- Legal / use notice: [NOTICE.md](./NOTICE.md)
- License: [LICENSE](./LICENSE)

## Legal and trademark notice

TradeNodeX is an original software project and does not include third-party product logos or copied proprietary frontend assets in this repository.

Exchange names such as `Binance`, `Bybit`, `OKX`, `Coinbase`, `Kraken`, `BitMEX`, and `Gate.io` are used only to describe compatibility targets. Their trademarks remain the property of their respective owners.

This software is distributed under the MIT License. It is provided as self-hosted infrastructure software, not financial advice, not custody, and not a guarantee of execution performance.
