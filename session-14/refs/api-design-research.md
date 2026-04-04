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
---

# API Design: REST, GraphQL, SDKs, and Public Interfaces

## 1. Foundational Concepts

### 1.1 What "API Design" Actually Means

API design is the process of defining the contract through which software systems communicate. The contract includes the structure of requests and responses, the semantics of operations, error behavior, authentication, and the evolution strategy over time. The quality of this contract determines whether consumers can integrate reliably, whether the system can evolve without breaking dependents, and whether the interface can scale to serve heterogeneous clients.

There is a recurring confusion in the industry between *protocol*, *architectural style*, and *API specification*. REST is an architectural style. HTTP is a protocol. OpenAPI is a specification format. GraphQL is a query language and runtime. These are not interchangeable categories, and conflating them leads to poor design decisions.

### 1.2 The Design-First vs. Code-First Dichotomy

Two approaches exist:

**Design-first (contract-first):** The API contract is authored before any implementation code. Stakeholders review the interface, mock servers can be generated for early testing, and frontend/backend teams can work in parallel against the agreed schema. Tools like Stoplight, SwaggerHub, and Postman support collaborative design workflows.

**Code-first:** Implementation is written first, and the API description is generated from annotations or introspection. This is faster for prototyping but frequently produces interfaces that leak internal data models and storage concerns into the public surface.

The industry consensus as of 2025 leans heavily toward design-first for any API that will be consumed by third parties.

**Ref:** MyAppAPI, "API Design Best Practices in 2025" (2025); Jitterbit, "7 Key Principles of API Design" (2025).

---

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

Idempotency — the property that performing an operation multiple times produces the same result as performing it once — is essential for reliable distributed systems. Network failures, timeouts, and retries are not edge cases; they are normal operating conditions.

Stripe pioneered the widely-adopted pattern of client-generated idempotency keys: the client generates a UUID and sends it as a header (`Idempotency-Key`). The server records the key and the result of the first execution. If the same key arrives again, the server returns the stored result instead of re-executing. Stripe stores keys for 24 hours (v1) or 30 days (v2) and validates that replay requests carry the same parameters.

GET and DELETE are idempotent by definition in HTTP semantics (RFC 9110 Section 9.2.2). POST is inherently non-idempotent and is the primary target for idempotency key mechanisms. PUT is idempotent by design (full replacement). Note that DELETE idempotency concerns server state, not response codes — a first `DELETE /resource/123` may return `200 OK` while a repeated request returns `404 Not Found`, yet the server state is identical (resource absent), satisfying the specification's definition.

**Ref:** Stripe Engineering Blog, "Designing robust and predictable APIs with idempotency" (2017); Stripe API Reference, "Idempotent requests"; Stripe Documentation, "API v2 overview."

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

Error responses are part of the public interface and deserve as much design attention as success responses. Principles:

- Use the most specific HTTP status code.
- Include a machine-readable error type/code (`card_declined`, `invalid_request_error`).
- Include a human-readable message explaining what happened.
- Include a `param` field identifying which input parameter caused the error.
- Include a `doc_url` linking to documentation for the specific error.
- Include a `request_id` for support and debugging correlation.

RFC 9457 (July 2023, successor to RFC 7807) defines the `application/problem+json` media type as the industry standard for structured error responses. It provides a consistent format with `type`, `title`, `status`, `detail`, and `instance` fields. Major frameworks (ASP.NET, Spring Boot, Quarkus) now have built-in support.

Anti-patterns: returning `200 OK` with an error payload, using generic messages like "Unknown error" or "Something went wrong," returning different error structures from different endpoints, and ignoring RFC 9457 when designing new APIs.

**Ref:** Apidog, "Why Stripe's API is the Gold Standard" (2026); Shake, "SDK design best practices" (2025); IETF, RFC 9457, "Problem Details for HTTP APIs" (2023).

### 6.3 Rate Limiting

Every public API needs rate limits. Implementation considerations:

- Tiered limits by plan (free vs. paid).
- Per-user and per-IP limits.
- Return `429 Too Many Requests` with a `Retry-After` header.
- For GraphQL, limit by query complexity/cost rather than simple request count, since queries vary enormously in server-side cost.

