from typing import Dict, List, Any
import re
from .base import BaseExtractor

class MedicalReportExtractor(BaseExtractor):
    """Extractor specialized for medical reports."""
    
    # Common medical value patterns with improved specificity
    PATTERNS = {
        'blood_pressure': r'\b(?:BP|Blood Pressure):?\s*(\d{2,3})/(\d{2,3})\s*(?:mmHg)?\b',
        'heart_rate': r'\b(?:HR|Heart Rate|Pulse):?\s*(\d{2,3})\s*(?:bpm|beats/min)?\b',
        'temperature': r'\b(?:Temp|Temperature|T):?\s*(\d{2,3}\.\d)\s*(?:°[CF])?\b',
        'date': r'\b(?:Date|Exam Date|Visit Date):?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
        'patient_id': r'\b(?:Patient ID|MRN|Medical Record Number):?\s*([A-Z0-9-]+)\b',
        'blood_values': r'\b(?:WBC|RBC|HGB|HCT|PLT|White Blood Cells|Red Blood Cells|Hemoglobin|Hematocrit|Platelets):?\s*(\d+\.?\d*)\s*(?:K/µL|M/µL|g/dL|%|K/µL)?\b'
    }

    # Validation ranges for vital signs
    VALIDATION_RANGES = {
        'blood_pressure': {
            'systolic': (60, 250),
            'diastolic': (40, 150)
        },
        'heart_rate': (30, 250),
        'temperature': (35.0, 42.0),
        'blood_values': {
            'WBC': (2.0, 20.0),
            'RBC': (3.5, 6.0),
            'HGB': (12.0, 18.0),
            'HCT': (35.0, 50.0),
            'PLT': (150, 450)
        }
    }

    def extract(self, **kwargs) -> Dict[str, Any]:
        """Extract medical data from the PDF.
        
        Returns:
            Dict[str, Any]: Extracted medical data
        """
        text = self.parser.extract_text()
        metadata = self.parser.extract_metadata()
        
        # Extract basic information
        results = {
            'metadata': metadata,
            'patient_info': self._extract_patient_info(text),
            'vital_signs': self._extract_vital_signs(text),
            'lab_results': self._extract_lab_results(),
            'diagnoses': self._extract_diagnoses(text),
            'medications': self._extract_medications(text)
        }
        
        return results
    
    def _extract_patient_info(self, text: str) -> Dict[str, str]:
        """Extract patient information."""
        info = {}
        
        # Extract patient ID
        patient_id = self.find_pattern(self.PATTERNS['patient_id'], text)
        if patient_id:
            info['patient_id'] = patient_id[0]
        
        # Extract date
        date = self.find_pattern(self.PATTERNS['date'], text)
        if date:
            info['date'] = date[0]
        
        return info
    
    def _validate_vital_sign(self, name: str, value: Any) -> bool:
        """Validate if a vital sign value is within normal ranges."""
        if name in self.VALIDATION_RANGES:
            if isinstance(value, dict) and name == 'blood_pressure':
                systolic = value.get('systolic')
                diastolic = value.get('diastolic')
                if systolic and diastolic:
                    return (self.VALIDATION_RANGES[name]['systolic'][0] <= systolic <= self.VALIDATION_RANGES[name]['systolic'][1] and
                            self.VALIDATION_RANGES[name]['diastolic'][0] <= diastolic <= self.VALIDATION_RANGES[name]['diastolic'][1])
            elif isinstance(value, (int, float)):
                min_val, max_val = self.VALIDATION_RANGES[name]
                return min_val <= value <= max_val
        return False

    def _extract_vital_signs(self, text: str) -> Dict[str, Any]:
        """Extract and validate vital signs."""
        vitals = {}
        
        # Extract blood pressure with validation
        bp = self.find_pattern(self.PATTERNS['blood_pressure'], text)
        if bp:
            bp_value = {
                'systolic': int(bp[0][0]),
                'diastolic': int(bp[0][1])
            }
            if self._validate_vital_sign('blood_pressure', bp_value):
                vitals['blood_pressure'] = bp_value
        
        # Extract heart rate with validation
        hr = self.find_pattern(self.PATTERNS['heart_rate'], text)
        if hr:
            hr_value = int(hr[0])
            if self._validate_vital_sign('heart_rate', hr_value):
                vitals['heart_rate'] = hr_value
        
        # Extract temperature with validation
        temp = self.find_pattern(self.PATTERNS['temperature'], text)
        if temp:
            temp_value = float(temp[0])
            if self._validate_vital_sign('temperature', temp_value):
                vitals['temperature'] = temp_value
        
        return vitals
    
    def _extract_lab_results(self) -> Dict[str, Any]:
        """Extract and validate laboratory results from tables."""
        lab_results = {}
        
        # Look for common lab result tables with improved section detection
        lab_sections = ['Laboratory Results', 'Lab Results', 'Blood Work', 'Lab Values']
        for section in lab_sections:
            lab_tables = self.extract_tables_by_keyword(section)
            if lab_tables:
                for table_data in lab_tables:
                    table = table_data['table']
                    # Skip empty tables or tables without headers
                    if not table or len(table) < 2:
                        continue
                    
                    # Process table rows with validation
                    headers = [str(h).strip().upper() for h in table[0]]
                    for row in table[1:]:
                        if len(row) >= 2:
                            test_name = str(row[0]).strip().upper()
                            value = str(row[1]).strip()
                            
                            # Validate test name and value
                            if test_name and value and test_name in self.VALIDATION_RANGES['blood_values']:
                                try:
                                    num_value = float(value.split()[0])  # Extract numeric part
                                    if self._validate_vital_sign('blood_values', num_value):
                                        lab_results[test_name] = value
                                except (ValueError, IndexError):
                                    continue
        
        return lab_results
    
    def _extract_diagnoses(self, text: str) -> List[str]:
        """Extract and validate diagnoses from the report."""
        diagnoses = []
        diagnosis_sections = ['Diagnosis', 'Diagnoses', 'Assessment', 'Impression']
        
        for section in diagnosis_sections:
            section_text = self.extract_text_by_section(section)
            if section_text:
                # Split by common delimiters and clean up
                items = re.split(r'[•\-\*]', section_text)
                for item in items:
                    item = item.strip()
                    # Filter out non-diagnosis items
                    if (item and 
                        len(item) > 3 and  # Avoid very short items
                        not item.lower().startswith(('see', 'refer', 'follow')) and
                        not re.match(r'^\d+\.', item)):  # Avoid numbered items without content
                        diagnoses.append(item)
        
        return list(set(diagnoses))  # Remove duplicates
    
    def _extract_medications(self, text: str) -> List[Dict[str, str]]:
        """Extract and validate medication information."""
        medications = []
        med_sections = ['Medications', 'Medication List', 'Current Medications', 'Prescriptions']
        
        for section in med_sections:
            med_section = self.extract_text_by_section(section)
            if med_section:
                # Split by common delimiters and clean up
                items = re.split(r'[•\-\*]', med_section)
                for item in items:
                    item = item.strip()
                    if not item or len(item) < 3:
                        continue
                        
                    # Try to extract medication details with improved patterns
                    med_info = {
                        'name': None,
                        'dosage': None,
                        'frequency': None
                    }
                    
                    # Extract medication name (avoid common false positives)
                    name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', item)
                    if name_match and not any(word in name_match.group(1).lower() for word in ['see', 'refer', 'follow']):
                        med_info['name'] = name_match.group(1)
                    
                    # Extract dosage with improved pattern
                    dosage_match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:mg|g|ml|mL|IU|units?)(?:\s+per\s+\d+\s*(?:hour|day|week|month))?)\b', item)
                    if dosage_match:
                        med_info['dosage'] = dosage_match.group(1)
                    
                    # Extract frequency with improved pattern
                    freq_match = re.search(r'\b(?:q|every|take|administer)\s*(\d+)\s*(?:hours?|hrs?|days?|times?(?:\s+per\s+day)?)\b', item)
                    if freq_match:
                        med_info['frequency'] = freq_match.group(0)
                    
                    # Only add if we have at least a name and either dosage or frequency
                    if med_info['name'] and (med_info['dosage'] or med_info['frequency']):
                        medications.append(med_info)
        
        return medications 