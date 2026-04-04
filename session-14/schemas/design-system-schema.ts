/**
 * ============================================================================
 * DISCLAIMER
 * No information within this document should be taken for granted. Any
 * statement or premise not backed by a real logical definition or verifiable
 * reference may be invalid, erroneous, or a hallucination. This schema was
 * reverse-engineered from a single HTML snapshot and screenshot of the
 * Claude.ai interface. It is an approximation — not an authoritative source.
 * ============================================================================
 *
 * Design System Schema — Claude.ai (Reverse-Engineered)
 *   Revision 2.1.0 — PALS's Law verification infrastructure.
 *
 * Source material:
 *   - HTML snapshot of claude.ai (build c54235956b, 2026-04-02)
 *   - Screenshot of the home/chat-input view
 *
 * What changed from v1 → v2:
 *   1. Conditional token resolution layer (replaces bare FK strings)
 *   2. Responsive adaptation rules (breakpoints → behavioral changes)
 *   3. Slot/composition model on component definitions
 *   4. Interaction state-machine topology (events, transitions, guards)
 *   5. Scope declaration + component manifest (modeled vs. known-unmodeled)
 *   6. Six additional component definitions (MessageBubble, CodeBlock,
 *      ToastNotification, ModalDialog, DropdownMenu, Tooltip)
 *
 * What changed from v2 → v2.1:
 *   7. PALS's Law 9-class error taxonomy as schema-level enum
 *   8. MutationSource (provenance tracking, LLM model version)
 *   9. VerificationBoundary (per-mutation verification scope declaration)
 *  10. Semantic validation rule types (13 domain-specific checks)
 *  11. CompletenessAssertion (ERR_OMISSION detection)
 *  12. VerificationAuditEntry (append-only verification log)
 *  13. SnapshotVerificationDeclaration (publish-time verification gate)
 *  14. VerificationConfig on DesignSystem root (policy enforcement)
 *
 * Schema language: TypeScript + Zod
 * Conforms to: Rules for Great Schema Design v2.0.0
 */

import { z } from "zod";

// ─────────────────────────────────────────────────────────────────────────────
// Schema Version
// ─────────────────────────────────────────────────────────────────────────────

export const SCHEMA_VERSION = "2.1.0" as const;

// ─────────────────────────────────────────────────────────────────────────────
// Part A — Shared Primitives
// ─────────────────────────────────────────────────────────────────────────────

/**
 * A CSS custom-property reference, always of the form `--<namespace>-<token>`.
 * At runtime, resolved via `hsl(var(...))` or `var(...)`.
 */
const CSSVariableRef = z
  .string()
  .regex(/^--[a-z][a-z0-9]*(-[a-z0-9]+)*$/)
  .describe("CSS custom property name, e.g. '--bg-100'");

/** HSL channel triple as stored in CSS variables (no `hsl()` wrapper). */
const HSLChannels = z
  .string()
  .regex(/^\d{1,3},\s*[\d.]+%,\s*[\d.]+%$/)
  .describe("HSL channels: 'H, S%, L%'");

/** An opaque hex color for fallback or static use. */
const HexColor = z
  .string()
  .regex(/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/)
  .describe("Hex color value");

/** A non-negative number representing pixels unless another unit is given. */
const Px = z.number().nonnegative().describe("Value in pixels");

/** A non-negative number representing rem units. */
const Rem = z.number().nonnegative().describe("Value in rem");

/** Duration in milliseconds. */
const DurationMs = z
  .number()
  .int()
  .nonnegative()
  .describe("Duration in milliseconds");

/** Semantic version string. */
const SemVer = z
  .string()
  .regex(/^\d+\.\d+\.\d+$/)
  .describe("Semantic version string");

/** Opaque UUID used as identity on all entities. */
const EntityId = z.string().uuid().describe("Opaque unique identifier");

/** FK reference to another entity's id field. */
const TokenRef = z.string().uuid().describe("FK → token or entity ID");

// ─────────────────────────────────────────────────────────────────────────────
// Part B — Theme & Color Tokens
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The observed Claude.ai color system uses semantic CSS variables following
 * the pattern `--<role>-<scale>`.
 *
 * Roles observed: bg, text, border, accent
 * Each role has a numeric scale where lower = more prominent / darker in
 * light mode.
 */

const ColorRole = z.enum([
  "bg",
  "text",
  "border",
  "accent",
  "always", // e.g. --always-black — theme-invariant colors
]);

const ColorScaleLevel = z.enum([
  "000",
  "100",
  "200",
  "300",
  "400",
  "500",
  "brand",
]);

/**
 * A single design token mapping a semantic name to its resolved HSL channels.
 *
 * Observed tokens from the HTML source:
 *   bg:     000, 100, 200, 300
 *   text:   000, 100, 200, 300, 400, 500
 *   border: 200, 300
 *   accent: 100, brand
 *   always: black
 */
const ColorToken = z.object({
  id: EntityId,
  variableName: CSSVariableRef.describe("CSS variable name, e.g. '--bg-100'"),
  role: ColorRole,
  scale: ColorScaleLevel,
  hslChannels: HSLChannels.describe(
    "Raw HSL channel values stored in the CSS variable"
  ),
  description: z
    .string()
    .min(1)
    .optional()
    .describe("Human-readable purpose of this token"),
});

const ThemeMode = z
  .enum(["light", "dark"])
  .describe("Observed from data-mode attribute on <html>");

/**
 * A theme is a complete assignment of HSL values to every token for a given
 * mode. The HTML uses `data-theme='claude'` and `data-mode='light'`.
 */
const Theme = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Theme name; observed value: 'claude'"),
  mode: ThemeMode,
  /** Association: Theme →* ColorToken. Every token gets a mode-specific value. */
  tokenOverrides: z
    .array(
      z.object({
        tokenId: TokenRef.describe("FK → ColorToken.id"),
        hslChannels: HSLChannels,
      })
    )
    .min(1)
    .describe("At least one token override must be defined"),
  themeColor: HexColor.optional().describe(
    "Value for <meta name='theme-color'>. Observed: hsl(53,28.6%,94.5%)"
  ),
});

// ─────────────────────────────────────────────────────────────────────────────
// Part C — Typography
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Font families observed:
 *   font-ui   — system UI stack for interface elements
 *   font-display — display/heading font (used in "Good morning, Pedro")
 *
 * Preloaded WOFF2 files suggest two custom typefaces are used.
 */
const FontFamily = z
  .enum(["ui", "display"])
  .describe("Semantic font family token");

const FontWeight = z
  .enum(["regular", "medium", "semibold", "bold"])
  .describe("Observed font weight classes");

/**
 * Typography size tokens observed from CSS classes:
 *   font-small, font-base, font-large, and clamp()-based display sizes.
 */
const TypographyScale = z.enum([
  "xs", //      text-xs: ~0.65rem–0.75rem
  "small", //   font-small: ~0.8125rem
  "base", //    font-base: ~0.875rem
  "large", //   font-large: ~1rem
  "display", // clamp(1.875rem, 1.2rem + 2vw, 2.5rem)
]);

const TypographyToken = z.object({
  id: EntityId,
  scale: TypographyScale,
  fontFamily: FontFamily,
  fontSize: z
    .union([
      Rem,
      z.object({
        clampMin: Rem,
        clampPreferred: z
          .string()
          .describe("CSS clamp preferred expression"),
        clampMax: Rem,
      }),
    ])
    .describe("Fixed rem value or fluid clamp() definition"),
  lineHeight: z.number().positive().describe("Unitless line-height ratio"),
  fontWeight: FontWeight,
  letterSpacing: Rem.optional().describe(
    "Letter spacing in rem, if non-default"
  ),
});

// Font asset (preloaded WOFF2 files)
const FontAsset = z.object({
  id: EntityId,
  family: FontFamily,
  weight: FontWeight,
  format: z.literal("woff2"),
  url: z.string().url().describe("CDN URL for the font file"),
  preload: z.boolean().default(true),
});

// ─────────────────────────────────────────────────────────────────────────────
// Part D — Spacing, Borders, Radii
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Spacing scale observed (in Tailwind-style increments):
 * 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 6, 7, 8, etc.
 * Unit: 1 = 0.25rem = 4px at default root font size.
 */
const SpacingToken = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Token name, e.g. 'spacing-2'"),
  /** Value in Tailwind spacing units (1 unit = 0.25rem). */
  value: z
    .number()
    .nonnegative()
    .describe("Value in spacing units (1 unit = 0.25rem)"),
});

const BorderWidthToken = z.object({
  id: EntityId,
  name: z.string().min(1),
  /** Observed: 0.5px (border-0.5), 1px */
  valuePx: Px.describe("Border width in pixels"),
});

const BorderRadiusToken = z.object({
  id: EntityId,
  name: z.string().min(1),
  value: z
    .union([
      Px,
      z.literal("full"), // 9999px — pills and circles
    ])
    .describe("Radius in px or 'full' for circular"),
});

// ─────────────────────────────────────────────────────────────────────────────
// Part E — Shadows & Elevation
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Claude.ai uses multi-layer box-shadow definitions with theme-aware colors.
 * Observed patterns include separate layers for ambient and key light, plus
 * an inset ring (0 0 0 0.5px) simulating a subtle border.
 */
const ShadowLayer = z.object({
  offsetX: Px.default(0),
  offsetY: Px,
  blur: Px,
  spread: Px.default(0),
  color: z
    .string()
    .describe(
      "CSS color expression, may reference CSS variables via hsl(var(...))"
    ),
  inset: z.boolean().default(false),
});

