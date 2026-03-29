from .shared import *
from .skeleton import *
from .joints_data import *
from .nerves_data import *

def gen_nerves(r: Reg) -> list[dict]:
    """Generate nerves with anatomically-derived path waypoints.

    Nerve paths computed from spinal exit levels and terminal distribution.
    Each path has 4 waypoints interpolated from the nerve's origin (spinal
    exit or brainstem) to its terminal region.
    """
    _SY: dict[str, float] = {}
    for lv in range(1, 8): _SY[f"C{lv}"] = 155 + (7 - lv) * 1.7
    for lv in range(1, 13): _SY[f"T{lv}"] = 113 + (12 - lv) * 2.3
    for lv in range(1, 6): _SY[f"L{lv}"] = 95 + (5 - lv) * 3.6
    for lv in range(1, 5): _SY[f"S{lv}"] = 90 - lv * 2

    _TY = {"brachial": 90, "lumbar": 50, "sacral": 30, "cervical": 155, "none": 165}

    nerves = []
    for name, ntype, plexus, roots, parent_name in NERVE_DEFS:
        nid = uid()
        r.nerve_ids.append(nid)
        r.nerve_name_to_idx[name] = len(r.nerve_ids) - 1
        parent_id = r.nerve_ids[r.nerve_name_to_idx[parent_name]] if parent_name else None
        oy = _SY.get(roots[0], 120)
        ty = _TY.get(plexus, 100)
        lx = -15.0 if plexus == "brachial" else (-6.0 if plexus in ("lumbar", "sacral") else 0.0)
        path = []
        for pi in range(4):
            t = pi / 3.0
            path.append(vec3(
                round(lx * t + random.uniform(-0.5, 0.5), 1),
                round(oy + (ty - oy) * t, 1),
                round(-2 + random.uniform(-0.5, 0.5), 1)))
        nerves.append({
            "id": nid, "name": name, "type": ntype, "plexus": plexus,
            "spinalRoots": roots, "parentNerveId": parent_id, "path": path,
        })
    return nerves
# =============================================================================
# ORGANS — 9
# =============================================================================

def gen_organs(r: Reg, sex: str = "male") -> list[dict]:
    """Generate organs including sex-specific reproductive anatomy.

    Organ masses from ICRP Publication 89, 'Basic Anatomical and
    Physiological Data for Use in Radiological Protection', 2002.
    Reproductive organ data sex-specific per biologicalSex field.
    """
    defs: list[tuple[str, str, float, float, bool, bool, str, tuple]] = [
        # === CARDIOVASCULAR ===
        ("Heart", "cardiovascular", 300, 310, True, False, "midline", (0, 130, 3)),
        # === RESPIRATORY ===
        ("Lung (R)", "respiratory", 1400, 600, True, True, "right", (-10, 135, 0)),
        ("Lung (L)", "respiratory", 1200, 530, True, True, "left", (10, 135, 0)),
        ("Trachea", "respiratory", 30, 30, False, False, "midline", (0, 150, 4)),
        ("Larynx", "respiratory", 20, 25, False, False, "midline", (0, 153, 5)),
        # === DIGESTIVE ===
        ("Liver", "digestive", 1500, 1800, True, False, "right", (-8, 115, 3)),
        ("Stomach", "digestive", 950, 150, False, False, "left", (5, 118, 3)),
        ("Pancreas", "digestive", 70, 100, False, False, "midline", (0, 112, -1)),
        ("Gallbladder", "digestive", 50, 30, False, False, "right", (-6, 112, 4)),
        ("Small intestine", "digestive", 900, 1000, False, False, "midline", (0, 100, 3)),
        ("Large intestine", "digestive", 700, 500, False, False, "midline", (0, 98, 2)),
        ("Esophagus", "digestive", 40, 50, False, False, "midline", (0, 140, -1)),
        ("Appendix", "digestive", 7, 8, False, False, "right", (-7, 94, 4)),
        ("Tongue", "digestive", 60, 70, False, False, "midline", (0, 163, 5)),
        ("Pharynx", "digestive", 30, 35, False, False, "midline", (0, 158, 2)),
        # === NERVOUS ===
        ("Brain", "nervous", 1400, 1400, True, False, "midline", (0, 168, 0)),
        ("Spinal cord", "nervous", 30, 35, True, False, "midline", (0, 120, -2)),
        ("Eye (R)", "nervous", 7, 7.5, False, True, "right", (-3, 170, 7)),
        ("Eye (L)", "nervous", 7, 7.5, False, True, "left", (3, 170, 7)),
        # === URINARY ===
        ("Kidney (R)", "urinary", 150, 140, False, True, "right", (-6, 110, -5)),
        ("Kidney (L)", "urinary", 150, 140, False, True, "left", (6, 110, -5)),
        ("Bladder", "urinary", 500, 50, False, False, "midline", (0, 88, 4)),
        ("Ureter (R)", "urinary", 5, 6, False, True, "right", (-5, 100, -3)),
        ("Ureter (L)", "urinary", 5, 6, False, True, "left", (5, 100, -3)),
        # === ENDOCRINE ===
        ("Thyroid gland", "endocrine", 20, 25, False, False, "midline", (0, 155, 5)),
        ("Adrenal gland (R)", "endocrine", 6, 5, False, True, "right", (-4, 112, -4)),
        ("Adrenal gland (L)", "endocrine", 6, 5, False, True, "left", (4, 112, -4)),
        ("Parathyroid glands", "endocrine", 0.5, 0.12, False, False, "midline", (0, 154, 4)),
        ("Pituitary gland", "endocrine", 0.6, 0.6, True, False, "midline", (0, 168, 1)),
        ("Pineal gland", "endocrine", 0.2, 0.15, False, False, "midline", (0, 170, -1)),
        # === LYMPHATIC ===
        ("Spleen", "lymphatic", 200, 180, False, False, "left", (10, 115, -2)),
        ("Thymus", "lymphatic", 25, 30, False, False, "midline", (0, 138, 4)),
        # === INTEGUMENTARY ===
        ("Skin", "integumentary", 3000, 4000, False, False, "midline", (0, 95, 0)),
    ]

    # Sex-specific reproductive organs
    # Masses from ICRP 89 (2002) Table 2.9
    if sex == "male":
        defs += [
            ("Prostate", "reproductive", 20, 16, False, False, "midline", (0, 86, 3)),
            ("Testis (R)", "reproductive", 20, 20, False, True, "right", (-2, 80, 6)),
            ("Testis (L)", "reproductive", 20, 20, False, True, "left", (2, 80, 6)),
            ("Seminal vesicle (R)", "reproductive", 4, 5, False, True, "right", (-2, 87, 2)),
            ("Seminal vesicle (L)", "reproductive", 4, 5, False, True, "left", (2, 87, 2)),
        ]
    elif sex == "female":
        defs += [
            ("Uterus", "reproductive", 80, 90, False, False, "midline", (0, 88, 3)),
            ("Ovary (R)", "reproductive", 6, 7, False, True, "right", (-3, 89, 2)),
            ("Ovary (L)", "reproductive", 6, 7, False, True, "left", (3, 89, 2)),
            ("Fallopian tube (R)", "reproductive", 3, 4, False, True, "right", (-4, 89, 2)),
            ("Fallopian tube (L)", "reproductive", 3, 4, False, True, "left", (4, 89, 2)),
        ]

    organs = []
    for name, system, vol, mass, vital, paired, lat, pos in defs:
        oid = uid(); r.organ_ids.append(oid)
        organs.append({"id": oid, "name": name, "system": system, "transform": tf(*pos),
                        "volume": vol, "mass": mass, "isVital": vital, "pairedOrgan": paired, "laterality": lat})
    return organs
