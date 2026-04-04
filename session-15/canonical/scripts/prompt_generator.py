"""
Character Drawing Prompt Generator
===================================

Generates structured, view-aware prompts for full-body character drawings.
Replaces manual copy-paste with typed parameters and view-specific construction guides.

Usage:
    python prompt_generator.py                  # generates example batch
    python prompt_generator.py --interactive    # interactive mode
    python prompt_generator.py --json input.json # from JSON spec

Disclaimer:
    Anatomical proportions reference standard figure-drawing canons
    (Loomis 8-head, Bridgman). No claim of medical or biomechanical accuracy.
"""

from __future__ import annotations

import json
import sys
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─── Enums ────────────────────────────────────────────────────────────────────


class Sex(Enum):
    FEMALE = "female"
    MALE = "male"


class AgeGroup(Enum):
    CHILD = "child"       # ~6-10 yr
    PRETEEN = "preteen"   # ~11-13 yr
    TEEN = "teen"         # ~14-17 yr
    ADULT = "adult"       # 18+


class View(Enum):
    FRONTAL = "frontal"           # coronal plane
    LATERAL_LEFT = "lateral_left"
    LATERAL_RIGHT = "lateral_right"
    POSTERIOR = "posterior"        # back view
    THREE_QUARTER = "three_quarter"
    TOP_DOWN_TRANSVERSE = "top_down_transverse"
    SAGITTAL = "sagittal"         # median section logic


class Composition(Enum):
    PORTRAIT = "portrait"   # tall
    SQUARE = "square"


class Perspective(Enum):
    EYE_LEVEL = "eye_level"
    SLIGHTLY_ABOVE = "slightly_above"  # top-down bias
    SLIGHTLY_BELOW = "slightly_below"


class Pose(Enum):
    STANDING_NEUTRAL = "standing_neutral"
    WALKING_PHASE_1 = "walking_phase_1"   # contact
    WALKING_PHASE_2 = "walking_phase_2"   # passing
    WALKING_PHASE_3 = "walking_phase_3"   # push-off
    ACTION_READY = "action_ready"
    CUSTOM = "custom"


# ─── Data Models ──────────────────────────────────────────────────────────────


@dataclass
class CharacterPreset:
    """Defines a character reference with outfit and style notes."""
    name: str
    sex: Sex
    age_group: AgeGroup
    height_cm: float
    build: str                   # e.g. "athletic", "lean muscular", "stocky"
    outfit: str                  # outfit description
    style_notes: str = ""        # additional character-specific notes
    inspiration_note: str = ""   # attribution/reference note


@dataclass
class PromptConfig:
    """Full specification for a single prompt."""
    character: CharacterPreset
    view: View
    composition: Composition = Composition.PORTRAIT
    perspective: Perspective = Perspective.SLIGHTLY_ABOVE
    pose: Pose = Pose.STANDING_NEUTRAL
    pose_description: str = ""
    include_scale_bar: bool = True
    show_construction_guides: bool = True
    guides_visible_in_drawing: bool = False  # True = drawn; False = conceptual only
    style_override: str = ""


# ─── Character Library ────────────────────────────────────────────────────────