const ShadowToken = z.object({
  id: EntityId,
  name: z
    .string()
    .min(1)
    .describe("E.g. 'input-rest', 'input-hover', 'input-focus'"),
  layers: z
    .array(ShadowLayer)
    .min(1)
    .describe("Ordered list of shadow layers (first = topmost)"),
});

// ─────────────────────────────────────────────────────────────────────────────
// Part F — Transitions & Animations
// ─────────────────────────────────────────────────────────────────────────────

const EasingFunction = z
  .enum([
    "ease",
    "ease-in",
    "ease-out",
    "ease-in-out",
    "linear",
    "snappy-out", // custom: used on icon animations
    "cubic-bezier",
  ])
  .describe("Named easing function");

const TransitionToken = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Semantic name, e.g. 'button-hover'"),
  properties: z
    .array(z.string().min(1))
    .min(1)
    .describe("CSS properties to transition"),
  durationMs: DurationMs.describe("Observed values: 35, 75, 150, 200, 300ms"),
  easing: z.union([
    EasingFunction,
    z
      .object({
        type: z.literal("cubic-bezier"),
        values: z.tuple([z.number(), z.number(), z.number(), z.number()]),
      })
      .describe("Observed: cubic-bezier(0.165, 0.85, 0.45, 1)"),
  ]),
  delay: DurationMs.default(0),
});

const KeyframeStep = z.object({
  offset: z.number().min(0).max(1).describe("0 = 0%, 1 = 100%"),
  properties: z
    .record(z.string(), z.string())
    .describe("CSS property → value at this keyframe offset"),
});

const AnimationToken = z.object({
  id: EntityId,
  name: z
    .string()
    .min(1)
    .describe("Keyframe animation name, e.g. 'look-around', 'ping'"),
  keyframes: z.array(KeyframeStep).min(2),
  durationMs: DurationMs,
  iterationCount: z.union([z.number().int().positive(), z.literal("infinite")]),
  timingFunction: EasingFunction.default("ease-in-out"),
});

// ─────────────────────────────────────────────────────────────────────────────
// Part G — Icons
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Claude.ai uses inline SVGs with `fill='currentColor'` and consistent
 * viewBox dimensions. Most interface icons use 20×20, some use 16×16.
 */
const IconSize = z
  .enum(["12", "14", "16", "20"])
  .describe("Icon canvas size in px. Observed: 12, 14, 16, 20");

const Icon = z.object({
  id: EntityId,
  name: z
    .string()
    .min(1)
    .describe("Semantic icon name, e.g. 'plus', 'search', 'sidebar-toggle'"),
  viewBox: z
    .string()
    .regex(/^0 0 \d+ \d+$/)
    .describe("SVG viewBox attribute"),
  /** The raw SVG path data (one or more <path> elements). */
  paths: z
    .array(
      z.object({
        d: z.string().min(1).describe("SVG path data"),
        fillRule: z.enum(["nonzero", "evenodd"]).optional(),
        clipRule: z.enum(["nonzero", "evenodd"]).optional(),
        /** Some paths have hover/transition classes for micro-interactions. */
        animationClass: z
          .string()
          .optional()
          .describe("CSS class controlling hover micro-animation on this path"),
      })
    )
    .min(1),
  defaultSize: IconSize.default("20"),
  /** Icons inherit color via `fill='currentColor'`. */
  colorMode: z.literal("currentColor").default("currentColor"),
});

// ─────────────────────────────────────────────────────────────────────────────
// Part H — Component Infrastructure  [NEW in v2]
// ─────────────────────────────────────────────────────────────────────────────

/**
 * H.1  Component Type Registry
 *
 * A closed enum of every component type the schema recognizes, whether or not
 * a full definition exists. This is the single source of truth for component
 * type names used in slots, manifests, and responsive rules.
 */
const ComponentTypeName = z.enum([
  // ── Modeled (full Zod definition exists) ──
  "Button",
  "SidebarItem",
  "ChatInput",
  "Avatar",
  "ModelSelector",
  "QuickActionChip",
  "UsageBanner",
  "MessageBubble",
  "CodeBlock",
  "ToastNotification",
  "ModalDialog",
  "DropdownMenu",
  "Tooltip",
  // ── Known-unmodeled (observed but not yet defined) ──
  "FileAttachmentCard",
  "LoadingSkeleton",
  "DownloadsPanel",
  "ProjectCard",
  "StarredItemsGroup",
  "SearchOverlay",
  "ContextMenu",
  "SettingsPanel",
]);

/**
 * H.2  Slot Model — Composition & Containment
 *
 * A slot is a typed insertion point on a component. It declares what child
 * component types may be placed there, whether the slot is required, and
 * its spatial position within the parent.
 *
 * Example: ChatInput has a 'trailing-actions' slot that accepts Buttons.
 */
const SlotPosition = z.enum([
  "leading",
  "trailing",
  "content",
  "overlay",
  "header",
  "footer",
  "inline",
]);

const ComponentSlot = z.object({
  name: z
    .string()
    .min(1)
    .describe("Slot name, e.g. 'trailing-actions', 'icon'"),
  position: SlotPosition,
  allowedChildTypes: z
    .array(ComponentTypeName)
    .min(1)
    .describe("Component types that may occupy this slot"),
  required: z.boolean().default(false),
  maxCount: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("Max children in this slot; omit for unbounded"),
  description: z.string().optional(),
});

/**
 * H.3  Interaction State Machine
 *
 * Models the *topology* of interaction states — which states exist, which
 * events trigger transitions between them, and which transition tokens
 * animate those changes. This is the layer v1 was missing: it had state
 * *values* (rest/hover/active/disabled token bindings) but not the state
 * *graph*.
 *
 * Design note: this is intentionally NOT a full statechart (no hierarchy,
 * no guards, no parallel regions). It captures the DOM-event-driven state
 * transitions observable in the UI. A full XState-style formalism would be
 * application-layer, not design-system-layer.
 */
const InteractionTrigger = z.enum([
  "pointerenter",
  "pointerleave",
  "pointerdown",
  "pointerup",
  "focus",
  "blur",
  "click",
  "keydown:Enter",
  "keydown:Escape",
  "keydown:Space",
  "keydown:Tab",
  "toggle",        // for open/close state (sidebar, dropdown)
  "media:resize",  // viewport resize crossing a breakpoint
]);

const InteractionStateName = z
  .string()
  .min(1)
  .describe("State name, e.g. 'rest', 'hovered', 'focused', 'open'");

const StateTransition = z.object({
  from: InteractionStateName,
  to: InteractionStateName,
  trigger: InteractionTrigger,
  transitionTokenId: TokenRef.optional().describe(
    "FK → TransitionToken.id — animation between states"
  ),
  /** If true, the reverse transition is implied (from↔to on inverse trigger). */
  reversible: z.boolean().default(false),
});

const InteractionModel = z.object({
  states: z
    .array(InteractionStateName)
    .min(1)
    .describe("All valid states for this component"),
  initialState: InteractionStateName.describe(
    "State the component enters on mount"
  ),
  transitions: z.array(StateTransition).min(1),
  focusTrap: z
    .boolean()
    .default(false)
    .describe("If true, Tab/Shift+Tab cycle is confined to this component"),
  ariaRole: z
    .string()
    .optional()
    .describe("WAI-ARIA role, e.g. 'dialog', 'menu', 'tooltip'"),
  keyboardDismiss: z
    .boolean()
    .default(false)
    .describe("If true, Escape closes/collapses the component"),
});

/**
 * H.4  Conditional Token Resolution  [NEW in v2]
 *
 * v1 used bare UUID FK strings for token-to-component bindings. That works
 * for the default case but cannot express "this component, in this variant,
 * at this breakpoint, in this theme mode, resolves to this token."
 *
 * The resolution model is a separate layer (not inline in component defs)
 * for two reasons:
 *   1. Keeps component definitions readable and flat.
 *   2. Mirrors the architecture of Style Dictionary / Figma variable modes,
 *      where resolution is a lookup table layered on top of token defs.
 *
 * Resolution precedence (most specific wins):
 *   themeMode + breakpoint + variant + state  →  highest specificity
 *   themeMode + variant + state               →  ...
 *   themeMode + state                         →  ...
 *   themeMode                                 →  ...
 *   (none)                                    →  default (bare FK in component def)
 */
const TokenResolutionRule = z.object({
  id: EntityId,
  /** What this rule targets. */
  target: z.object({
    componentType: ComponentTypeName,
    /** Dot-path to the property on the component definition, e.g.
     *  'states.rest.bgTokenId' or 'shadowStates.focus'. */
    property: z
      .string()
      .min(1)
      .describe("Dot-path to the FK field on the component definition"),
    /** Restrict to a specific variant value, if the component has variants. */
    variant: z.string().optional(),
  }),
  /** Conditions under which this override applies. */
  conditions: z
    .object({
      themeMode: ThemeMode.optional(),
      /** References Breakpoint.name — applies at this breakpoint and above. */
      breakpointName: z.string().optional(),
      /** Interaction state name from the component's InteractionModel. */
      interactionState: InteractionStateName.optional(),
    })
    .refine(
      (c) => c.themeMode || c.breakpointName || c.interactionState,
      "At least one condition must be set; a rule with no conditions is the default (use the component's inline FK instead)"
    ),
  /** The token ID that wins when all conditions match. */
  resolvedTokenId: TokenRef.describe("FK → ColorToken.id (or any token)"),
});

/**
 * H.5  Responsive Adaptation Rules  [NEW in v2]
 *
 * v1 defined breakpoints as raw values with no mechanism to express what
 * changes at each one. This type fills that gap. Each rule binds a
 * breakpoint to a concrete property change on a layout section or component.
 *
 * Example:
 *   { breakpointName: "lg",
 *     target: { kind: "layout", section: "sidebar", property: "position" },
 *     value: "sticky",
 *     description: "Sidebar switches from fixed overlay to sticky at lg" }
 */