# =============================================================================
# VASCULAR — 20 vessels
# =============================================================================

def gen_vascular(r: Reg) -> list[dict]:
    """Generate ~70 vessels: complete arterial tree from aorta to terminal branches,
    venous return, portal circulation, coronary, pulmonary, and cerebral.

    Vessel calibers from:
      - Aorta: Redheuil et al., Radiology 260(2):454-462, 2011
      - Coronary: Dodge et al., Circulation 86(1):232-246, 1992
      - Cerebral: Kochanowicz et al., Med Sci Monit 15(10):MT135-139, 2009
      - Peripheral: Gray's Anatomy 42nd ed. (2020), Ch. 72-80
    """
    vessels: list[dict] = []

    def _art(name, pi, rad, path, **kw):
        vid = uid(); r.vessel_ids.append(vid)
        v: dict = {"id": vid, "name": name, "vesselType": "artery", "path": path,
                    "averageLumenRadius": round(rad * 10, 1), "parentVesselId": r.vessel_ids[pi] if pi is not None else None}
        v.update(kw); vessels.append(v)

    def _vein(name, pi, rad, path, **kw):
        vid = uid(); r.vessel_ids.append(vid)
        v: dict = {"id": vid, "name": name, "vesselType": "vein", "path": path,
                    "averageLumenRadius": round(rad * 10, 1), "parentVesselId": r.vessel_ids[pi] if pi is not None else None,
                    "hasValves": kw.pop("hasValves", True)}
        v.update(kw); vessels.append(v)

    # =======================  ARTERIAL TREE  =======================
    _art("Aorta", None, 1.5, [vec3(0,135,3), vec3(0,125,1), vec3(0,110,0), vec3(0,95,-1), vec3(0,70,-2)],  # 0
         systolicPressure=120, diastolicPressure=80, oxygenSaturation=98)
    # --- Abdominal branches ---
    _art("Celiac trunk", 0, 0.6, [vec3(0,115,3), vec3(0,112,5)])                                            # 1
    _art("Hepatic artery", 1, 0.3, [vec3(0,112,5), vec3(-5,112,4)])                                         # 2
    _art("Splenic artery", 1, 0.35, [vec3(0,112,5), vec3(8,112,0)])                                         # 3
    _art("Left gastric artery", 1, 0.2, [vec3(0,112,5), vec3(3,116,4)])                                     # 4
    _art("Superior mesenteric artery", 0, 0.5, [vec3(0,113,3), vec3(0,105,5)])                               # 5
    _art("Inferior mesenteric artery", 0, 0.3, [vec3(0,95,2), vec3(0,85,4)])                                 # 6
    _art("Renal artery (R)", 0, 0.35, [vec3(-2,110,-2), vec3(-6,110,-5)])                                    # 7
    _art("Renal artery (L)", 0, 0.35, [vec3(2,110,-2), vec3(6,110,-5)])                                     # 8
    _art("Gonadal artery (R)", 0, 0.1, [vec3(-2,105,-1), vec3(-3,92,2)])                                    # 9
    _art("Gonadal artery (L)", 0, 0.1, [vec3(2,105,-1), vec3(3,92,2)])                                     # 10
    # --- Iliac and lower limb ---
    _art("Common iliac (R)", 0, 0.8, [vec3(-3,70,-2), vec3(-7,60,-1)])                                      # 11
    _art("Common iliac (L)", 0, 0.8, [vec3(3,70,-2), vec3(7,60,-1)])                                        # 12
    _art("Internal iliac (R)", 11, 0.4, [vec3(-7,60,-1), vec3(-6,55,-3)])                                    # 13
    _art("Internal iliac (L)", 12, 0.4, [vec3(7,60,-1), vec3(6,55,-3)])                                     # 14
    _art("External iliac (R)", 11, 0.5, [vec3(-7,60,-1), vec3(-9,55,0)])                                     # 15
    _art("External iliac (L)", 12, 0.5, [vec3(7,60,-1), vec3(9,55,0)])                                      # 16
    _art("Femoral artery (R)", 15, 0.5, [vec3(-9,55,0), vec3(-9,45,0), vec3(-9,30,0)])                       # 17
    _art("Femoral artery (L)", 16, 0.5, [vec3(9,55,0), vec3(9,45,0), vec3(9,30,0)])                          # 18
    _art("Deep femoral artery (R)", 17, 0.35, [vec3(-9,52,0), vec3(-10,45,-2)])                              # 19
    _art("Deep femoral artery (L)", 18, 0.35, [vec3(9,52,0), vec3(10,45,-2)])                                # 20
    _art("Popliteal artery (R)", 17, 0.3, [vec3(-9,30,0), vec3(-9,25,-1)])                                   # 21
    _art("Popliteal artery (L)", 18, 0.3, [vec3(9,30,0), vec3(9,25,-1)])                                     # 22
    _art("Posterior tibial artery (R)", 21, 0.2, [vec3(-9,25,0), vec3(-9,15,1), vec3(-9,5,2)])                # 23
    _art("Posterior tibial artery (L)", 22, 0.2, [vec3(9,25,0), vec3(9,15,1), vec3(9,5,2)])                   # 24
    _art("Anterior tibial artery (R)", 21, 0.18, [vec3(-9,25,1), vec3(-9,15,3), vec3(-9,5,5)])                # 25
    _art("Anterior tibial artery (L)", 22, 0.18, [vec3(9,25,1), vec3(9,15,3), vec3(9,5,5)])                   # 26
    _art("Dorsalis pedis (R)", 25, 0.12, [vec3(-9,3,6), vec3(-9,0,10)])                                      # 27
    _art("Dorsalis pedis (L)", 26, 0.12, [vec3(9,3,6), vec3(9,0,10)])                                        # 28
    # --- Upper limb ---
    _art("Subclavian artery (R)", 0, 0.55, [vec3(-2,140,2), vec3(-12,145,1)])                                # 29
    _art("Subclavian artery (L)", 0, 0.55, [vec3(2,140,2), vec3(12,145,1)])                                  # 30
    _art("Brachial artery (R)", 29, 0.35, [vec3(-18,145,0), vec3(-23,130,0), vec3(-25,112,0)])               # 31
    _art("Brachial artery (L)", 30, 0.35, [vec3(18,145,0), vec3(23,130,0), vec3(25,112,0)])                  # 32
    _art("Radial artery (R)", 31, 0.15, [vec3(-25,112,2), vec3(-26,95,3)])                                   # 33
    _art("Radial artery (L)", 32, 0.15, [vec3(25,112,2), vec3(26,95,3)])                                     # 34
    _art("Ulnar artery (R)", 31, 0.15, [vec3(-24,112,-1), vec3(-26,95,1)])                                   # 35
    _art("Ulnar artery (L)", 32, 0.15, [vec3(24,112,-1), vec3(26,95,1)])                                     # 36
    # --- Head and neck ---
    _art("Common carotid (R)", 0, 0.4, [vec3(-2,135,3), vec3(-3,150,2)])                                     # 37
    _art("Common carotid (L)", 0, 0.4, [vec3(2,135,3), vec3(3,150,2)])                                       # 38
    _art("Internal carotid (R)", 37, 0.25, [vec3(-3,150,2), vec3(-3,160,1), vec3(-2,168,0)])                  # 39
    _art("Internal carotid (L)", 38, 0.25, [vec3(3,150,2), vec3(3,160,1), vec3(2,168,0)])                     # 40
    _art("External carotid (R)", 37, 0.25, [vec3(-3,150,3), vec3(-4,158,4)])                                  # 41
    _art("External carotid (L)", 38, 0.25, [vec3(3,150,3), vec3(4,158,4)])                                    # 42
    _art("Vertebral artery (R)", 29, 0.2, [vec3(-5,145,-2), vec3(-3,155,-2), vec3(-1,165,-3)])                # 43
    _art("Vertebral artery (L)", 30, 0.2, [vec3(5,145,-2), vec3(3,155,-2), vec3(1,165,-3)])                   # 44
    _art("Basilar artery", 43, 0.22, [vec3(0,165,-3), vec3(0,168,-2)])                                       # 45
    # Circle of Willis
    _art("Anterior cerebral artery (R)", 39, 0.12, [vec3(-1,168,1), vec3(0,170,2)])                           # 46
    _art("Anterior cerebral artery (L)", 40, 0.12, [vec3(1,168,1), vec3(0,170,2)])                            # 47
    _art("Middle cerebral artery (R)", 39, 0.16, [vec3(-2,168,0), vec3(-5,170,0)])                            # 48
    _art("Middle cerebral artery (L)", 40, 0.16, [vec3(2,168,0), vec3(5,170,0)])                              # 49
    _art("Posterior cerebral artery (R)", 45, 0.1, [vec3(-1,168,-1), vec3(-3,170,-1)])                        # 50
    _art("Posterior cerebral artery (L)", 45, 0.1, [vec3(1,168,-1), vec3(3,170,-1)])                          # 51
    # Circle of Willis communicating arteries
    _art("Anterior communicating artery", 46, 0.08, [vec3(-0.5,170,2), vec3(0.5,170,2)])
    _art("Posterior communicating artery (R)", 39, 0.06, [vec3(-2,168,0), vec3(-1,168,-1)])
    _art("Posterior communicating artery (L)", 40, 0.06, [vec3(2,168,0), vec3(1,168,-1)])
    # --- Axillary arteries (between subclavian and brachial) ---
    _art("Axillary artery (R)", 29, 0.45, [vec3(-12,145,1), vec3(-18,145,0)])
    _art("Axillary artery (L)", 30, 0.45, [vec3(12,145,1), vec3(18,145,0)])
    # --- Peroneal (fibular) arteries ---
    _art("Peroneal artery (R)", 21, 0.15, [vec3(-11,25,-1), vec3(-12,15,-1), vec3(-12,5,-1)])
    _art("Peroneal artery (L)", 22, 0.15, [vec3(11,25,-1), vec3(12,15,-1), vec3(12,5,-1)])
    # --- Coronary ---
    _art("Left coronary artery (LCA)", 0, 0.2, [vec3(-1,133,4), vec3(-3,131,5), vec3(-4,128,4)])             # 52
    _art("Left anterior descending", 52, 0.15, [vec3(-3,131,5), vec3(-2,127,5)])                              # 53
    _art("Left circumflex", 52, 0.12, [vec3(-3,131,5), vec3(-5,130,3)])                                       # 54
    _art("Right coronary artery (RCA)", 0, 0.18, [vec3(1,133,4), vec3(2,131,5), vec3(3,128,3)])              # 55
    # --- Pulmonary ---
    _art("Pulmonary trunk", None, 1.3, [vec3(1,132,5), vec3(0,130,4)], oxygenSaturation=75)                  # 56
    _art("Pulmonary artery (R)", 56, 0.9, [vec3(-2,130,3), vec3(-8,132,1)])                                  # 57
    _art("Pulmonary artery (L)", 56, 0.9, [vec3(2,130,3), vec3(8,132,1)])                                    # 58

    # === BRANCH ARTERIES referenced by muscle bloodSupply ===
    # These smaller arteries are required for bloodSupply.primaryArteryId resolution.
    # Parent indices: 31=Brachial(R), 32=Brachial(L), 29=Subclavian(R), 30=Subclavian(L)
    #   41=Ext carotid(R), 42=Ext carotid(L), 13=Int iliac(R), 14=Int iliac(L)
    #   0=Aorta, 35=Ulnar(R), 36=Ulnar(L), 23=Post tib(R), 24=Post tib(L)
    #   19=Deep fem(R), 20=Deep fem(L)
    # Reference: Gray's Anatomy 42nd ed. (2020), arterial distribution tables
    _art("Deep brachial artery (R)", 31, 0.15, [vec3(-22,140,0), vec3(-23,130,-2)])
    _art("Deep brachial artery (L)", 32, 0.15, [vec3(22,140,0), vec3(23,130,-2)])
    _art("Deep palmar arch (R)", 35, 0.08, [vec3(-26,88,2), vec3(-27,86,3)])
    _art("Deep palmar arch (L)", 36, 0.08, [vec3(26,88,2), vec3(27,86,3)])
    _art("External carotid artery (R)", 41, 0.2, [vec3(-4,158,4), vec3(-5,162,5)])
    _art("External carotid artery (L)", 42, 0.2, [vec3(4,158,4), vec3(5,162,5)])
    _art("Facial artery (R)", 41, 0.12, [vec3(-4,160,4), vec3(-3,165,6)])
    _art("Facial artery (L)", 42, 0.12, [vec3(4,160,4), vec3(3,165,6)])
    _art("Superior gluteal artery (R)", 13, 0.2, [vec3(-6,55,-3), vec3(-8,60,-4)])
    _art("Superior gluteal artery (L)", 14, 0.2, [vec3(6,55,-3), vec3(8,60,-4)])
    _art("Obturator artery (R)", 13, 0.15, [vec3(-6,55,-2), vec3(-7,52,0)])
    _art("Obturator artery (L)", 14, 0.15, [vec3(6,55,-2), vec3(7,52,0)])
    _art("Suprascapular artery (R)", 29, 0.12, [vec3(-10,148,0), vec3(-16,146,-3)])
    _art("Suprascapular artery (L)", 30, 0.12, [vec3(10,148,0), vec3(16,146,-3)])
    _art("Thoracoacromial artery (R)", 29, 0.12, [vec3(-10,148,1), vec3(-14,146,2)])
    _art("Thoracoacromial artery (L)", 30, 0.12, [vec3(10,148,1), vec3(14,146,2)])
    _art("Posterior interosseous artery (R)", 35, 0.08, [vec3(-24,112,-1), vec3(-25,100,-2)])
    _art("Posterior interosseous artery (L)", 36, 0.08, [vec3(24,112,-1), vec3(25,100,-2)])
    _art("Medial plantar artery (R)", 23, 0.1, [vec3(-9,3,3), vec3(-8,1,8)])
    _art("Medial plantar artery (L)", 24, 0.1, [vec3(9,3,3), vec3(8,1,8)])
    _art("Transverse cervical artery (R)", 29, 0.1, [vec3(-8,148,-1), vec3(-16,146,-4)])
    _art("Transverse cervical artery (L)", 30, 0.1, [vec3(8,148,-1), vec3(16,146,-4)])
    _art("Lumbar arteries", 0, 0.15, [vec3(0,105,-2), vec3(-3,100,-4), vec3(3,95,-4)])
    _art("Superior epigastric artery", 0, 0.1, [vec3(0,120,4), vec3(0,110,5)])
    _art("Intercostal arteries", 0, 0.08, [vec3(-8,130,0), vec3(-12,125,0)])
    _art("Regional artery", 0, 0.08, [vec3(0,120,2), vec3(0,115,2)])

    # =======================  VENOUS TREE  =======================
    ivc_i = len(vessels)  # IVC index
    _vein("Inferior vena cava", None, 1.8, [vec3(1,70,-2), vec3(1,100,0), vec3(1,135,3)], hasValves=False)   # 59
    svc_i = len(vessels)
    _vein("Superior vena cava", None, 1.2, [vec3(-1,145,2), vec3(-1,135,3)], hasValves=False)                # 60
    # --- Lower limb veins ---
    _vein("Great saphenous (R)", ivc_i, 0.4, [vec3(-10,5,2), vec3(-9,30,0), vec3(-9,60,0)])                  # 61
    _vein("Great saphenous (L)", ivc_i, 0.4, [vec3(10,5,2), vec3(9,30,0), vec3(9,60,0)])                     # 62
    _vein("Small saphenous (R)", ivc_i, 0.3, [vec3(-11,5,-2), vec3(-10,25,-2)])                              # 63
    _vein("Small saphenous (L)", ivc_i, 0.3, [vec3(11,5,-2), vec3(10,25,-2)])                                # 64
    _vein("Popliteal vein (R)", ivc_i, 0.5, [vec3(-9,25,-1), vec3(-9,45,-1)])                                # 65
    _vein("Popliteal vein (L)", ivc_i, 0.5, [vec3(9,25,-1), vec3(9,45,-1)])                                  # 66
    _vein("Femoral vein (R)", ivc_i, 0.55, [vec3(-9,50,0), vec3(-9,70,0)])                                   # 67
    _vein("Femoral vein (L)", ivc_i, 0.55, [vec3(9,50,0), vec3(9,70,0)])                                     # 68
    # --- Upper limb veins ---
    _vein("Subclavian vein (R)", svc_i, 0.6, [vec3(-15,145,1), vec3(-5,145,2)])                              # 69
    _vein("Subclavian vein (L)", svc_i, 0.6, [vec3(15,145,1), vec3(5,145,2)])                                # 70
    _vein("Basilic vein (R)", 69, 0.25, [vec3(-25,112,0), vec3(-20,135,-1)])                                 # 71
    _vein("Basilic vein (L)", 70, 0.25, [vec3(25,112,0), vec3(20,135,-1)])                                   # 72
    _vein("Cephalic vein (R)", 69, 0.25, [vec3(-25,112,2), vec3(-15,140,2)])                                 # 73
    _vein("Cephalic vein (L)", 70, 0.25, [vec3(25,112,2), vec3(15,140,2)])                                   # 74
    # --- Head and neck veins ---
    _vein("Internal jugular vein (R)", svc_i, 0.7, [vec3(-3,160,2), vec3(-2,145,3)])                         # 75
    _vein("Internal jugular vein (L)", svc_i, 0.7, [vec3(3,160,2), vec3(2,145,3)])                           # 76
    _vein("External jugular vein (R)", svc_i, 0.3, [vec3(-5,158,3), vec3(-4,145,3)])                         # 77
    _vein("External jugular vein (L)", svc_i, 0.3, [vec3(5,158,3), vec3(4,145,3)])                           # 78
    # --- Visceral veins ---
    _vein("Portal vein", ivc_i, 0.6, [vec3(0,108,4), vec3(-5,112,3)], hasValves=False)                       # 79
    _vein("Hepatic vein (R)", ivc_i, 0.5, [vec3(-8,115,2), vec3(-4,120,3)])                                  # 80
    _vein("Hepatic vein (L)", ivc_i, 0.5, [vec3(4,115,2), vec3(2,120,3)])                                    # 81
    _vein("Hepatic vein (middle)", ivc_i, 0.4, [vec3(-2,115,3), vec3(-1,120,3)])                             # 82
    _vein("Splenic vein", 79, 0.4, [vec3(10,112,-1), vec3(3,110,3)])                                         # 83
    _vein("Superior mesenteric vein", 79, 0.5, [vec3(0,105,5), vec3(0,108,4)])                               # 84
    _vein("Inferior mesenteric vein", 83, 0.3, [vec3(0,90,4), vec3(3,105,2)])                                # → splenic vein
    _vein("Renal vein (R)", ivc_i, 0.4, [vec3(-6,110,-4), vec3(-2,110,-2)])                                  # 85
    _vein("Renal vein (L)", ivc_i, 0.45, [vec3(6,110,-4), vec3(2,110,-2)])                                   # 86
    # --- Pulmonary veins ---
    _vein("Pulmonary vein (R superior)", None, 0.6, [vec3(-8,133,1), vec3(-1,133,3)],
          hasValves=False, oxygenSaturation=98)                                                               # 87
    _vein("Pulmonary vein (R inferior)", None, 0.5, [vec3(-8,130,0), vec3(-1,132,3)],
          hasValves=False, oxygenSaturation=98)                                                               # 88
    _vein("Pulmonary vein (L superior)", None, 0.6, [vec3(8,133,1), vec3(1,133,3)],
          hasValves=False, oxygenSaturation=98)                                                               # 89
    _vein("Pulmonary vein (L inferior)", None, 0.5, [vec3(8,130,0), vec3(1,132,3)],
          hasValves=False, oxygenSaturation=98)                                                               # 90
    # --- Cerebral veins ---
    _vein("Superior sagittal sinus", svc_i, 0.5, [vec3(0,174,0), vec3(0,170,-4)], hasValves=False)           # 91
    _vein("Transverse sinus (R)", 91, 0.4, [vec3(0,170,-4), vec3(-5,168,-3)], hasValves=False)               # 92
    _vein("Transverse sinus (L)", 91, 0.4, [vec3(0,170,-4), vec3(5,168,-3)], hasValves=False)                # 93

    return vessels
