import React, { useState, useEffect } from 'react';
import { PatientInfo } from '../../types/patient';
import { Input } from '../UI/Input';
import { Select } from '../UI/Select';
import { FormField } from '../UI/FormField';
import { useVocabulary } from '../../hooks/useVocabulary';

interface MultipleMyelomaTabProps {
  patientInfo: PatientInfo;
  onSave: (data: Partial<PatientInfo>) => Promise<void>;
}

export const MultipleMyelomaTab: React.FC<MultipleMyelomaTabProps> = ({ patientInfo, onSave }) => {
  const [formData, setFormData] = useState<Partial<PatientInfo>>(patientInfo);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setFormData(patientInfo);
  }, [patientInfo]);

  const handleChange = (field: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(formData);
      alert('Information saved successfully!');
    } catch (error) {
      alert('Error saving information');
    } finally {
      setSaving(false);
    }
  };

  const yesNoOptions = [
    { value: 'true', label: 'Yes' },
    { value: 'false', label: 'No' },
  ];

  const { options: toxicityOptions, source: toxicitySource } = useVocabulary('toxicity-grade', 'code');
  const { options: progressionOptions, source: progressionSource } = useVocabulary('disease-progression', 'title');
  const { options: measurableDiseaseOptions, source: measurableDiseaseSource } = useVocabulary('measurable-disease', 'title');

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-8">
        <div className="space-y-4">
          {/* Cytogenic Markers and Molecular Markers */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Cytogenic Markers">
              <Input
                value={formData.cytogenic_markers || ''}
                onChange={(e) => handleChange('cytogenic_markers', e.target.value)}
                placeholder="e.g., t(4;14), del(17p)"
              />
            </FormField>

            <FormField label="Molecular Markers">
              <Input
                value={formData.molecular_markers || ''}
                onChange={(e) => handleChange('molecular_markers', e.target.value)}
                placeholder="e.g., TP53, KRAS"
              />
            </FormField>
          </div>

          {/* Plasma Cell Leukemia and Progression */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Plasma Cell Leukemia">
              <Select
                value={formData.plasma_cell_leukemia ? 'true' : 'false'}
                onChange={(e) => handleChange('plasma_cell_leukemia', e.target.value === 'true')}
                options={yesNoOptions}
              />
            </FormField>

            <FormField label="Progression" vocabSource={progressionSource}>
              <Select
                value={formData.progression || ''}
                onChange={(e) => handleChange('progression', e.target.value)}
                options={progressionOptions}
              />
            </FormField>
          </div>

          {/* Toxicity Grade and Measurable Disease */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Toxicity Grade Maximum" vocabSource={toxicitySource}>
              <Select
                value={formData.toxicity_grade_maximum || ''}
                onChange={(e) => handleChange('toxicity_grade_maximum', parseInt(e.target.value))}
                options={toxicityOptions}
              />
            </FormField>

            <FormField label="Measurable Disease (IMWG)" vocabSource={measurableDiseaseSource}>
              <Select
                value={formData.measurable_disease_imwg || ''}
                onChange={(e) => handleChange('measurable_disease_imwg', e.target.value)}
                options={measurableDiseaseOptions}
              />
            </FormField>
          </div>
        </div>

        <div className="mt-8">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </form>
  );
};