const ResponsiveAdaptation = z.object({
  id: EntityId,
  /** Breakpoint at which this adaptation activates (min-width, mobile-first). */
  breakpointName: z.string().min(1).describe("References Breakpoint.name"),
  target: z.discriminatedUnion("kind", [
    z.object({
      kind: z.literal("layout"),
      section: z
        .string()
        .min(1)
        .describe("Layout section, e.g. 'sidebar', 'mainContent'"),
      property: z.string().min(1).describe("CSS or schema property name"),
    }),
    z.object({
      kind: z.literal("component"),
      componentType: ComponentTypeName,
      variant: z
        .string()
        .optional()
        .describe("Restrict to a specific variant, if applicable"),
      property: z.string().min(1),
    }),
  ]),
  /** The value the property takes at this breakpoint. */
  value: z.union([z.string(), z.number(), z.boolean()]),
  description: z
    .string()
    .optional()
    .describe("Human-readable explanation of the adaptation"),
});

// ─────────────────────────────────────────────────────────────────────────────
// Part I — Component Definitions
// ─────────────────────────────────────────────────────────────────────────────

// ── I.1 Button ──

/**
 * Button variants observed in the HTML class names:
 *   _fill_   — solid background
 *   _ghost_  — transparent background, hover reveals bg
 *   _claude_ — brand-accent fill (used for send button)
 */
const ButtonVariant = z.enum(["fill", "ghost", "claude"]);

const ButtonSize = z.enum([
  "xs", // h-6 w-6
  "sm", // h-8 w-8 (icon-only) or h-8 px-3 (with label)
  "md", // h-9 px-4 py-2
]);

const ButtonShape = z.enum(["rounded-md", "rounded-lg", "rounded-full"]);

const ButtonComponent = z.object({
  id: EntityId,
  type: z.literal("Button").default("Button"),
  variant: ButtonVariant,
  size: ButtonSize,
  shape: ButtonShape.default("rounded-md"),
  iconOnly: z
    .boolean()
    .default(false)
    .describe("If true, button renders only an icon with equal width/height"),
  label: z
    .string()
    .optional()
    .describe("Accessible label (aria-label) — required when iconOnly=true"),
  iconId: TokenRef.optional().describe("FK → Icon.id"),
  /** Interaction states — defined by token references, not raw values.
   *  These are the *defaults*. Use TokenResolutionRule for conditional
   *  overrides per theme/breakpoint/variant. */
  states: z.object({
    rest: z.object({
      bgTokenId: TokenRef.nullable().describe(
        "FK → ColorToken.id or null for transparent"
      ),
      textTokenId: TokenRef.describe("FK → ColorToken.id"),
    }),
    hover: z.object({
      bgTokenId: TokenRef.nullable(),
      textTokenId: TokenRef,
      scale: z
        .number()
        .default(1)
        .describe("transform: scale() value on hover"),
    }),
    active: z.object({
      bgTokenId: TokenRef.nullable(),
      scale: z
        .number()
        .default(1)
        .describe("Observed: 0.85 for launcher, 0.98 for sidebar items"),
    }),
    disabled: z.object({
      opacity: z.number().min(0).max(1).default(0.5),
    }),
  }),
  transitionId: TokenRef.describe("FK → TransitionToken.id"),
  /** v2: slot model */
  slots: z
    .array(ComponentSlot)
    .default([
      {
        name: "icon",
        position: "leading",
        allowedChildTypes: ["Button"], // self-referential: icon is technically a child SVG but typed as slot for extensibility
        required: false,
        maxCount: 1,
      },
    ])
    .describe("Slots available on this component"),
  /** v2: interaction model */
  interaction: InteractionModel.default({
    states: ["rest", "hovered", "active", "focused", "disabled"],
    initialState: "rest",
    transitions: [
      { from: "rest", to: "hovered", trigger: "pointerenter", reversible: true },
      { from: "hovered", to: "active", trigger: "pointerdown", reversible: true },
      { from: "rest", to: "focused", trigger: "focus", reversible: true },
    ],
    focusTrap: false,
    keyboardDismiss: false,
  }),
});

// ── I.2 Sidebar Navigation Item ──

const SidebarItemKind = z.enum([
  "nav", //     top-level navigation (New chat, Search, Customize, etc.)
  "chat", //    chat history entry
  "project", // project entry
  "more", //    "All chats" overflow link
]);

const SidebarItem = z.object({
  id: EntityId,
  type: z.literal("SidebarItem").default("SidebarItem"),
  kind: SidebarItemKind,
  /** Icon displayed to the left. Null for chat items (no icon). */
  iconId: TokenRef.nullable().describe("FK → Icon.id"),
  label: z.string().min(1),
  href: z.string().min(1).describe("Navigation target"),
  /** Whether the label truncates with a gradient mask on hover. */
  truncateWithMask: z.boolean().default(true),
  /** Context menu trigger (three-dot button). */
  hasContextMenu: z.boolean().default(false),
  isStarred: z.boolean().default(false),
  /** v2: slots */
  slots: z
    .array(ComponentSlot)
    .default([
      {
        name: "leading-icon",
        position: "leading",
        allowedChildTypes: ["Button"],
        required: false,
        maxCount: 1,
      },
      {
        name: "trailing-action",
        position: "trailing",
        allowedChildTypes: ["Button", "ContextMenu"],
        required: false,
        maxCount: 1,
        description: "Three-dot menu or pin action",
      },
    ]),
  interaction: InteractionModel.default({
    states: ["rest", "hovered", "active", "focused"],
    initialState: "rest",
    transitions: [
      { from: "rest", to: "hovered", trigger: "pointerenter", reversible: true },
      { from: "hovered", to: "active", trigger: "pointerdown", reversible: true },
      { from: "rest", to: "focused", trigger: "focus", reversible: true },
    ],
    focusTrap: false,
    keyboardDismiss: false,
  }),
});

// ── I.3 Chat Input ──

const ChatInputComponent = z.object({
  id: EntityId,
  type: z.literal("ChatInput").default("ChatInput"),
  placeholder: z.string().default("How can I help you today?"),
  minHeightRem: Rem.default(3).describe("Observed: min-h-[3rem]"),
  maxHeightRem: Rem.default(24).describe("Observed: max-h-96 = 24rem"),
  borderRadius: Px.default(20).describe("Observed: rounded-[20px]"),
  /** Shadow tokens for each interaction state. */
  shadowStates: z.object({
    rest: TokenRef.describe("FK → ShadowToken.id"),
    hover: TokenRef.describe("FK → ShadowToken.id"),
    focus: TokenRef.describe("FK → ShadowToken.id"),
  }),
  /** Attachment thumbnails config. */
  attachmentThumbnail: z.object({
    sizePx: Px.default(120),
    borderRadius: Px.default(8).describe("Observed: rounded-lg"),
  }),
  /** v2: slots — the chat input is a rich container */
  slots: z
    .array(ComponentSlot)
    .default([
      {
        name: "leading-attachments",
        position: "leading",
        allowedChildTypes: ["FileAttachmentCard"],
        required: false,
        description: "Uploaded file/image thumbnails above the text area",
      },
      {
        name: "trailing-actions",
        position: "trailing",
        allowedChildTypes: ["Button", "ModelSelector"],
        required: true,
        description: "Send button, model picker, attachment button",
      },
      {
        name: "footer-tools",
        position: "footer",
        allowedChildTypes: ["Button"],
        required: false,
        description:
          "Tool toggles below the input (web search, deep research, etc.)",
      },
    ]),
  interaction: InteractionModel.default({
    states: ["rest", "hovered", "focused", "disabled"],
    initialState: "rest",
    transitions: [
      { from: "rest", to: "hovered", trigger: "pointerenter", reversible: true },
      { from: "rest", to: "focused", trigger: "focus", reversible: true },
      { from: "hovered", to: "focused", trigger: "focus", reversible: true },
    ],
    focusTrap: false,
    keyboardDismiss: false,
  }),
});

// ── I.4 Avatar ──

const AvatarSize = z.enum(["sm", "md"]).describe("sm = h-6 w-6, md = h-9 w-9");

const AvatarComponent = z.object({
  id: EntityId,
  type: z.literal("Avatar").default("Avatar"),
  size: AvatarSize,
  shape: z.literal("circle"),
  /** For initials-based avatars. */
  initialsMaxLength: z.number().int().min(1).max(2).default(2),
  fontSizeForSize: z
    .record(AvatarSize, Rem)
    .describe("Font size per avatar size. Observed: md → 16px"),
  bgTokenId: TokenRef.describe("FK → ColorToken.id (text-200 observed)"),
  textTokenId: TokenRef.describe("FK → ColorToken.id (bg-100 observed)"),
});

// ── I.5 Model Selector (Pill/Chip) ──

const ModelSelectorComponent = z.object({
  id: EntityId,
  type: z.literal("ModelSelector").default("ModelSelector"),
  modelName: z.string().min(1).describe("E.g. 'Opus 4.6'"),
  modeSuffix: z.string().optional().describe("E.g. 'Extended'"),
  /** Renders as a ghost button with dropdown arrow. */
  buttonVariant: z.literal("ghost"),
  /** v2: opens a dropdown */
  slots: z
    .array(ComponentSlot)
    .default([
      {
        name: "dropdown",
        position: "overlay",
        allowedChildTypes: ["DropdownMenu"],
        required: true,
        maxCount: 1,
      },
    ]),
  interaction: InteractionModel.default({
    states: ["closed", "open"],
    initialState: "closed",
    transitions: [
      { from: "closed", to: "open", trigger: "click", reversible: false },
      { from: "open", to: "closed", trigger: "click", reversible: false },
      { from: "open", to: "closed", trigger: "keydown:Escape", reversible: false },
    ],
    focusTrap: false,
    keyboardDismiss: true,
    ariaRole: "listbox",
  }),
});

