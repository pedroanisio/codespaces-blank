# Correctness and completeness audit of the API design document

This document is **substantially accurate** on its core technical claims — roughly 80% of verifiable facts check out cleanly — but contains **several meaningful errors, imprecise attributions, and six critical topic omissions** that undermine its claim to comprehensiveness. The most consequential factual error is the misattribution of SDK design principles to Auth0 and IBM Watson (they originate from Microsoft Azure). The most consequential structural gap is the near-total absence of API security coverage, event-driven patterns, and error handling standards. Below is a claim-by-claim assessment followed by a completeness analysis.

---

## REST foundations hold up well, with one nuance on Fielding's authorship

**Claims 1–3 (Fielding's dissertation, REST constraints, 2008 blog post):** All verified as accurate with one minor precision issue.

The dissertation title, "Architectural Styles and the Design of Network-based Software Architectures," was indeed completed at UC Irvine in 2000. Fielding was a co-author of HTTP/1.0 (RFC 1945, alongside Berners-Lee and Frystyk) and the **first-listed author** of HTTP/1.1 across both RFC 2068 (5 co-authors) and RFC 2616 (7 co-authors). Calling him "primary author" is **directionally correct but slightly imprecise** — "lead author" or "principal editor" would be more accurate for a collaborative specification. The IETF convention of listing "Fielding, et al." on RFC 2616 supports his leading role.

The REST constraint derivation chain (Client-Server → Stateless → Cache → Uniform Interface → Layered System → Code-on-Demand as optional) **exactly matches** Sections 5.1.2–5.1.7 of the dissertation. The four Uniform Interface sub-constraints — identification of resources, manipulation through representations, self-descriptive messages, and hypermedia as the engine of application state — are confirmed verbatim from Section 5.1.5. Note that Fielding used the full phrase; the acronym "HATEOAS" was coined later by the community.

Fielding's 2008 blog post, titled **"REST APIs must be hypertext-driven,"** was published **October 20, 2008** at `roy.gbiv.com/untangled/2008/rest-apis-must-be-hypertext-driven`. Its central argument — "if the engine of application state is not being driven by hypertext, then it cannot be RESTful and cannot be a REST API. Period." — is confirmed. The post included six specific rules for REST APIs and generated 51 comments, including Fielding's notable clarification that "REST is software design on the scale of decades."

**Corrections needed:** Change "primary author of HTTP/1.1" to "lead author" or "first-listed author and editor" of HTTP/1.1.

---

## Richardson Maturity Model and HTTP idempotency are accurately described

**Claim 4 (Richardson Maturity Model):** Leonard Richardson presented what he called the **"Maturity Heuristic"** at **QCon San Francisco on November 19, 2008**, in a talk titled "Justice Will Take Us Millions of Intricate Moves." The name "Richardson Maturity Model" was applied later by Martin Fowler, who published his article **"Richardson Maturity Model: steps toward the glory of REST"** on **March 18, 2010** at `martinfowler.com/articles/richardsonMaturityModel.html`. The four levels (0–3) are accurately described. One nuance worth noting: the level names "Swamp of POX," "HTTP Verbs," etc. are **Fowler's popularized terminology**, not Richardson's original labels. Richardson himself described this popularization as "very embarrassing" at RESTFest 2015.

**Claim 5 (HTTP Method Idempotency):** Both claims are **correct per specification**. RFC 5789 (which defines PATCH) explicitly states: "PATCH is neither safe nor idempotent," though it notes PATCH *can be* implemented as idempotent depending on the patch format (e.g., JSON Merge Patch is typically idempotent; a JSON Patch with "increment by 1" is not). RFC 9110 Section 9.2.2 explicitly lists **DELETE as idempotent**: "Of the request methods defined by this specification, PUT, DELETE, and safe request methods are idempotent."

The important nuance the document should mention: DELETE idempotency concerns **server state**, not response codes. A first `DELETE /resource/123` may return `200 OK` while a second returns `404 Not Found` — the server state is identical (resource absent), which satisfies the spec's definition. RFC 9110 explicitly acknowledges that "the response might differ" for repeated idempotent requests.

---

## Stripe claims are mostly accurate, with one meaningful error

**Claim 6 (Idempotency keys):** **Fully verified.** Stripe's official documentation confirms **24-hour retention for API v1** and **30-day retention for API v2**. Parameter validation on replay is confirmed for v1: "The idempotency layer compares incoming parameters to those of the original request and errors if they're not the same." The v2 behavior differs slightly — it focuses on retrying failed requests rather than strict parameter matching.

**Claim 7 (Versioning):** **Partially accurate.** The document says Stripe "pins each API key to the version active when the key was first used." The actual mechanism is that **Stripe pins each account (not each API key) to the most recent version available at the time of the account's first API request**. The 2017 Stripe engineering blog post ("APIs as infrastructure: future-proofing Stripe with versioning," published August 15, 2017) states: "The first time a user makes an API request, their account is automatically pinned to the most recent version available." Users can override per-request via a `Stripe-Version` header. Additionally, newer SDKs (stripe-ruby v9+, stripe-node v12+) now pin to the API version at SDK release rather than the account's pinned version. Backward compatibility since 2011 is **confirmed** — Stripe's blog states they maintained compatibility with "every version of our API since the company's inception in 2011."

**Claims 17 and 19 (Prefixed IDs and key prefixes):** **Fully verified.** The prefixes `ch_`, `cus_`, `pi_`, and `sub_` are confirmed from Stripe's API documentation. Key prefixes `sk_test_` and `sk_live_` (and corresponding `pk_test_`, `pk_live_` for publishable keys) are confirmed from Stripe's official API keys documentation.

**Claim 18 (20-page design document):** **Partially verified, likely mischaracterized.** The source is a Postman Blog article summarizing a talk by CJ Avilla (Stripe Developer Advocate), who said "it's not unusual to circulate 20-page design documents proposing new changes during an API review." This describes a **cultural practice** of writing lengthy design docs for individual API proposals — not necessarily a single canonical 20-page API design rulebook. The document should clarify this distinction.

**Corrections needed:** Change "pins each API key" to "pins each account on first API request." Add the nuance about SDK-level version pinning in newer versions.

---

## GraphQL section is solid, with minor naming inaccuracies

**Claim 8 (GraphQL origin):** **Confirmed.** Development began at Facebook in **2012** (initially called "SuperGraph" by Nick Schrock, joined by Lee Byron and Dan Schafer). It was first publicly discussed at React.js Europe 2014 and **open-sourced in 2015** — the first spec working draft in July 2015, with the formal blog announcement on September 14, 2015.

**Claim 9 (Apollo Federation):** **Confirmed.** Apollo Federation was introduced on **May 30, 2019**, with Federation 2 reaching alpha in November 2021 and GA in approximately April 2022.

**Claim 10 (Composite Schema Working Group):** **Substantially correct with minor inaccuracies.** The group exists and does work on standardizing federation, but the official name is **"Composite Schemas Working Group"** (plural "Schemas"), and it is technically a **subcommittee** of the GraphQL Specification Working Group, not a standalone working group. It was formally announced on **May 16, 2024**, includes engineers from Apollo, ChilliCream, Graphile, Hasura, Netflix, and The Guild, and maintains a specification draft at `graphql.github.io/composite-schemas-spec/`.

**Claim 11 (Relay Pagination):** The structural description — edges, nodes, pageInfo, cursor — is **accurate**, but the name is wrong. The official name is the **"GraphQL Cursor Connections Specification"** (hosted at `relay.dev/graphql/connections.htm`), not "Relay Pagination Specification." Connection types must have `edges` and `pageInfo` fields; Edge types must have `node` and `cursor` fields. The `pageInfo` object contains `hasNextPage`, `hasPreviousPage`, `startCursor`, and `endCursor`.

**Corrections needed:** Fix the spec name to "GraphQL Cursor Connections Specification." Fix "Composite Schema" to "Composite Schemas" (plural) and note it's a subcommittee.

---

## The SDK design principles are misattributed — they belong to Microsoft Azure

**Claim 12 (gRPC):** **Fully confirmed.** gRPC uses Protocol Buffers as its default IDL and HTTP/2 as its transport. gRPC-Web is accurately described as a browser workaround — the specific technical limitation is that browsers don't expose HTTP/2 trailer HEADERS frames to JavaScript, and there's no mechanism to control raw HTTP/2 framing. The Chromium team explicitly closed this as "WontFix."

**Claim 13 (Pragmatic Engineer on SDK generators):** **Confirmed.** Gergely Orosz (with co-author Quentin Pradet from Elastic) published **"Building great SDKs"** in approximately late July/early August 2025. The article explicitly states: "The rule of thumb used to be that one engineer can maintain one SDK. But with SDK generators, a single engineer can support SDKs written in 4-5 languages." The tools listed — OpenAPI Generator, Speakeasy, Stainless, AWS Smithy, and Microsoft TypeSpec — are all real, though **Smithy and TypeSpec are more accurately API modeling/IDL tools** that feed into code generation pipelines rather than direct SDK generators. The article does group them together in a broader "SDK ladder" context.

**Claim 14 (SDK principles attribution):** **INCORRECT.** The five principles — idiomatic, consistent, approachable, diagnosable, dependable — are definitively from the **Microsoft Azure SDK Design Guidelines** (`azure.github.io/azure-sdk/general_introduction.html`), not from Auth0 or IBM Watson. Auth0's SDK guidelines (published March 2024) discuss different principles (empathy, contextual awareness, modular architecture, extensibility). IBM Watson's SDK guidelines focus on open-source practices, package manager usage, and developer burden reduction. Neither uses this specific five-principle framework. **This is the document's most significant factual error.**

**Correction required:** Reattribute the five SDK design principles to Microsoft Azure SDK Design Guidelines.

---

## Specification versions need updating

**Claim 15 (OpenAPI):** **OpenAPI 3.2.0 was released on September 19, 2025**, making the claim correct as of late 2025 and early 2026. However, if the document was written before September 2025, it may be anachronistic — for most of 2025, the latest version was **3.1.1**. Notable additions in 3.2 include support for the HTTP QUERY method, improved deprecation semantics, and sequential/streaming data protocols.

**Claim 16 (AsyncAPI):** **Partially correct.** AsyncAPI 3.0.0 was the major release (late 2023), but the **current latest version is 3.1.0**, which added a ROS 2 binding. The document should specify 3.0 as the major version line and note 3.1.0 as the current release.

---

## Emerging patterns and references check out cleanly

**Claim 20 (Apollo Connectors):** **Confirmed.** Apollo Connectors were announced at **GraphQL Summit 2024** (October 8–10, 2024) and reached general availability with Apollo Router 2.0 in early 2025. They use `@connect` and `@source` directives to declaratively map REST endpoints to GraphQL schema fields without custom resolver code. Apollo CTO Matt DeBergalis called them "the biggest thing we've ever shipped."

**Claim 21 (MCP integrations):** **Confirmed.** The Model Context Protocol was created by **Anthropic** and announced in **November 2024**. WunderGraph offers an "MCP Gateway" in their Cosmo platform. Apollo released the "Apollo MCP Server" on **May 16, 2025**, and was explicitly mentioned as an early MCP adopter in Anthropic's original announcement. MCP was donated to the **Linux Foundation** in December 2025 and now has **97M+ monthly SDK downloads** and **5,800+ MCP servers**.

**Claims 22–23 (Reference verification):** All three sampled references are **confirmed accurate**:

- Stripe's API versioning blog post: "APIs as infrastructure: future-proofing Stripe with versioning," published **August 15, 2017** at `stripe.com/blog/api-versioning`
- Fowler's article: "Richardson Maturity Model," published **March 18, 2010** at `martinfowler.com/articles/richardsonMaturityModel.html`
- Two-Bit History: "Roy Fielding's Misappropriated REST Dissertation," published **June 28, 2020** at `twobithistory.org/2020/06/28/rest.html`

---

## Six critical topics are missing from the document

The completeness analysis reveals **6 critical omissions, 6 moderate omissions, and 3 minor omissions**. The critical gaps are:

**API security** is the most consequential absence. RFC 9700 (January 2025) made OAuth 2.0 security best practices mandatory, deprecating the Implicit Grant and ROPC flows. The OWASP API Security Top 10 remains the definitive threat model. FAPI 2.0 reached Final status in 2025. **91% of organizations** experienced an API security incident in 2023 per F5 Networks. A comprehensive API design document without security coverage is fundamentally incomplete.

**Webhooks and event-driven APIs** represent a primary architectural pattern now on par with REST and GraphQL. AsyncAPI has become the industry-standard specification, CloudEvents graduated from CNCF in 2024, and Kong's 2026 API landscape report identifies event-driven architecture as a major pillar.

**Error handling patterns and RFC 9457** (successor to RFC 7807, published July 2023) define the industry standard for structured `application/problem+json` error responses. The OWASP Top 10 2025 added "Mishandling of Exceptional Conditions" as a new category. Major frameworks (ASP.NET, Spring Boot, Quarkus) now have built-in support.

**Long-running operations patterns** are essential for real-world API design. Both MCP and Google's A2A protocol explicitly address asynchronous task handling. Polling, webhook callbacks, and the async request-acknowledge-poll pattern are universal design challenges.

**API governance** — including design review processes, style guides, linting tools (Spectral, Redocly), and shift-left enforcement in CI/CD — is consistently ranked as a top concern. The 2025 Postman State of API Report found **55% of organizations** struggle with inconsistent documentation.

**Backwards compatibility strategies beyond versioning** — additive-only change policies, deprecation timelines, sunset headers (RFC 8594), field-level deprecation — are core design concerns. The GraphQL September 2025 spec explicitly clarified deprecation semantics, and modern REST APIs increasingly favor additive changes over traditional versioning.

The moderate omissions include API gateways (especially the emerging "AI Gateway" category), OpenTelemetry for observability, contract testing, batch/bulk operations, pagination pattern depth, and API testing strategies. Minor omissions include hypermedia formats (HAL, JSON:API), content negotiation, and API monetization.

---

## The document misses the most transformative 2025–2026 development: agentic API patterns

Beyond the topic gaps, the document does not adequately account for how **AI agents are reshaping API design**. Three developments in particular are transforming the field:

**MCP's rapid standardization** — from Anthropic's November 2024 announcement to Linux Foundation stewardship, 97M+ monthly downloads, and adoption by OpenAI, Google, and hundreds of vendors — is forcing APIs to be machine-readable by design. The November 2025 spec added OAuth 2.1 authorization and structured tool outputs. Thoughtworks placed "naive API-to-MCP conversion" in its Technology Radar "Hold" category, warning that wrapping existing APIs as MCP tools without security redesign is an anti-pattern.

**Google's Agent2Agent (A2A) protocol**, launched April 2025 with 50+ technology partners and donated to the Linux Foundation in June 2025, addresses agent-to-agent communication (complementary to MCP's agent-to-tool focus). Its Agent Cards (`.well-known/agent.json`) introduce a new discovery pattern.

