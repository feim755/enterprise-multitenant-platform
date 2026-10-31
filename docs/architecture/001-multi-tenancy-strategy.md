# ADR 001: Multi-Tenancy Isolation Strategy

## Context
The platform must host multiple independent organizations (tenants) while guaranteeing data privacy, fair resource allocation, and predictable operating costs.

## Decision
We adopt a hybrid multi-tenancy model:
1. **Compute Layer (Kubernetes):** Namespace-per-Tenant
   - Each tenant receives an isolated namespace.
   - ResourceQuotas prevent CPU/memory starvation (Noisy Neighbor problem).
   - NetworkPolicies strictly block inter-tenant pod communication.

2. **Data Layer (PostgreSQL):** Schema-per-Tenant
   - Single PostgreSQL instance/cluster to optimize memory and connection limits.
   - Isolated schema per tenant (`tenant_<id>.*`) ensuring strict logical boundaries.
   - Dynamic schema migration runner triggered upon tenant onboarding.

## Status
Accepted

## Consequences
- Requires strict automated tenant provisioning via Infrastructure as Code (Pulumi).
- Database migration pipelines must iterate over all active tenant schemas.
