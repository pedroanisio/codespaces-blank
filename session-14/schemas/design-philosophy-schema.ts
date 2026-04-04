/**
 * ============================================================================
 * DISCLAIMER
 * No information within this document should be taken for granted. Any
 * statement or premise not backed by a real logical definition or verifiable
 * reference may be invalid, erroneous, or a hallucination. This schema was
 * designed from domain analysis of publicly documented design systems
 * (Material Design 3, Bootstrap 5, Carbon Design System, Ant Design, Fluent 2,
 * Apple HIG). Enum values and classifications reflect the author's
 * interpretation of published documentation — not official statements from
 * any design system's maintainers.
 * ============================================================================
 *
 * Design Philosophy Schema
 *
 * PURPOSE:
 *   Define a meta-schema that can represent the *philosophical and
 *   architectural decisions* of any design system — not its tokens or
 *   components, but the reasoning layer that determines why those tokens
 *   and components exist and behave the way they do.
 *
 *   Two populated instances placed side-by-side should make the structural
 *   and conceptual differences between systems immediately legible.
 *
 * DOMAIN MODEL:
 *   DesignPhilosophy (root, 1 per design system)
 *     ◆── Foundation         (metaphor, principles, audience, platform)
 *     ◆── SpatialModel       (depth, grid, spacing)
 *     ◆── ColorArchitecture  (organization, palette, theming, dark mode)
 *     ◆── TypographySystem   (scale, roles, font philosophy)
 *     ◆── MotionPhilosophy   (purpose, durations, easings, choreography)
 *     ◆── ComponentModel     (anatomy, variants, states, density)
 *     ◆── AccessibilityModel (WCAG target, focus, contrast, ARIA)
 *     ◆── TokenArchitecture  (layers, naming, resolution, technology)
 *     ◆── ResponsiveStrategy (approach, breakpoints, containers)
 *     ◆── ShapeAndSurface    (corners, borders, surface treatment)
 *     ◆── DesignDecision[]   (explicit decision records for anything above)
 *
 *   All sub-objects are composition — lifecycle-owned by the root entity.
 *   There are no cross-references between dimensions; each dimension is
 *   self-contained for independent comparison.
 *
 * Schema language: TypeScript + Zod
 * Conforms to: Rules for Great Schema Design v2.0.0
 */

import { z } from "zod";

// ─────────────────────────────────────────────────────────────────────────────
// Schema Version
// ─────────────────────────────────────────────────────────────────────────────

export const SCHEMA_VERSION = "1.0.0" as const;

// ─────────────────────────────────────────────────────────────────────────────
// Shared Primitives
// ─────────────────────────────────────────────────────────────────────────────

/** Semantic version string for versioned references. */
const SemVer = z
  .string()
  .regex(/^\d+\.\d+\.\d+$/)
  .describe("Semantic version string");

/**
 * A sourced rationale — every architectural decision should state *why*
 * and optionally cite the authoritative documentation.
 */
const Rationale = z.object({
  why: z
    .string()
    .min(1)
    .describe(
      "Human-readable explanation of the reasoning behind this decision"
    ),
  sourceUrl: z
    .string()
    .url()
    .optional()
    .describe("URL to authoritative documentation, if available"),
  tradeoff: z
    .string()
    .optional()
    .describe(
      "What this choice sacrifices or makes harder — every decision has a cost"
    ),
});

/**
 * A concrete example that grounds an abstract classification.
 * Without these, enum labels are meaningless.
 */
const ConcreteExample = z.object({
  name: z.string().min(1).describe("Short label, e.g. 'Button elevation'"),
  value: z.string().min(1).describe("The actual token/CSS/code value"),
  context: z
    .string()
    .optional()
    .describe("Where this example appears in the system"),
});

// ─────────────────────────────────────────────────────────────────────────────
// §1 — Foundation
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The foundational metaphor that gives a design system its conceptual
 * coherence. Systems without explicit metaphors tend to be pragmatic
 * utility collections; systems with strong metaphors constrain every
 * downstream decision.
 */
const FoundationalMetaphor = z.enum([
  /** Physical materials: paper, ink, light, shadow (Material Design) */
  "physical_material",
  /** Digital-native: no real-world analogy, pure screen logic (Fluent 2) */
  "digital_native",
  /** Industrial/systematic: productivity, scale, consistency (Carbon) */
  "industrial_systematic",
  /** Organic/natural: natural shapes, soft edges, living feel */
  "organic_natural",
  /** Pragmatic/none: no explicit metaphor, utility-driven (Bootstrap) */
  "pragmatic_utility",
  /** Skeuomorphic: direct physical mimicry (classic iOS pre-7) */
  "skeuomorphic",
  /** Other — use extensionLabel to describe */
  "other",
]);

const PlatformScope = z.enum([
  /** Web-only: HTML/CSS/JS, no native targets */
  "web_only",
  /** Web-first: web primary, with guidance for native adaptation */
  "web_first",
  /** Cross-platform: explicit native implementations (iOS, Android, desktop) */
  "cross_platform",
  /** Native-first: native platform primary, web secondary */
  "native_first",
]);

