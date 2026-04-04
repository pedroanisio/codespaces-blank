---
title: "API Design: REST, GraphQL, SDKs, and Public Interfaces"
date: 2026-04-04
type: research
disclaimer: >
  **DISCLAIMER**: No information within this document should be taken for
  granted. Any statement or premise not backed by a real logical definition
  or verifiable reference may be invalid, erroneous, or a hallucination.
  The reader is responsible for independently verifying all claims. Where
  references are provided, they point to publicly available sources that
  existed at the time of writing and may have since changed. This document
  represents a synthesis of publicly available information and the author's
  analytical framing — neither of which constitutes authoritative guidance.
version: 1.2
status: draft
last_reviewed: 2026-04-04
change_note: Expanded guidance for AI-heavy, AI-agent, and agentic API consumers with verification-first framing; fixed audit issues and added event-driven coverage.
---

# API Design: REST, GraphQL, SDKs, and Public Interfaces

## 1. Foundational Concepts

### 1.1 What "API Design" Actually Means

API design is the process of defining the contract through which software systems communicate. The contract includes the structure of requests and responses, the semantics of operations, error behavior, authentication, and the evolution strategy over time. The quality of this contract determines whether consumers can integrate reliably, whether the system can evolve without breaking dependents, and whether the interface can scale to serve heterogeneous clients.

There is a recurring confusion in the industry between *protocol*, *architectural style*, and *API specification*. REST is an architectural style. HTTP is a protocol. OpenAPI is a specification format. GraphQL is a query language and runtime. These are not interchangeable categories, and conflating them leads to poor design decisions.

### 1.2 The Design-First vs. Code-First Dichotomy
Two approaches exist:

**Design-first (contract-first):** The API contract is authored before implementation. Stakeholders can review it, mock servers can be generated, and multiple teams can work against a shared schema before the backend is complete. This remains the safer default for public APIs because it makes interface drift visible early.

**Code-first:** Implementation is written first, and the API description is derived from annotations, code generation, or introspection. This is faster for prototypes, but it often leaks storage shape and framework defaults into the external contract.

For AI-heavy systems, agentic AI workflows, and AI-agent consumers, neither framing is sufficient on its own. A third concern matters: **verification-first design**. If an API will be consumed by LLM-driven agents, tool-using assistants, or multi-step automated pipelines, the contract must be shaped so downstream systems can mechanically validate requests, responses, errors, and side effects. That means explicit schemas, stable identifiers, machine-readable failure classes, replay-safe mutations, and observable commit boundaries.

In that sense, design-first is useful not merely because humans can review the contract earlier, but because machine consumers can be constrained earlier. The more an interface depends on prose interpretation, hidden side effects, or inconsistent response shapes, the less safe it is to pipe into an AI-heavy system.

**Ref:** Microsoft Azure Architecture Center, "Web API Design Best Practices"; GraphQL Foundation, "GraphQL Best Practices"; Postman, *State of the API Report* (2025, as discussed in vendor summaries).

### 1.3 API Design Under PALS's Law

PALS's Law introduces a stronger architectural premise for AI-mediated API use:
LLM output must be treated as untrusted by default. In the original formulation,
the core claim is that model error is not an exceptional bug but a statistical
property of the model class, which means any system that consumes LLM output
without a verification boundary contains an architectural defect.

Applied to APIs, the consequence is straightforward: if an API is likely to be
used by tool-calling assistants, agent pipelines, or other LLM-mediated systems,
the interface cannot assume a careful human operator is always interpreting
ambiguous responses correctly. The contract must instead constrain and expose
enough structure that a fallible model can be checked, bounded, and audited.

The most important imported PALS definitions, adapted to API and tool contexts,
are:

- **Untrusted output:** any model-produced request, parameter selection, tool
  call, or interpretation of API response must be assumed potentially wrong
  until verified.
- **Verification boundary:** the explicit layer at which the surrounding system
  checks whether a proposed API interaction is valid, safe, and actually
  committed. For APIs, this includes schema validation, auth checks,
  idempotency, retry classification, and post-call state inspection.
- **Architectural omission:** if a workflow lets an LLM trigger or interpret API
  actions without a declared verification step, the defect is in the system
  design, not merely in the model output.
- **Error taxonomy:** failures should be partitioned into machine-meaningful
  classes so that downstream automation does not have to guess whether a call
  should be retried, revised, abandoned, or escalated.

Under this framing, API quality for AI-heavy systems is not mainly about style
preference between REST, GraphQL, or gRPC. It is about whether the chosen
interface makes verification possible at the point where model error would
otherwise become side effect.

**Ref:** [core/PALS_LAW-v1.5.4.md](/home/admin/codebases/codespaces-blank/core/PALS_LAW-v1.5.4.md); Zenodo record: https://zenodo.org/records/19401530
## 2. REST

### 2.1 Origin and Actual Definition

