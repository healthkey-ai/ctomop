from django.db import migrations


def seed_forward(apps, schema_editor):
    Ethnicity = apps.get_model("omop_core", "Ethnicity")
    StemCellTransplant = apps.get_model("omop_core", "StemCellTransplant")
    HistologicType = apps.get_model("omop_core", "HistologicType")
    EstrogenReceptorStatus = apps.get_model("omop_core", "EstrogenReceptorStatus")
    ProgesteroneReceptorStatus = apps.get_model("omop_core", "ProgesteroneReceptorStatus")
    Her2Status = apps.get_model("omop_core", "Her2Status")
    HrStatus = apps.get_model("omop_core", "HrStatus")
    HrdStatus = apps.get_model("omop_core", "HrdStatus")
    MutationOrigin = apps.get_model("omop_core", "MutationOrigin")
    MutationGene = apps.get_model("omop_core", "MutationGene")
    MutationInterpretation = apps.get_model("omop_core", "MutationInterpretation")
    MutationCode = apps.get_model("omop_core", "MutationCode")
    TumorStage = apps.get_model("omop_core", "TumorStage")
    NodesStage = apps.get_model("omop_core", "NodesStage")
    DistantMetastasisStage = apps.get_model("omop_core", "DistantMetastasisStage")
    StagingModality = apps.get_model("omop_core", "StagingModality")
    ToxicityGrade = apps.get_model("omop_core", "ToxicityGrade")
    Language = apps.get_model("omop_core", "Language")
    LanguageSkillLevel = apps.get_model("omop_core", "LanguageSkillLevel")
    BinetStage = apps.get_model("omop_core", "BinetStage")
    ProteinExpression = apps.get_model("omop_core", "ProteinExpression")
    RichterTransformation = apps.get_model("omop_core", "RichterTransformation")
    TumorBurden = apps.get_model("omop_core", "TumorBurden")
    MorphologicVariant = apps.get_model("omop_core", "MorphologicVariant")
    DiseaseActivity = apps.get_model("omop_core", "DiseaseActivity")
    PreExistingConditionCategory = apps.get_model("omop_core", "PreExistingConditionCategory")

    # ------------------------------------------------------------------
    # Ethnicity
    # ------------------------------------------------------------------
    for code, title in [
        ("caucasian_or_european", "Caucasian/European"),
        ("african_or_black", "African/Black"),
        ("asian", "Asian"),
        ("native_american", "Native American"),
        ("other", "Other/Won't Say"),
    ]:
        Ethnicity.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # StemCellTransplant
    # ------------------------------------------------------------------
    for code, title in [
        ("priorSCT", "prior SCT"),
        ("priorAutologousSCT", "prior autologous SCT"),
        ("priorAllogeneicSCT", "prior allogeneic SCT"),
        ("recentSCT", "recent SCT"),
        ("recentAutologousSCT", "recent autologous SCT"),
        ("recentAllogeneicSCT", "recent allogeneic SCT"),
        ("relapsedPostSCT", "relapsed post-SCT"),
        ("relapsedPostAutologousSCT", "relapsed post-autologous SCT"),
        ("relapsedPostAllogeneicSCT", "relapsed post-allogeneic SCT"),
        ("completedTandemSCT", "completed tandem SCT"),
        ("neverReceivedSCT", "never received SCT"),
        ("preAutologousSCT", "pre-autologous SCT"),
        ("preAllogeneicSCT", "pre-allogeneic SCT"),
    ]:
        StemCellTransplant.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # HistologicType
    # ------------------------------------------------------------------
    for sort_key, code, title in [
        (10,  "infiltrating_ductal_carcinoma",       "Infiltrating ductal carcinoma (IDC)"),
        (20,  "dcis",                                "Ductal carcinoma in situ (DCIS)"),
        (30,  "infiltrating_lobular_carcinoma",      "Infiltrating lobular carcinoma (ILC)"),
        (40,  "lcis",                                "Lobular carcinoma in situ (LCIS)"),
        (50,  "mixed_ductal_and_lobular_carcinoma",  "Mixed ductal and lobular carcinoma"),
        (60,  "mucinous_colloid_carcinoma",          "Mucinous (colloid) carcinoma"),
        (70,  "tubular_carcinoma",                   "Tubular carcinoma"),
        (80,  "medullary_carcinoma",                 "Medullary carcinoma"),
        (90,  "papillary_carcinoma",                 "Papillary carcinoma"),
        (100, "metaplastic_carcinoma",               "Metaplastic carcinoma"),
        (110, "paget_disease_of_the_nipple",         "Paget disease of the nipple"),
        (120, "inflammatory_carcinoma",              "Inflammatory carcinoma"),
    ]:
        HistologicType.objects.get_or_create(
            code=code, defaults={"title": title, "sort_key": sort_key}
        )

    # ------------------------------------------------------------------
    # EstrogenReceptorStatus
    # ------------------------------------------------------------------
    for code, title in [
        ("er_minus",            "ER-"),
        ("er_plus",             "ER+"),
        ("er_plus_with_low_exp", "ER+ with low expression"),
        ("er_plus_with_hi_exp",  "ER+ with high expression"),
    ]:
        EstrogenReceptorStatus.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # ProgesteroneReceptorStatus
    # ------------------------------------------------------------------
    for code, title in [
        ("pr_minus",            "PR-"),
        ("pr_plus",             "PR+"),
        ("pr_plus_with_low_exp", "PR+ with low expression"),
        ("pr_plus_with_hi_exp",  "PR+ with high expression"),
    ]:
        ProgesteroneReceptorStatus.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # Her2Status
    # ------------------------------------------------------------------
    for code, title in [
        ("her2_plus",  "HER2+"),
        ("her2_minus", "HER2-"),
        ("her2_low",   "HER2 low"),
    ]:
        Her2Status.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # HrStatus
    # ------------------------------------------------------------------
    for code, title in [
        ("hr_plus",             "HR+"),
        ("hr_minus",            "HR-"),
        ("hr_plus_with_low_exp", "HR+ with low expression"),
        ("hr_plus_with_hi_exp",  "HR+ with high expression"),
    ]:
        HrStatus.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # HrdStatus
    # ------------------------------------------------------------------
    for code, title in [
        ("hrd_plus",  "HRD+"),
        ("hrd_minus", "HRD-"),
    ]:
        HrdStatus.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # MutationOrigin
    # ------------------------------------------------------------------
    for code, title in [
        ("somatic",  "somatic"),
        ("germline", "germline"),
    ]:
        MutationOrigin.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # MutationGene  (must be seeded before MutationCode)
    # ------------------------------------------------------------------
    gene_codes = [
        ("brca1", "BRCA1"),
        ("brca2", "BRCA2"),
        ("tp53",  "TP53"),
        ("pik3ca", "PIK3CA"),
        ("esr1",  "ESR1"),
    ]
    for code, title in gene_codes:
        MutationGene.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # MutationInterpretation
    # ------------------------------------------------------------------
    for code, title in [
        ("pathogenic",           "Pathogenic"),
        ("likely_pathogenic",    "Likely pathogenic"),
        ("vus",                  "Variant of Uncertain Significance (VUS)"),
        ("likely_benign",        "Likely benign"),
        ("benign",               "Benign"),
        ("no_mutation_detected", "No mutation detected"),
    ]:
        MutationInterpretation.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # MutationCode  (one entry per mutation variant, linked to gene)
    # ------------------------------------------------------------------
    brca1 = MutationGene.objects.get(code="brca1")
    brca2 = MutationGene.objects.get(code="brca2")
    tp53  = MutationGene.objects.get(code="tp53")
    pik3ca = MutationGene.objects.get(code="pik3ca")
    esr1  = MutationGene.objects.get(code="esr1")

    def _add_mutations(gene_obj, variants):
        for variant in variants:
            # Use the variant string as both code and title;
            # slugify to make a DB-safe code key.
            import re
            safe_code = re.sub(r"[^a-zA-Z0-9_]", "_", variant)[:200]
            MutationCode.objects.get_or_create(
                code=safe_code,
                defaults={"title": variant, "gene": gene_obj},
            )

    _add_mutations(brca1, [
        "c.1135_1136insA (1135insA)",
        "c.1294_1333del40 (1294del40)",
        "c.68_69delAG (185delAG)",
        "c.3700_3704delGTAAA (3819delGTAAA)",
        "c.3786_3789delGTCT (3875delGTCT)",
        "c.4035delA (4153delA)",
        "c.5266dupC (5382insC)",
        "c.181T>G (p.C61G)",
        "c.1687C>T (p.Q563X)",
        "c.4330C>T (p.R1443X)",
        "c.211G>A (p.R71G)",
        "c.314A>G (p.Y105C)",
        "c.5096G>A",
        "c.4035delAAGA",
    ])

    _add_mutations(brca2, [
        "c.10095delC (3366delC)", "c.10150C>T", "c.10204C>T (R3402X)",
        "c.10230_10233delAGAA", "c.10247A>G", "c.10276C>T",
        "c.10323C>T (R3442X)", "c.10350C>A (Y3450X)", "c.10370A>G (N3457S)",
        "c.10411C>T", "c.10453C>T (R3485X)", "c.10509C>A (Y3503X)",
        "c.10580G>A", "c.10606C>T (R3536X)", "c.10632_10633delAG",
        "c.10647delC (3550delC)", "c.10692_10693insA", "c.10740C>T (R3572X)",
        "c.10776_10777delAG", "c.10810C>T (R3604X)", "c.10824_10825delCT (3609delCT)",
        "c.10830_10831delAA (3611delAA)", "c.10844C>T (R3615X)",
        "c.2338C>T (Q780*)", "c.3036_3039del (3036del4)", "c.3326_3327insA (3326insA)",
        "c.5950_5951delCT (5950delCT)", "c.5946delT (6174delT)", "c.6174delT (6174delT)",
        "c.6503_6504delTT (6503delTT)", "c.7558C>T", "c.7845+1G>A (7845+1G>A)",
        "c.7617+1G>A", "c.7913_7917delTTAAA", "c.7975A>T", "c.8168A>G",
        "c.8537_8538delAG", "c.8572C>T", "c.873delT (873delT)", "c.8755delG",
        "c.886_887delGT (886delGT)", "c.999_1003del (999del5)",
        "c.9097_9098insA (3033insA)", "c.9117G>A", "c.9154C>T",
        "c.9235delG (3079delG)", "c.9308G>A", "c.9382C>T (R3128X)",
        "c.9610C>T (R3204X)", "c.9631delC", "c.9653delA", "c.9700C>T",
        "c.9816delC (3272delC)", "c.9852delT (3285delT)",
        "c.9924C>A (Y3308X)", "c.9976A>T (K3326X)",
    ])

    _add_mutations(tp53, [
        "c.404G>A (C135Y)", "c.853G>A (E285K)", "c.733G>A (G245S)",
        "c.451C>T (P151S)", "c.472G>T (R158L)", "c.524G>A (R175H)",
        "c.586C>T (R196*)", "c.743G>A (R248Q)", "c.743G>T (R248W)",
        "c.746C>G (R249S)", "c.818G>A (R273H)", "c.844C>T (R282W)",
        "c.469G>T (V157F)", "c.658T>C (Y220C)", "c.487T>A (Y163N)",
        "c.841G>C (D281H)", "c.578C>T (H193Y)", "c.535C>T (H179Y)",
        "c.638G>T (R213L)", "c.637C>T (R213*)", "c.637C>A (R213Q)",
        "c.329G>T (R110L)", "c.476C>T (A159V)", "c.461G>T (G154V)",
        "c.500C>A (Q167K)", "c.584T>C (I195T)", "c.701A>G (Y234C)",
        "c.489A>G (Y163C)", "c.332T>A (L111Q)", "c.833C>T (P278L)",
        "c.818G>C (R273C)", "c.329G>A (R110H)", "c.404G>T (C135F)",
        "c.818G>T (R273L)", "c.847G>C (R282G)", "c.587G>A (R196Q)",
        "c.476G>A (R158H)", "c.514G>T (Q172H)", "c.742C>T (R248Q)",
        "c.332T>G (L111R)", "c.844C>A (R282S)", "c.904C>T (R302W)",
        "c.916C>T (R306*)", "c.713G>T (C238F)", "c.796G>T (G266V)",
        "c.700C>T (Q234*)", "c.917G>A (R306Q)", "c.865C>T (R289W)",
        "c.877A>G (K292E)", "c.886C>T (Y296*)",
    ])

    _add_mutations(pik3ca, [
        "c.1624G>A (p.E542K)", "c.1625A>G (p.E542G)", "c.1633G>A (p.E545K)",
        "c.1633G>C (p.E545Q)", "c.1637A>C (p.Q546P)", "c.1637A>G (p.Q546R)",
        "c.1637A>T (p.Q546K)", "c.3140A>C (p.H1047P)", "c.3140A>G (p.H1047R)",
        "c.3140A>T (p.H1047L)", "c.3142C>T (p.H1048Y)", "c.3143A>G (p.H1048R)",
        "c.3144T>G (p.H1048Q)", "c.3145G>A (p.G1049S)", "c.3145G>C (p.G1049R)",
        "c.3146G>C (p.G1049A)", "c.3146G>T (p.G1049V)", "c.3147G>A (p.G1049D)",
        "c.3147G>C (p.G1049E)", "c.3147G>T (p.G1049F)", "c.3148G>A (p.G1049N)",
        "c.3148G>C (p.G1049T)", "c.3148G>T (p.G1049Y)", "c.3149G>A (p.G1049C)",
        "c.3149G>C (p.G1049W)", "c.3149G>T (p.G1049H)", "c.3150G>A (p.G1049L)",
        "c.3150G>C (p.G1049M)", "c.3150G>T (p.G1049I)", "c.3151G>A (p.G1049K)",
    ])

    _add_mutations(esr1, [
        "c.1138G>C (E380Q)", "c.1264_1266delGTG (V422del)",
        "c.1387T>C (S463P)", "c.1604C>A (P535H)",
        "c.1607T>A (L536H)", "c.1607T>A (L536Q)",
        "c.1609A>C (Y537S)", "c.1609T>A (Y537N)",
        "c.1610A>G (Y537C)", "c.1613A>G (D538G)",
        "c.908A>G (K303R)",
    ])

    # ------------------------------------------------------------------
    # TumorStage
    # ------------------------------------------------------------------
    for sort_key, code, title in [
        (10,  "tx",   "Tx: Primary Tumor, cannot be assessed"),
        (20,  "t0",   "T0: No tumor evidence"),
        (30,  "tis",  "Tis: Non-invasive Carcinoma in situ (DCIS, LCIS, Paget's without tumor)"),
        (40,  "t1",   "T1: Invasive Tumor ≤ 2 cm"),
        (50,  "t1mi", "T1mi: Invasive Tumor ≤ 0.1 cm"),
        (60,  "t1a",  "T1a: 0.1 – 0.5 cm"),
        (70,  "t1b",  "T1b: 0.5 – 1 cm"),
        (80,  "t1c",  "T1c: 1 – 2 cm"),
        (90,  "t2",   "T2: Invasive Tumor > 2 – 5 cm"),
        (100, "t3",   "T3: Invasive Tumor > 5 cm"),
        (110, "t4",   "T4: Invades chest wall or skin, or inflammatory"),
        (120, "t4a",  "T4a: Invades chest wall"),
        (130, "t4b",  "T4b: Invades skin (may be swelling/ulcer)"),
        (140, "t4c",  "T4c: Invades both skin + chest wall"),
        (150, "t4d",  "T4d: Inflammatory carcinoma"),
    ]:
        TumorStage.objects.get_or_create(
            code=code, defaults={"title": title, "sort_key": sort_key}
        )

    # ------------------------------------------------------------------
    # NodesStage
    # ------------------------------------------------------------------
    for sort_key, code, title in [
        (10,  "nx",   "NX: Nodes cannot be assessed (e.g., previously removed)"),
        (20,  "n0",   "N0: No lymph node involvement"),
        (30,  "n1",   "N1: 1–3 axillary lymph nodes or small internal mammary nodes"),
        (40,  "n1mi", "N1mi: Micrometastasis (0.2–2 mm)"),
        (50,  "n1a",  "N1a: 1–3 axillary nodes (>2 mm)"),
        (60,  "n1b",  "N1b: Cancer cells in internal mammary sentinel nodes"),
        (70,  "n1c",  "N1c: 1–3 axillary nodes + internal mammary sentinel nodes"),
        (80,  "n2",   "N2: 4–9 axillary nodes or internal mammary nodes without axillary nodes"),
        (90,  "n2a",  "N2a: 4–9 axillary nodes (>2 mm)"),
        (100, "n2b",  "N2b: Internal mammary nodes only (no axillary)"),
        (110, "n3",   "N3: 10+ axillary, infraclavicular, or supraclavicular nodes; or both axillary + internal mammary"),
        (120, "n3a",  "N3a: ≥10 axillary nodes (≥2 mm) or infraclavicular"),
        (130, "n3b",  "N3b: 4–9 Axillary + mammary nodes"),
        (140, "n3c",  "N3c: Supraclavicular nodes"),
    ]:
        NodesStage.objects.get_or_create(
            code=code, defaults={"title": title, "sort_key": sort_key}
        )

    # ------------------------------------------------------------------
    # DistantMetastasisStage
    # ------------------------------------------------------------------
    for sort_key, code, title in [
        (10, "m0",        "M0: No distant metastasis"),
        (20, "m0_i_plus", "M0(i+): No metastasis on scans, but cancer cells found in blood/bone marrow/distant nodes"),
        (30, "m1",        "M1: Distant metastasis present"),
    ]:
        DistantMetastasisStage.objects.get_or_create(
            code=code, defaults={"title": title, "sort_key": sort_key}
        )

    # ------------------------------------------------------------------
    # StagingModality
    # ------------------------------------------------------------------
    for code, title in [
        ("c",  "c → Clinical"),
        ("p",  "p → Pathological"),
        ("yp", "yp → Pathological after neoadjuvant therapy"),
    ]:
        StagingModality.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # ToxicityGrade  (integer codes)
    # ------------------------------------------------------------------
    for code, title in [
        (0, "Grade 0 (None)"),
        (1, "Grade 1 (Mild)"),
        (2, "Grade 2 (Moderate)"),
        (3, "Grade 3 (Severe)"),
        (4, "Grade 4 (Life-Threatening)"),
    ]:
        ToxicityGrade.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------
    for code, title in [
        ("en",    "English"),
        ("es",    "Spanish"),
        ("other", "Other"),
    ]:
        Language.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # LanguageSkillLevel
    # ------------------------------------------------------------------
    for code, title in [
        ("speak", "Speak"),
        ("write", "Write"),
    ]:
        LanguageSkillLevel.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # BinetStage
    # ------------------------------------------------------------------
    for code, title in [
        ("binet_stage_a", "Binet Stage A (<3 lymphoid areas involved)"),
        ("binet_stage_b", "Binet Stage B (≥3 lymphoid areas involved)"),
        ("binet_stage_c", "Binet Stage C (Anemia or Thrombocytopenia)"),
    ]:
        BinetStage.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # ProteinExpression
    # ------------------------------------------------------------------
    for code, title in [
        ("cd38_plus_ve",             "CD38 +ve"),
        ("cd38_minus_ve",            "CD38 -ve"),
        ("zap_70_plus_ve",           "ZAP-70 +ve"),
        ("zap_70_minus_ve",          "ZAP-70 -ve"),
        ("cd49d_plus_ve",            "CD49d +ve"),
        ("cd49d_minus_ve",           "CD49d -ve"),
        ("cd19_plus_ve",             "CD19 +ve"),
        ("cd19_minus_ve",            "CD19 -ve"),
        ("cd5_plus_ve",              "CD5 +ve"),
        ("cd5_minus_ve",             "CD5 -ve"),
        ("cd20_plus_ve",             "CD20 +ve"),
        ("cd20_minus_ve",            "CD20 -ve"),
        ("cd23_plus_ve",             "CD23 +ve"),
        ("cd23_minus_ve",            "CD23 -ve"),
        ("kappa_light_chain_plus_ve",  "Kappa (κ) light chain +ve"),
        ("kappa_light_chain_minus_ve", "Kappa (κ) light chain -ve"),
        ("lambda_light_chain_plus_ve",  "Lambda (λ) light chain +ve"),
        ("lambda_light_chain_minus_ve", "Lambda (λ) light chain -ve"),
    ]:
        ProteinExpression.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # RichterTransformation
    # ------------------------------------------------------------------
    for code, title in [
        ("richter_transformation_to_dlbcl",              "Richter Transformation to DLBCL"),
        ("richter_transformation_to_hodgkin_lymphoma",    "Richter Transformation to Hodgkin Lymphoma"),
        ("richter_transformation_to_non_hodgkin_lymphoma", "Richter Transformation to Non-Hodgkin Lymphoma"),
        ("clonally_related_rt",                           "Clonally Related RT"),
        ("clonally_unrelated_rt",                         "Clonally Unrelated RT"),
    ]:
        RichterTransformation.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # TumorBurden
    # ------------------------------------------------------------------
    for code, title in [
        ("low",          "Low"),
        ("intermediate", "Intermediate"),
        ("high",         "High"),
    ]:
        TumorBurden.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # MorphologicVariant
    # ------------------------------------------------------------------
    for code, title in [
        ("classic",     "Classic"),
        ("blastoid",    "Blastoid"),
        ("pleomorphic", "Pleomorphic"),
    ]:
        MorphologicVariant.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # DiseaseActivity
    # ------------------------------------------------------------------
    for code, title in [
        ("active",     "Active"),
        ("inactive",   "Inactive"),
        ("remission",  "Remission"),
        ("relapsed",   "Relapsed"),
        ("refractory", "Refractory"),
    ]:
        DiseaseActivity.objects.get_or_create(code=code, defaults={"title": title})

    # ------------------------------------------------------------------
    # PreExistingConditionCategory
    # ------------------------------------------------------------------
    for code, title in [
        ("cardiacIssues",                        "Cardiac Issues"),
        ("pulmonaryDisease",                     "Pulmonary Disease"),
        ("renalImpairment",                      "Renal Impairment"),
        ("hepaticImpairment",                    "Hepatic Impairment"),
        ("infections",                           "Infections"),
        ("otherActiveMalignancies",              "Other Active Malignancies"),
        ("neurologicalAndPsychiatricConditions", "Neurological and Psychiatric Conditions"),
        ("autoimmuneAndInflammatoryDisorders",   "Autoimmune and Inflammatory Disorders"),
        ("pregnancyOrBreastfeeding",             "Pregnancy or Breastfeeding"),
        ("performanceStatus",                    "Performance Status"),
        ("priorTherapies",                       "Prior Therapies"),
    ]:
        PreExistingConditionCategory.objects.get_or_create(code=code, defaults={"title": title})


def seed_reverse(apps, schema_editor):
    # Truncate all seeded tables – safe because Phase 2 FK columns don't exist yet
    model_names = [
        "PreExistingConditionCategory", "DiseaseActivity", "MorphologicVariant",
        "TumorBurden", "RichterTransformation", "ProteinExpression", "BinetStage",
        "LanguageSkillLevel", "Language", "ToxicityGrade", "StagingModality",
        "DistantMetastasisStage", "NodesStage", "TumorStage",
        "MutationCode", "MutationInterpretation", "MutationGene", "MutationOrigin",
        "HrdStatus", "HrStatus", "Her2Status", "ProgesteroneReceptorStatus",
        "EstrogenReceptorStatus", "HistologicType", "StemCellTransplant", "Ethnicity",
    ]
    for name in model_names:
        apps.get_model("omop_core", name).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("omop_core", "0051_add_vocabulary_lookup_tables"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