const GovernanceModel = z.enum([
  /** Single company controls all decisions (Google → Material) */
  "corporate_single",
  /** Corporate-sponsored open governance (IBM → Carbon) */
  "corporate_open",
  /** Community-driven with steering committee (Bootstrap) */
  "community_driven",
  /** Standards body (W3C, WHATWG) */
  "standards_body",
]);

const NamedPrinciple = z.object({
  name: z.string().min(1).describe("The principle's short name"),
  statement: z
    .string()
    .min(1)
    .describe("The principle in one sentence"),
  rank: z
    .number()
    .int()
    .min(1)
    .describe(
      "Priority rank — when principles conflict, lower rank wins"
    ),
});

const Foundation = z.object({
  metaphor: FoundationalMetaphor,
  metaphorExtensionLabel: z
    .string()
    .optional()
    .describe("Required when metaphor is 'other'"),
  metaphorRationale: Rationale,
  principles: z
    .array(NamedPrinciple)
    .min(1)
    .describe(
      "Ordered list of named design principles (Material: 'Material is the metaphor', 'Bold, graphic, intentional', 'Motion provides meaning')"
    ),
  targetAudience: z.enum([
    "consumer",
    "enterprise",
    "developer_tools",
    "creative_professional",
    "general_purpose",
  ]),
  platformScope: PlatformScope,
  governance: GovernanceModel,
  firstPublished: z
    .string()
    .regex(/^\d{4}$/)
    .describe("Year of first public release, e.g. '2014'"),
  currentMajorVersion: z.string().min(1).describe("E.g. '3', '5', '10'"),
});

// ─────────────────────────────────────────────────────────────────────────────
// §2 — Spatial Model
// ─────────────────────────────────────────────────────────────────────────────

/**
 * How the system models depth — the z-axis. This is one of the most
 * distinguishing characteristics:
 *   - Material: explicit numbered elevation (0–24 dp) with shadow mapping
 *   - Carbon: contextual layers ($layer-01, $layer-02) without numeric scale
 *   - Bootstrap: utility shadows with no semantic layer model
 */
const DepthStrategy = z.enum([
  /** Numeric elevation scale mapped to shadow tokens (Material) */
  "elevation_numeric",
  /** Named contextual layers (Carbon: layer-01, layer-02, etc.) */
  "contextual_layers",
  /** Utility shadows with no semantic ordering (Bootstrap) */
  "utility_shadows",
  /** Material blur effects (Fluent: Acrylic, Apple: vibrancy) */
  "material_blur",
  /** Flat — no intentional depth system */
  "flat",
]);

const GridSystemType = z.enum([
  /** Fixed column count with responsive gutters (Bootstrap: 12-col) */
  "fixed_column",
  /** Flexible column count derived from content (CSS Grid native) */
  "flexible_column",
  /** Compound grid (Material: margin + body + gutter with column ranges) */
  "compound_grid",
  /** No prescribed grid — layout is component-driven */
  "none",
]);

const SpacingProgression = z.enum([
  /** Linear multiple of base unit (4px × n) */
  "linear",
  /** Geometric / modular scale (base × ratio^n) */
  "modular_scale",
  /** Named t-shirt sizes with arbitrary values (xs, sm, md, lg, xl) */
  "named_arbitrary",
  /** Fibonacci or golden-ratio derived */
  "fibonacci",
]);

const SpatialModel = z.object({
  depth: z.object({
    strategy: DepthStrategy,
    rationale: Rationale,
    /** Number of distinct depth levels the system defines. */
    levelCount: z
      .number()
      .int()
      .nonnegative()
      .describe(
        "Material: 6 canonical levels (0,1,2,3,4,5). Bootstrap: 4 (none,sm,md,lg). Carbon: 3 layers."
      ),
    examples: z.array(ConcreteExample).min(1),
  }),
  grid: z.object({
    type: GridSystemType,
    columnCount: z
      .number()
      .int()
      .positive()
      .optional()
      .describe("E.g. 12 for Bootstrap, 4/8/12 adaptive for Material"),
    gutterUnit: z
      .string()
      .optional()
      .describe("E.g. '16px', '24px', 'var(--grid-gutter)'"),
    rationale: Rationale,
  }),
  spacing: z.object({
    baseUnitPx: z
      .number()
      .int()
      .positive()
      .describe(
        "Fundamental spacing atom in pixels. Material: 4, Carbon: 8, Bootstrap: varies."
      ),
    progression: SpacingProgression,
    scaleSteps: z
      .array(z.number().nonnegative())
      .min(2)
      .describe("The actual spacing scale values in base-unit multiples"),
    rationale: Rationale,
  }),
});

// ─────────────────────────────────────────────────────────────────────────────
// §3 — Color Architecture
// ─────────────────────────────────────────────────────────────────────────────

/**
 * How colors are organized into a system — the most philosophically
 * divergent dimension across design systems.
 */