REST (Representational State Transfer) was defined by Roy Fielding in his 2000 doctoral dissertation at UC Irvine, titled *"Architectural Styles and the Design of Network-based Software Architectures."* Fielding was a co-author of HTTP/1.0 (RFC 1945) and lead author of the HTTP/1.1 specifications (RFC 2068, RFC 2616). REST was not designed as a recipe for building web APIs — it was a post-hoc distillation of the architectural constraints that guided the design of HTTP itself.

Fielding's dissertation derives REST incrementally from the Null style by adding constraints. The derivation chain is:

1. **Client-Server** — Separation of concerns between UI and data storage.
2. **Stateless** — Each request contains all information needed to process it; the server stores no client session state between requests.
3. **Cache** — Responses must implicitly or explicitly label themselves as cacheable or non-cacheable.
4. **Uniform Interface** — The central differentiator. Decomposes into four sub-constraints:
   - Resource identification in requests (URIs).
   - Resource manipulation through representations.
   - Self-descriptive messages.
   - Hypermedia as the engine of application state (HATEOAS).
5. **Layered System** — Clients cannot tell whether they connect directly to the origin server or through intermediaries.
6. **Code-on-Demand (optional)** — Servers can extend client functionality by transferring executable code.

A critical and widely-ignored point: Fielding stated in a 2008 blog post that for an API to legitimately call itself RESTful, it must be hypertext-driven. Most APIs marketed as "REST" satisfy only constraints 1–3 and part of constraint 4 (URIs + HTTP verbs), which places them at Level 2 of the Richardson Maturity Model — not REST proper.

**Ref:** Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures.* Doctoral dissertation, University of California, Irvine. Available at: https://roy.gbiv.com/pubs/dissertation/top.htm; Two-Bit History, "Roy Fielding's Misappropriated REST Dissertation" (2020).

### 2.2 The Richardson Maturity Model

Leonard Richardson proposed a maturity model in 2008 (popularized by Martin Fowler) that classifies APIs on a 0-to-3 scale:

- **Level 0 — The Swamp of POX:** A single URI, a single HTTP method (usually POST), operation semantics encoded in the request body. SOAP and XML-RPC operate at this level.
- **Level 1 — Resources:** Multiple URIs, each addressing a distinct resource, but still typically using a single HTTP method.
- **Level 2 — HTTP Verbs:** Proper use of GET, POST, PUT, PATCH, DELETE mapped to CRUD semantics on resources. Correct use of HTTP status codes. This is where the vast majority of production "REST APIs" operate.
- **Level 3 — Hypermedia Controls (HATEOAS):** Responses include links that tell the client what actions are available and how to perform them, making the API self-describing and navigable without out-of-band documentation.

Fielding has stated that Level 3 is a *precondition* of REST, not an optional enhancement. In practice, Level 2 dominates because HATEOAS adds implementation complexity that many teams consider disproportionate to its benefits for tightly-coupled client-server systems where the same team controls both sides.

**Ref:** Fowler, M. (2010). "Richardson Maturity Model." https://martinfowler.com/articles/richardsonMaturityModel.html; Microsoft Azure Architecture Center, "Web API Design Best Practices."

### 2.3 REST Design Principles That Matter in Practice

The following are empirically well-supported principles for REST API design, separated from Fielding's architectural theory:

**Resource naming:** Use plural nouns for collections (`/users`, `/orders`). Avoid verbs in URIs — the HTTP method carries the verb. Limit nesting to 2–3 levels to avoid excessively long paths.

**HTTP method semantics:**

| Method  | Semantics        | Idempotent | Safe |
|---------|------------------|------------|------|
| GET     | Read             | Yes        | Yes  |
| POST    | Create           | No         | No   |
| PUT     | Full replace     | Yes        | No   |
| PATCH   | Partial update   | No*        | No   |
| DELETE  | Remove           | Yes        | No   |

(*PATCH can be made idempotent with careful design, but the spec does not guarantee it.)

**Status codes:** Use the most specific applicable code. Common mappings: 201 for resource creation, 204 for successful deletion with no body, 400 for malformed requests, 401 for missing/invalid authentication, 403 for insufficient authorization, 404 for nonexistent resources, 409 for conflicts, 422 for semantically invalid input, 429 for rate limiting.

**Pagination:** Offset-based (`?page=3&limit=20`) is simple but degrades on large datasets with concurrent writes. Cursor-based pagination (keyset pagination) is more robust for datasets that change during traversal.

**Filtering and sorting:** Use query parameters (`?status=active&sort=created_at`). Do not encode filtering logic into the path.

**Ref:** Datanizant, "8 Essential API Design Best Practices" (2025); ARDURA Consulting, "API Design Best Practices: Implementation Checklist" (2026).

### 2.4 Idempotency
Idempotency — the property that performing an operation multiple times produces the same result as performing it once — is essential for reliable distributed systems. Network failures, timeouts, duplicate submissions, and retries are normal operating conditions.