CHARACTERS: dict[str, CharacterPreset] = {
    "kill_bill_woman": CharacterPreset(
        name="Kill Bill Woman",
        sex=Sex.FEMALE,
        age_group=AgeGroup.ADULT,
        height_cm=175.0,
        build="athletic",
        outfit="fitted leather jacket over a sleek bodysuit, motorcycle helmet with visor",
        inspiration_note="Inspired by the protagonist in Kill Bill",
    ),
    "bruce_lee": CharacterPreset(
        name="Martial Artist",
        sex=Sex.MALE,
        age_group=AgeGroup.ADULT,
        height_cm=172.0,
        build="lean muscular",
        outfit="fitted leather suit with minimal martial-arts aesthetic, "
               "high collar, clean lines",
        inspiration_note="Inspired by classic martial-arts cinema",
    ),
    "lion_o": CharacterPreset(
        name="Lion Warrior",
        sex=Sex.MALE,
        age_group=AgeGroup.ADULT,
        height_cm=188.0,
        build="athletic muscular",
        outfit="fitted armor-like suit with feline motifs, gauntlets, "
               "broad shoulder guards, emblem on chest",
        inspiration_note="Inspired by heroic fantasy warriors",
    ),
    "conan": CharacterPreset(
        name="Barbarian Warrior",
        sex=Sex.MALE,
        age_group=AgeGroup.ADULT,
        height_cm=190.0,
        build="heavy muscular",
        outfit="minimal leather harness, fur loincloth, arm bracers, "
               "broad belt with metal buckle",
        inspiration_note="Inspired by sword-and-sorcery archetypes",
    ),
    "iron_armor": CharacterPreset(
        name="Armored Figure",
        sex=Sex.MALE,
        age_group=AgeGroup.ADULT,
        height_cm=185.0,
        build="athletic",
        outfit="full-body segmented armor with smooth plates, "
               "arc-reactor-style chest circle, helmet with narrow visor slit",
        inspiration_note="Inspired by high-tech powered armor designs",
    ),
    "action_woman": CharacterPreset(
        name="Action Heroine",
        sex=Sex.FEMALE,
        age_group=AgeGroup.ADULT,
        height_cm=170.0,
        build="athletic lean",
        outfit="tactical fitted suit, utility belt, ankle boots",
        inspiration_note="Inspired by action-cinema heroines",
    ),
    "young_hero": CharacterPreset(
        name="Young Hero",
        sex=Sex.MALE,
        age_group=AgeGroup.PRETEEN,
        height_cm=145.0,
        build="athletic lean",
        outfit="stylized adventure outfit, light armor elements, "
               "short cape, boots",
        inspiration_note="Inspired by young adventure protagonists",
    ),
}


# ─── View-Specific Construction Guides ────────────────────────────────────────


def _construction_guides(view: View, config: PromptConfig) -> str:
    """Return construction-guide text appropriate for the anatomical view."""

    visibility = (
        "Construction guides should be drawn as visible reference lines."
        if config.guides_visible_in_drawing
        else "Construction guides are conceptual scaffolding only — "
             "do NOT render them in the final drawing."
    )

    common_geometric = (
        "Use simplified geometric forms: ovals/spheres for joints, "
        "boxes for ribcage and pelvis masses, cylinders for limbs."
    )

    guides: dict[View, str] = {
        View.FRONTAL: textwrap.dedent(f"""\
            Construction guide logic (coronal / frontal plane):
            - Central vertical symmetry axis dividing left and right halves.
            - Horizontal landmark lines at: top of head, acromion (shoulders),
              nipple line, navel / waist, iliac crest (hips), mid-thigh,
              patella (knees), malleoli (ankles).
            - Ribcage and pelvis drawn as tilted rectangular masses with width ratios:
              shoulders ≈ 2× head-widths, waist ≈ 1× head-width, hips per sex.
            - {common_geometric}
            - {visibility}"""),

        View.POSTERIOR: textwrap.dedent(f"""\
            Construction guide logic (posterior / back view):
            - Central vertical axis along spine from occiput to sacrum.
            - Horizontal landmark lines matching frontal view (shoulders, waist,
              hips, knees, ankles) to keep cross-view consistency.
            - Scapulae outlines overlaid on ribcage mass.
            - Gluteal mass indicated as paired ovals below pelvis block.
            - {common_geometric}
            - {visibility}"""),

        View.LATERAL_LEFT: textwrap.dedent(f"""\
            Construction guide logic (left lateral / sagittal view):
            - Vertical plumb line from ear canal through greater trochanter
              to lateral malleolus.
            - Spine S-curve visible: cervical lordosis → thoracic kyphosis →
              lumbar lordosis → sacral curve.
            - Ribcage and pelvis as tilted masses showing anterior-posterior depth.
            - Limbs layered: near-side limbs in full outline, far-side limbs
              with lighter or dashed lines to indicate depth.
            - {common_geometric}
            - {visibility}"""),

        View.LATERAL_RIGHT: textwrap.dedent(f"""\
            Construction guide logic (right lateral / sagittal view):
            - Mirror of left lateral: plumb line from ear to trochanter to ankle.
            - Spine S-curve visible (reversed reading direction).
            - Near-side (right) limbs in full outline; far-side (left) limbs
              lighter/dashed.
            - Ribcage and pelvis depth shown through overlapping masses.
            - {common_geometric}
            - {visibility}"""),

        View.SAGITTAL: textwrap.dedent(f"""\
            Construction guide logic (median sagittal section):
            - Central sagittal plane divides anterior/posterior volumes.
            - Full spine S-curve as primary structural line.
            - Ribcage mass tilted ~30° back from vertical; pelvis tilted ~10° forward.
            - Depth distribution: chest projection forward, gluteal projection backward.
            - Head tilt aligned with cervical spine; helmet follows head angle.
            - {common_geometric}
            - {visibility}"""),

        View.TOP_DOWN_TRANSVERSE: textwrap.dedent(f"""\
            Construction guide logic (superior / transverse plane):
            - Horizontal cross-section ellipses at key levels: cranium, shoulders/
              upper chest, waist, hips/pelvis, mid-thigh.
            - Ellipse rotation indicates torso twist (ribcage vs pelvis alignment).
            - Limb orientation shown as circular cross-sections with rotation markers.
            - Perspective foreshortening: upper body slightly larger, lower body
              recedes.
            - {common_geometric}
            - {visibility}"""),

        View.THREE_QUARTER: textwrap.dedent(f"""\
            Construction guide logic (three-quarter view):
            - Off-center vertical axis showing depth recession.
            - Visible overlap: near shoulder/hip overlaps torso; far shoulder/hip
              partially hidden.
            - Ribcage and pelvis as rotated boxes (approx. 30-45° from frontal).
            - Near-side limbs full; far-side limbs foreshortened.
            - Central line curves across torso surface to indicate volume.
            - {common_geometric}
            - {visibility}"""),
    }

    return guides.get(view, guides[View.FRONTAL])