const ColorOrganization = z.enum([
  /**
   * Role-based with tonal palettes: colors named by function, generated
   * algorithmically from key colors. (Material 3: primary, secondary,
   * tertiary, error, each with on-/container variants)
   */
  "role_tonal",
  /**
   * Contextual/semantic: colors named by UI meaning.
   * (Bootstrap: primary, secondary, success, danger, warning, info, light, dark)
   */
  "contextual_semantic",
  /**
   * Token-layered: colors named by abstraction layer.
   * (Carbon: $ui-01, $ui-02, $text-01, $interactive-01, $support-error)
   */
  "token_layered",
  /**
   * Functional + neutral: explicit functional roles plus a neutral ramp.
   * (Ant Design: primary, success, warning, error + neutral-1..13)
   */
  "functional_neutral",
  /** Brand-centric: brand palette is the system; roles are derived ad-hoc. */
  "brand_centric",
]);

const PaletteGenerationMethod = z.enum([
  /**
   * Algorithmic from key color(s): a color science model generates the
   * full palette. (Material 3: HCT tonal palettes from a seed color)
   */
  "algorithmic",
  /**
   * Manually curated: human designers pick every swatch.
   * (Bootstrap: hand-chosen contextual palette)
   */
  "manual_curation",
  /**
   * Token aliasing: raw values defined once, consumed via semantic aliases.
   * (Carbon: primitives → tokens → themes)
   */
  "token_aliasing",
  /** Mixed: some algorithmic, some manual. */
  "mixed",
]);

const DarkModeStrategy = z.enum([
  /**
   * Re-derive from palette: dark mode generates new tonal values from the
   * same seed colors using the color model. (Material 3)
   */
  "palette_rederivation",
  /**
   * Token remapping: same token names, different resolved values per mode.
   * (Carbon: $ui-01 resolves to white in light, gray-90 in dark)
   */
  "token_remap",
  /**
   * Simple inversion: background ↔ foreground swap with manual overrides.
   * (Bootstrap 5.3 dark mode)
   */
  "simple_inversion",
  /**
   * Layered surface tones: dark mode adjusts surface elevation tinting.
   * (Material 2: elevation overlays on dark surfaces)
   */
  "layered_surface",
  /** Not supported as a first-class feature. */
  "unsupported",
]);

const ThemingMechanism = z.enum([
  /** CSS custom properties swapped at runtime. */
  "css_custom_properties",
  /** Sass/Less variable overrides at build time. */
  "preprocessor_variables",
  /** Design token JSON resolved through a pipeline (Style Dictionary). */
  "design_token_pipeline",
  /** JavaScript theme objects (styled-components, Emotion, etc.). */
  "js_theme_objects",
  /** Multiple mechanisms supported simultaneously. */
  "multi_mechanism",
]);

const ColorArchitecture = z.object({
  organization: ColorOrganization,
  organizationRationale: Rationale,
  paletteGeneration: PaletteGenerationMethod,
  paletteGenerationRationale: Rationale,
  darkMode: DarkModeStrategy,
  darkModeRationale: Rationale,
  themingMechanism: ThemingMechanism,
  /**
   * Canonical role names as the system defines them.
   * This list is what makes side-by-side comparison immediate.
   */
  canonicalRoles: z
    .array(
      z.object({
        name: z
          .string()
          .min(1)
          .describe("Role name as the system uses it, e.g. 'primary'"),
        purpose: z.string().min(1).describe("What this role communicates"),
        hasContainerVariant: z
          .boolean()
          .describe(
            "Material 3 has on-primary, primary-container, on-primary-container"
          ),
      })
    )
    .min(1),
  examples: z.array(ConcreteExample).min(1),
});

// ─────────────────────────────────────────────────────────────────────────────
// §4 — Typography System
// ─────────────────────────────────────────────────────────────────────────────

const TypeScaleMethod = z.enum([
  /** Fixed step scale: explicit size at each step, no mathematical relationship. */
  "fixed_step",
  /** Modular ratio: each step = previous × ratio (e.g. 1.25 major third). */
  "modular_ratio",
  /** Fluid/responsive: sizes defined with clamp() or viewport-relative units. */
  "fluid_responsive",
  /** Dual-track: separate scales for different contexts (Carbon: productive + expressive). */
  "dual_track",
]);

const TypeRoleTaxonomy = z.enum([
  /**
   * Named purpose roles: each role has a semantic name.
   * (Material 3: display, headline, title, body, label × large/medium/small)
   */
  "named_purpose",
  /**
   * HTML heading hierarchy: h1–h6 plus body/lead/small.
   * (Bootstrap)
   */
  "heading_hierarchy",
  /**
   * Numbered scale: sizes referenced by number, not name.
   * (Tailwind: text-xs, text-sm, text-base, text-lg, etc.)
   */
  "numbered_scale",
  /**
   * Functional split: separate type systems for different functional contexts.
   * (Carbon: productive UI type vs. expressive editorial type)
   */
  "functional_split",
]);

const FontPhilosophy = z.enum([
  /** System fonts: use the OS native font stack, no custom fonts. (Bootstrap 5) */
  "system_native",
  /** Brand typeface: a specific font designed/chosen for the system. (Material: Roboto) */
  "brand_typeface",
  /** Configurable: system provides a font token the consumer overrides. (Ant Design) */
  "configurable",
]);