// ── I.6 Quick-Action Chip ──

const QuickActionChip = z.object({
  id: EntityId,
  type: z.literal("QuickActionChip").default("QuickActionChip"),
  label: z.string().min(1).describe("E.g. 'Write', 'Learn', 'Code'"),
  iconId: TokenRef.optional().describe("FK → Icon.id"),
});

// ── I.7 Usage Banner ──

const UsageBanner = z.object({
  id: EntityId,
  type: z.literal("UsageBanner").default("UsageBanner"),
  messageTemplate: z
    .string()
    .describe("Template with {percentage} placeholder"),
  ctaLabel: z.string().default("Get more usage"),
  bgTokenId: TokenRef.describe("FK → ColorToken.id — observed: bg-300"),
  borderRadius: z.string().default("rounded-b-xl"),
});

// ── I.8 Message Bubble  [NEW in v2] ──

/**
 * Conversation message container. Two variants — human messages and
 * assistant messages — with distinct styling, alignment, and slot
 * structures.
 *
 * Source: inferred from the chat view structure in the HTML snapshot
 * (partial — the home view shows the chat container skeleton but not
 * populated messages). Slot structure inferred from known UI patterns.
 */
const MessageRole = z.enum(["user", "assistant"]);

const MessageBubbleComponent = z.object({
  id: EntityId,
  type: z.literal("MessageBubble").default("MessageBubble"),
  role: MessageRole,
  /** User messages have a tinted bg; assistant messages are transparent. */
  bgTokenId: TokenRef.nullable().describe(
    "FK → ColorToken.id. User: bg-200; Assistant: null (transparent)"
  ),
  borderRadiusId: TokenRef.describe("FK → BorderRadiusToken.id"),
  maxWidth: z
    .string()
    .default("max-w-3xl")
    .describe("Tailwind max-width class for content column"),
  typographyId: TokenRef.describe("FK → TypographyToken.id (base scale)"),
  slots: z
    .array(ComponentSlot)
    .default([
      {
        name: "avatar",
        position: "leading",
        allowedChildTypes: ["Avatar"],
        required: true,
        maxCount: 1,
      },
      {
        name: "content",
        position: "content",
        allowedChildTypes: ["CodeBlock"],
        required: true,
        description:
          "Primary message content (markdown-rendered). CodeBlocks are inline children.",
      },
      {
        name: "actions",
        position: "footer",
        allowedChildTypes: ["Button"],
        required: false,
        description: "Copy, retry, thumbs-up/down action buttons",
      },
    ]),
  interaction: InteractionModel.default({
    states: ["rest", "hovered"],
    initialState: "rest",
    transitions: [
      {
        from: "rest",
        to: "hovered",
        trigger: "pointerenter",
        reversible: true,
      },
    ],
    focusTrap: false,
    keyboardDismiss: false,
  }),
});

// ── I.9 Code Block  [NEW in v2] ──

/**
 * Fenced code block rendered inside assistant messages. Features syntax
 * highlighting (via a highlight.js or Shiki-like tokenizer), a language
 * label header, and a copy button.
 */
const CodeBlockComponent = z.object({
  id: EntityId,
  type: z.literal("CodeBlock").default("CodeBlock"),
  bgTokenId: TokenRef.describe(
    "FK → ColorToken.id — typically a darker bg tier"
  ),
  textTokenId: TokenRef.describe("FK → ColorToken.id — monospace text color"),
  fontFamily: z
    .literal("monospace")
    .default("monospace")
    .describe("Always rendered in a monospace stack"),
  fontSize: TokenRef.describe("FK → TypographyToken.id (small or xs)"),
  borderRadiusId: TokenRef.describe("FK → BorderRadiusToken.id"),
  /** Language label shown in the header bar. */
  languageLabel: z.object({
    typographyId: TokenRef.describe("FK → TypographyToken.id"),
    textTokenId: TokenRef.describe("FK → ColorToken.id"),
  }),
  slots: z
    .array(ComponentSlot)
    .default([
      {
        name: "header-actions",
        position: "header",
        allowedChildTypes: ["Button"],
        required: false,
        maxCount: 2,
        description: "Copy button, language label",
      },
    ]),
  /** Syntax highlighting token color map — keys are highlight scope names. */
  syntaxColors: z
    .record(z.string(), TokenRef)
    .optional()
    .describe(
      "Scope → ColorToken.id, e.g. { 'keyword': '<uuid>', 'string': '<uuid>' }"
    ),
});

// ── I.10 Toast Notification  [NEW in v2] ──

const ToastSeverity = z.enum(["info", "success", "warning", "error"]);

const ToastNotificationComponent = z.object({
  id: EntityId,
  type: z.literal("ToastNotification").default("ToastNotification"),
  severity: ToastSeverity,
  bgTokenId: TokenRef.describe("FK → ColorToken.id — per severity"),
  textTokenId: TokenRef.describe("FK → ColorToken.id"),
  borderRadiusId: TokenRef.describe("FK → BorderRadiusToken.id"),
  shadowId: TokenRef.describe("FK → ShadowToken.id"),
  /** Auto-dismiss duration. Null means persistent until user action. */
  autoDismissMs: DurationMs.nullable().default(5000),
  position: z.enum(["top-center", "bottom-center", "top-right"]).default("top-center"),
  slots: z
    .array(ComponentSlot)
    .default([
      {
        name: "leading-icon",
        position: "leading",
        allowedChildTypes: ["Button"],
        required: false,
        maxCount: 1,
      },
      {
        name: "dismiss",
        position: "trailing",
        allowedChildTypes: ["Button"],
        required: false,
        maxCount: 1,
      },
    ]),
  interaction: InteractionModel.default({
    states: ["entering", "visible", "exiting", "dismissed"],
    initialState: "entering",
    transitions: [
      { from: "entering", to: "visible", trigger: "toggle", reversible: false },
      { from: "visible", to: "exiting", trigger: "click", reversible: false },
      { from: "visible", to: "exiting", trigger: "toggle", reversible: false },
      { from: "exiting", to: "dismissed", trigger: "toggle", reversible: false },
    ],
    focusTrap: false,
    keyboardDismiss: true,
    ariaRole: "alert",
  }),
});

// ── I.11 Modal Dialog  [NEW in v2] ──

const ModalDialogComponent = z.object({
  id: EntityId,
  type: z.literal("ModalDialog").default("ModalDialog"),
  bgTokenId: TokenRef.describe("FK → ColorToken.id — dialog surface"),
  overlayColor: z
    .string()
    .describe("Backdrop color expression, e.g. 'rgba(0,0,0,0.5)'"),
  borderRadiusId: TokenRef.describe("FK → BorderRadiusToken.id"),
  shadowId: TokenRef.describe("FK → ShadowToken.id"),
  maxWidthPx: Px.default(480),
  slots: z
    .array(ComponentSlot)
    .default([
      {
        name: "header",
        position: "header",
        allowedChildTypes: ["Button"],
        required: false,
        description: "Title area and close button",
      },
      {
        name: "body",
        position: "content",
        allowedChildTypes: [
          "Button",
          "ChatInput",
          "Avatar",
          "QuickActionChip",
        ],
        required: true,
        description: "Primary dialog content — allows arbitrary children",
      },
      {
        name: "footer-actions",
        position: "footer",
        allowedChildTypes: ["Button"],
        required: false,
        description: "Confirm/cancel action buttons",
      },
    ]),
  interaction: InteractionModel.default({
    states: ["closed", "open"],
    initialState: "closed",
    transitions: [
      { from: "closed", to: "open", trigger: "toggle", reversible: false },
      { from: "open", to: "closed", trigger: "keydown:Escape", reversible: false },
      { from: "open", to: "closed", trigger: "toggle", reversible: false },
    ],
    focusTrap: true,
    keyboardDismiss: true,
    ariaRole: "dialog",
  }),
});

// ── I.12 Dropdown Menu  [NEW in v2] ──

const DropdownMenuComponent = z.object({
  id: EntityId,
  type: z.literal("DropdownMenu").default("DropdownMenu"),
  bgTokenId: TokenRef.describe("FK → ColorToken.id — menu surface"),
  borderTokenId: TokenRef.describe("FK → ColorToken.id"),
  borderRadiusId: TokenRef.describe("FK → BorderRadiusToken.id"),
  shadowId: TokenRef.describe("FK → ShadowToken.id"),
  itemHeight: Rem.default(2.25),
  /** Menu items are effectively SidebarItem-shaped: icon + label + optional shortcut. */
  slots: z
    .array(ComponentSlot)
    .default([
      {
        name: "items",
        position: "content",
        allowedChildTypes: ["Button", "SidebarItem"],
        required: true,
        description: "Menu item rows",
      },
    ]),
  interaction: InteractionModel.default({
    states: ["closed", "open"],
    initialState: "closed",
    transitions: [
      { from: "closed", to: "open", trigger: "click", reversible: false },
      { from: "open", to: "closed", trigger: "click", reversible: false },
      { from: "open", to: "closed", trigger: "keydown:Escape", reversible: false },
    ],
    focusTrap: true,
    keyboardDismiss: true,
    ariaRole: "menu",
  }),
});

// ── I.13 Tooltip  [NEW in v2] ──

const TooltipPlacement = z.enum([
  "top",
  "bottom",
  "left",
  "right",
]);

