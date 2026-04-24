# TradeNodeX Architecture

TradeNodeX is organized as a self-hosted operational control center with a backend API, web control plane, background workers, exchange adapters, and audit-oriented storage.

## High-level flow

```text
Signal Source
    |
    v
Private Stream / Position Reconcile
    |
    v
Standardized Signal
    |
    v
Routing Rules
    |
    v
Operational Task Queue
    |
    v
Worker Runtime
    |
    v
Exchange Adapter
    |
    v
Audit Logs / Equity Snapshots / Operator UI
```

## Core components

### Backend API

The backend exposes the control surface used by the web UI and operational workflows. It is responsible for configuration, dashboards, account records, routing records, logs, and command endpoints.

### Web control plane

The React control plane provides operator visibility across signals, routing, API registry records, queues, logs, equity snapshots, and manual operational flows.

### Worker runtime

The worker runtime handles background processing, listener workflows, queue processing, and adapter calls. The web UI alone is not sufficient for continuous background operation; the worker process must also be running.

### Exchange adapters

Exchange adapters isolate venue-specific credential requirements, API behavior, symbol conventions, and connectivity paths. Some venues use private WebSocket streams directly; some also rely on REST reconciliation fallback paths.

### Audit logs

Audit logs are a first-class part of the architecture. They make operational behavior reviewable by recording important events, state changes, responses, warnings, and errors.

## Operational boundaries

TradeNodeX is not a custody system. It does not hold user funds. Users operate their own exchange accounts and are responsible for API permissions, server security, network policy, and operational procedures.

## Recommended production posture

- Use trading-only exchange API keys.
- Disable withdrawal permissions.
- Use exchange-side IP allowlists where supported.
- Run from a fixed-IP server.
- Protect environment variables and local configuration.
- Monitor logs and queue health.
- Validate each exchange path with small-size or demo workflows before scaling.

## Extension points

Potential extension areas include:

- New exchange adapters
- Improved deployment templates
- Additional observability exporters
- More granular audit-log filters
- Operator runbooks
- Localization improvements
- Test coverage around connector behavior