# =============================================================================
# LIGAMENTS — 12
# =============================================================================

def gen_ligaments(r: Reg) -> list[dict]:
    defs = [
        ("Anterior cruciate ligament (R)", B_FEM_R, B_TIB_R, J_KNEE_R, 3.2),
        ("Posterior cruciate ligament (R)", B_FEM_R, B_TIB_R, J_KNEE_R, 3.8),
        ("Medial collateral ligament (R)", B_FEM_R, B_TIB_R, J_KNEE_R, 8),
        ("Lateral collateral ligament (R)", B_FEM_R, B_TIB_R, J_KNEE_R, 5.5),
        ("Anterior cruciate ligament (L)", B_FEM_L, B_TIB_L, J_KNEE_L, 3.2),
        ("Posterior cruciate ligament (L)", B_FEM_L, B_TIB_L, J_KNEE_L, 3.8),
        ("Iliofemoral ligament (R)", B_HIP_R, B_FEM_R, J_HIP_R, 8.5),
        ("Iliofemoral ligament (L)", B_HIP_L, B_FEM_L, J_HIP_L, 8.5),
        ("Glenohumeral ligament (R)", B_SCAP_R, B_HUMER_R, J_SHOULDER_R, 3.5),
        ("Glenohumeral ligament (L)", B_SCAP_L, B_HUMER_L, J_SHOULDER_L, 3.5),
        ("Anterior longitudinal ligament (lumbar)", B_SACRUM, B_L1, J_L5S1, 15),
        ("Posterior longitudinal ligament (lumbar)", B_SACRUM, B_L1, J_L5S1, 14),
        ("Deltoid ligament (R)", B_TIB_R, B_FOOT_R_TALUS, J_ANKLE_R, 4),
        ("Deltoid ligament (L)", B_TIB_L, B_FOOT_L_START + 1, J_ANKLE_L, 4),
        ("Anterior talofibular ligament (R)", B_FIB_R, B_FOOT_R_TALUS, J_ANKLE_R, 2),
        ("Anterior talofibular ligament (L)", B_FIB_L, B_FOOT_L_START + 1, J_ANKLE_L, 2),
        ("Calcaneofibular ligament (R)", B_FIB_R, B_FOOT_R_CALCANEUS, J_ANKLE_R, 3),
        ("Calcaneofibular ligament (L)", B_FIB_L, B_FOOT_L_START, J_ANKLE_L, 3),
        ("Pubofemoral ligament (R)", B_HIP_R, B_FEM_R, J_HIP_R, 6),
        ("Pubofemoral ligament (L)", B_HIP_L, B_FEM_L, J_HIP_L, 6),
        ("Ischiofemoral ligament (R)", B_HIP_R, B_FEM_R, J_HIP_R, 5),
        ("Ischiofemoral ligament (L)", B_HIP_L, B_FEM_L, J_HIP_L, 5),
        ("Coracoacromial ligament (R)", B_SCAP_R, B_SCAP_R, J_SHOULDER_R, 3),
        ("Coracoacromial ligament (L)", B_SCAP_L, B_SCAP_L, J_SHOULDER_L, 3),
        ("Medial collateral ligament (L)", B_FEM_L, B_TIB_L, J_KNEE_L, 8),
        ("Lateral collateral ligament (L)", B_FEM_L, B_TIB_L, J_KNEE_L, 5.5),
        # Spinal ligaments for new IVD joints (Round 3)
        ("Ligamentum flavum (L5-L4)", B_L5, B_L5 + 1, 9, 3),
        ("Ligamentum flavum (L4-L3)", B_L5 + 1, B_L5 + 2, 10, 3),
        ("Ligamentum flavum (L3-L2)", B_L5 + 2, B_L5 + 3, 11, 3),
        ("Ligamentum flavum (L2-L1)", B_L5 + 3, B_L1, 12, 3),
        ("Ligamentum flavum (T12-L1)", B_L1, B_T12, 13, 2.5),
        ("Interspinous ligament (lumbar)", B_SACRUM, B_L1, J_L5S1, 12),
        ("Supraspinous ligament (thoracolumbar)", B_L5, B_T1, J_L5S1, 35),
        # Sacroiliac ligaments
        ("Anterior sacroiliac ligament (R)", B_SACRUM, B_HIP_R, J_SI_R, 4),
        ("Anterior sacroiliac ligament (L)", B_SACRUM, B_HIP_L, J_SI_L, 4),
        ("Posterior sacroiliac ligament (R)", B_SACRUM, B_HIP_R, J_SI_R, 5),
        ("Posterior sacroiliac ligament (L)", B_SACRUM, B_HIP_L, J_SI_L, 5),
        # Sternoclavicular ligaments
        ("Costoclavicular ligament (R)", B_RIB_R[0], B_CLAV_R, J_SC_R, 2.5),
        ("Costoclavicular ligament (L)", B_RIB_L[0], B_CLAV_L, J_SC_L, 2.5),
        # Foot ligaments
        ("Plantar fascia (R)", B_FOOT_R_CALCANEUS, B_FOOT_R_MT[0], J_SUBTALAR_R, 15),
        ("Plantar fascia (L)", B_FOOT_L_START, B_FOOT_L_START + 7, J_SUBTALAR_L, 15),
        ("Spring ligament (R)", B_FOOT_R_CALCANEUS, B_FOOT_R_NAVICULAR, J_SUBTALAR_R, 3),
        ("Spring ligament (L)", B_FOOT_L_START, B_FOOT_L_START + 2, J_SUBTALAR_L, 3),
    ]
    ligs = []
    for name, ob, ib, ji, length in defs:
        lid = uid(); r.ligament_ids.append(lid)
        ligs.append({"id": lid, "name": name,
            "originBoneId": r.bone_ids[ob],
            "originPosition": vec3(
                random.uniform(-0.3, 0.3) * BONE_DEFS[ob][5],
                BONE_DEFS[ob][4] * random.uniform(0.2, 0.4),
                random.choice([-1, 1]) * random.uniform(0.2, 0.5) * BONE_DEFS[ob][6]),
            "insertionBoneId": r.bone_ids[ib],
            "insertionPosition": vec3(
                random.uniform(-0.3, 0.3) * BONE_DEFS[ib][5],
                -BONE_DEFS[ib][4] * random.uniform(0.2, 0.4),
                random.choice([-1, 1]) * random.uniform(0.2, 0.5) * BONE_DEFS[ib][6]),
            "jointId": r.joint_ids[ji], "restingLength": length})
    return ligs


