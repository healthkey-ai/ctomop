# PatientInfo Population Analysis

## Fields in PatientInfo that need OMOP/Extension support

### Demographics & Physical Measurements
- ✅ patient_age (can be calculated from Person.year_of_birth)
- ✅ gender (from Person.gender_concept)
- ✅ ethnicity (from Person.ethnicity_concept)
- ❌ weight, weight_units (needs Measurement enhancement)
- ❌ height, height_units (needs Measurement enhancement)
- ❌ bmi (calculated field)
- ❌ systolic_blood_pressure, diastolic_blood_pressure (needs Measurement enhancement)
- ❌ heartrate, heartrate_variability (needs Measurement enhancement)

### Geographic Information
- ❌ country, region, postal_code, longitude, latitude (needs Location table)
- ❌ languages, language_skill_level (needs Person enhancement)

### Disease Information
- ❌ disease (needs ConditionOccurrence enhancement)
- ❌ stage (needs ConditionOccurrence enhancement for cancer staging)
- ❌ karnofsky_performance_score, ecog_performance_status (needs Observation enhancement)
- ❌ no_other_active_malignancies, no_pre_existing_conditions (needs Observation)
- ❌ peripheral_neuropathy_grade (needs Observation)

### Cancer-Specific Fields
- ✅ cytogenetic_markers (PatientRecord-first with Observation projection)
- ❌ molecular_markers (needs new table)
- ❌ stem_cell_transplant_history (needs Procedure enhancement)
- ❌ plasma_cell_leukemia (needs ConditionOccurrence enhancement)
- ❌ progression (needs Episode enhancement)
- ❌ condition_code_icd_10, condition_code_snomed_ct (needs ConditionOccurrence enhancement)

### Treatment History
- ❌ prior_therapy, first_line_therapy, second_line_therapy, later_therapy (needs new TreatmentLine table)
- ❌ first_line_date, second_line_date, later_date (needs TreatmentLine table)
- ❌ first_line_outcome, second_line_outcome, later_outcome (needs TreatmentLine table)
- ❌ supportive_therapies, supportive_therapy_date (needs DrugExposure/Procedure enhancement)
- ❌ relapse_count, treatment_refractory_status (needs Episode/Observation enhancement)
- ❌ therapy_lines_count, line_of_therapy (calculated from TreatmentLine)
- ❌ last_treatment (calculated from DrugExposure/Procedure)

### Laboratory Values (All need Measurement enhancement with specific concepts)
- ❌ All blood work fields (hemoglobin, platelets, WBC, RBC, etc.)
- ❌ All chemistry fields (creatinine, calcium, bilirubin, albumin, etc.)
- ❌ All liver function tests (AST, ALT, ALP)
- ❌ All specialized tests (LDH, ejection fraction, etc.)

### Cancer Biomarkers & Staging
- ❌ bone_lesions, meets_crab, meets_slim (needs Observation/Measurement)
- ❌ estimated_glomerular_filtration_rate, renal_adequacy_status (needs Measurement)
- ❌ pulmonary_function_test_result, bone_imaging_result (needs Procedure)
- ❌ clonal_plasma_cells, ejection_fraction (needs Measurement)
- ❌ estrogen_receptor_status, progesterone_receptor_status, her2_status (needs new BiomarkerMeasurement table)
- ❌ tnbc_status, hrd_status, hr_status (needs BiomarkerMeasurement)
- ❌ tumor_stage, nodes_stage, distant_metastasis_stage (needs ConditionOccurrence enhancement)
- ❌ staging_modalities (needs new table)

### Behavioral & Risk Factors
- ❌ All consent/caregiver/behavioral fields (needs new SocialDeterminant table)
- ❌ All substance use fields (needs new HealthBehavior table)
- ❌ All infection status fields (needs Observation enhancement)
- ❌ All medication fields (needs DrugExposure enhancement)

### Genetic Information
- ❌ genetic_mutations (needs GenomicVariantOccurrence enhancement)
- ❌ pd_l1_tumor_cels, pd_l1_assay, pd_l1_ic_percentage, etc. (needs BiomarkerMeasurement)
- ❌ ki67_proliferation_index (needs BiomarkerMeasurement)

### Clinical Assessments
- ❌ histologic_type, biopsy_grade (needs Specimen enhancement)
- ❌ measurable_disease_by_recist_status (needs Observation)
- ❌ bone_only_metastasis_status, metastatic_status (needs ConditionOccurrence enhancement)
- ❌ menopausal_status (needs Observation)
- ❌ toxicity_grade (needs Observation)
- ❌ planned_therapies (needs new table)

### Time-based Data
- ❌ remission_duration_min, washout_period_duration (needs Episode enhancement)
- ❌ concomitant_medication_date (needs DrugExposure enhancement)

## Required New Tables/Enhancements

### 1. New Tables Needed:
- Location (for geographic data)
- BiomarkerMeasurement (for cancer biomarkers)
- SocialDeterminant (for behavioral/social data)
- HealthBehavior (for substance use, tobacco, etc.)
- TreatmentLine (for treatment line tracking)
- ClinicalTrial (for trial participation)
- TumorAssessment (for staging and response)

### 2. Table Enhancements Needed:
- Person (add language fields)
- ConditionOccurrence (add cancer staging fields)
- Measurement (add specific cancer lab concepts)
- Observation (add performance status, behavioral data)
- DrugExposure (add treatment line context)
- Specimen (add genomic context)
- Episode (add progression tracking)
- GenomicVariantOccurrence (add clinical significance)

### 3. New Concept Categories Needed:
- Cancer staging systems
- Biomarker types
- Performance status scales
- Treatment response categories
- Social determinants
- Behavioral risk factors