For APIs used by humans, idempotency is already important. For APIs used by agentic systems, it becomes a hard architectural requirement on any mutation that may be retried, replayed, or parallelized. LLM-driven clients can repeat calls because of uncertainty, tool retry logic, planner branching, or partial failure recovery. An API that treats duplicate writes as an edge case is unsafe for AI-heavy orchestration.

Stripe popularized the client-generated idempotency key pattern: the client generates a UUID and sends it as a header (`Idempotency-Key`). The server records the key and the result of the first execution. If the same key arrives again, the server returns the stored result instead of re-executing. Stripe stores keys for at least 24 hours and validates that replay requests carry the same parameters.

GET and DELETE are idempotent by HTTP semantics (RFC 9110 Section 9.2.2). POST is inherently non-idempotent and is therefore the primary target for idempotency keys. PUT is idempotent by design when treated as full replacement. DELETE idempotency concerns server state, not necessarily identical response codes: the first deletion may return `200 OK` and a replay may return `404 Not Found`, yet the resource is absent in both cases.

For AI-heavy systems, idempotency should be paired with **observable write state**: a request identifier, a stable operation identifier, and a way to determine whether a write was proposed, accepted, committed, rejected, or only partially applied. Idempotency without post-call observability still leaves downstream agents guessing about the actual side effect boundary.

**Ref:** Stripe Engineering Blog, "Designing robust and predictable APIs with idempotency" (2017); Stripe API Reference, "Idempotent requests"; Brandur, "Implementing Stripe-like Idempotency Keys in Postgres" (2017); IETF, RFC 9110.
### 2.5 Versioning Strategies

Versioning addresses the inevitability that APIs change. Strategies include:

**Path versioning** (`/v1/users`, `/v2/users`): Most visible, easiest to route and cache, widely adopted. Downsides: URI proliferation, breaks HATEOAS purist principles.

**Header versioning** (`Accept: application/vnd.myapi.v2+json`): Cleaner from a REST perspective (same resource, different representation), but harder to test in browsers and less discoverable.

**Query parameter versioning** (`?version=2`): Flexible but complicates caching.

**Stripe's model (rolling versioning):** Stripe pins each account to the most recent API version available at the time of the account's first API request. Breaking changes are encapsulated in version change modules that transform request/response objects. Developers can test new versions per-request via a `Stripe-Version` header. Stripe has maintained backward compatibility with every version since 2011 by running all version transformations as a pipeline.

**GraphQL's approach:** GraphQL avoids explicit versioning by design. New fields are added, old fields are marked `@deprecated` with a reason string. This works only if the team exercises discipline — removing deprecated fields without a transition period is still a breaking change.

**Ref:** Stripe Engineering Blog, "APIs as infrastructure: future-proofing Stripe with versioning" (2017); Redocly, "API versioning best practices"; Adidas API Guidelines.

---

## 3. GraphQL

### 3.1 Origin and Model

GraphQL was developed internally at Facebook in 2012 and open-sourced in 2015. It is a query language for APIs and a runtime for executing those queries against a type system that the server defines. Unlike REST's resource-oriented model with multiple endpoints, GraphQL exposes a single endpoint that accepts structured queries.

The core proposition: the client declares exactly what data it needs, and the server returns precisely that shape. This addresses two inefficiencies common in REST APIs:

- **Over-fetching:** Receiving fields the client does not need (e.g., requesting `/users/123` returns 30 fields when the client only needs `name` and `email`).
- **Under-fetching:** Needing to make multiple sequential requests to assemble data that spans several resources (the "N+1 client requests" problem).

GraphQL operates through three root operation types: `query` (read), `mutation` (write), and `subscription` (real-time updates via long-lived connections).

**Ref:** GraphQL Foundation, https://graphql.org/; HowToGraphQL, "GraphQL is the better REST."

### 3.2 Schema Design

The GraphQL schema, written in the Schema Definition Language (SDL), serves as the contract between client and server. It defines types, fields, arguments, and relationships. The schema is introspectable — clients can query the schema itself to discover available types and fields at runtime.

Key schema design principles from production experience:

**Design for the consumer, not the storage layer.** Do not auto-generate schemas from database tables. How data is stored is often shaped very differently from what clients need. Apollo's documentation explicitly warns against auto-generating schemas because it brings unused fields onto the graph in the wrong shape.

**Use the GraphQL Cursor Connections Specification** (commonly called the Relay pagination spec, or equivalent) for list fields. This standardizes cursor-based pagination with `edges`, `nodes`, `pageInfo`, and `cursor` fields. Beyond usability, pagination limits the potential for denial-of-service by bounding response sizes.

**Prefer nullable fields with defaults for new additions.** When evolving a schema, make new fields nullable or provide default values to avoid breaking existing clients.

**Use descriptive, unambiguous type names drawn from shared domain language.** Consistency across the schema reduces cognitive load for consumers and for the team itself. Linters integrated into schema registries can enforce naming conventions.

**Ref:** Apollo GraphQL Blog, "Federated Schema Design" (2022); The Guild / Hive, "Proven Schema Designs and Best Practices – Part 1" (GraphQL Conf 2025); Zuplo, "GraphQL API Design: Powerful Practices" (2025).