const TooltipComponent = z.object({
  id: EntityId,
  type: z.literal("Tooltip").default("Tooltip"),
  bgTokenId: TokenRef.describe("FK → ColorToken.id — typically dark bg"),
  textTokenId: TokenRef.describe("FK → ColorToken.id — typically light text"),
  borderRadiusId: TokenRef.describe("FK → BorderRadiusToken.id"),
  typographyId: TokenRef.describe("FK → TypographyToken.id (small or xs)"),
  placement: TooltipPlacement.default("top"),
  offsetPx: Px.default(4),
  delayMs: DurationMs.default(200).describe("Show delay on hover"),
  interaction: InteractionModel.default({
    states: ["hidden", "visible"],
    initialState: "hidden",
    transitions: [
      { from: "hidden", to: "visible", trigger: "pointerenter", reversible: true },
      { from: "hidden", to: "visible", trigger: "focus", reversible: true },
      { from: "visible", to: "hidden", trigger: "keydown:Escape", reversible: false },
    ],
    focusTrap: false,
    keyboardDismiss: true,
    ariaRole: "tooltip",
  }),
});

// ─────────────────────────────────────────────────────────────────────────────
// Part J — Layout Tokens
// ─────────────────────────────────────────────────────────────────────────────

const SidebarLayout = z.object({
  id: EntityId,
  collapsedWidthRem: Rem.default(3.05).describe("Observed: width 3.05rem"),
  expandedWidthRem: Rem.describe("Full sidebar width when pinned open"),
  /**
   * Default position. v1 had this as z.literal("fixed") with a comment about
   * the lg+ switch. v2 keeps the default here and models the switch via
   * ResponsiveAdaptation rules.
   */
  position: z
    .enum(["fixed", "sticky"])
    .default("fixed")
    .describe("Default (mobile) position; overridden at lg+ via responsive rules"),
  zIndex: z.number().int().describe("Observed z-index layer: z-sidebar"),
  borderRight: z.object({
    widthTokenId: TokenRef.describe("FK → BorderWidthToken.id"),
    colorTokenId: TokenRef.describe("FK → ColorToken.id"),
  }),
  /** Sidebar sections observed. */
  sections: z
    .array(
      z.enum([
        "header", //  logo + toggle button
        "actions", // new chat, search, customize
        "content", // chats, projects, artifacts, code
        "starred", // starred items
        "recents", // recent chat history
        "footer", //  downloads, user profile
      ])
    )
    .min(1),
  /** v2: sidebar-level interaction model (open/close choreography) */
  interaction: InteractionModel.default({
    states: ["collapsed", "expanded", "pinned"],
    initialState: "collapsed",
    transitions: [
      { from: "collapsed", to: "expanded", trigger: "pointerenter", reversible: true },
      { from: "expanded", to: "collapsed", trigger: "pointerleave", reversible: false },
      { from: "expanded", to: "pinned", trigger: "click", reversible: false },
      { from: "pinned", to: "collapsed", trigger: "click", reversible: false },
      { from: "collapsed", to: "expanded", trigger: "media:resize", reversible: false },
    ],
    focusTrap: false,
    keyboardDismiss: false,
  }),
});

const MainContentLayout = z.object({
  id: EntityId,
  maxWidth: z.string().default("max-w-7xl").describe("Tailwind max-width class"),
  paddingX: z.object({
    mobile: Rem,
    tablet: Rem,
    desktop: Rem,
  }),
  /** Grid template for header + content. */
  gridTemplateRows: z.string().default("0px 1fr"),
});

const Breakpoint = z.object({
  id: EntityId,
  name: z.enum(["sm", "md", "lg", "xl", "2xl", "3xl"]),
  minWidthPx: Px,
});

// ─────────────────────────────────────────────────────────────────────────────
// Part K — Scope & Component Manifest  [NEW in v2]
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Declares the coverage boundary of this schema. Consumers can distinguish
 * "this component doesn't exist" from "this component wasn't in scope."
 */
const SchemaScope = z.object({
  /** Application views this schema was derived from. */
  observedViews: z
    .array(z.string().min(1))
    .min(1)
    .describe(
      "Views/routes observed during reverse-engineering, e.g. ['home', 'chat-input']"
    ),
  /** Known views NOT observed (seen in routing but not inspected). */
  knownUnobservedViews: z
    .array(z.string().min(1))
    .default([])
    .describe("E.g. ['settings', 'chat-thread', 'project-detail']"),
  /** Estimated coverage of the observed views (self-assessed). */
  estimatedCoverage: z
    .object({
      tokenLayer: z
        .number()
        .min(0)
        .max(1)
        .describe("0–1 fraction of token coverage"),
      componentLayer: z
        .number()
        .min(0)
        .max(1)
        .describe("0–1 fraction of component coverage"),
      behavioralLayer: z
        .number()
        .min(0)
        .max(1)
        .describe("0–1 fraction of interaction/responsive/composition coverage"),
    })
    .describe(
      "Self-assessed coverage fractions. v2 estimate: tokens ~0.80, components ~0.50, behavioral ~0.30"
    ),
});

/**
 * Manifest entry for a component type that is known to exist but does not
 * yet have a full Zod definition in this schema.
 */
const UnmodeledComponent = z.object({
  typeName: ComponentTypeName,
  observedIn: z
    .array(z.string().min(1))
    .min(1)
    .describe("Views where this component was observed"),
  /** Priority for future modeling. */
  priority: z.enum(["high", "medium", "low"]),
  notes: z
    .string()
    .optional()
    .describe("Brief description of what was observed"),
});

const ComponentManifest = z.object({
  /** Component types with full definitions in this schema. */
  modeled: z.array(ComponentTypeName).min(1),
  /** Component types observed but not yet defined. */
  knownUnmodeled: z.array(UnmodeledComponent),
});

// ─────────────────────────────────────────────────────────────────────────────
// Part L — PALS's Law Verification Infrastructure  [NEW in v2.1]
// ─────────────────────────────────────────────────────────────────────────────

/**
 * ARCHITECTURAL CONTRACT — PALS's LAW
 *
 * Principle authored by: Pedro Anisio de Luna e Silva
 * PALS_LAW_VERSION: 1.5.4
 *
 * INVARIANT (operative form):
 *   E[ε(M(x), x)] ≥ δ > 0
 *
 * Any system consuming LLM output without a declared verification boundary
 * contains a structural defect. The types below make verification boundaries
 * explicit, auditable, and enforceable at the type level.
 *
 * Ref: PALS's Law v1.5.4, §8.4 (Corollary 4 — Silent acceptance is an
 *      architectural defect), §8.3 (Corollary 3 — Verification scope must
 *      match error taxonomy).
 */

/**
 * L.1  Error Class Enum
 *
 * The 9-class taxonomy from PALS's Law §5. This is the canonical enum
 * used throughout the verification infrastructure. Every verification
 * boundary must be scoped against these classes.
 */
const PALSErrorClass = z.enum([
  "ERR_HALLUCINATION",
  "ERR_OMISSION",
  "ERR_SCHEMA",
  "ERR_TRUNCATION",
  "ERR_SYCOPHANCY",
  "ERR_INSTRUCTION",
  "ERR_CALIBRATION",
  "ERR_SEMANTIC",
  "ERR_REASONING",
]);

/**
 * L.2  Source Metadata
 *
 * Every mutation must carry provenance metadata: who or what produced
 * the data. This is the mechanism for Corollary 2 compliance (trust
 * accumulation is prohibited) — the system never implicitly trusts
 * input based on past success.
 *
 * When sourceType is "llm", modelVersion is required (Corollary 5 —
 * capability growth shifts the verification problem).
 */
const MutationSourceType = z.enum([
  "human",     // manually authored by a person
  "llm",       // generated by an LLM (any model)
  "automated", // produced by deterministic tooling (no LLM)
  "unknown",   // caller cannot or will not declare
]);

const MutationSource = z.object({
  sourceType: MutationSourceType,
  /** Required when sourceType = "llm". Corollary 5 compliance. */
  modelVersion: z
    .string()
    .min(1)
    .optional()
    .describe(
      "Model identifier + version, e.g. 'claude-sonnet-4.6', 'gpt-4o-2025-03'. " +
        "REQUIRED when sourceType = 'llm'."
    ),
  /** Optional: the API key prefix used, for audit trail correlation. */
  apiKeyPrefix: z
    .string()
    .optional()
    .describe("First 8 chars of the API key, e.g. 'dsk_live'"),
  /** Optional: human-readable actor name. */
  actor: z
    .string()
    .optional()
    .describe("Actor identifier, e.g. 'figma-plugin-v3', 'pedro@example.com'"),
}).refine(
  (s) => s.sourceType !== "llm" || (s.modelVersion !== undefined && s.modelVersion.length > 0),
  {
    message:
      "PALS's Law Corollary 5: modelVersion is REQUIRED when sourceType is 'llm'. " +
      "Verification requirements change with model capability.",
    path: ["modelVersion"],
  }
);

/**
 * L.3  Verification Boundary
 *
 * The core PALS's Law compliance type. Every mutation response includes
 * this structure, declaring exactly which error classes were checked and
 * which are accepted risks. This makes silent acceptance (Corollary 4)
 * structurally impossible.
 *
 * Ref: PALS's Law §9.1 (Full Contract Block) — this is the runtime
 *      equivalent of the code-level contract checklist.
 */
const VerificationCheckStatus = z.enum([
  "passed",         // check ran and found no issues
  "failed",         // check ran and found issues (see findings)
  "skipped",        // check was not executed (see rationale)
  "not_applicable", // error class does not apply to this operation
]);