# ─── Proportion Notes ─────────────────────────────────────────────────────────


def _proportion_notes(char: CharacterPreset) -> str:
    """Return proportion guidance adapted to age group and sex."""

    if char.age_group == AgeGroup.CHILD:
        return (
            "Proportions: approximately 6-head canon. Larger head-to-body ratio, "
            "shorter limbs relative to torso, narrower shoulders. "
            f"Target height: {char.height_cm} cm."
        )
    if char.age_group == AgeGroup.PRETEEN:
        return (
            "Proportions: approximately 6.5-head canon. Head slightly large "
            "relative to adult, limbs lengthening, shoulders beginning to broaden. "
            f"Target height: {char.height_cm} cm."
        )
    if char.age_group == AgeGroup.TEEN:
        return (
            "Proportions: approximately 7-head canon. Near-adult proportions, "
            "slightly narrower shoulders and hips than full adult. "
            f"Target height: {char.height_cm} cm."
        )

    # Adult
    if char.sex == Sex.FEMALE:
        return (
            "Proportions: 8-head adult female canon. Shoulders ≈ 1.5 head-widths, "
            "waist narrower than ribcage, hips approximately shoulder-width or slightly wider. "
            f"Target height: {char.height_cm} cm. Build: {char.build}."
        )
    return (
        "Proportions: 8-head adult male canon. Shoulders ≈ 2+ head-widths, "
        "waist narrower than ribcage, hips narrower than shoulders. "
        f"Target height: {char.height_cm} cm. Build: {char.build}."
    )


# ─── Pose Text ────────────────────────────────────────────────────────────────


_POSE_DESCRIPTIONS: dict[Pose, str] = {
    Pose.STANDING_NEUTRAL: "Standing in a neutral, balanced pose with weight evenly distributed.",
    Pose.WALKING_PHASE_1: "Walking cycle — contact phase: lead foot heel-striking, "
                          "rear foot toe-off, arms in counter-swing.",
    Pose.WALKING_PHASE_2: "Walking cycle — passing phase: weight over support leg, "
                          "swing leg passing underneath, arms near body midline.",
    Pose.WALKING_PHASE_3: "Walking cycle — push-off phase: rear foot pushing off ground, "
                          "lead leg reaching forward, maximum arm swing.",
    Pose.ACTION_READY: "Dynamic ready stance: knees slightly bent, weight on balls of feet, "
                       "hands raised or at guard position.",
}


def _pose_text(config: PromptConfig) -> str:
    if config.pose == Pose.CUSTOM and config.pose_description:
        return f"Pose: {config.pose_description}"
    return f"Pose: {_POSE_DESCRIPTIONS.get(config.pose, 'Standing neutral.')}"


# ─── Prompt Assembly ──────────────────────────────────────────────────────────