### 3.3 Federation

GraphQL federation is an architectural pattern for composing a single GraphQL API from multiple independently deployable services (subgraphs). It gained widespread adoption after Apollo introduced Apollo Federation in 2019.

The architecture consists of:

- **Subgraphs:** Independent GraphQL services, each owning a portion of the overall schema corresponding to a business domain.
- **Gateway (Router):** A service that composes subgraph schemas into a unified supergraph and routes incoming queries to the appropriate subgraphs.
- **Schema Registry:** A tool that validates schema composition and manages version history.

Federation aligns with Domain-Driven Design: each team owns its subgraph, controls its deployment lifecycle, and can use different languages and frameworks. The gateway hides this distribution from clients — they see a single, coherent schema.

Entity resolution across subgraphs works via the `@key` directive, which identifies the fields that uniquely identify a type. When a query spans multiple subgraphs, the gateway generates a query plan that fetches the key from one subgraph and uses it to resolve extended fields from another.

The GraphQL Foundation's Composite Schemas Working Group is now working toward standardization of federation patterns across the ecosystem (not just Apollo's implementation).

**Ref:** GraphQL Foundation, "GraphQL federation" (2026); Apollo GraphQL, "Introduction to Apollo Federation"; Contentful, "Understanding federated GraphQL" (2024).

### 3.4 Performance Concerns

GraphQL introduces performance challenges that REST does not:

**The N+1 resolver problem:** A naive resolver for a list of users that each have associated orders will issue one database query per user. The standard mitigation is the DataLoader pattern (batching and caching within a single request).

**Query complexity and depth:** Without restrictions, a client can construct deeply nested queries that explode into massive backend workloads. Mitigations include: query depth limiting, query complexity analysis (assigning cost weights to fields), request size limits, and persistent/allowlisted queries in production.

**Caching:** REST benefits from HTTP-native caching (ETags, Cache-Control). GraphQL's single-endpoint, POST-based model largely bypasses HTTP caching. Solutions include: CDN-level caching via query hashing (Automatic Persisted Queries), normalized client-side caching (Apollo Client, Relay), and schema-level `@cacheControl` directives.

**Ref:** Zuplo, "GraphQL API Design" (2025); API7.ai, "GraphQL vs REST API" (2025).

### 3.5 When to Use GraphQL vs. REST

This is not a binary choice. Many organizations use both:

| Criterion                          | REST                                      | GraphQL                                    |
|------------------------------------|-------------------------------------------|--------------------------------------------|
| Client diversity                   | Works well for homogeneous clients        | Excels when mobile, web, and IoT have different data needs |
| Caching                            | HTTP-native, well-understood              | Requires custom solutions                  |
| Learning curve                     | Lower (HTTP is widely understood)         | Higher (SDL, resolvers, DataLoader, etc.)  |
| Over/under-fetching                | Common problem without careful design     | Solved by design                           |
| File uploads                       | Native multipart support                  | Requires workarounds or extensions         |
| Real-time                          | Requires WebSockets or SSE separately     | Native subscriptions                       |
| Tooling maturity                   | Extremely mature                          | Rapidly maturing                           |
| Public APIs for external consumers | Generally preferred                       | Increasing but still less common           |

A common hybrid: expose REST publicly (broad adoption, simpler onboarding) and use GraphQL internally (flexible data composition for UI teams).

**Ref:** Postman Blog, "GraphQL vs REST" (2025); AWS, "GraphQL vs REST API" (2026); ARDURA Consulting, "API Design Best Practices Checklist" (2026).

---

## 4. gRPC (Brief Comparison)

gRPC is a high-performance RPC framework from Google using Protocol Buffers (protobuf) for serialization and HTTP/2 for transport. It supports bidirectional streaming, is strongly typed via `.proto` files, and generates client/server stubs in many languages.

gRPC is not a direct competitor to REST or GraphQL in most contexts — it excels in service-to-service communication within microservices architectures where latency and throughput matter more than human readability. Its binary protocol and HTTP/2 requirement make it poorly suited for browser-based clients without a proxy (though gRPC-Web exists as a workaround).

The tradeoff space: REST for public APIs and simplicity, GraphQL for flexible client-driven queries, gRPC for low-latency internal service meshes.

**Ref:** DEV Community, "Modern API Design Best Practices: REST, GraphQL, and gRPC in 2025."

---

## 5. SDK Design

### 5.1 Why SDKs Exist

An SDK (Software Development Kit) for an HTTP API exists to reduce the friction of integration. While any developer can use `curl` or a generic HTTP client, an SDK wraps authentication, request construction, response parsing, error handling, retries, pagination, and type safety into idiomatic library code. The goal is to make the most common integration paths trivially easy while keeping advanced usage accessible.

The Pragmatic Engineer newsletter observes that a single engineer historically maintained one SDK, but with the advent of SDK generators (OpenAPI Generator, Speakeasy, Stainless, AWS Smithy, Microsoft TypeSpec), a single engineer can now support SDKs in 4–5 languages — with caveats around idiomatic quality and edge cases.