const VerificationFinding = z.object({
  severity: z.enum(["error", "warning", "info"]),
  errorClass: PALSErrorClass,
  message: z.string().min(1).describe("Human-readable finding description"),
  /** Dot-path to the offending field, e.g. 'colors[3].hslChannels'. */
  path: z.string().optional(),
  /** ID of the entity where the issue was found. */
  entityId: z.string().optional(),
});

const VerificationCheckResult = z.object({
  errorClass: PALSErrorClass,
  status: VerificationCheckStatus,
  /** If skipped, why. This is the "accepted risk" documentation. */
  skipRationale: z
    .string()
    .optional()
    .describe("Required when status = 'skipped'"),
  /** Concrete findings from this check. */
  findings: z.array(VerificationFinding).default([]),
});

const VerificationBoundary = z.object({
  /** The PALS's Law version this boundary conforms to. */
  palsLawVersion: z.literal("1.5.4"),
  /** Timestamp of verification execution. */
  verifiedAt: z.string().datetime(),
  /** Who/what produced the input being verified. */
  source: MutationSource,
  /** Per-class check results. MUST cover all 9 classes. */
  checks: z
    .array(VerificationCheckResult)
    .length(9)
    .describe(
      "Exactly 9 entries — one per PALS's Law error class. " +
        "Omitting a class is a Corollary 3 violation."
    ),
  /** Aggregate pass/fail. True only if no check has status 'failed'. */
  passed: z.boolean(),
  /** Summary counts for quick inspection. */
  summary: z.object({
    classesChecked: z.number().int().min(0).max(9),
    classesPassed: z.number().int().min(0).max(9),
    classesFailed: z.number().int().min(0).max(9),
    classesSkipped: z.number().int().min(0).max(9),
    totalFindings: z.number().int().min(0),
  }),
});

/**
 * L.4  Semantic Validation Rules
 *
 * Beyond schema validation (ERR_SCHEMA), these rules detect
 * ERR_HALLUCINATION, ERR_SEMANTIC, ERR_REASONING, and ERR_OMISSION
 * through domain-specific invariant checks.
 *
 * Each rule is a declarative check the server executes. Consumers
 * can also define custom rules via the API.
 */
const SemanticCheckKind = z.enum([
  // ── ERR_HALLUCINATION detectors ──
  "dangling_reference",       // FK points to a non-existent entity
  "nonexistent_css_variable", // variableName not in known CSS variable set
  "unreachable_component",    // component type referenced but not in manifest

  // ── ERR_SEMANTIC detectors ──
  "hsl_range_sanity",         // lightness > 80% for a "dark" theme token
  "contrast_ratio_minimum",   // WCAG AA contrast check between fg/bg pairs
  "duplicate_variable_name",  // two tokens with the same CSS variable name

  // ── ERR_REASONING detectors ──
  "circular_resolution",      // resolution rules that create infinite loops
  "contradictory_adaptations", // two responsive rules targeting the same
                               // property at the same breakpoint with
                               // different values
  "slot_type_mismatch",       // slot allowedChildTypes references a type
                               // with no definition and not in manifest
  "unreachable_state",        // interaction model state with no incoming
                               // transition (other than initial)

  // ── ERR_OMISSION detectors ──
  "incomplete_theme_coverage", // theme doesn't override all color tokens
  "missing_required_slot",     // component has a required slot with no
                               // default child defined
  "orphaned_resolution_rule",  // rule targets a component/property that
                               // doesn't exist
]);

const SemanticCheckResult = z.object({
  kind: SemanticCheckKind,
  /** Which PALS error class this check covers. */
  coversErrorClass: PALSErrorClass,
  passed: z.boolean(),
  findings: z.array(VerificationFinding).default([]),
});

/**
 * L.5  Completeness Assertion
 *
 * Declares what the design system SHOULD contain and checks what's
 * actually present. This is the ERR_OMISSION detector for the system
 * as a whole.
 *
 * Ref: PALS's Law §5, ERR_OMISSION — "Silently dropping required
 *      content — instructions followed partially, constraints missed,
 *      fields absent from structured output."
 */
const CompletenessAssertion = z.object({
  id: EntityId,
  /** Human-readable description of what this assertion checks. */
  description: z.string().min(1),
  /** Expected color roles that must each have at least one token. */
  expectedColorRoles: z.array(ColorRole).optional(),
  /** Expected color scales per role. */
  expectedColorScales: z.array(ColorScaleLevel).optional(),
  /** Component types that must be fully modeled (not just in manifest). */
  expectedComponentTypes: z.array(ComponentTypeName).optional(),
  /** Breakpoint names that must be defined. */
  expectedBreakpoints: z
    .array(z.string().min(1))
    .optional(),
  /** Theme modes that must be fully overridden. */
  expectedThemeModes: z.array(ThemeMode).optional(),
});

const CompletenessResult = z.object({
  assertion: CompletenessAssertion,
  passed: z.boolean(),
  missing: z.array(
    z.object({
      category: z.string().min(1).describe("What's missing: 'color_role', 'component', etc."),
      expected: z.string().min(1),
      description: z.string().optional(),
    })
  ),
});

/**
 * L.6  Verification Audit Entry
 *
 * Immutable log entry recording the result of every verification run.
 * This is the runtime equivalent of PALS's Law §9.1 contract block —
 * a permanent, queryable record of what was checked and what wasn't.
 *
 * Corollary 2 compliance: the audit trail makes it visible that past
 * success does not reduce future verification requirements.
 */
const VerificationAuditEntry = z.object({
  id: EntityId,
  /** What triggered this verification (mutation, snapshot, manual). */
  trigger: z.enum(["mutation", "snapshot_creation", "manual_run", "scheduled"]),
  /** The mutation or operation that was verified. */
  operationId: z.string().optional().describe("Request ID of the triggering operation"),
  /** Full verification boundary as computed at execution time. */
  boundary: VerificationBoundary,
  /** Semantic checks executed. */
  semanticChecks: z.array(SemanticCheckResult).default([]),
  /** Completeness checks executed. */
  completenessResults: z.array(CompletenessResult).default([]),
  /** Timestamp (redundant with boundary.verifiedAt but useful for indexing). */
  timestamp: z.string().datetime(),
});

/**
 * L.7  Snapshot Verification Declaration
 *
 * Required on every snapshot creation. Forces the publisher to declare
 * the verification status of the snapshot. A snapshot without this
 * declaration is a Corollary 4 violation.
 *
 * Ref: PALS's Law §8.4 — "Any production system that passes LLM output
 *      directly to downstream consumers without a declared verification
 *      boundary has an architectural omission."
 *
 * Snapshots are the "production deployment" of a design system — they
 * are what code generators and CI consume. Publishing without a
 * verification declaration is exactly the architectural omission the
 * corollary describes.
 */
const SnapshotVerificationStatus = z.enum([
  "fully_verified",    // all 9 classes checked, all passed
  "partially_verified", // some classes checked, none failed
  "unverified",        // no verification was performed
  "verified_with_accepted_risks", // some classes checked, some skipped with rationale
]);

const SnapshotVerificationDeclaration = z.object({
  palsLawVersion: z.literal("1.5.4"),
  status: SnapshotVerificationStatus,
  /** The verification boundary at snapshot time. */
  boundary: VerificationBoundary,
  /** Completeness assertion results at snapshot time. */
  completenessResults: z.array(CompletenessResult).default([]),
  /**
   * For status = "verified_with_accepted_risks": each skipped class
   * must have a rationale. This is enforced by VerificationCheckResult
   * already, but surfaced here for snapshot-level documentation.
   */
  acceptedRiskSummary: z
    .array(
      z.object({
        errorClass: PALSErrorClass,
        rationale: z.string().min(1),
      })
    )
    .default([]),
});

/**
 * L.8  Design System Verification Configuration
 *
 * Per-design-system configuration controlling how verification runs.
 * This lives on the DesignSystem root and determines the default
 * behavior for all mutations and snapshot operations.
 */
const VerificationPolicy = z.enum([
  "enforce",  // mutations with failed verification are rejected (HTTP 422)
  "warn",     // mutations proceed but verification failures are logged
  "audit",    // verification runs but results are only in the audit trail
  "disabled", // verification is off (Corollary 4 violation — logged as such)
]);

const VerificationConfig = z.object({
  /** PALS's Law version this config targets. */
  palsLawVersion: z.literal("1.5.4"),
  /** Default policy for mutations. */
  mutationPolicy: VerificationPolicy.default("warn"),
  /** Policy for snapshot creation. "enforce" is recommended. */
  snapshotPolicy: VerificationPolicy.default("enforce"),
  /** Which semantic checks are enabled by default. */
  enabledSemanticChecks: z
    .array(SemanticCheckKind)
    .default([
      "dangling_reference",
      "hsl_range_sanity",
      "circular_resolution",
      "contradictory_adaptations",
      "incomplete_theme_coverage",
      "orphaned_resolution_rule",
      "slot_type_mismatch",
    ])
    .describe("Semantic checks that run on every mutation"),
  /** Completeness assertions that run on snapshot creation. */
  completenessAssertions: z
    .array(CompletenessAssertion)
    .default([])
    .describe("Custom completeness assertions for this design system"),
  /** Whether to require source metadata on all mutations. */
  requireSourceMetadata: z
    .boolean()
    .default(true)
    .describe("If true, mutations without MutationSource are rejected"),
  /**
   * Elevated verification for LLM-sourced mutations.
   * When true, mutations with sourceType='llm' run ALL semantic checks
   * regardless of enabledSemanticChecks.
   */
  elevatedLLMVerification: z
    .boolean()
    .default(true)
    .describe(
      "If true, LLM-sourced mutations run the full semantic check suite. " +
        "Corollary 5: model capability demands proportional verification."
    ),
});