def generate_prompt(config: PromptConfig) -> str:
    """Assemble a complete, clean prompt from a PromptConfig."""

    char = config.character
    sex_word = char.sex.value
    age_label = "" if char.age_group == AgeGroup.ADULT else f" {char.age_group.value}"

    view_labels: dict[View, str] = {
        View.FRONTAL: "frontal (coronal plane) view",
        View.POSTERIOR: "posterior (back) view",
        View.LATERAL_LEFT: "left lateral (profile) view",
        View.LATERAL_RIGHT: "right lateral (profile) view",
        View.SAGITTAL: "sagittal plane view",
        View.TOP_DOWN_TRANSVERSE: "superior (top-down) view emphasizing transverse plane",
        View.THREE_QUARTER: "three-quarter view",
    }
    view_label = view_labels.get(config.view, "frontal view")

    comp_label = "portrait (tall)" if config.composition == Composition.PORTRAIT else "square"
    persp_labels = {
        Perspective.EYE_LEVEL: "eye-level",
        Perspective.SLIGHTLY_ABOVE: "slightly above eye-level (mild top-down foreshortening)",
        Perspective.SLIGHTLY_BELOW: "slightly below eye-level (mild worm's-eye foreshortening)",
    }
    persp_label = persp_labels.get(config.perspective, "eye-level")

    # Style
    style_line = config.style_override or (
        "Clean black outline only on a white background. "
        "No shading, no color fills, no hatching."
    )

    # Scale bar
    scale_line = ""
    if config.include_scale_bar:
        scale_line = (
            f"\nInclude a vertical scale bar on the drawing edge, marked in cm, "
            f"calibrated to {char.height_cm} cm total height."
        )

    # Construction guides
    guide_block = ""
    if config.show_construction_guides:
        guide_block = "\n" + _construction_guides(config.view, config)

    # Build final prompt
    parts = [
        f"Full-body{age_label} {sex_word} figure, {view_label}.",
        f"{comp_label.capitalize()} composition, {persp_label} perspective.",
        _proportion_notes(char),
        _pose_text(config),
        "",
        f"Outfit: {char.outfit}.",
        f"Style: {style_line}",
        scale_line,
        guide_block,
    ]

    if char.inspiration_note:
        parts.append(f"\nReference note: {char.inspiration_note}.")

    # Join, collapse multiple blank lines
    raw = "\n".join(parts)
    import re
    cleaned = re.sub(r"\n{3,}", "\n\n", raw).strip()
    return cleaned


# ─── Batch Generation ─────────────────────────────────────────────────────────


def generate_view_set(
    character_key: str,
    views: Optional[list[View]] = None,
    pose: Pose = Pose.STANDING_NEUTRAL,
) -> list[tuple[str, str]]:
    """Generate one prompt per view for a given character. Returns (label, prompt) pairs."""

    if character_key not in CHARACTERS:
        raise ValueError(
            f"Unknown character '{character_key}'. "
            f"Available: {', '.join(CHARACTERS.keys())}"
        )

    char = CHARACTERS[character_key]
    if views is None:
        views = [View.FRONTAL, View.POSTERIOR, View.LATERAL_LEFT,
                 View.LATERAL_RIGHT, View.THREE_QUARTER, View.TOP_DOWN_TRANSVERSE]

    results = []
    for v in views:
        comp = Composition.SQUARE if v == View.TOP_DOWN_TRANSVERSE else Composition.PORTRAIT
        cfg = PromptConfig(
            character=char,
            view=v,
            composition=comp,
            perspective=Perspective.SLIGHTLY_ABOVE,
            pose=pose,
        )
        label = f"{character_key}__{v.value}__{pose.value}"
        results.append((label, generate_prompt(cfg)))

    return results


def generate_walk_cycle(
    character_key: str,
    view: View = View.LATERAL_LEFT,
) -> list[tuple[str, str]]:
    """Generate walking-cycle prompts (3 phases) for a character."""

    char = CHARACTERS[character_key]
    results = []
    for pose in [Pose.WALKING_PHASE_1, Pose.WALKING_PHASE_2, Pose.WALKING_PHASE_3]:
        cfg = PromptConfig(
            character=char,
            view=view,
            composition=Composition.PORTRAIT,
            perspective=Perspective.EYE_LEVEL,
            pose=pose,
        )
        label = f"{character_key}__walk__{pose.value}"
        results.append((label, generate_prompt(cfg)))

    return results