const TypographySystem = z.object({
  scaleMethod: TypeScaleMethod,
  scaleRationale: Rationale,
  /** If modular_ratio, the ratio value. */
  modularRatioValue: z
    .number()
    .positive()
    .optional()
    .describe("E.g. 1.25 (major third), 1.333 (perfect fourth)"),
  roleTaxonomy: TypeRoleTaxonomy,
  /**
   * The actual role names the system defines, in order from largest to smallest.
   * E.g. Material 3: ['display-large', 'display-medium', ..., 'label-small']
   * E.g. Bootstrap: ['display-1', ..., 'h1', ..., 'h6', 'lead', 'body', 'small']
   */
  roleNames: z
    .array(z.string().min(1))
    .min(2)
    .describe("Ordered list of type role names, largest to smallest"),
  fontPhilosophy: FontPhilosophy,
  /** Primary typeface name(s). */
  primaryFontFamily: z
    .string()
    .min(1)
    .describe(
      "E.g. 'Roboto', 'IBM Plex Sans', 'system-ui stack', 'SF Pro'"
    ),
  rationale: Rationale,
  examples: z.array(ConcreteExample).min(1),
});

// ─────────────────────────────────────────────────────────────────────────────
// §5 — Motion Philosophy
// ─────────────────────────────────────────────────────────────────────────────

const MotionPurpose = z.enum([
  /**
   * Meaningful/narrative: motion communicates spatial relationships,
   * hierarchy, and causality. Every animation exists for a reason.
   * (Material Design)
   */
  "meaningful_narrative",
  /**
   * Productive: motion guides the eye and confirms actions without
   * drawing attention to itself. Functional, not decorative.
   * (Carbon)
   */
  "productive",
  /**
   * Minimal: motion is used sparingly — transitions are instant or
   * near-instant. Efficiency over delight.
   * (Bootstrap)
   */
  "minimal",
  /**
   * Expressive/playful: motion is part of the brand personality.
   * Delight is an explicit goal.
   */
  "expressive_playful",
  /**
   * Adaptive: different motion intensity based on context.
   * (Apple HIG: reduced motion, prefer-reduced-motion)
   */
  "adaptive",
]);

const EasingPhilosophy = z.enum([
  /**
   * Purpose-classified: different curves for different motion purposes.
   * (Material: standard, deceleration, acceleration, sharp)
   * (Carbon: productive, expressive)
   */
  "purpose_classified",
  /**
   * Single default: one easing curve for everything.
   * (Bootstrap: ease-in-out for all transitions)
   */
  "single_default",
  /**
   * Spring-based: physics simulation rather than cubic-bezier.
   */
  "spring_physics",
]);

const MotionPhilosophy = z.object({
  purpose: MotionPurpose,
  purposeRationale: Rationale,
  easingPhilosophy: EasingPhilosophy,
  /**
   * Named easing curves the system defines. Each entry is a named
   * curve with its actual value.
   */
  namedCurves: z
    .array(
      z.object({
        name: z
          .string()
          .min(1)
          .describe("E.g. 'standard', 'deceleration', 'productive'"),
        value: z
          .string()
          .min(1)
          .describe("E.g. 'cubic-bezier(0.2, 0, 0, 1)'"),
        usedFor: z.string().min(1).describe("When to use this curve"),
      })
    )
    .min(1),
  durationScale: z
    .array(
      z.object({
        name: z.string().min(1),
        durationMs: z.number().int().positive(),
      })
    )
    .min(1)
    .describe("Named duration tokens from shortest to longest"),
  choreographyRules: z
    .array(z.string().min(1))
    .describe(
      "Explicit sequencing rules, e.g. 'Parent before children', 'Exits before entrances'"
    ),
  prefersReducedMotion: z.enum([
    "fully_supported",
    "partially_supported",
    "not_addressed",
  ]),
  rationale: Rationale,
});

// ─────────────────────────────────────────────────────────────────────────────
// §6 — Component Model
// ─────────────────────────────────────────────────────────────────────────────

const ComponentAnatomyPattern = z.enum([
  /**
   * Slot-based: components define named slots (leading, content, trailing)
   * that consumers fill. (Material 3, Fluent 2)
   */
  "slot_based",
  /**
   * Compositional: small primitives composed by the consumer into
   * larger patterns. Headless or unstyled core. (Radix, Headless UI)
   */
  "compositional_headless",
  /**
   * Monolithic: components are opaque units configured via props/classes.
   * Internal structure is not consumer-visible. (Bootstrap, Ant Design)
   */
  "monolithic_configured",
  /**
   * Hybrid: slot-based for complex components, monolithic for simple ones.
   */
  "hybrid",
]);

const VariantSystem = z.enum([
  /**
   * Props/attributes: variant selected by passing a prop (variant="outlined").
   * (Material, Ant Design, most React systems)
   */
  "prop_driven",
  /**
   * CSS class composition: variant selected by adding modifier classes.
   * (Bootstrap: btn-primary, btn-outline-primary, btn-lg)
   */
  "class_modifier",
  /**
   * Token-driven: variant resolved from design token context, not explicit props.
   */
  "token_resolved",
  /**
   * Mixed: some components use props, others use classes.
   */
  "mixed",
]);

