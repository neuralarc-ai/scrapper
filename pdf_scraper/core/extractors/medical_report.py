from typing import Dict, List, Any
import re
from .base import BaseExtractor

class MedicalReportExtractor(BaseExtractor):
    """Extractor specialized for medical reports."""
    
    # Common medical value patterns
    PATTERNS = {
        'blood_pressure': r'\b(\d{2,3})/(\d{2,3})\s*(?:mmHg)?\b',
        'heart_rate': r'\b(?:HR|Heart Rate):?\s*(\d{2,3})\s*(?:bpm)?\b',
        'temperature': r'\b(?:Temp|Temperature):?\s*(\d{2,3}\.\d)\s*(?:°[CF])?\b',
        'date': r'\b(?:Date|Exam Date):?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
        'patient_id': r'\b(?:Patient ID|MRN):?\s*([A-Z0-9-]+)\b',
        'blood_values': r'\b(?:WBC|RBC|HGB|HCT|PLT):?\s*(\d+\.?\d*)\s*(?:K/µL|M/µL|g/dL|%|K/µL)?\b'
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
    
    def _extract_vital_signs(self, text: str) -> Dict[str, Any]:
        """Extract vital signs."""
        vitals = {}
        
        # Extract blood pressure
        bp = self.find_pattern(self.PATTERNS['blood_pressure'], text)
        if bp:
            vitals['blood_pressure'] = {
                'systolic': int(bp[0][0]),
                'diastolic': int(bp[0][1])
            }
        
        # Extract heart rate
        hr = self.find_pattern(self.PATTERNS['heart_rate'], text)
        if hr:
            vitals['heart_rate'] = int(hr[0])
        
        # Extract temperature
        temp = self.find_pattern(self.PATTERNS['temperature'], text)
        if temp:
            vitals['temperature'] = float(temp[0])
        
        return vitals
    
    def _extract_lab_results(self) -> Dict[str, Any]:
        """Extract laboratory results from tables."""
        lab_results = {}
        
        # Look for common lab result tables
        lab_tables = self.extract_tables_by_keyword('Laboratory Results')
        if lab_tables:
            for table_data in lab_tables:
                table = table_data['table']
                # Process table rows
                for row in table[1:]:  # Skip header row
                    if len(row) >= 2:
                        test_name = str(row[0]).strip()
                        value = str(row[1]).strip()
                        if test_name and value:
                            lab_results[test_name] = value
        
        return lab_results
    
    def _extract_diagnoses(self, text: str) -> List[str]:
        """Extract diagnoses from the report."""
        diagnoses = []
        
        # Look for diagnosis section
        diagnosis_section = self.extract_text_by_section('Diagnosis')
        if diagnosis_section:
            # Split by common delimiters
            items = re.split(r'[•\-\*]', diagnosis_section)
            diagnoses = [item.strip() for item in items if item.strip()]
        
        return diagnoses
    
    def _extract_medications(self, text: str) -> List[Dict[str, str]]:
        """Extract medication information."""
        medications = []
        
        # Look for medication section
        med_section = self.extract_text_by_section('Medications')
        if med_section:
            # Split by common delimiters
            items = re.split(r'[•\-\*]', med_section)
            for item in items:
                if item.strip():
                    # Try to extract medication details
                    med_info = {
                        'name': item.strip(),
                        'dosage': None,
                        'frequency': None
                    }
                    
                    # Look for dosage pattern
                    dosage_match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:mg|g|ml|mL|IU|units?))\b', item)
                    if dosage_match:
                        med_info['dosage'] = dosage_match.group(1)
                    
                    # Look for frequency pattern
                    freq_match = re.search(r'\b(?:q|every)\s*(\d+)\s*(?:hours?|hrs?|days?|times?)\b', item)
                    if freq_match:
                        med_info['frequency'] = freq_match.group(0)
                    
                    medications.append(med_info)
        
        return medications 