// ─────────────────────────────────────────────────────────────────────────────
// Part M — Top-Level Design System Definition
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The root entity that composes all tokens, component definitions,
 * resolution rules, responsive adaptations, scope metadata, and
 * verification infrastructure into a single, versioned design
 * system artifact.
 *
 * Composition semantics:
 *   DesignSystem ◆── ColorToken              (composition — lifecycle-owned)
 *   DesignSystem ◆── TypographyToken         (composition)
 *   DesignSystem ◆── SpacingToken            (composition)
 *   DesignSystem ◆── Theme                   (composition)
 *   DesignSystem ◆── Icon                    (composition)
 *   DesignSystem ◆── TokenResolutionRule     (composition) [v2]
 *   DesignSystem ◆── ResponsiveAdaptation    (composition) [v2]
 *   DesignSystem ◆── VerificationConfig      (composition) [v2.1/PALS]
 *   DesignSystem ◆── VerificationAuditEntry  (composition) [v2.1/PALS]
 *   DesignSystem ◇── ButtonComponent         (aggregation — reusable)
 *   DesignSystem ◇── SidebarItem             (aggregation)
 *   DesignSystem ◇── MessageBubbleComponent  (aggregation) [v2]
 *   etc.
 */
const DesignSystem = z.object({
  id: EntityId,
  name: z.string().min(1).default("claude").describe(
    "Design system name. Observed: 'claude' from data-theme attribute."
  ),
  version: SemVer.describe("Schema version"),
  buildId: z
    .string()
    .optional()
    .describe("Observed: data-build-id='c54235956b'"),
  gitHash: z
    .string()
    .optional()
    .describe(
      "Observed: data-git-hash='413e2801e5fb13ed25964ba45a7aa2c54235956b'"
    ),

  // ── Scope & manifest (v2) ──
  scope: SchemaScope,
  componentManifest: ComponentManifest,

  // ── Token layers (composition) ──
  colors: z.array(ColorToken).min(1),
  themes: z.array(Theme).min(1),
  typography: z.array(TypographyToken).min(1),
  fontAssets: z.array(FontAsset).min(1),
  spacing: z.array(SpacingToken).min(1),
  borderWidths: z.array(BorderWidthToken).min(1),
  borderRadii: z.array(BorderRadiusToken).min(1),
  shadows: z.array(ShadowToken).min(1),
  transitions: z.array(TransitionToken).min(1),
  animations: z.array(AnimationToken).min(1),
  icons: z.array(Icon).min(1),
  breakpoints: z.array(Breakpoint).min(1),

  // ── Conditional resolution & responsive rules (v2) ──
  tokenResolutions: z
    .array(TokenResolutionRule)
    .default([])
    .describe(
      "Conditional overrides for token-to-component bindings. " +
        "Empty array means all bindings use the defaults in component defs."
    ),
  responsiveAdaptations: z
    .array(ResponsiveAdaptation)
    .default([])
    .describe("Rules for what changes at each breakpoint"),

  // ── Component definitions (aggregation) ──
  components: z.object({
    buttons: z.array(ButtonComponent).min(1),
    sidebarItems: z.array(SidebarItem).min(1),
    chatInput: ChatInputComponent,
    avatar: AvatarComponent,
    modelSelector: ModelSelectorComponent,
    quickActionChips: z.array(QuickActionChip).min(1),
    usageBanner: UsageBanner,
    // v2 additions
    messageBubbles: z
      .array(MessageBubbleComponent)
      .min(1)
      .describe("One per MessageRole"),
    codeBlock: CodeBlockComponent,
    toastNotification: ToastNotificationComponent,
    modalDialog: ModalDialogComponent,
    dropdownMenu: DropdownMenuComponent,
    tooltip: TooltipComponent,
  }),

  // ── Layout definitions ──
  layout: z.object({
    sidebar: SidebarLayout,
    mainContent: MainContentLayout,
    breakpoints: z.array(Breakpoint).min(1),
  }),

  // ── PALS's Law verification infrastructure (v2.1) ──

  /**
   * Verification configuration for this design system.
   *
   * PALS's LAW §8.4 (Corollary 4): "Any production system that passes
   * LLM output directly to downstream consumers without a declared
   * verification boundary has an architectural omission."
   *
   * This field makes the verification boundary a first-class,
   * schema-level concern — not an afterthought.
   */
  verification: VerificationConfig.describe(
    "PALS's Law compliance configuration. Controls verification " +
      "behavior for mutations and snapshots."
  ),

  /**
   * Audit trail of all verification runs.
   *
   * PALS's LAW §8.2 (Corollary 2): "A system must not relax its
   * verification layer after observing a run of correct outputs."
   *
   * The audit trail makes this enforceable: you can query whether
   * past verification succeeded, but it structurally cannot reduce
   * future verification requirements.
   */
  verificationAuditLog: z
    .array(VerificationAuditEntry)
    .default([])
    .describe(
      "Append-only log of verification results. " +
        "Every mutation and snapshot creation appends an entry."
    ),
});

// ─────────────────────────────────────────────────────────────────────────────
// Type Exports
// ─────────────────────────────────────────────────────────────────────────────

export type ColorToken = z.infer<typeof ColorToken>;
export type Theme = z.infer<typeof Theme>;
export type TypographyToken = z.infer<typeof TypographyToken>;
export type FontAsset = z.infer<typeof FontAsset>;
export type SpacingToken = z.infer<typeof SpacingToken>;
export type BorderWidthToken = z.infer<typeof BorderWidthToken>;
export type BorderRadiusToken = z.infer<typeof BorderRadiusToken>;
export type ShadowToken = z.infer<typeof ShadowToken>;
export type ShadowLayer = z.infer<typeof ShadowLayer>;
export type TransitionToken = z.infer<typeof TransitionToken>;
export type AnimationToken = z.infer<typeof AnimationToken>;
export type Icon = z.infer<typeof Icon>;
export type ComponentSlot = z.infer<typeof ComponentSlot>;
export type InteractionModel = z.infer<typeof InteractionModel>;
export type StateTransition = z.infer<typeof StateTransition>;
export type TokenResolutionRule = z.infer<typeof TokenResolutionRule>;
export type ResponsiveAdaptation = z.infer<typeof ResponsiveAdaptation>;
export type ButtonComponent = z.infer<typeof ButtonComponent>;
export type SidebarItem = z.infer<typeof SidebarItem>;
export type ChatInputComponent = z.infer<typeof ChatInputComponent>;
export type AvatarComponent = z.infer<typeof AvatarComponent>;
export type ModelSelectorComponent = z.infer<typeof ModelSelectorComponent>;
export type QuickActionChip = z.infer<typeof QuickActionChip>;
export type UsageBanner = z.infer<typeof UsageBanner>;
export type MessageBubbleComponent = z.infer<typeof MessageBubbleComponent>;
export type CodeBlockComponent = z.infer<typeof CodeBlockComponent>;
export type ToastNotificationComponent = z.infer<typeof ToastNotificationComponent>;
export type ModalDialogComponent = z.infer<typeof ModalDialogComponent>;
export type DropdownMenuComponent = z.infer<typeof DropdownMenuComponent>;
export type TooltipComponent = z.infer<typeof TooltipComponent>;
export type SidebarLayout = z.infer<typeof SidebarLayout>;
export type MainContentLayout = z.infer<typeof MainContentLayout>;
export type Breakpoint = z.infer<typeof Breakpoint>;
export type SchemaScope = z.infer<typeof SchemaScope>;
export type ComponentManifest = z.infer<typeof ComponentManifest>;
export type UnmodeledComponent = z.infer<typeof UnmodeledComponent>;
// PALS's Law verification types (v2.1)
export type PALSErrorClass = z.infer<typeof PALSErrorClass>;
export type MutationSourceType = z.infer<typeof MutationSourceType>;
export type MutationSource = z.infer<typeof MutationSource>;
export type VerificationCheckStatus = z.infer<typeof VerificationCheckStatus>;
export type VerificationFinding = z.infer<typeof VerificationFinding>;
export type VerificationCheckResult = z.infer<typeof VerificationCheckResult>;
export type VerificationBoundary = z.infer<typeof VerificationBoundary>;
export type SemanticCheckKind = z.infer<typeof SemanticCheckKind>;
export type SemanticCheckResult = z.infer<typeof SemanticCheckResult>;
export type CompletenessAssertion = z.infer<typeof CompletenessAssertion>;
export type CompletenessResult = z.infer<typeof CompletenessResult>;
export type VerificationAuditEntry = z.infer<typeof VerificationAuditEntry>;
export type SnapshotVerificationStatus = z.infer<typeof SnapshotVerificationStatus>;
export type SnapshotVerificationDeclaration = z.infer<typeof SnapshotVerificationDeclaration>;
export type VerificationPolicy = z.infer<typeof VerificationPolicy>;
export type VerificationConfig = z.infer<typeof VerificationConfig>;
export type DesignSystem = z.infer<typeof DesignSystem>;

// ─────────────────────────────────────────────────────────────────────────────
// Schema Exports (for runtime validation)
// ─────────────────────────────────────────────────────────────────────────────