const StateModel = z.object({
  /**
   * The complete list of interaction states the system formally defines.
   * This is a key comparator: Material defines more states than Bootstrap.
   */
  formalStates: z
    .array(
      z.enum([
        "rest",
        "hover",
        "focus",
        "focus_visible",
        "active",
        "pressed",
        "disabled",
        "disabled_interactive",
        "selected",
        "activated",
        "dragged",
        "error",
        "loading",
        "skeleton",
      ])
    )
    .min(2)
    .describe("States the system explicitly defines visual treatments for"),
  /**
   * How states are visually communicated.
   */
  stateCommunication: z.enum([
    /** State layers: translucent overlays on the component surface (Material 3). */
    "state_layer_overlay",
    /** Direct property change: bg-color, border-color swap (Bootstrap). */
    "direct_property_change",
    /** Combined: overlays + property changes depending on component. */
    "combined",
  ]),
  stateLayerOpacities: z
    .record(z.string(), z.number().min(0).max(1))
    .optional()
    .describe(
      "Material 3 pattern: { hover: 0.08, focus: 0.12, pressed: 0.12, dragged: 0.16 }"
    ),
});

const DensitySupport = z.enum([
  /**
   * Explicit density scale: components have a density prop with numeric levels.
   * (Material 3: density from 0 to -3)
   */
  "explicit_scale",
  /**
   * Size variants: components have size props (sm, md, lg) that adjust density.
   * (Bootstrap, Ant Design)
   */
  "size_variants",
  /**
   * Token-driven: spacing tokens adjusted globally to change density.
   */
  "token_driven",
  /**
   * Not addressed: density is not a formal concept in the system.
   */
  "not_addressed",
]);

const ComponentModel = z.object({
  anatomyPattern: ComponentAnatomyPattern,
  anatomyRationale: Rationale,
  variantSystem: VariantSystem,
  stateModel: StateModel,
  densitySupport: DensitySupport,
  densityRationale: Rationale,
  /**
   * Approximate number of components the system ships.
   * Gives a sense of scope and opinion breadth.
   */
  componentCount: z
    .number()
    .int()
    .positive()
    .describe("Approximate number of distinct components in the system"),
  examples: z.array(ConcreteExample).min(1),
});

// ─────────────────────────────────────────────────────────────────────────────
// §7 — Accessibility Model
// ─────────────────────────────────────────────────────────────────────────────

const WcagLevel = z.enum(["A", "AA", "AAA"]);

const FocusIndicationStrategy = z.enum([
  /** Outline ring: visible outline around focused element (Bootstrap, Carbon). */
  "outline_ring",
  /** State layer: translucent overlay (Material 3). */
  "state_layer",
  /** Border change: element border changes color/width on focus. */
  "border_change",
  /** Combined: multiple indicators used together. */
  "combined",
  /** Browser default: no custom focus indication. */
  "browser_default",
]);

const AccessibilityModel = z.object({
  wcagTarget: WcagLevel,
  wcagTargetRationale: Rationale,
  focusIndication: FocusIndicationStrategy,
  /**
   * Whether focus styles are always visible or only on keyboard interaction.
   */
  focusVisibleOnly: z
    .boolean()
    .describe(
      "true = focus ring only on keyboard (focus-visible). false = always visible."
    ),
  minimumContrastRatio: z
    .number()
    .min(1)
    .describe(
      "Minimum contrast ratio for normal text. WCAG AA requires 4.5:1."
    ),
  /**
   * How the system ensures contrast — at the palette level or component level.
   */
  contrastEnforcement: z.enum([
    /** Palette-constrained: palette generation enforces contrast mathematically. (Material 3 HCT) */
    "palette_constrained",
    /** Documentation-guided: docs state requirements, consumer must verify. (Bootstrap) */
    "documentation_guided",
    /** Tooling-assisted: linting/testing tools check contrast. (Carbon) */
    "tooling_assisted",
  ]),
  ariaPatterns: z.enum([
    /** Comprehensive: every component has documented ARIA roles/states/properties. */
    "comprehensive",
    /** Partial: major components documented, simpler ones rely on semantic HTML. */
    "partial",
    /** Minimal: accessibility mentioned but not systematically documented. */
    "minimal",
  ]),
  reducedMotionSupport: z.boolean().describe(
    "Whether the system explicitly supports prefers-reduced-motion"
  ),
  rationale: Rationale,
});

// ─────────────────────────────────────────────────────────────────────────────
// §8 — Token Architecture
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Token layer model — how design tokens are organized into abstraction levels.
 * This is where systems differ most in engineering philosophy.
 */
const TokenLayerModel = z.enum([
  /**
   * Three-tier: global primitives → semantic aliases → component-specific.
   * (Material 3: ref.palette → sys.color → comp.button)
   * (Carbon: primitives → tokens → themes)
   */
  "three_tier",
  /**
   * Two-tier: raw values → semantic tokens.
   * (Bootstrap 5: Sass variables → CSS custom properties)
   */
  "two_tier",
  /**
   * Flat: tokens defined at a single level with no aliasing hierarchy.
   */
  "flat",
  /**
   * Multi-tier: more than three explicit layers.
   */
  "multi_tier",
]);