**The GraphQL September 2025 spec** — the first major update since October 2021 — added Schema Coordinates, OneOf Input Objects (input unions), and descriptions on executable documents specifically to support MCP/AI tooling. These changes reflect a broader trend: API specifications are being designed with machine consumers in mind.

Other notable 2025–2026 developments the document should reference include **RFC 9700** (mandatory OAuth 2.0 security practices), the **HTTP QUERY method** IETF draft (a new safe, idempotent method allowing request bodies), **OpenAPI 3.2's** support for QUERY and streaming protocols, and the emergence of **zero-trust API architectures** with mTLS and fine-grained RBAC/ABAC enforcement at every request.

## Conclusion

The document is a strong technical foundation. Its treatment of Fielding's REST theory, the Richardson Maturity Model, Stripe's design patterns, and GraphQL's ecosystem is detailed and overwhelmingly accurate. The **three corrections requiring immediate attention** are: (1) reattribute SDK design principles from Auth0/IBM Watson to Microsoft Azure, (2) change Stripe's version pinning from "per API key" to "per account," and (3) rename the "Relay Pagination Specification" to "GraphQL Cursor Connections Specification." The **six critical topic additions** — security, event-driven APIs, error handling (RFC 9457), long-running operations, governance, and backwards compatibility strategies — would transform this from a solid technical reference into a genuinely comprehensive API design guide. Most urgently, the document needs a section on agentic API patterns (MCP, A2A) as a first-class architectural concern, not just an "emerging" footnote.