# =============================================================================
# CARTILAGE — 9
# =============================================================================

def gen_cartilage(r: Reg) -> list[dict]:
    """Generate cartilage including articular surfaces, menisci, labra, and intervertebral discs.

    Intervertebral disc data from:
      - Thickness: Shao et al., Eur Spine J 11(6):513-517, 2002
      - Surface area: estimated from vertebral body dimensions
      - Material: biphasic model per Mow et al., J Biomech Eng 102(1):73-84, 1980
    """
    defs: list[tuple[str, str, int | None, int, float, float]] = [
        # Knee cartilage (bilateral)
        ("Femoral condyle articular cartilage (R)", "hyaline", B_FEM_R, J_KNEE_R, 3.5, 12),
        ("Femoral condyle articular cartilage (L)", "hyaline", B_FEM_L, J_KNEE_L, 3.5, 12),
        ("Tibial plateau articular cartilage (R)", "hyaline", B_TIB_R, J_KNEE_R, 3, 10),
        ("Tibial plateau articular cartilage (L)", "hyaline", B_TIB_L, J_KNEE_L, 3, 10),
        ("Medial meniscus (R)", "fibrocartilage", None, J_KNEE_R, 5, 8),
        ("Medial meniscus (L)", "fibrocartilage", None, J_KNEE_L, 5, 8),
        ("Lateral meniscus (R)", "fibrocartilage", None, J_KNEE_R, 4.5, 7),
        ("Lateral meniscus (L)", "fibrocartilage", None, J_KNEE_L, 4.5, 7),
        # Hip cartilage (bilateral)
        ("Acetabular cartilage (R)", "hyaline", B_HIP_R, J_HIP_R, 2.5, 16),
        ("Acetabular cartilage (L)", "hyaline", B_HIP_L, J_HIP_L, 2.5, 16),
        ("Femoral head cartilage (R)", "hyaline", B_FEM_R, J_HIP_R, 2, 14),
        ("Femoral head cartilage (L)", "hyaline", B_FEM_L, J_HIP_L, 2, 14),
        ("Acetabular labrum (R)", "fibrocartilage", None, J_HIP_R, 4, 6),
        ("Acetabular labrum (L)", "fibrocartilage", None, J_HIP_L, 4, 6),
        # Shoulder labra (bilateral)
        ("Glenoid labrum (R)", "fibrocartilage", None, J_SHOULDER_R, 3.5, 4),
        ("Glenoid labrum (L)", "fibrocartilage", None, J_SHOULDER_L, 3.5, 4),
    ]

    # Intervertebral discs for ALL vertebral joints
    # Thickness: Shao et al., Eur Spine J (2002); area estimated from body size
    # Original joints 8-19: L5-S1(8), L5-L4(9)..L2-L1(12), T12-L1(13),
    #   T12-T11(14), T9-T8(15), T5-T4(16), T2-T1(17), C7-T1(18), C1-C2(19)
    # Round 3 joints 37-43: T11-T10(37), T10-T9(38), T8-T7(39), T7-T6(40),
    #   T6-T5(41), T4-T3(42), T3-T2(43)
    ivd_data = [
        (J_L5S1, "L5-S1 intervertebral disc", 9, 16),
        (9,  "L5-L4 intervertebral disc", 10, 16),
        (10, "L4-L3 intervertebral disc", 10.5, 15),
        (11, "L3-L2 intervertebral disc", 10, 14),
        (12, "L2-L1 intervertebral disc", 9, 13),
        (13, "T12-L1 intervertebral disc", 8, 12),
        (14, "T12-T11 intervertebral disc", 7, 10),
        (37, "T11-T10 intervertebral disc", 6.5, 9.5),
        (38, "T10-T9 intervertebral disc", 6, 9),
        (15, "T9-T8 intervertebral disc", 5.5, 8.5),
        (39, "T8-T7 intervertebral disc", 5.5, 8),
        (40, "T7-T6 intervertebral disc", 5, 7.5),
        (41, "T6-T5 intervertebral disc", 5, 7),
        (16, "T5-T4 intervertebral disc", 5, 7),
        (42, "T4-T3 intervertebral disc", 4.5, 6.5),
        (43, "T3-T2 intervertebral disc", 4.5, 6),
        (17, "T2-T1 intervertebral disc", 4, 5.5),
        (18, "C7-T1 intervertebral disc", 4, 5),
        # Cervical IVDs (C6-C5 through C3-C2) — Shao et al., Eur Spine J (2002)
        (68, "C6-C5 intervertebral disc", 3.5, 4.5),
        (69, "C5-C4 intervertebral disc", 3.5, 4.5),
        (70, "C4-C3 intervertebral disc", 3, 4),
        (71, "C3-C2 intervertebral disc", 3, 3.5),
    ]
    for ji, name, thick, area in ivd_data:
        if ji < len(r.joint_ids):
            defs.append((name, "fibrocartilage", None, ji, thick, area))

    # TMJ disc cartilage (bilateral)
    if J_TMJ_R < len(r.joint_ids):
        defs.append(("TMJ disc (R)", "fibrocartilage", None, J_TMJ_R, 3, 3))
    if J_TMJ_L < len(r.joint_ids):
        defs.append(("TMJ disc (L)", "fibrocartilage", None, J_TMJ_L, 3, 3))

    carts = []
    for name, ctype, bone_idx, joint_idx, thickness, area in defs:
        cid = uid(); r.cartilage_ids.append(cid)
        c: dict = {"id": cid, "name": name, "type": ctype, "thickness": thickness, "surfaceArea": area}
        if bone_idx is not None:
            c["boneId"] = r.bone_ids[bone_idx]
        c["jointId"] = r.joint_ids[joint_idx]
        carts.append(c)
    return carts


__all__ = [name for name in globals() if not name.startswith("__")]


# =============================================================================
# BONE GEOMETRIES — Parametric CSG for all 206 bones
#
# Each bone gets a CSG tree composed from primitives (capsule, ellipsoid,
# box, cylinder, sphere, torus) combined via union/subtract operations.
# All geometry is in the bone's LOCAL coordinate frame (origin = bone center,
# Y-up = long axis).
#
# CSG constraints: max 64 nodes/tree, max depth 8.
# Actual budget: long bones ~4-6 nodes, irregular ~6-10, flat ~3-5, short ~2-3.
#
# References:
#   - Requicha, ACM Comput. Surv. 12(4):437-464, 1980 (CSG theory)
#   - Anatomy: Gray's Anatomy 42nd ed. (2020)
# =============================================================================