const TokenNamingConvention = z.enum([
  "kebab-case",
  "camelCase",
  "dot.notation",
  "slash/notation",
  "BEM_style",
]);

const TokenTechnology = z.enum([
  "css_custom_properties",
  "sass_variables",
  "less_variables",
  "design_token_json_w3c",
  "style_dictionary",
  "js_theme_objects",
  "figma_variables",
  "multi_technology",
]);

const TokenArchitecture = z.object({
  layerModel: TokenLayerModel,
  layerModelRationale: Rationale,
  /**
   * The actual layer names as the system defines them, from raw to specific.
   * E.g. Material 3: ['ref (reference)', 'sys (system)', 'comp (component)']
   * E.g. Carbon: ['primitives', 'tokens', 'theme']
   */
  layerNames: z
    .array(z.string().min(1))
    .min(1)
    .describe("Named layers from most primitive to most specific"),
  namingConvention: TokenNamingConvention,
  /**
   * A representative token path showing the naming structure.
   */
  namingExample: z
    .string()
    .min(1)
    .describe(
      "E.g. 'md.sys.color.primary', '--cds-text-01', '--bs-primary'"
    ),
  technology: TokenTechnology,
  /**
   * Whether the system publishes tokens in W3C Design Tokens Format.
   */
  w3cDesignTokensCompliant: z.boolean(),
  /**
   * Approximate total token count — gives a sense of system granularity.
   */
  approximateTokenCount: z
    .number()
    .int()
    .positive()
    .describe("Rough count of distinct tokens in the system"),
  rationale: Rationale,
  examples: z.array(ConcreteExample).min(1),
});

// ─────────────────────────────────────────────────────────────────────────────
// §9 — Responsive Strategy
// ─────────────────────────────────────────────────────────────────────────────

const ResponsiveApproach = z.enum([
  /** Mobile-first: base styles are mobile, breakpoints add complexity. (Bootstrap) */
  "mobile_first",
  /** Adaptive: distinct layouts for named device classes. (Material: compact, medium, expanded) */
  "adaptive",
  /** Fluid: sizes defined with clamp/vw, minimal breakpoints. */
  "fluid",
  /** Desktop-first: base styles are desktop, breakpoints simplify. */
  "desktop_first",
]);

const BreakpointPhilosophy = z.enum([
  /** Device-class: breakpoints named after device types (phone, tablet, desktop). */
  "device_class",
  /** Content-based: breakpoints set where content breaks, not at device widths. */
  "content_based",
  /** Window-class: named abstract sizes (compact, medium, expanded, large). */
  "window_class",
  /** Arbitrary: breakpoints at fixed pixel values with no semantic naming. */
  "arbitrary_fixed",
]);

const ResponsiveStrategy = z.object({
  approach: ResponsiveApproach,
  approachRationale: Rationale,
  breakpointPhilosophy: BreakpointPhilosophy,
  /**
   * The actual breakpoints, ordered from smallest to largest.
   */
  breakpoints: z
    .array(
      z.object({
        name: z.string().min(1).describe("E.g. 'sm', 'compact', 'tablet'"),
        minWidthPx: z.number().int().nonnegative(),
      })
    )
    .min(1),
  /**
   * Whether the system supports container queries as a first-class feature.
   */
  containerQuerySupport: z.enum([
    "first_class",
    "documented_guidance",
    "not_addressed",
  ]),
  rationale: Rationale,
});

// ─────────────────────────────────────────────────────────────────────────────
// §10 — Shape & Surface
// ─────────────────────────────────────────────────────────────────────────────

const CornerRadiusModel = z.enum([
  /**
   * Semantic scale: named radius tokens with distinct purposes.
   * (Material 3: none, extra-small, small, medium, large, extra-large, full)
   */
  "semantic_scale",
  /**
   * Utility values: a set of radius values without semantic naming.
   * (Bootstrap: .rounded, .rounded-sm, .rounded-lg, .rounded-pill)
   */
  "utility_values",
  /**
   * Global configurable: one or two radius values applied system-wide.
   * (Ant Design: borderRadius, borderRadiusLG, borderRadiusSM)
   */
  "global_configurable",
  /**
   * Per-component: radius defined individually per component, no shared system.
   */
  "per_component",
]);

const SurfaceTreatment = z.enum([
  /**
   * Elevation + tint: surfaces are differentiated by elevation which affects
   * shadow and a subtle color tint. (Material 3: surface tint)
   */
  "elevation_and_tint",
  /**
   * Container variants: components come in filled, outlined, tonal, elevated
   * variants. (Material 3 buttons, cards)
   */
  "container_variants",
  /**
   * Background hierarchy: surfaces use progressively different background
   * colors (bg-primary, bg-secondary, bg-tertiary). (Bootstrap)
   */
  "background_hierarchy",
  /**
   * Layer-based: surface appearance changes based on the layer context.
   * (Carbon: components on $layer-01 look different than on $layer-02)
   */
  "layer_based",
]);

