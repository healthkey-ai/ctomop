import { usePatientInfoContext } from "./PatientInfoContext";
import {
  usePatientInfoMe as _usePatientInfoMe,
  usePatchPatientInfo as _usePatchPatientInfo,
} from "./patientInfoApi";

export function usePatientInfoMe() {
  const { apiClient, apiBasePath } = usePatientInfoContext();
  return _usePatientInfoMe(apiClient, apiBasePath);
}

export function usePatchPatientInfo() {
  const { apiClient, apiBasePath } = usePatientInfoContext();
  return _usePatchPatientInfo(apiClient, apiBasePath);
}