export const schemas = {
  // Primitives
  CSSVariableRef,
  HSLChannels,
  HexColor,

  // Tokens
  ColorToken,
  Theme,
  TypographyToken,
  FontAsset,
  SpacingToken,
  BorderWidthToken,
  BorderRadiusToken,
  ShadowToken,
  ShadowLayer,
  TransitionToken,
  AnimationToken,
  Icon,

  // Infrastructure (v2)
  ComponentTypeName,
  ComponentSlot,
  InteractionModel,
  StateTransition,
  InteractionTrigger,
  TokenResolutionRule,
  ResponsiveAdaptation,

  // Components
  ButtonComponent,
  SidebarItem,
  ChatInputComponent,
  AvatarComponent,
  ModelSelectorComponent,
  QuickActionChip,
  UsageBanner,
  MessageBubbleComponent,
  CodeBlockComponent,
  ToastNotificationComponent,
  ModalDialogComponent,
  DropdownMenuComponent,
  TooltipComponent,

  // Layout & Scope
  SidebarLayout,
  MainContentLayout,
  Breakpoint,
  SchemaScope,
  ComponentManifest,
  UnmodeledComponent,

  // PALS's Law Verification (v2.1)
  PALSErrorClass,
  MutationSourceType,
  MutationSource,
  VerificationCheckStatus,
  VerificationFinding,
  VerificationCheckResult,
  VerificationBoundary,
  SemanticCheckKind,
  SemanticCheckResult,
  CompletenessAssertion,
  CompletenessResult,
  VerificationAuditEntry,
  SnapshotVerificationStatus,
  SnapshotVerificationDeclaration,
  VerificationPolicy,
  VerificationConfig,

  // Root
  DesignSystem,
} as const;

// ─────────────────────────────────────────────────────────────────────────────
// Example: Responsive Adaptation Data  [NEW in v2]
// ─────────────────────────────────────────────────────────────────────────────

/**
 * This section provides example data showing how ResponsiveAdaptation rules
 * would be populated. It is NOT part of the schema — it illustrates usage.
 *
 * const exampleAdaptations: ResponsiveAdaptation[] = [
 *   {
 *     id: "...",
 *     breakpointName: "lg",
 *     target: {
 *       kind: "layout",
 *       section: "sidebar",
 *       property: "position",
 *     },
 *     value: "sticky",
 *     description: "Sidebar switches from fixed overlay to sticky at lg+",
 *   },
 *   {
 *     id: "...",
 *     breakpointName: "lg",
 *     target: {
 *       kind: "component",
 *       componentType: "ChatInput",
 *       property: "paddingX",
 *     },
 *     value: 1.5,
 *     description: "Chat input gets wider horizontal padding on desktop",
 *   },
 *   {
 *     id: "...",
 *     breakpointName: "md",
 *     target: {
 *       kind: "layout",
 *       section: "mainContent",
 *       property: "paddingX",
 *     },
 *     value: 2,
 *     description: "Main content area increases padding at md",
 *   },
 * ];
 */

// ─────────────────────────────────────────────────────────────────────────────
// Example: Component Manifest Data  [NEW in v2]
// ─────────────────────────────────────────────────────────────────────────────

/**
 * const exampleManifest: ComponentManifest = {
 *   modeled: [
 *     "Button", "SidebarItem", "ChatInput", "Avatar", "ModelSelector",
 *     "QuickActionChip", "UsageBanner", "MessageBubble", "CodeBlock",
 *     "ToastNotification", "ModalDialog", "DropdownMenu", "Tooltip",
 *   ],
 *   knownUnmodeled: [
 *     {
 *       typeName: "FileAttachmentCard",
 *       observedIn: ["chat-thread"],
 *       priority: "high",
 *       notes: "Thumbnail card for uploaded files/images in chat input and messages",
 *     },
 *     {
 *       typeName: "LoadingSkeleton",
 *       observedIn: ["home", "chat-thread"],
 *       priority: "medium",
 *       notes: "Shimmer placeholder shown while content loads",
 *     },
 *     {
 *       typeName: "DownloadsPanel",
 *       observedIn: ["home"],
 *       priority: "low",
 *       notes: "Sidebar footer panel listing downloaded artifacts",
 *     },
 *     {
 *       typeName: "ProjectCard",
 *       observedIn: ["home", "projects"],
 *       priority: "medium",
 *       notes: "Card representing a project in the sidebar or projects view",
 *     },
 *     {
 *       typeName: "StarredItemsGroup",
 *       observedIn: ["home"],
 *       priority: "low",
 *       notes: "Grouping wrapper for starred sidebar items with header",
 *     },
 *     {
 *       typeName: "SearchOverlay",
 *       observedIn: ["home"],
 *       priority: "high",
 *       notes: "Full-screen search overlay triggered from sidebar action",
 *     },
 *     {
 *       typeName: "ContextMenu",
 *       observedIn: ["home", "chat-thread"],
 *       priority: "medium",
 *       notes: "Right-click or three-dot context menu; structurally a DropdownMenu variant",
 *     },
 *     {
 *       typeName: "SettingsPanel",
 *       observedIn: ["settings"],
 *       priority: "low",
 *       notes: "Full-page settings layout — not observed in snapshot",
 *     },
 *   ],
 * };
 */

// ─────────────────────────────────────────────────────────────────────────────
// Scorecard — Self-Review (v2.1)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * SCORECARD (Rules for Great Schema Design v2.0.0)
 *
 * Part I — Type Safety and Precision
 *   1. Every field has a single unambiguous type      MUST   → Pass
 *   2. Constraints live in the schema                 MUST   → Pass
 *   3. Enums: closed, versioned, not overloaded       MUST   → Pass
 *   4. Nullable ≠ optional ≠ absent                   MUST   → Pass
 *   5. Arrays: item type + cardinality + order        MUST   → Pass
 *   6. Temporal: precision, timezone, format          MUST   → Pass (datetime strings are ISO 8601)
 *   7. Numeric units declared                         MUST   → Pass (units documented via .describe())
 *   8. Polymorphism: explicit discriminator           MUST   → Pass (discriminatedUnion for targets)
 *   9. Defaults declared in schema                    SHOULD → Pass
 *
 * Part II — Identity and Relationships
 *  10. Stable, opaque identity                        MUST   → Pass (EntityId on every entity)
 *  11. Relationships navigable in ≥1 direction        MUST   → Pass (FK fields + slot containment)
 *  12. Composition / aggregation / association        MUST   → Pass (documented in DesignSystem JSDoc)
 *  13. FK targets declared                            MUST   → Pass (FK → EntityName.id in .describe())
 *  14. Cyclic graph constraints declared              MUST   → Pass
 *
 * Part III — Normalization and Coherence
 *  15. Single source of truth per fact                MUST   → Pass
 *  16. No bag-of-arrays entities                      SHOULD → Warn
 *      Rationale: same as v2 — aggregate root pattern.
 *  17. Cross-cutting types defined once               SHOULD → Pass
 *      (EntityId, TokenRef, PALSErrorClass, VerificationFinding shared)
 *  18. Computed vs. stored distinguished              SHOULD → Pass
 *      (VerificationBoundary.summary is computed; stored for performance)
 *
 * Part IV — Evolution and Compatibility
 *  19. Explicit, monotonic versioning                 MUST   → Pass (SCHEMA_VERSION = "2.1.0")
 *  20. No duplicate-version entities                  MUST   → Pass
 *  21. Breaking changes classified                    MUST   → Pass
 *      Breaking from v2: DesignSystem gains `verification` (required) and
 *      `verificationAuditLog` (defaulted to []). The `verification` field
 *      has all-defaulted children, so migration is: add empty object.
 *  22. Field deprecation annotated                    MUST   → Pass (no deprecated fields)
 *
 * Part V — Operational Annotations
 *  23. Sensitive fields classified                    MAY    → Pass
 *      (MutationSource.apiKeyPrefix is security-adjacent; only prefix stored)
 *  24. Identity/provenance immutability               SHOULD → Pass
 *  25. Localization strategy declared                 SHOULD → Warn
 *      Rationale: same as v2 — tokens are language-independent.
 *  26. Multi-actor provenance metadata                SHOULD → Pass [IMPROVED in v2.1]
 *      MutationSource now tracks actor, sourceType, modelVersion.
 *
 * Part VI — Documentation and Generability
 *  27. Consistent naming (camelCase throughout)       MUST   → Pass
 *  28. Mechanically generatable validators            MUST   → Pass (Zod)
 *  29. Intentional extension points                   MUST   → Pass
 *      (SemanticCheckKind enum is the extension vector for new checks;
 *       CompletenessAssertion is user-definable)
 *  30. Access patterns don't dictate structure        SHOULD → Pass
 *  31. Readable as standalone artifact                MUST   → Pass
 *
 * TOTALS
 *   MUST Pass:              19/19
 *   SHOULD Pass/Documented: 10/11 (1 Warn with rationale; Rule 26 upgraded)
 *
 * PALS's LAW COMPLIANCE (v1.5.4)
 *   Corollary 1 (Appearance ≠ correctness):      ADDRESSED
 *     — SemanticCheckResult goes beyond schema validation
 *   Corollary 2 (Trust accumulation prohibited):  ADDRESSED
 *     — VerificationAuditEntry is append-only; no trust decay
 *     — MutationSource.sourceType tracks provenance per-call
 *   Corollary 3 (Scope must match taxonomy):      ADDRESSED
 *     — VerificationBoundary.checks has exactly 9 entries
 *     — Every error class explicitly passed/failed/skipped
 *   Corollary 4 (Silent acceptance is a defect):  ADDRESSED
 *     — VerificationConfig.mutationPolicy controls enforcement
 *     — SnapshotVerificationDeclaration required on publish
 *   Corollary 5 (Capability shifts verification): ADDRESSED
 *     — MutationSource.modelVersion required for LLM sources
 *     — VerificationConfig.elevatedLLMVerification flag
 *
 * COVERAGE DELTA (v2 → v2.1)
 *   Token layer:       ~80%  (unchanged)
 *   Component layer:   ~55%  (unchanged)
 *   Behavioral layer:  ~30%  (unchanged)
 *   Verification layer:  0% → ~75%  (new; 13 semantic checks, 9-class coverage)
 *   Weighted overall:  ~50% → ~60%
 */