# ─── JSON Input ───────────────────────────────────────────────────────────────


def from_json(path: str) -> list[tuple[str, str]]:
    """
    Load prompt specs from a JSON file. Expected format:

    [
      {
        "character": "kill_bill_woman",
        "view": "frontal",
        "pose": "standing_neutral",
        "composition": "portrait",
        "perspective": "slightly_above",
        "include_scale_bar": true,
        "show_construction_guides": true,
        "guides_visible": false
      },
      ...
    ]
    """
    with open(path) as f:
        specs = json.load(f)

    results = []
    for i, spec in enumerate(specs):
        char_key = spec.get("character", "kill_bill_woman")
        if char_key not in CHARACTERS:
            print(f"[WARN] Spec #{i}: unknown character '{char_key}', skipping.")
            continue

        cfg = PromptConfig(
            character=CHARACTERS[char_key],
            view=View(spec.get("view", "frontal")),
            composition=Composition(spec.get("composition", "portrait")),
            perspective=Perspective(spec.get("perspective", "slightly_above")),
            pose=Pose(spec.get("pose", "standing_neutral")),
            pose_description=spec.get("pose_description", ""),
            include_scale_bar=spec.get("include_scale_bar", True),
            show_construction_guides=spec.get("show_construction_guides", True),
            guides_visible_in_drawing=spec.get("guides_visible", False),
        )
        label = f"spec_{i}__{char_key}__{cfg.view.value}"
        results.append((label, generate_prompt(cfg)))

    return results


# ─── Interactive Mode ─────────────────────────────────────────────────────────


def interactive():
    print("\n=== Character Drawing Prompt Generator ===\n")
    print("Available characters:")
    for i, (key, ch) in enumerate(CHARACTERS.items(), 1):
        print(f"  {i}. {key:20s}  ({ch.sex.value}, {ch.age_group.value}, {ch.height_cm}cm)")

    choice = input("\nSelect character number (or name): ").strip()
    keys = list(CHARACTERS.keys())
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        char_key = keys[int(choice) - 1]
    elif choice in CHARACTERS:
        char_key = choice
    else:
        print(f"Unknown selection '{choice}'.")
        return

    print("\nAvailable views:")
    for i, v in enumerate(View, 1):
        print(f"  {i}. {v.value}")
    view_choice = input("Select view number: ").strip()
    view_list = list(View)
    view = view_list[int(view_choice) - 1] if view_choice.isdigit() else View.FRONTAL

    print("\nAvailable poses:")
    for i, p in enumerate(Pose, 1):
        print(f"  {i}. {p.value}")
    pose_choice = input("Select pose number: ").strip()
    pose_list = list(Pose)
    pose = pose_list[int(pose_choice) - 1] if pose_choice.isdigit() else Pose.STANDING_NEUTRAL

    cfg = PromptConfig(
        character=CHARACTERS[char_key],
        view=view,
        pose=pose,
    )
    prompt = generate_prompt(cfg)
    print("\n" + "=" * 70)
    print(prompt)
    print("=" * 70 + "\n")


# ─── CLI Entry Point ─────────────────────────────────────────────────────────


def main():
    if "--interactive" in sys.argv:
        interactive()
        return

    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        if idx + 1 < len(sys.argv):
            results = from_json(sys.argv[idx + 1])
            for label, prompt in results:
                print(f"\n{'='*70}")
                print(f"[{label}]")
                print(f"{'='*70}")
                print(prompt)
            return
        else:
            print("Error: --json requires a file path argument.")
            return

    # Default: generate a demo batch
    print("Generating demo batch...\n")

    all_results: list[tuple[str, str]] = []

    # Full view set for two characters
    all_results.extend(generate_view_set("kill_bill_woman"))
    all_results.extend(generate_view_set("iron_armor", views=[View.FRONTAL, View.THREE_QUARTER]))

    # Walk cycle
    all_results.extend(generate_walk_cycle("kill_bill_woman"))

    for label, prompt in all_results:
        print(f"\n{'='*70}")
        print(f"[{label}]")
        print(f"{'='*70}")
        print(prompt)

    print(f"\n\nTotal prompts generated: {len(all_results)}")


if __name__ == "__main__":
    main()
