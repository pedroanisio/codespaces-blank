from .shared import *

# =============================================================================
# NERVES — 13
# =============================================================================

NERVE_DEFS = [
    ("Femoral nerve", "mixed", "lumbar", ["L2", "L3", "L4"], None),
    ("Sciatic nerve", "mixed", "sacral", ["L4", "L5", "S1", "S2", "S3"], None),
    ("Tibial nerve", "mixed", "sacral", ["L4", "L5", "S1", "S2", "S3"], "Sciatic nerve"),
    ("Musculocutaneous nerve", "mixed", "brachial", ["C5", "C6", "C7"], None),
    ("Radial nerve", "mixed", "brachial", ["C5", "C6", "C7", "C8", "T1"], None),
    ("Pectoral nerves", "motor", "brachial", ["C5", "C6", "C7", "C8", "T1"], None),
    ("Axillary nerve", "mixed", "brachial", ["C5", "C6"], None),
    ("Thoracodorsal nerve", "motor", "brachial", ["C6", "C7", "C8"], None),
    ("Superior gluteal nerve", "motor", "sacral", ["L4", "L5", "S1"], None),
    ("Inferior gluteal nerve", "motor", "sacral", ["L5", "S1", "S2"], None),
    ("Common peroneal nerve", "mixed", "sacral", ["L4", "L5", "S1", "S2"], "Sciatic nerve"),
    ("Phrenic nerve", "motor", "cervical", ["C3", "C4", "C5"], None),
    ("Spinal accessory nerve (XI)", "motor", "none", ["C1", "C2", "C3", "C4", "C5"], None),
    ("Median nerve", "mixed", "brachial", ["C5", "C6", "C7", "C8", "T1"], None),
    ("Ulnar nerve", "mixed", "brachial", ["C8", "T1"], None),
    ("Obturator nerve", "mixed", "lumbar", ["L2", "L3", "L4"], None),
    ("Pudendal nerve", "mixed", "sacral", ["S2", "S3", "S4"], None),
    ("Subclavian nerve", "motor", "brachial", ["C5", "C6"], None),
    ("Long thoracic nerve", "motor", "brachial", ["C5", "C6", "C7"], None),
    ("Dorsal scapular nerve", "motor", "brachial", ["C5"], None),
    ("Suprascapular nerve", "motor", "brachial", ["C5", "C6"], None),
    ("Subscapular nerve", "motor", "brachial", ["C5", "C6", "C7"], None),
    ("Medial pectoral nerve", "motor", "brachial", ["C8", "T1"], None),
    ("Subcostal nerve", "mixed", "none", ["T12"], None),
    ("Intercostal nerves", "mixed", "none", ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11"], None),
    ("Medial plantar nerve", "mixed", "sacral", ["L4", "L5", "S1"], "Tibial nerve"),
    ("Lateral plantar nerve", "mixed", "sacral", ["S1", "S2"], "Tibial nerve"),
    ("Trigeminal V3", "mixed", "none", ["CN5"], None),
    ("Facial VII", "mixed", "none", ["CN7"], None),
    ("Sacral plexus", "mixed", "sacral", ["L4", "L5", "S1", "S2", "S3"], None),
    ("Lumbar plexus", "mixed", "lumbar", ["L1", "L2", "L3", "L4"], None),
    ("Posterior rami", "mixed", "none", ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12", "L1", "L2", "L3", "L4", "L5"], None),
    ("Ansa cervicalis", "motor", "cervical", ["C1", "C2", "C3"], None),
    ("Cervical plexus", "mixed", "cervical", ["C1", "C2", "C3", "C4"], None),
    # === CRANIAL NERVES (12 pairs, I-XII) ===
    # Reference: Standring, Gray's Anatomy 42nd ed., Ch. 33-38
    # CN V (Trigeminal V3) already present above; CN VII (Facial VII) already present above;
    # CN XI (Spinal accessory nerve) already present above.
    ("Olfactory nerve (I)", "sensory", "none", ["CN1"], None),
    ("Optic nerve (II)", "sensory", "none", ["CN2"], None),
    ("Oculomotor nerve (III)", "motor", "none", ["CN3"], None),
    ("Trochlear nerve (IV)", "motor", "none", ["CN4"], None),
    ("Trigeminal V1 (ophthalmic)", "sensory", "none", ["CN5"], None),
    ("Trigeminal V2 (maxillary)", "sensory", "none", ["CN5"], None),
    ("Abducens nerve (VI)", "motor", "none", ["CN6"], None),
    ("Vestibulocochlear nerve (VIII)", "sensory", "none", ["CN8"], None),
    ("Glossopharyngeal nerve (IX)", "mixed", "none", ["CN9"], None),
    ("Vagus nerve (X)", "mixed", "none", ["CN10"], None),
    ("Hypoglossal nerve (XII)", "motor", "none", ["CN12"], None),
    # === ADDITIONAL PERIPHERAL ===
    ("Deep peroneal nerve", "mixed", "sacral", ["L4", "L5", "S1"], "Common peroneal nerve"),
    ("Superficial peroneal nerve", "mixed", "sacral", ["L5", "S1"], "Common peroneal nerve"),
    ("Lateral femoral cutaneous nerve", "sensory", "lumbar", ["L2", "L3"], None),
    ("Saphenous nerve", "sensory", "lumbar", ["L3", "L4"], "Femoral nerve"),
    ("Sural nerve", "sensory", "sacral", ["S1", "S2"], "Tibial nerve"),
    ("Digital nerves (hand)", "mixed", "brachial", ["C6", "C7", "C8"], "Median nerve"),
]


__all__ = [name for name in globals() if not name.startswith("__")]