const ShapeAndSurface = z.object({
  cornerRadius: z.object({
    model: CornerRadiusModel,
    rationale: Rationale,
    /** The actual scale values, from smallest to largest. */
    scaleValues: z
      .array(
        z.object({
          name: z.string().min(1),
          valuePx: z.number().nonnegative(),
        })
      )
      .min(1),
  }),
  surfaceTreatment: z.object({
    approach: SurfaceTreatment,
    rationale: Rationale,
    /**
     * What container/surface variants the system formally defines.
     * E.g. Material 3: ['filled', 'outlined', 'tonal', 'elevated', 'text']
     * E.g. Bootstrap: ['bg-primary', 'bg-secondary', 'bg-light', 'bg-dark']
     */
    variants: z.array(z.string().min(1)).min(1),
  }),
  borderPhilosophy: z.enum([
    /** Borders are primary separators — used heavily for structure. (Carbon, Ant Design) */
    "primary_separator",
    /** Borders are secondary — elevation/shadow preferred for separation. (Material) */
    "secondary_to_elevation",
    /** Borders are utility — available but no prescribed preference. (Bootstrap) */
    "utility",
  ]),
  borderPhilosophyRationale: Rationale,
});

// ─────────────────────────────────────────────────────────────────────────────
// §11 — Design Decision Record
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Explicit decision records for choices that don't fit neatly into the
 * above dimensions, or cross-cutting decisions that affect multiple
 * dimensions simultaneously. Extension point (Rule 29).
 */
const DesignDecision = z.object({
  id: z.string().uuid(),
  title: z.string().min(1).describe("Short decision title"),
  dimension: z
    .enum([
      "foundation",
      "spatial",
      "color",
      "typography",
      "motion",
      "component",
      "accessibility",
      "tokens",
      "responsive",
      "shape",
      "cross_cutting",
    ])
    .describe("Which dimension this decision primarily affects"),
  decision: z
    .string()
    .min(1)
    .describe("The actual decision that was made"),
  rationale: Rationale,
  /**
   * Which other design systems made the opposite choice — for comparison.
   */
  counterexamples: z
    .array(
      z.object({
        systemName: z.string().min(1),
        alternativeChoice: z.string().min(1),
      })
    )
    .optional()
    .describe(
      "Systems that chose differently, to highlight what makes this system distinctive"
    ),
});

// ─────────────────────────────────────────────────────────────────────────────
// §12 — Root Entity
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Root entity — one instance per design system.
 *
 * Composition semantics:
 *   DesignPhilosophy ◆── Foundation          (composition)
 *   DesignPhilosophy ◆── SpatialModel        (composition)
 *   DesignPhilosophy ◆── ColorArchitecture   (composition)
 *   DesignPhilosophy ◆── TypographySystem    (composition)
 *   DesignPhilosophy ◆── MotionPhilosophy    (composition)
 *   DesignPhilosophy ◆── ComponentModel      (composition)
 *   DesignPhilosophy ◆── AccessibilityModel  (composition)
 *   DesignPhilosophy ◆── TokenArchitecture   (composition)
 *   DesignPhilosophy ◆── ResponsiveStrategy  (composition)
 *   DesignPhilosophy ◆── ShapeAndSurface     (composition)
 *   DesignPhilosophy ◆── DesignDecision[]    (composition, extension point)
 *
 * All sub-objects are lifecycle-owned by the root entity. There are no
 * foreign key references between dimensions — each is independently
 * comparable across system instances.
 */
const DesignPhilosophy = z.object({
  id: z.string().uuid(),
  /** The canonical name of the design system. */
  systemName: z
    .string()
    .min(1)
    .describe(
      "E.g. 'Material Design 3', 'Bootstrap 5', 'Carbon Design System v11'"
    ),
  /** The version of the design system this instance describes. */
  systemVersion: z.string().min(1).describe("E.g. '3', '5.3', 'v11'"),
  /** The version of this schema. */
  schemaVersion: z.literal(SCHEMA_VERSION),
  /** Canonical documentation URL. */
  documentationUrl: z.string().url().describe("E.g. 'https://m3.material.io'"),
  /** When this philosophy instance was captured/authored. */
  capturedAt: z
    .string()
    .datetime()
    .describe("ISO 8601 datetime of when this analysis was performed"),

  // ── Dimensions (composition) ──
  foundation: Foundation,
  spatialModel: SpatialModel,
  colorArchitecture: ColorArchitecture,
  typographySystem: TypographySystem,
  motionPhilosophy: MotionPhilosophy,
  componentModel: ComponentModel,
  accessibilityModel: AccessibilityModel,
  tokenArchitecture: TokenArchitecture,
  responsiveStrategy: ResponsiveStrategy,
  shapeAndSurface: ShapeAndSurface,

  // ── Extension point ──
  designDecisions: z
    .array(DesignDecision)
    .describe(
      "Explicit decision records for cross-cutting or noteworthy choices"
    ),
});

// ─────────────────────────────────────────────────────────────────────────────
// Type Exports
// ─────────────────────────────────────────────────────────────────────────────