**Ref:** The Pragmatic Engineer / Gergely Orosz, "Building great SDKs" (2025).

### 5.2 Core Design Principles

The following principles are synthesized from multiple sources (Microsoft Azure SDK Design Guidelines, Stripe's practices, Eyal Lantzman's SDK taxonomy):

**Idiomatic:** The SDK must feel natural in its target language. A Python SDK should use snake_case, context managers, and async/await. A Java SDK should use builders and typed exceptions. A common failure mode is when SDK authors who primarily write in one language transplant that language's idioms into another (e.g., Java-style verbose camelCase method names in a Python library).

**Consistent:** Terminology and behavior should be predictable within the SDK and aligned with the underlying API. If the API calls something a "customer," the SDK should not rename it to "user."

**Approachable:** Sensible defaults, progressive disclosure of advanced features, and a quick-start path that takes developers from zero to a successful API call in minutes.

**Diagnosable:** Clear, actionable error messages with contextual information (which function failed, relevant IDs, timestamps). Logging and tracing support (OpenTelemetry, W3C Trace Context).

**Dependable:** Minimize breaking changes. Follow Semantic Versioning (SemVer) rigorously. Be explicit about what is public API and what is internal.

**Ref:** Microsoft Azure SDK Design Guidelines, https://azure.github.io/azure-sdk/general_introduction.html; Lantzman, E. "SDKs: Principles and Best Practices" (2025); Shake, "SDK design best practices" (2025).

### 5.3 Thin vs. Thick SDKs

**Thin SDKs** are lightweight wrappers that handle authentication, serialization, and HTTP transport, mapping API endpoints 1:1 to methods. They add minimal logic beyond the API itself.

