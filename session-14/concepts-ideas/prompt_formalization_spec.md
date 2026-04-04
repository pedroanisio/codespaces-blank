---
title: "Formal Specification: PROMPT_MARKUP_LANGUAGE (PML) v1.0"
author: "Claude (rewritten for internal consistency)"
date: "2026-04-04"
method: "spec rewrite after review"
disclaimer: |
  No information within this document should be taken for granted.
  Any statement or premise not backed by a real logical definition or
  verifiable reference may be invalid, erroneous, or a hallucination.
  This document specifies a constrained prompt markup language and its
  execution contract. Claims about semantic quality, factual accuracy,
  and intent preservation are explicitly separated from the normative,
  mechanically checkable core.
status: "active"
version: "1.0"
---

# Formal Specification: PROMPT_MARKUP_LANGUAGE (PML) v1.0

## 1. Purpose

This document defines a constrained XML-based prompt markup language called
**PROMPT_MARKUP_LANGUAGE (PML)**.

The goal of PML is modest and explicit:

- Provide a structural format for declaring prompt variables and rules.
- Define a small execution contract for binary evaluation outcomes.
- Separate mechanically checkable constraints from non-mechanical judgment.

This specification does **not** claim to solve factual verification,
hallucination detection, or semantic equivalence of revised text. Those are
out of scope for the normative core and are treated here as external review
concerns.

## 2. Source Basis

This specification is derived from the following source classes:

1. Ranked user interaction preferences.
2. An example `SYSTEM_PROMPT` written in XML with variables and rules.
3. The requirement to distinguish explicit formal definition from implicit
   behavioral interpretation.

Where the sources underdetermine the design, this document marks the result
as a design choice rather than a source fact.

## 3. Scope

### 3.1 In Scope

- XML document structure for `SYSTEM_PROMPT`, `VARIABLE_SET`, `VAR`,
  `RULE_SET`, and `RULE`.
- A binary outcome space: `Approve` or `Improve`.
- Output-shape constraints associated with each outcome.
- A normative XSD for the document grammar.

### 3.2 Out of Scope

- Determining whether a claim is true in the external world.
- Proving that a rewrite preserves author intent.
- Detecting hallucinations from first principles.
- Proving that an English-language rule is unambiguous.

## 4. Claim Inventory

| ID | Claim | Class | Source Basis |
|----|-------|-------|--------------|
| C01 | Markdown documents in this workspace require an explicit disclaimer. | Workspace obligation | User/project instruction |
| C02 | Formalization must prefer references, provenance, and explicit definitions over unsupported assertion. | Workspace obligation | User preference |
| C03 | Unbiased output is preferred over flattering output. | Behavioral preference | User preference |
| C04 | Feedback is evaluated by content, not treated as automatically true. | Behavioral obligation | User preference |
| C05 | Markdown is preferred over DOCX; TypeScript over JavaScript. | Format preference | User preference |
| C06 | English is the default working language. | Language preference | User preference |
| C07 | A structured prompt language may be represented in XML. | Design assumption | Example prompt |
| C08 | The language includes variables and declarative rules. | Design assumption | Example prompt |
| C09 | Evaluation returns exactly one of two outcomes. | Core definition | Example prompt |
| C10 | `Approve` returns only the approval payload inside one fenced code block. | Output obligation | Example prompt |
| C11 | `Improve` returns improvements followed by revised content inside one fenced code block. | Output obligation | Example prompt |
| C12 | No text is emitted outside the required fenced code block. | Output obligation | Example prompt |
| C13 | Extra commentary or reasoning trace is forbidden in the emitted payload. | Output obligation | Example prompt |

## 5. Design Choices Introduced By This Rewrite

The original draft mixed source-derived facts and implementation choices.
This rewrite makes the following design choices explicit:

1. Variable lookup is keyed by `VAR/@id`, not by `VAR/@name`.
2. A `SYSTEM_PROMPT` contains at most one `VARIABLE_SET`.
3. The normative core is syntactic and contractual, not semantic.
4. References support the rationale of the spec, but the XML grammar is
   defined by the XSD in Appendix A rather than by prose alone.

## 6. Formal Model

### 6.1 Sets and Basic Objects

```text
Doc          := set of valid PML documents
Outcome      := {Approve, Improve}
RuleText     := set of rule strings
VarId        := set of XML IDs used by VAR/@id
VarName      := set of human-readable variable names
String       := set of finite strings
CodeFence    := set of fenced code block payloads
```

### 6.2 Record Model

For a valid `SYSTEM_PROMPT` document `d`:

```text
vars(d) : VarId -> String
name(d) : VarId -> VarName
rules(d) : finite sequence of RuleText
outcome(d, x) : Outcome
emit(d, x) : CodeFence
```

Interpretation:

- `vars(d)[id]` is the string stored in `VAR/@text` for `VAR/@id = id`.
- `name(d)[id]` is descriptive metadata stored in `VAR/@name`.
- Rules are ordered textually but semantically conjoined unless an external
  interpreter defines stronger control semantics.
- `x` denotes the external input artifact being evaluated by the prompt.

### 6.3 Well-Formedness

A document `d` is well-formed PML iff:

1. `d` contains exactly one `SYSTEM_PROMPT` root element.
2. `SYSTEM_PROMPT/@id` is present and is a valid XML `ID`.
3. `d` contains zero or one `VARIABLE_SET`.
4. Every `VAR/@id` is unique within the document.
5. Every `RULE_SET/@target` equals the root `SYSTEM_PROMPT/@id`.
6. Every `RULE` contains non-empty character data after trimming whitespace.

## 7. Normative Semantics

### 7.1 Variable Semantics

For any valid document `d` and any `VAR` element `v` in `d`:

```text
binding_key(v)   = v.@id
binding_name(v)  = v.@name
binding_value(v) = v.@text
vars(d)[v.@id]   = v.@text
name(d)[v.@id]   = v.@name
```

`@name` is documentary. It is not a lookup key.

### 7.2 Rule Semantics

Each `RULE` contributes a declarative constraint expressed in English.
This specification does not formalize natural-language rule parsing.
Normatively, the document asserts only that:

- each rule is part of the rule set named by its containing `RULE_SET`;
- multiple rules are jointly asserted;
- enforcement is delegated to the interpreter that consumes the prompt.

### 7.3 Outcome Contract

For every evaluation input `x`, an interpreter compliant with this spec must
produce exactly one outcome:

```text
forall d in Doc, forall x:
  outcome(d, x) in {Approve, Improve}
```

This specification does **not** define the decision procedure that selects
`Approve` or `Improve`.

### 7.4 Output Contract For `Approve`

If `outcome(d, x) = Approve`, then:

```text
emit(d, x) is exactly one fenced code block
and its payload is vars(d)["APRV_MSG"] if that variable exists
and no text is emitted before or after that fence
```

If `APRV_MSG` is absent, the document remains valid PML, but an interpreter
that requires the approval message variable is underspecified at runtime.

### 7.5 Output Contract For `Improve`

If `outcome(d, x) = Improve`, then:

```text
emit(d, x) is exactly one fenced code block
and its payload contains:
  (a) an improvement list
  (b) revised content
and (a) precedes (b)
and no text is emitted before or after that fence
```

This specification constrains payload shape only. It does not prove that the
revised content is substantively better, factually correct, or intent-preserving.

### 7.6 No-Commentary Rule

For both outcomes, the emitted payload must exclude free-standing commentary
outside the required approval or improvement content.

Operationally:

- `Approve` may contain only the approval payload.
- `Improve` may contain only the improvement list and revised content.

## 8. Decidability Boundary

This section distinguishes what the specification defines mechanically from
what it leaves to external judgment.

### 8.1 Mechanically Checkable Core

The following are mechanically checkable from the document or emitted output:

- XML well-formedness.
- XSD validation.
- Presence and uniqueness constraints on IDs.
- Whether the document has zero or one `VARIABLE_SET`.
- Whether an output contains exactly one fenced code block.
- Whether text exists outside the required fence.
- Whether an `Improve` payload orders the improvement list before revised content,
  assuming the interpreter labels those regions in a detectable way.

### 8.2 Not Mechanically Solved By This Spec

The following are not solved by PML itself:

- Whether a factual statement is true.
- Whether a rule written in English is semantically precise enough.
- Whether a revision preserves intent.
- Whether feedback is sound.
- Whether an improvement list is complete.

These properties may be reviewed by humans or approximated by external tools,
but they are not part of the normative decidable core.

## 9. Conformance

### 9.1 Document Conformance

A **conforming PML document** is any XML document that:

1. validates against Appendix A;
2. satisfies the well-formedness conditions in Section 6.3;
3. does not rely on `VAR/@name` as a binding key.

### 9.2 Interpreter Conformance

A **conforming interpreter** is any system that:

1. accepts a conforming PML document;
2. binds variables by `VAR/@id`;
3. exposes exactly one outcome from `Outcome`;
4. enforces the output contract in Section 7 for the chosen outcome.

This specification intentionally allows different interpreters to disagree on
how `Approve` versus `Improve` is selected.

## 10. Gaps And Non-Normative Recommendations

The following are known gaps in the source pattern rather than bugs in this
rewritten spec.

### 10.1 Missing Decision Procedure

The language defines the shape of outcomes, not a scoring function that maps
input artifacts to `Approve` or `Improve`.

Non-normative recommendation:

```xml
<EVALUATION_CRITERIA>
  <CRITERION id="epistemic">Claims are sourced or derived</CRITERION>
  <CRITERION id="structural">Output shape matches the contract</CRITERION>
  <CRITERION id="behavioral">Tone matches declared preferences</CRITERION>
</EVALUATION_CRITERIA>
```

### 10.2 Missing Evidence Model

The language does not define how claims are supported by references,
derivations, or provenance metadata.

Non-normative recommendation:

```xml
<EVIDENCE_POLICY>
  <FACT requires="citation-or-derivation" />
  <REFERENCE requires="resolvable-source" />
  <INFERENCE requires="explicit-steps" />
</EVIDENCE_POLICY>
```

### 10.3 English Rule Ambiguity

`RULE` content is natural language. That is practical, but not formally closed.

Non-normative recommendation:

- keep rules atomic;
- avoid hidden exceptions;
- separate syntactic obligations from judgment obligations;
- attach examples when ambiguity is likely.

## 11. Minimal Example

```xml
<SYSTEM_PROMPT id="SYSP1" description="Binary review prompt">
  <VARIABLE_SET id="VS1">
    <VAR id="APRV_MSG" name="approval_message" text="Approved." />
  </VARIABLE_SET>
  <RULE_SET id="RS1" target="SYSP1">
    <RULE id="R1">Emit exactly one fenced code block.</RULE>
    <RULE id="R2">Emit no text outside the code block.</RULE>
    <RULE id="R3">If approved, emit only the approval payload.</RULE>
    <RULE id="R4">If improvement is required, emit improvements then revised content.</RULE>
  </RULE_SET>
</SYSTEM_PROMPT>
```

## 12. Summary

PML v1.0 is a structural prompt language, not a complete theory of textual
quality. Its normative core is intentionally narrow:

- XML grammar for prompt documents.
- Stable variable binding by `VAR/@id`.
- Binary outcome contract.
- Output-shape constraints for `Approve` and `Improve`.

What it does **not** provide is equally important:

- no truth oracle;
- no automatic hallucination proof;
- no semantic-equivalence proof for rewrites;
- no universal algorithm for prompt evaluation quality.

That narrower claim is more defensible than the earlier draft because the
spec now avoids treating semantic judgment as though it were syntactically
decidable.

## Appendix A: Normative XML Schema

**File name:** `pml-v1.xsd`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">

  <xs:element name="SYSTEM_PROMPT">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="VARIABLE_SET" minOccurs="0" maxOccurs="1"/>
        <xs:element ref="RULE_SET" minOccurs="1" maxOccurs="unbounded"/>
      </xs:sequence>
      <xs:attribute name="id" type="xs:ID" use="required"/>
      <xs:attribute name="description" type="xs:string" use="optional"/>
    </xs:complexType>
  </xs:element>

  <xs:element name="VARIABLE_SET">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="VAR" minOccurs="1" maxOccurs="unbounded"/>
      </xs:sequence>
      <xs:attribute name="id" type="xs:ID" use="required"/>
    </xs:complexType>
  </xs:element>

  <xs:element name="VAR">
    <xs:complexType>
      <xs:attribute name="id" type="xs:ID" use="required"/>
      <xs:attribute name="name" type="xs:string" use="required"/>
      <xs:attribute name="text" type="xs:string" use="required"/>
    </xs:complexType>
  </xs:element>

  <xs:element name="RULE_SET">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="RULE" minOccurs="1" maxOccurs="unbounded"/>
      </xs:sequence>
      <xs:attribute name="id" type="xs:ID" use="required"/>
      <xs:attribute name="target" type="xs:IDREF" use="required"/>
    </xs:complexType>
  </xs:element>

  <xs:element name="RULE">
    <xs:complexType mixed="true">
      <xs:attribute name="id" type="xs:ID" use="required"/>
    </xs:complexType>
  </xs:element>

</xs:schema>
```

## Appendix B: Conformance Checklist

### Document Author Checklist

- Root element is `SYSTEM_PROMPT`.
- `SYSTEM_PROMPT/@id` exists.
- At most one `VARIABLE_SET` exists.
- Each `VAR/@id` is unique.
- Each `RULE_SET/@target` points to the root prompt ID.
- Rules are written as standalone obligations.

### Interpreter Checklist

- Variable lookup is by `VAR/@id`.
- Outcome space is exactly `{Approve, Improve}`.
- Output uses exactly one fenced code block.
- No text is emitted outside that code block.

## References

1. W3C, *Extensible Markup Language (XML) 1.0*.
2. W3C, *XML Schema Part 1: Structures*.
3. W3C, *XML Schema Part 2: Datatypes*.
4. Michael Sipser, *Introduction to the Theory of Computation*.
5. Project instructions and prompt examples available in this workspace.

**Specification version:** 1.0
**Last updated:** 2026-04-04
**Status:** Active