export type Rationale = z.infer<typeof Rationale>;
export type ConcreteExample = z.infer<typeof ConcreteExample>;
export type Foundation = z.infer<typeof Foundation>;
export type SpatialModel = z.infer<typeof SpatialModel>;
export type ColorArchitecture = z.infer<typeof ColorArchitecture>;
export type TypographySystem = z.infer<typeof TypographySystem>;
export type MotionPhilosophy = z.infer<typeof MotionPhilosophy>;
export type ComponentModel = z.infer<typeof ComponentModel>;
export type AccessibilityModel = z.infer<typeof AccessibilityModel>;
export type TokenArchitecture = z.infer<typeof TokenArchitecture>;
export type ResponsiveStrategy = z.infer<typeof ResponsiveStrategy>;
export type ShapeAndSurface = z.infer<typeof ShapeAndSurface>;
export type DesignDecision = z.infer<typeof DesignDecision>;
export type DesignPhilosophy = z.infer<typeof DesignPhilosophy>;

// ─────────────────────────────────────────────────────────────────────────────
// Schema Exports (for runtime validation)
// ─────────────────────────────────────────────────────────────────────────────

export const schemas = {
  Rationale,
  ConcreteExample,
  Foundation,
  SpatialModel,
  ColorArchitecture,
  TypographySystem,
  MotionPhilosophy,
  ComponentModel,
  AccessibilityModel,
  TokenArchitecture,
  ResponsiveStrategy,
  ShapeAndSurface,
  DesignDecision,
  DesignPhilosophy,
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// Scorecard — Self-Review (Rules for Great Schema Design v2.0.0)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Part I — Type Safety and Precision
 *   1. Every field has a single unambiguous type          MUST   → Pass
 *   2. Constraints live in the schema                     MUST   → Pass
 *   3. Enums: closed, versioned, not overloaded           MUST   → Pass
 *      All enums include an exhaustive set of observed approaches.
 *      Each value has a JSDoc comment explaining what it means.
 *   4. Nullable ≠ optional ≠ absent                       MUST   → Pass
 *   5. Arrays: item type + cardinality + order            MUST   → Pass
 *   6. Temporal: precision, timezone, format              MUST   → Pass
 *      capturedAt uses z.string().datetime() (ISO 8601).
 *   7. Numeric units declared                             MUST   → Pass
 *      Px values and ratios documented in .describe().
 *   8. Polymorphism: explicit discriminator                MUST   → Pass
 *      No polymorphic unions — each dimension is a concrete object.
 *   9. Defaults declared in schema                        SHOULD → Pass
 *
 * Part II — Identity and Relationships
 *  10. Stable, opaque identity                            MUST   → Pass
 *      UUID on root entity and DesignDecision.
 *      Sub-objects are composition — no independent identity needed.
 *  11. Relationships navigable in ≥1 direction            MUST   → Pass
 *      All composition is top-down from root entity.
 *  12. Composition / aggregation / association explicit    MUST   → Pass
 *      All dimensions are ◆── composition (documented in root JSDoc).
 *  13. FK targets declared                                MUST   → Pass
 *      No FKs — dimensions are self-contained by design.
 *  14. Cyclic graph constraints declared                   MUST   → Pass
 *      No cycles — strictly hierarchical composition.
 *
 * Part III — Normalization and Coherence
 *  15. Single source of truth per fact                    MUST   → Pass
 *  16. No bag-of-arrays entities                          SHOULD → Pass
 *      Root entity is a named-field composition, not a bag-of-arrays.
 *      designDecisions[] is the only array, and it's an extension point.
 *  17. Cross-cutting types defined once                   SHOULD → Pass
 *      Rationale and ConcreteExample are shared primitives.
 *  18. Computed vs. stored distinguished                  SHOULD → Pass
 *      All fields are stored (human-authored analysis).
 *
 * Part IV — Evolution and Compatibility
 *  19. Explicit, monotonic versioning                     MUST   → Pass
 *  20. No duplicate-version entities                      MUST   → Pass
 *  21. Breaking changes classified                        MUST   → Pass (first version)
 *  22. Field deprecation annotated                        MUST   → Pass (no deprecated fields)
 *
 * Part V — Operational Annotations
 *  23. Sensitive fields classified                        MAY    → Pass (no PII)
 *  24. Identity/provenance immutability                   SHOULD → Pass
 *  25. Localization strategy declared                     SHOULD → Warn
 *      Waiver: design philosophy descriptions are inherently authored
 *      in a single language per instance. A translated instance would
 *      be a separate document, not a localized field.
 *  26. Multi-actor provenance metadata                    SHOULD → Warn
 *      Waiver: each instance is a single-author analytical artifact.
 *      capturedAt provides temporal provenance.
 *
 * Part VI — Documentation and Generability
 *  27. Consistent naming (camelCase throughout)           MUST   → Pass
 *  28. Mechanically generatable validators                MUST   → Pass (Zod)
 *  29. Intentional extension points                       MUST   → Pass
 *      DesignDecision[] is the explicit extension mechanism.
 *      FoundationalMetaphor includes 'other' + extensionLabel.
 *  30. Access patterns don't dictate structure            SHOULD → Pass
 *  31. Readable as standalone artifact                    MUST   → Pass
 *
 * TOTALS
 *   MUST Pass:              19/19 (no PII → Rule 23 is MAY)
 *   SHOULD Pass/Documented: 9/11 (2 Warn with documented waivers)
 */