**Thick SDKs** include additional client-side intelligence: parallelized file transfers (like boto3's S3 multipart uploads), local caching, retry policies with exponential backoff and jitter, pagination helpers, connection pooling, and observability integration.

The choice depends on the API's complexity and the expected usage patterns. Payment APIs (Stripe) and cloud infrastructure APIs (AWS) benefit heavily from thick SDKs. Simple CRUD services may only need thin wrappers.

**Ref:** Lantzman, E. "SDKs: Principles and Best Practices" (2025); Vineeth.io, "Comprehensive Analysis of Design Patterns for REST API SDKs" (2024).

### 5.4 SDK Generation vs. Manual Authoring

SDK generation from OpenAPI specs or interface definition languages (protobuf, TypeSpec) offers scalability: define once, generate for many languages. However, generated code frequently requires post-generation cleanup to achieve idiomatic quality. The generated dependency trees may be outdated, the code may lack ergonomic features like method overloading or fluent builders, and edge cases around error handling often need manual intervention.

Manual authoring produces higher-quality developer experiences but scales poorly. The practical middle ground used by many organizations: generate the boilerplate (transport, serialization, types) and manually author the ergonomic layer (convenience methods, pagination iterators, retry logic).

**Ref:** The Pragmatic Engineer, "Building great SDKs" (2025); Lantzman, E. "SDKs: Principles and Best Practices" (2025).

---

## 6. Public Interface Design

### 6.1 APIs as Products

Stripe's internal philosophy — where it is reportedly not unusual to circulate 20-page design documents proposing individual API changes — treats APIs as products and developers as customers. This framing has consequences: every endpoint undergoes cross-functional design review, documentation quality is a factor in engineering career advancement, and backward compatibility is maintained indefinitely (since 2011).

Practical patterns from Stripe that generalize:

- **Prefixed IDs** (`ch_`, `cus_`, `pi_`, `sub_`): Instant identification of object type from any ID, preventing cross-type confusion and aiding debugging.
- **Consistent object structure:** Every resource includes `id`, `object` (type name), `created`, `livemode`, and `metadata` (arbitrary key-value store for consumer use).
- **Expandable relationships:** Instead of always embedding or always referencing, Stripe allows `?expand[]=customer` to selectively inline related objects, reducing round trips without bloating default responses.
- **Test mode as a parallel environment:** `sk_test_` vs. `sk_live_` keys route to isolated data, removing fear of experimentation.

**Ref:** Apidog, "Why Stripe's API is the Gold Standard" (2026); Stripe API Documentation.

### 6.2 Error Design
Error responses are part of the public interface and deserve as much design attention as success responses. For AI-heavy systems, they are also part of the verification boundary: a model or orchestration layer can only recover safely if failures are classified in a machine-readable way.

Baseline requirements:

- Use the most specific HTTP status code.
- Include a machine-readable error type or code (`invalid_request_error`, `rate_limit_exceeded`, `conflict`, `not_authorized`).
- Include a human-readable message explaining what happened.
- Include a field identifying the offending parameter, path, or schema location when applicable.
- Include a request or trace identifier for support and audit correlation.
- Include a documentation pointer for stable error families.

RFC 9457 (successor to RFC 7807) defines `application/problem+json` as the standard structured envelope with `type`, `title`, `status`, `detail`, and `instance`. That is a strong baseline, but AI-heavy systems usually need one layer more: explicit recovery semantics. In practice, the error model should tell the caller whether the failure is retryable, whether the request was applied, whether user confirmation is required, and whether the state should be re-fetched before a follow-up action.

A useful operational taxonomy is:

- **Validation failures:** the payload is structurally or semantically invalid; retry only after modification.
- **Authentication/authorization failures:** credentials or scope are insufficient; retry only after credential or permission change.
- **Conflict/state failures:** the request is valid but incompatible with current resource state; refresh state before retry.
- **Rate-limit/transient failures:** back off and retry according to explicit server guidance.
- **Internal failures:** the caller cannot assume whether a side effect occurred unless the API exposes a stable operation record or idempotent replay mechanism.

Anti-patterns are worse in AI-heavy systems than in ordinary integrations: returning `200 OK` with an error payload, relying on prose-only failure messages, mixing incompatible error shapes across endpoints, or omitting retry semantics forces the downstream model to guess.

**Ref:** IETF, RFC 9457, "Problem Details for HTTP APIs" (2023); Microsoft Azure Architecture Center, "Web API Design Best Practices"; OWASP, "API Security Top 10" (2023).
### 6.3 Rate Limiting
Every public API needs rate limits, but AI-heavy systems need them to be legible as control signals rather than opaque refusals. Automated clients can burst, retry, and fan out much more aggressively than human-written point integrations.

Implementation considerations:

- Tiered limits by plan, credential, tenant, or workload class.
- Distinct limits for reads, writes, and high-cost operations.
- `429 Too Many Requests` with explicit `Retry-After` guidance.
- Stable headers or fields exposing remaining budget and reset timing.
- For GraphQL, limits based on query depth, complexity, or estimated backend cost rather than raw request count.

For agentic systems, hidden or inconsistent rate-limit behavior creates planner instability. If one endpoint returns clean retry metadata and another silently degrades or emits generic 500s, the automation layer cannot make a safe scheduling decision. The rate-limit contract should therefore be explicit enough for a machine to decide whether to wait, re-plan, reduce scope, or seek user confirmation.

**Ref:** Microsoft Azure Architecture Center, "Web API Design Best Practices"; ARDURA Consulting, "API Design Best Practices Checklist" (2026).
### 6.4 Authentication and Security

Standard patterns:

- **API keys** for server-to-server authentication. Simple, widely supported, but cannot represent scoped permissions granularly.
- **OAuth 2.0** for delegated authorization (user grants app limited access). More complex but necessary for third-party integrations.
- **JWT (JSON Web Tokens)** for stateless bearer tokens with embedded claims.

Security fundamentals: enforce HTTPS everywhere, validate and sanitize all input, implement authentication and authorization on every request, use short-lived tokens with refresh mechanisms, and log all access for audit.

RFC 9700 (January 2025) codified OAuth 2.0 security best practices as mandatory, deprecating the Implicit Grant and Resource Owner Password Credentials (ROPC) flows. The OWASP API Security Top 10 remains the definitive threat model for API-specific vulnerabilities — covering broken object-level authorization, broken authentication, excessive data exposure, and injection attacks among others.

For GraphQL specifically: field-level authorization is critical because a single query can traverse multiple resource types with different access requirements.

**Ref:** TechGenyz, "API Design Best Practices" (2026); IETF, RFC 9700, "OAuth 2.0 Security Best Current Practice" (2025); OWASP, "API Security Top 10" (2023).

### 6.5 Documentation and Developer Experience
Documentation is the first touchpoint developers have with an API, but for AI-heavy systems the contract itself must also function as machine-readable documentation. Human-friendly prose alone is insufficient.

Human-oriented requirements remain important:

- **Interactive API reference** generated from the spec (Swagger UI, Redoc, Postman).
- **Quick-start guide** that gets a developer from zero to first successful call quickly.
- **Code examples in multiple languages** (at minimum: curl, Python, JavaScript/TypeScript).
- **Changelog** with dates, categorized by additive, breaking, and deprecation changes.
- **Sandbox environment** for testing without production consequences.
- **SDKs and client libraries** in popular languages.

For AI-heavy systems, additional requirements become first-class:

- explicit request and response schemas with examples;
- field-level semantics, units, nullability, and enum meanings;
- machine-readable deprecation metadata;
- explicit preconditions and postconditions for mutating calls;
- deterministic pagination and sorting semantics;
- stable error families and retry guidance;
- clear indication of whether a call is side-effect-free, idempotent, asynchronous, or confirmation-gated.

GraphQL introspection, OpenAPI, AsyncAPI, protobuf schemas, and similar specification formats help because they reduce ambiguity. But they only become safe tooling inputs when the documented semantics are concrete enough that a downstream system can validate them rather than infer them from prose.

**Ref:** GraphQL Foundation, "GraphQL Best Practices"; OpenAPI-related best-practices guides; Microsoft Azure SDK Design Guidelines.
## 7. Specification Formats
Specification formats matter not only for documentation and code generation, but also for whether an API can be safely consumed by AI-heavy systems. The key question is not merely whether a format is popular, but whether it exposes enough structure for downstream validation.

| Format | Domain | Strength for AI-heavy systems |
|---|---|---|
| OpenAPI 3.x | REST APIs | Strong for request/response schemas, examples, operation metadata, and code generation; weaker when teams leave semantics in prose or underspecify side effects. |
| AsyncAPI 3.x | Event-driven APIs | Strong for message contracts, channels, and event payload structure; safety still depends on explicit delivery, retry, and ordering semantics. |
| GraphQL SDL | GraphQL APIs | Strong type system and introspection; weaker if field semantics, authorization boundaries, cost models, and mutation side effects are implicit. |
| Protobuf | gRPC | Strong typing and code generation for internal systems; weaker for external discoverability without additional descriptive metadata. |
| TypeSpec | Multi-target | Strong when used as a single source of truth across generated interfaces, provided generated artifacts retain explicit behavior contracts. |

For AI-heavy systems, a specification format is only the first layer. Safe toolability usually requires additional declared semantics: idempotency, retry class, side-effect boundary, confirmation requirements for destructive actions, error taxonomy, pagination invariants, and operation status resources for long-running writes.

**Ref:** GraphQL Foundation, "GraphQL Best Practices"; Microsoft Azure Architecture Center, "Web API Design Best Practices"; Microsoft TypeSpec documentation.
## 8. Emerging Patterns (2025–2026)

**Hybrid REST + GraphQL architectures:** REST remains common for public distribution, while GraphQL often acts as an internal aggregation layer on top of existing services. This can work well for AI-heavy systems when the GraphQL layer normalizes resource shape, but it can also hide the true side-effect and authorization boundaries if the federation layer exposes convenience without provenance.

**API-first for AI agents:** As AI systems become active consumers of APIs rather than mere text users, the quality bar shifts from readable to verifiable. The safest APIs for agentic use expose explicit schemas, narrow action scopes, deterministic pagination, stable identifiers, machine-readable error classes, and observable commit state for writes.

**Webhooks and event-driven patterns:** Production API design increasingly depends on outbound events as much as inbound requests. For AI-agent and automation contexts, webhook contracts need the same rigor as synchronous APIs: signed payloads, delivery identifiers, replay protection, retry policy disclosure, event versioning, ordering assumptions, and explicit idempotency expectations on the consumer side. AsyncAPI helps with payload structure, but not all delivery semantics are implied by the schema alone.

**Long-running operations:** Many important actions cannot complete within a single request-response cycle. Standard patterns include request-acknowledge-poll workflows, operation status resources, webhook callbacks, and explicit terminal states such as `succeeded`, `failed`, or `canceled`. This matters for AI-heavy systems because observable write state is only credible if the caller can inspect the lifecycle of a long-running mutation instead of inferring completion from an initial `202 Accepted`.

**Safe toolability:** An endpoint is not automatically safe just because it is documented. For AI-heavy use, a toolable endpoint should answer at least these questions mechanically: what inputs are valid, what outputs are possible, whether the action is idempotent, whether it has side effects, whether confirmation is required, how failure classes are partitioned, and how the caller can determine whether the action actually committed.

**Model Context Protocol (MCP) and Agent2Agent (A2A):** MCP standardizes model-to-tool interaction, while A2A addresses agent-to-agent communication and delegation. They are complementary rather than interchangeable. An MCP or A2A wrapper around an ambiguous or side-effect-opaque API does not remove risk; it only changes where the ambiguity surfaces. The underlying API still needs verification-friendly semantics.

**Ref:** GraphQL Foundation, "GraphQL federation"; Apollo GraphQL, "Apollo Connectors"; AsyncAPI Initiative; Google A2A materials should be treated as current ecosystem inputs rather than settled standards unless backed by stable specifications.
## 9. Decision Framework
When choosing an API style, the relevant question is not "which is better" but "which contract can be verified under the actual failure modes of the system that will consume it."

1. **Who are the consumers?** External third parties often favor REST because onboarding and tooling are broad. Internal frontend teams often benefit from GraphQL. Internal service meshes may favor gRPC. AI-heavy consumers add a separate axis: can the interface be validated mechanically, or does safe use depend on prose interpretation?
2. **How diverse are client data needs?** Homogeneous needs can fit REST cleanly. Heterogeneous UI clients often benefit from GraphQL. But if query flexibility makes authorization, cost, or side effects harder to reason about, the flexibility may be too expensive for automated consumers.
3. **What is the retry and replay model?** If writes may be retried, parallelized, or resumed by agents, idempotency and explicit operation-state observability become design requirements rather than refinements.
4. **How is failure classified?** If the API cannot distinguish validation, auth, conflict, transient, and partial-commit states in machine-readable form, AI-heavy systems will guess, which is unsafe.
5. **What is the verification boundary?** The more the contract depends on undocumented conventions, hidden side effects, or inconsistent schemas, the less suitable it is for agentic orchestration.
6. **What is the evolution strategy?** Versioning and deprecation are not only compatibility concerns. Automated systems need to know when a field, enum, or behavior changed and whether the change is additive, breaking, or only documentary.

There is no universal answer. But one conclusion is robust: if an API is likely to be piped into an AI-heavy system, the contract should be evaluated as an execution surface for a fallible model, not just as a convenience layer for human developers. In that environment, verification, replay safety, explicit semantics, and observable side effects are first-class architecture.

### 9.1 PALS-Aligned Checklist

An API intended for LLM-mediated or agentic use should pass the following
minimum checklist before being treated as safe tool surface:

- Can every request and response be validated mechanically against an explicit
  schema?
- Can the caller distinguish validation, authorization, conflict, transient,
  and internal failure classes without interpreting prose?
- Are mutating operations replay-safe or otherwise protected by explicit
  idempotency and operation identifiers?
- Can the system determine whether a write actually committed, partially
  applied, or failed before taking the next step?
- Are destructive or high-impact actions bounded by confirmation, narrow scope,
  or reversible workflow design?
- Does the API expose stable identifiers, pagination semantics, and state
  inspection endpoints sufficient for post-call verification?

If the answer to these questions is no, the API may still be usable by humans,
but it is not yet a well-bounded execution substrate for AI-heavy systems under
PALS's Law.

**Ref:** core/PALS_LAW-v1.5.4.md; Zenodo record: https://zenodo.org/records/19401530; Microsoft Azure Architecture Center, "Web API Design Best Practices"; GraphQL Foundation, "GraphQL Best Practices".
## References
- Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures.* Doctoral dissertation, UC Irvine. https://roy.gbiv.com/pubs/dissertation/top.htm
- Fielding, R. T. (2008). "REST APIs must be hypertext-driven." Blog post.
- Fowler, M. (2010). "Richardson Maturity Model." https://martinfowler.com/articles/richardsonMaturityModel.html
- IETF. RFC 9110. *HTTP Semantics.* https://www.rfc-editor.org/rfc/rfc9110
- IETF. RFC 9457. *Problem Details for HTTP APIs* (2023). https://www.rfc-editor.org/rfc/rfc9457
- IETF. RFC 9700. *OAuth 2.0 Security Best Current Practice* (2025). https://www.rfc-editor.org/rfc/rfc9700
- OWASP. *API Security Top 10* (2023). https://owasp.org/API-Security/
- Stripe Engineering Blog. "APIs as infrastructure: future-proofing Stripe with versioning" (2017). https://stripe.com/blog/api-versioning
- Stripe Engineering Blog. "Designing robust and predictable APIs with idempotency" (2017). https://stripe.com/blog/idempotency
- Stripe API Documentation. "Idempotent requests." https://docs.stripe.com/api/idempotent_requests
- Stripe Documentation. "API upgrades." https://docs.stripe.com/upgrades
- Brandur. "Implementing Stripe-like Idempotency Keys in Postgres" (2017). https://brandur.org/idempotency-keys
- GraphQL Foundation. "GraphQL Best Practices." https://graphql.org/learn/best-practices/
- GraphQL Foundation. "GraphQL federation." https://graphql.org/learn/federation/
- Apollo GraphQL. "Introduction to Apollo Federation." https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/federation
- Apollo GraphQL Blog. "Federated Schema Design" (2022). https://www.apollographql.com/blog/backend/federation/federated-schema-design/
- Microsoft Azure. "Azure SDK Design Guidelines." https://azure.github.io/azure-sdk/general_introduction.html
- Microsoft Azure Architecture Center. "Web API Design Best Practices." https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design
- Microsoft. TypeSpec documentation. https://typespec.io/
- Orosz, G. & Pradet, Q. "Building great SDKs." *The Pragmatic Engineer* (2025). https://newsletter.pragmaticengineer.com/p/building-great-sdks
- Lantzman, E. "SDKs: Principles and Best Practices" (2025). https://eyallantzman.substack.com/p/sdks-principles-and-best-practices
- The Guild / Hive. "Proven Schema Designs and Best Practices – Part 1" (2025). https://the-guild.dev/graphql/hive/blog/schema-design-best-practices-part-1
- Adidas API Guidelines. "Changes and Versioning." https://adidas.gitbook.io/api-guidelines/rest-api-guidelines/evolution/versioning
- core/PALS_LAW-v1.5.4.md
- Zenodo. "PALS's Law" record. https://zenodo.org/records/19401530

**Reference note:** This bibliography mixes primary standards, primary vendor documentation, and secondary commentary. Standards and primary product documentation should be treated as authoritative for protocol and product behavior. Blog posts, consultancies, and summaries are useful for practice patterns and industry framing, but not for establishing formal consensus claims by themselves.
