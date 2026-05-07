import React, { useState, useEffect } from 'react';
import { PatientInfo, User } from '../../types/patient';
import { Input } from '../UI/Input';
import { Select } from '../UI/Select';
import { FormField } from '../UI/FormField';
import { useVocabulary } from '../../hooks/useVocabulary';
import { CheckboxList } from '../UI/CheckboxList';

interface GeneralTabProps {
  patientInfo: PatientInfo;
  user: User;
  onSave: (data: Partial<PatientInfo> & { first_name?: string; last_name?: string }) => Promise<void>;
  onDiseaseChange?: (disease: string) => void; // Add callback for immediate disease change
}

export const GeneralTab: React.FC<GeneralTabProps> = ({ patientInfo, user, onSave, onDiseaseChange }) => {
  const [formData, setFormData] = useState<Partial<PatientInfo> & { first_name?: string; last_name?: string }>({
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    ...patientInfo,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setFormData({
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      ...patientInfo,
    });
  }, [patientInfo, user]);

  const handleChange = (field: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [field]: value }));
    
    // If disease changes, immediately update and notify parent
    if (field === 'disease' && onDiseaseChange) {
      onDiseaseChange(value);
      // Auto-save disease change
      onSave({ ...formData, [field]: value }).catch(err => {
        console.error('Error auto-saving disease:', err);
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(formData);
      alert('Information saved successfully!');
    } catch (error) {
      console.error('Save error:', error);
      alert('Error saving information. Please check the console for details.');
    } finally {
      setSaving(false);
    }
  };

  const { options: ethnicityOptions, source: ethnicitySource } = useVocabulary('ethnicity', 'title');
  const { options: preexistingConditionOptions, source: preexistingSource } = useVocabulary('pre-existing-condition-category', 'title');
  const { options: diseaseOptions, source: diseaseSource } = useVocabulary('disease', 'title');
  const { options: cancerStageOptions, source: cancerStageSource } = useVocabulary('cancer-stage', 'title');
  const { options: karnofskyOptions, source: karnofskySource } = useVocabulary('karnofsky-score', 'code');
  const { options: ecogOptions, source: ecogSource } = useVocabulary('ecog-status', 'code');
  const { options: neuropathyOptions, source: neuropathySource } = useVocabulary('peripheral-neuropathy-grade', 'code');

  const genderOptions = [
    { value: 'Male', label: 'Male' },
    { value: 'Female', label: 'Female' },
    { value: 'Other', label: 'Other' },
  ];

  const yesNoOptions = [
    { value: 'Yes', label: 'Yes' },
    { value: 'No', label: 'No' },
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-8">
        <div className="space-y-4">
          {/* First Name and Last Name */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="First Name">
              <Input
                value={formData.first_name || ''}
                onChange={(e) => handleChange('first_name', e.target.value)}
              />
            </FormField>

            <FormField label="Last Name">
              <Input
                value={formData.last_name || ''}
                onChange={(e) => handleChange('last_name', e.target.value)}
              />
            </FormField>
          </div>

          {/* Email */}
          <div className="grid grid-cols-1 gap-4">
            <FormField label="Email">
              <Input
                type="email"
                placeholder="patient@example.com"
                value={formData.email || ''}
                onChange={(e) => handleChange('email', e.target.value)}
              />
            </FormField>
          </div>

          {/* Age and Gender */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Patient Age">
              <Input
                type="number"
                value={formData.patient_age || ''}
                onChange={(e) => handleChange('patient_age', parseInt(e.target.value))}
              />
            </FormField>

            <FormField label="Gender">
              <Select
                value={formData.gender || ''}
                onChange={(e) => handleChange('gender', e.target.value)}
                options={genderOptions}
              />
            </FormField>
          </div>

          {/* Weight and Height */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Weight">
              <div className="flex gap-2">
                <Input
                  type="number"
                  step="0.1"
                  value={formData.weight_kg || ''}
                  onChange={(e) => handleChange('weight_kg', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <Select
                  value="kg"
                  disabled
                  options={[{ value: 'kg', label: 'Kilograms' }]}
                  className="w-40"
                />
              </div>
            </FormField>

            <FormField label="Height">
              <div className="flex gap-2">
                <Input
                  type="number"
                  step="0.1"
                  value={formData.height_cm || ''}
                  onChange={(e) => handleChange('height_cm', parseFloat(e.target.value))}
                  className="flex-1"
                />
                <Select
                  value="cm"
                  disabled
                  options={[{ value: 'cm', label: 'Centimeters' }]}
                  className="w-40"
                />
              </div>
            </FormField>
          </div>

          {/* Ethnicity and Blood Pressure */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Ethnicity" vocabSource={ethnicitySource}>
              <Select
                value={formData.ethnicity || ''}
                onChange={(e) => handleChange('ethnicity', e.target.value)}
                options={ethnicityOptions}
              />
            </FormField>

            <FormField label="Blood Pressure (SBP / DBP)">
              <div className="flex gap-2 items-center">
                <Input
                  type="number"
                  placeholder="SBP"
                  value={formData.systolic_bp || ''}
                  onChange={(e) => handleChange('systolic_bp', parseInt(e.target.value))}
                  className="flex-1"
                />
                <span className="text-gray-500">/</span>
                <Input
                  type="number"
                  placeholder="DBP"
                  value={formData.diastolic_bp || ''}
                  onChange={(e) => handleChange('diastolic_bp', parseInt(e.target.value))}
                  className="flex-1"
                />
              </div>
            </FormField>
          </div>

          {/* Location and Zip/Postal Code */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Location">
              <Select
                value={formData.location || ''}
                onChange={(e) => handleChange('location', e.target.value)}
                options={[
                  { value: 'United Kingdom', label: 'United Kingdom' },
                  { value: 'United States', label: 'United States' },
                  { value: 'Canada', label: 'Canada' },
                  { value: 'Other', label: 'Other' },
                ]}
              />
            </FormField>

            <FormField label="Zip/Postal Code">
              <Input
                placeholder="Zip/Postal Code"
                value={formData.postal_code || ''}
                onChange={(e) => handleChange('postal_code', e.target.value)}
              />
            </FormField>
          </div>

          {/* Disease and Stage */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Disease" vocabSource={diseaseSource}>
              <Select
                value={formData.disease || ''}
                onChange={(e) => handleChange('disease', e.target.value)}
                options={diseaseOptions}
              />
            </FormField>

            <FormField label="Stage" vocabSource={cancerStageSource}>
              <Select
                value={formData.stage || ''}
                onChange={(e) => handleChange('stage', e.target.value)}
                options={cancerStageOptions}
              />
            </FormField>
          </div>

          {/* Karnofsky and ECOG */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Karnofsky Performance Score" vocabSource={karnofskySource}>
              <Select
                value={formData.karnofsky_performance_status || ''}
                onChange={(e) => handleChange('karnofsky_performance_status', parseInt(e.target.value))}
                options={karnofskyOptions}
              />
            </FormField>

            <FormField label="ECOG Performance Status" vocabSource={ecogSource}>
              <Select
                value={formData.ecog_performance_status || ''}
                onChange={(e) => handleChange('ecog_performance_status', parseInt(e.target.value))}
                options={ecogOptions}
              />
            </FormField>
          </div>

          {/* Active Malignancies and Active Infection */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="No Other Active Malignancies">
              <Select
                value={formData.active_malignancies || 'Yes'}
                onChange={(e) => handleChange('active_malignancies', e.target.value)}
                options={yesNoOptions}
              />
            </FormField>

            <FormField label="No Active Infection">
              <Select
                value={formData.active_infection ? 'No' : 'Yes'}
                onChange={(e) => handleChange('active_infection', e.target.value === 'No')}
                options={yesNoOptions}
              />
            </FormField>
          </div>

          {/* Preexisting Conditions and Peripheral Neuropathy */}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Preexisting Conditions" vocabSource={preexistingSource}>
              <CheckboxList
                options={preexistingConditionOptions}
                selected={formData.preexisting_conditions || []}
                onChange={(vals) => handleChange('preexisting_conditions', vals)}
              />
            </FormField>

            <FormField label="Peripheral Neuropathy Grade" vocabSource={neuropathySource}>
              <Select
                value={formData.peripheral_neuropathy_grade || ''}
                onChange={(e) => handleChange('peripheral_neuropathy_grade', parseInt(e.target.value))}
                options={neuropathyOptions}
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