**Ref:** ARDURA Consulting, "API Design Best Practices Checklist" (2026); TechGenyz, "API Design Best Practices" (2026).

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

Documentation is the first (and often only) touchpoint developers have with an API. Requirements:

- **Interactive API reference** generated from the spec (Swagger UI, Redoc, Postman).
- **Quick-start guide** that gets a developer from zero to first successful call in under 30 minutes.
- **Code examples in multiple languages** (at minimum: curl, Python, JavaScript/TypeScript).
- **Changelog** with dates, categorized by additive/breaking/deprecation.
- **Sandbox environment** for testing without production consequences.
- **SDKs and client libraries** in popular languages, installable via standard package managers (npm, pip, Maven, etc.).

GraphQL adds introspection as a documentation mechanism — tools can auto-generate docs and provide IDE autocompletion directly from the schema.

**Ref:** OpenAPI Specification, "Best Practices for API Design"; ARDURA Consulting, "API Design Best Practices Checklist" (2026).

---

## 7. Specification Formats

| Format       | Domain              | Status (2025)                        |
|-------------|---------------------|--------------------------------------|
| OpenAPI 3.2 | REST APIs           | Dominant standard; evolved from Swagger |
| AsyncAPI 3.0/3.1 | Event-driven APIs  | Standard for WebSocket, message-driven architectures; 3.1.0 adds ROS 2 binding |
| GraphQL SDL | GraphQL APIs        | Standard schema definition language   |
| Protobuf    | gRPC                | Binary IDL, code generation focused   |
| TypeSpec     | Multi-target (Microsoft) | Newer; generates OpenAPI, protobuf, etc. from a single source |

**Ref:** MyAppAPI, "API Design Best Practices in 2025" (2025).

---

## 8. Emerging Patterns (2025–2026)

**Hybrid REST + GraphQL architectures:** REST for public distribution, GraphQL as an internal aggregation layer sitting on top of REST services. Apollo Connectors allow declaratively connecting REST APIs into a federated GraphQL graph.

**API-first for AI agents:** The 2025 State of the API Report (Postman) identifies APIs as the execution layer for AI systems. This raises the bar for machine-readable descriptions, consistent error formats, and self-documenting schemas — essentially HATEOAS concerns reframed for LLM consumers rather than human developers.

**Model Context Protocol (MCP):** An emerging protocol allowing AI models to interact with external services through standardized tool interfaces. MCP servers are increasingly being integrated into API platforms (WunderGraph, Apollo).

**Ref:** Postman Blog, "GraphQL vs REST" (2025); Apollo GraphQL, "Apollo Connectors"; WunderGraph.

---

## 9. Decision Framework

When choosing an API style, the relevant variables are not "which is better" but "which constraints match your requirements":

1. **Who are the consumers?** External third parties → REST (lower barrier, broader tooling). Internal frontend teams → GraphQL (flexibility). Internal microservices → gRPC (performance).
2. **How diverse are client data needs?** Homogeneous → REST is sufficient. Heterogeneous (mobile, web, TV, IoT) → GraphQL reduces per-client backend work.
3. **What is the caching strategy?** HTTP caching is critical → REST. Application-level caching is acceptable → GraphQL.
4. **What is the team's expertise?** REST has a shallower learning curve. GraphQL requires understanding resolvers, DataLoader, schema design, and (for federation) distributed schema composition.
5. **What is the evolution strategy?** Rolling versioning à la Stripe requires significant internal infrastructure. GraphQL's deprecation model is lighter but requires discipline. Path-versioned REST is simplest but can accumulate legacy endpoints.

There is no universal answer. Fielding's own dissertation was explicitly about *not* treating any single architectural style as a silver bullet — the irony that REST itself became one is well-documented.

---

## References

- Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures.* Doctoral dissertation, UC Irvine. https://roy.gbiv.com/pubs/dissertation/top.htm
- Fielding, R. T. (2008). "REST APIs must be hypertext-driven." Blog post.
- Fowler, M. (2010). "Richardson Maturity Model." https://martinfowler.com/articles/richardsonMaturityModel.html
- Wikipedia. "Richardson Maturity Model." https://en.wikipedia.org/wiki/Richardson_Maturity_Model
- Stripe Engineering Blog. "APIs as infrastructure: future-proofing Stripe with versioning" (2017). https://stripe.com/blog/api-versioning
- Stripe Engineering Blog. "Designing robust and predictable APIs with idempotency" (2017). https://stripe.com/blog/idempotency
- Stripe API Documentation. "Idempotent requests." https://docs.stripe.com/api/idempotent_requests
- Stripe Documentation. "API upgrades." https://docs.stripe.com/upgrades
- GraphQL Foundation. "GraphQL Best Practices." https://graphql.org/learn/best-practices/
- GraphQL Foundation. "GraphQL federation." https://graphql.org/learn/federation/
- Apollo GraphQL. "Introduction to Apollo Federation." https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/federation
- Apollo GraphQL Blog. "Federated Schema Design" (2022). https://www.apollographql.com/blog/backend/federation/federated-schema-design/
- The Guild / Hive. "Proven Schema Designs and Best Practices – Part 1" (2025). https://the-guild.dev/graphql/hive/blog/schema-design-best-practices-part-1
- Orosz, G. & Pradet, Q. "Building great SDKs." The Pragmatic Engineer (2025). https://newsletter.pragmaticengineer.com/p/building-great-sdks
- Lantzman, E. "SDKs: Principles and Best Practices" (2025). https://eyallantzman.substack.com/p/sdks-principles-and-best-practices
- Microsoft Azure. "Azure SDK Design Guidelines." https://azure.github.io/azure-sdk/general_introduction.html
- Microsoft Azure Architecture Center. "Web API Design Best Practices." https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design
- AWS. "GraphQL vs REST API." https://aws.amazon.com/compare/the-difference-between-graphql-and-rest/
- Postman Blog. "GraphQL vs REST" (2025). https://blog.postman.com/graphql-vs-rest/
- MyAppAPI. "API Design Best Practices in 2025." https://myappapi.com/blog/api-design-best-practices-2025
- Redocly. "API versioning best practices." https://redocly.com/blog/api-versioning-best-practices
- ARDURA Consulting. "API Design Best Practices: Implementation Checklist" (2026). https://ardura.consulting/blog/api-design-best-practices-checklist/
- Datanizant. "8 Essential API Design Best Practices" (2025). https://datanizant.com/api-design-best-practices/
- Zuplo. "GraphQL API Design: Powerful Practices" (2025). https://zuplo.com/blog/2025/05/26/graphql-api-design
- API7.ai. "GraphQL vs REST API Comparison 2025." https://api7.ai/blog/graphql-vs-rest-api-comparison-2025
- TechGenyz. "API Design Best Practices" (2026). https://techgenyz.com/api-design-best-practices-rest-graphql-guide/
- Vineeth.io. "Comprehensive Analysis of Design Patterns for REST API SDKs" (2024). https://vineeth.io/posts/sdk-development
- Apidog. "Why Stripe's API is the Gold Standard" (2026). https://apidog.com/blog/why-stripes-api-is-the-gold-standard-design-patterns-that-every-api-builder-should-steal/
- Two-Bit History. "Roy Fielding's Misappropriated REST Dissertation" (2020). https://twobithistory.org/2020/06/28/rest.html
- Brandur. "Implementing Stripe-like Idempotency Keys in Postgres" (2017). https://brandur.org/idempotency-keys
- Adidas API Guidelines. "Changes and Versioning." https://adidas.gitbook.io/api-guidelines/rest-api-guidelines/evolution/versioning
- Shake. "SDK design best practices" (2025). https://www.shakebugs.com/blog/sdk-design-best-practices/
- OpenAPI Specification. "Best Practices for API Design." https://openapispec.com/docs/best-practices-for-api-design/
- IETF. RFC 9457, "Problem Details for HTTP APIs" (2023). https://www.rfc-editor.org/rfc/rfc9457
- IETF. RFC 9700, "OAuth 2.0 Security Best Current Practice" (2025). https://www.rfc-editor.org/rfc/rfc9700
- OWASP. "API Security Top 10" (2023). https://owasp.org/API-Security/
- Microsoft Azure. "Azure SDK Design Guidelines." https://azure.github.io/azure-sdk/general_introduction.html
