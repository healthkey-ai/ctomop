import React, { useState, useEffect } from 'react';
import { PatientInfo } from '../../types/patient';
import { Input } from '../UI/Input';
import { Select } from '../UI/Select';
import { FormField } from '../UI/FormField';
import { useVocabulary } from '../../hooks/useVocabulary';

interface LabsTabProps {
  patientInfo: PatientInfo;
  onSave: (data: Partial<PatientInfo>) => Promise<void>;
}

export const LabsTab: React.FC<LabsTabProps> = ({ patientInfo, onSave }) => {
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
      alert('Labs information saved successfully!');
    } catch (error) {
      console.error('Error saving labs:', error);
      alert('Error saving labs information');
    } finally {
      setSaving(false);
    }
  };

  const yesNoOptions = [
    { value: 'true', label: 'Yes' },
    { value: 'false', label: 'No' },
  ];

  const { options: statusOptions, source: infectionSource } = useVocabulary('infection-status', 'title');

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-8">
        <div className="space-y-4">
          {/* M-Protein Serum and M-Protein Urine */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="M-Protein Serum (g/dL)">
              <Input
                type="number"
                step="0.01"
                value={formData.m_protein_serum || ''}
                onChange={(e) => handleChange('m_protein_serum', parseFloat(e.target.value))}
                placeholder="0.00"
              />
            </FormField>

            <FormField label="M-Protein Urine (mg/24h)">
              <Input
                type="number"
                step="0.01"
                value={formData.m_protein_urine || ''}
                onChange={(e) => handleChange('m_protein_urine', parseFloat(e.target.value))}
                placeholder="0.00"
              />
            </FormField>
          </div>

          {/* LDH and Pulmonary Function Test */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="LDH (U/L)">
              <Input
                type="number"
                value={formData.ldh_u_l || ''}
                onChange={(e) => handleChange('ldh_u_l', parseInt(e.target.value))}
                placeholder="0"
              />
            </FormField>

            <FormField label="Pulmonary Function Test">
              <Select
                value={formData.pulmonary_function_test ? 'true' : 'false'}
                onChange={(e) => handleChange('pulmonary_function_test', e.target.value === 'true')}
                options={yesNoOptions}
              />
            </FormField>
          </div>

          {/* Bone Imaging Result and # Lesions */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Bone Imaging Result">
              <Select
                value={formData.bone_imaging_result ? 'true' : 'false'}
                onChange={(e) => handleChange('bone_imaging_result', e.target.value === 'true')}
                options={yesNoOptions}
              />
            </FormField>

            <FormField label="# Lesions">
              <Input
                type="number"
                value={formData.num_lesions || 0}
                onChange={(e) => handleChange('num_lesions', parseInt(e.target.value) || 0)}
                placeholder="0"
              />
            </FormField>
          </div>

          {/* Clonal Plasma % and Ejection Fraction % */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Clonal Plasma %">
              <Input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={formData.clonal_plasma_percent || ''}
                onChange={(e) => handleChange('clonal_plasma_percent', parseFloat(e.target.value))}
                placeholder="0.0"
              />
            </FormField>

            <FormField label="Ejection Fraction %">
              <Input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={formData.lvef_percent || ''}
                onChange={(e) => handleChange('lvef_percent', parseFloat(e.target.value))}
                placeholder="0.0"
              />
            </FormField>
          </div>

          {/* HIV and Hep B */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="HIV Status" vocabSource={infectionSource}>
              <Select
                value={formData.hiv_status || ''}
                onChange={(e) => handleChange('hiv_status', e.target.value)}
                options={statusOptions}
              />
            </FormField>

            <FormField label="Hepatitis B Status" vocabSource={infectionSource}>
              <Select
                value={formData.hepatitis_b_status || ''}
                onChange={(e) => handleChange('hepatitis_b_status', e.target.value)}
                options={statusOptions}
              />
            </FormField>
          </div>

          {/* Hep C */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Hepatitis C Status" vocabSource={infectionSource}>
              <Select
                value={formData.hepatitis_c_status || ''}
                onChange={(e) => handleChange('hepatitis_c_status', e.target.value)}
                options={statusOptions}
              />
            </FormField>

            <div></div>
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