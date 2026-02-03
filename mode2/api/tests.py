"""
Comprehensive tests for MODE II API.

Tests cover:
- Data file validation
- Data import endpoints
- Water table calibration
- Slope stability prevision
"""

import uuid
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .importers import get_table_name
from .validators import ValidationResult, parse_european_float, validate_data_file


# =============================================================================
# Validator Tests
# =============================================================================

class ParseEuropeanFloatTests(TestCase):
    """Tests for parse_european_float function."""

    def test_parse_comma_decimal(self):
        """Should parse European-style float with comma decimal separator."""
        self.assertEqual(parse_european_float('6,13599536'), 6.13599536)
        self.assertEqual(parse_european_float('-1,77325353'), -1.77325353)
        self.assertEqual(parse_european_float('0,0'), 0.0)

    def test_parse_integer(self):
        """Should parse integers without decimal separator."""
        self.assertEqual(parse_european_float('100'), 100.0)
        self.assertEqual(parse_european_float('-50'), -50.0)

    def test_parse_dot_decimal(self):
        """Should handle dot decimal separator (already standard)."""
        self.assertEqual(parse_european_float('3.14'), 3.14)


class ValidationResultTests(TestCase):
    """Tests for ValidationResult class."""

    def test_initial_state(self):
        """Should initialize as valid with no errors or warnings."""
        result = ValidationResult()
        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertIsNone(result.data)

    def test_add_error_invalidates(self):
        """Adding an error should set valid to False."""
        result = ValidationResult()
        result.add_error("Errore italiano", "English error")
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0]['it'], "Errore italiano")
        self.assertEqual(result.errors[0]['en'], "English error")

    def test_add_warning_keeps_valid(self):
        """Adding a warning should not affect validity."""
        result = ValidationResult()
        result.add_warning("Avviso italiano", "English warning")
        self.assertTrue(result.valid)
        self.assertEqual(len(result.warnings), 1)

    def test_to_dict(self):
        """Should convert to dictionary for JSON response."""
        result = ValidationResult()
        result.add_error("Errore", "Error")
        result.add_warning("Avviso", "Warning")
        d = result.to_dict()

        self.assertFalse(d['valid'])
        self.assertEqual(len(d['errors']), 1)
        self.assertEqual(len(d['warnings']), 1)
        self.assertNotIn('data', d)

    def test_to_dict_with_data(self):
        """Should include data in dict when present."""
        result = ValidationResult()
        result.data = [{'index': 0, 'value': 1.0}]
        d = result.to_dict()

        self.assertIn('data', d)
        self.assertEqual(d['data'], [{'index': 0, 'value': 1.0}])


class ValidateDataFileTests(TestCase):
    """Tests for validate_data_file function."""

    def _create_valid_file_content(self):
        """Create valid 12-row data file content."""
        lines = []
        for i in range(12):
            lines.append(f"{i}\t{i * 10},5")
        return "\n".join(lines)

    def test_valid_file(self):
        """Should validate a correctly formatted file."""
        content = self._create_valid_file_content()
        result = validate_data_file(content)

        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
        self.assertIsNotNone(result.data)
        self.assertEqual(len(result.data), 12)
        self.assertEqual(result.data[0]['index'], 0)
        self.assertEqual(result.data[0]['value'], 0.5)

    def test_valid_bytes_utf8(self):
        """Should handle UTF-8 encoded bytes."""
        content = self._create_valid_file_content().encode('utf-8')
        result = validate_data_file(content)
        self.assertTrue(result.valid)

    def test_valid_bytes_latin1(self):
        """Should handle Latin-1 encoded bytes."""
        content = self._create_valid_file_content().encode('latin-1')
        result = validate_data_file(content)
        self.assertTrue(result.valid)

    def test_bom_removal(self):
        """Should remove BOM from file content."""
        content = '\ufeff' + self._create_valid_file_content()
        result = validate_data_file(content)
        self.assertTrue(result.valid)

    def test_wrong_row_count(self):
        """Should reject files with wrong number of rows."""
        content = "0\t1,0\n1\t2,0"
        result = validate_data_file(content)

        self.assertFalse(result.valid)
        self.assertTrue(any('12' in e['en'] for e in result.errors))

    def test_wrong_column_count(self):
        """Should reject rows with wrong number of columns."""
        lines = [f"{i}\t{i},5\textra" for i in range(12)]
        content = "\n".join(lines)
        result = validate_data_file(content)

        self.assertFalse(result.valid)
        self.assertTrue(any('2 tab-separated' in e['en'] for e in result.errors))

    def test_non_sequential_index(self):
        """Should reject non-sequential indices."""
        lines = []
        for i in range(12):
            idx = i if i != 5 else 99  # Wrong index at row 5
            lines.append(f"{idx}\t{i},5")
        content = "\n".join(lines)
        result = validate_data_file(content)

        self.assertFalse(result.valid)
        self.assertTrue(any('non-sequential' in e['en'] for e in result.errors))

    def test_invalid_index_format(self):
        """Should reject non-integer indices."""
        lines = []
        for i in range(12):
            idx = 'abc' if i == 3 else str(i)
            lines.append(f"{idx}\t{i},5")
        content = "\n".join(lines)
        result = validate_data_file(content)

        self.assertFalse(result.valid)
        self.assertTrue(any('integer' in e['en'] for e in result.errors))

    def test_invalid_value_format(self):
        """Should reject non-numeric values."""
        lines = []
        for i in range(12):
            val = 'not_a_number' if i == 7 else f"{i},5"
            lines.append(f"{i}\t{val}")
        content = "\n".join(lines)
        result = validate_data_file(content)

        self.assertFalse(result.valid)
        self.assertTrue(any('invalid numeric' in e['en'] for e in result.errors))

    def test_empty_lines_filtered(self):
        """Should filter out empty lines."""
        content = self._create_valid_file_content()
        content_with_blanks = "\n\n" + content + "\n\n"
        result = validate_data_file(content_with_blanks)
        self.assertTrue(result.valid)

    def test_real_pioggia_data(self):
        """Should validate real rainfall data format."""
        content = """0	6,13599536
1	161,902106
2	140,762227
3	29,5641577
4	156,236345
5	146,566066
6	95,4563347
7	98,3502668
8	44,6017347
9	17,4273983
10	2,55718497
11	5,29880969"""
        result = validate_data_file(content)

        self.assertTrue(result.valid)
        self.assertEqual(result.data[0]['value'], 6.13599536)
        self.assertEqual(result.data[1]['value'], 161.902106)

    def test_real_falda_data(self):
        """Should validate real water table data format (negative values)."""
        content = """0	-1,77325353
1	-1,190466818
2	-0,78159939
3	-0,843863614
4	-0,70463685
5	-0,45979896
6	-0,56104626
7	-0,70274546
8	-0,957575351
9	-1,194135433
10	-1,419464747
11	-1,415712638"""
        result = validate_data_file(content)

        self.assertTrue(result.valid)
        self.assertEqual(result.data[0]['value'], -1.77325353)


# =============================================================================
# Importer Tests
# =============================================================================

class GetTableNameTests(TestCase):
    """Tests for get_table_name function."""

    def test_basic_table_name(self):
        """Should generate table name from UUID and reference name."""
        test_uuid = uuid.UUID('550e8400-e29b-41d4-a716-446655440000')
        name = get_table_name(test_uuid, 'pioggia')
        self.assertEqual(name, 'import_550e8400e29b41d4a716446655440000_pioggia')

    def test_sanitizes_ref_name(self):
        """Should sanitize special characters in reference name."""
        test_uuid = uuid.UUID('550e8400-e29b-41d4-a716-446655440000')
        name = get_table_name(test_uuid, 'special-chars.here!')
        self.assertNotIn('-', name.split('_', 2)[2])
        self.assertNotIn('.', name)
        self.assertNotIn('!', name)


# =============================================================================
# API Endpoint Tests
# =============================================================================

class DataValidateViewTests(APITestCase):
    """Tests for the data validation endpoint."""

    def _create_valid_file_content(self):
        """Create valid 12-row data file content."""
        lines = []
        for i in range(12):
            lines.append(f"{i}\t{i * 10},5")
        return "\n".join(lines)

    def test_validate_valid_file(self):
        """Should return valid=True for correct file."""
        content = self._create_valid_file_content()
        file_obj = BytesIO(content.encode('utf-8'))
        file_obj.name = 'test.txt'

        url = '/datasets/landslide/550e8400-e29b-41d4-a716-446655440000/data/pioggia/validate'
        response = self.client.post(url, {'file': file_obj}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertEqual(len(response.data['errors']), 0)
        self.assertIsNotNone(response.data.get('data'))

    def test_validate_invalid_file(self):
        """Should return valid=False for incorrect file."""
        content = "0\t1,0\n1\t2,0"  # Only 2 rows
        file_obj = BytesIO(content.encode('utf-8'))
        file_obj.name = 'test.txt'

        url = '/datasets/landslide/550e8400-e29b-41d4-a716-446655440000/data/pioggia/validate'
        response = self.client.post(url, {'file': file_obj}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])
        self.assertGreater(len(response.data['errors']), 0)

    def test_validate_no_file(self):
        """Should return 400 when no file is provided."""
        url = '/datasets/landslide/550e8400-e29b-41d4-a716-446655440000/data/pioggia/validate'
        response = self.client.post(url, {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['valid'])


class DataImportViewTests(APITestCase):
    """Tests for the data import endpoint."""

    def _create_valid_file_content(self):
        """Create valid 12-row data file content."""
        lines = []
        for i in range(12):
            lines.append(f"{i}\t{i * 10},5")
        return "\n".join(lines)

    @patch('mode2.api.views.import_data')
    def test_import_valid_file(self, mock_import_data):
        """Should import valid file and return success."""
        mock_import_data.return_value = {
            'table_name': 'import_550e8400e29b41d4a716446655440000_pioggia',
            'rows_imported': 12,
        }

        content = self._create_valid_file_content()
        file_obj = BytesIO(content.encode('utf-8'))
        file_obj.name = 'test.txt'

        url = '/datasets/landslide/550e8400-e29b-41d4-a716-446655440000/data/pioggia/import'
        response = self.client.post(url, {'file': file_obj}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['rows_imported'], 12)
        self.assertIn('table_name', response.data)

    def test_import_invalid_file(self):
        """Should reject invalid file with validation errors."""
        content = "invalid content"
        file_obj = BytesIO(content.encode('utf-8'))
        file_obj.name = 'test.txt'

        url = '/datasets/landslide/550e8400-e29b-41d4-a716-446655440000/data/pioggia/import'
        response = self.client.post(url, {'file': file_obj}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_import_no_file(self):
        """Should return 400 when no file is provided."""
        url = '/datasets/landslide/550e8400-e29b-41d4-a716-446655440000/data/pioggia/import'
        response = self.client.post(url, {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])


class CalibrateViewTests(APITestCase):
    """Tests for the water table calibration endpoint."""

    def test_calibrate_missing_dataset_uuid(self):
        """Should reject request without dataset_uuid."""
        response = self.client.post('/functions/calibrate/', {
            'mode': 'automatic',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertTrue(any('dataset_uuid' in e['en'] for e in response.data['errors']))

    def test_calibrate_invalid_uuid(self):
        """Should reject request with invalid UUID."""
        response = self.client.post('/functions/calibrate/', {
            'dataset_uuid': 'not-a-valid-uuid',
            'mode': 'automatic',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertTrue(any('Invalid' in e['en'] for e in response.data['errors']))

    def test_calibrate_invalid_mode(self):
        """Should reject request with invalid mode."""
        response = self.client.post('/functions/calibrate/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'mode': 'invalid_mode',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertTrue(any('mode' in e['en'].lower() for e in response.data['errors']))

    def test_calibrate_missing_geometry(self):
        """Should reject request without geometry."""
        response = self.client.post('/functions/calibrate/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'mode': 'automatic'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertTrue(any('geometry' in e['en'] for e in response.data['errors']))

    def test_calibrate_missing_geometry_params(self):
        """Should reject request with missing geometry parameters."""
        response = self.client.post('/functions/calibrate/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'mode': 'automatic',
            'geometry': {
                'l1': 409.71,
                # Missing other parameters
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertTrue(any('Missing' in e['en'] for e in response.data['errors']))

    def test_calibrate_manual_requires_params(self):
        """Should require calibration_params for manual mode."""
        response = self.client.post('/functions/calibrate/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'mode': 'manual',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertTrue(any('calibration_params' in e['en'] for e in response.data['errors']))

    @patch('mode2.api.function_views.check_required_data')
    def test_calibrate_data_not_found(self, mock_check_data):
        """Should return 404 when required data is missing."""
        mock_check_data.return_value = [
            {'it': 'Dati di pioggia non trovati.', 'en': 'Rainfall data not found.'}
        ]

        response = self.client.post('/functions/calibrate/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'mode': 'automatic',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error_code'], 'DATA_NOT_FOUND')


class PrevisionViewTests(APITestCase):
    """Tests for the slope stability prevision endpoint."""

    def test_prevision_missing_dataset_uuid(self):
        """Should reject request without dataset_uuid."""
        response = self.client.post('/functions/prevision/', {
            'prevision_type': 'standard',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            },
            'geotechnical_params': {
                'gamma_sat': 20.5, 'gamma_w': 10.0, 'fi': 13.8,
                'c': 0.0, 'mu': 4.44e10
            },
            'model_params': {
                'hs': 161.9, 'kt': 2.9, 'an': 0.27, 'ho': 0.0, 'hmin': -1.773
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_prevision_invalid_type(self):
        """Should reject request with invalid prevision_type."""
        response = self.client.post('/functions/prevision/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'prevision_type': 'invalid_type',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            },
            'geotechnical_params': {
                'gamma_sat': 20.5, 'gamma_w': 10.0, 'fi': 13.8,
                'c': 0.0, 'mu': 4.44e10
            },
            'model_params': {
                'hs': 161.9, 'kt': 2.9, 'an': 0.27, 'ho': 0.0, 'hmin': -1.773
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_prevision_missing_geotechnical_params(self):
        """Should reject request without geotechnical_params."""
        response = self.client.post('/functions/prevision/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'prevision_type': 'standard',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            },
            'model_params': {
                'hs': 161.9, 'kt': 2.9, 'an': 0.27, 'ho': 0.0, 'hmin': -1.773
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertTrue(any('geotechnical_params' in e['en'] for e in response.data['errors']))

    def test_prevision_missing_model_params(self):
        """Should reject request without model_params."""
        response = self.client.post('/functions/prevision/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'prevision_type': 'standard',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            },
            'geotechnical_params': {
                'gamma_sat': 20.5, 'gamma_w': 10.0, 'fi': 13.8,
                'c': 0.0, 'mu': 4.44e10
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertTrue(any('model_params' in e['en'] for e in response.data['errors']))

    @patch('mode2.api.function_views.check_required_data')
    def test_prevision_data_not_found(self, mock_check_data):
        """Should return 404 when required data is missing."""
        mock_check_data.return_value = [
            {'it': 'Dati di pioggia non trovati.', 'en': 'Rainfall data not found.'}
        ]

        response = self.client.post('/functions/prevision/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'prevision_type': 'standard',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            },
            'geotechnical_params': {
                'gamma_sat': 20.5, 'gamma_w': 10.0, 'fi': 13.8,
                'c': 0.0, 'mu': 4.44e10
            },
            'model_params': {
                'hs': 161.9, 'kt': 2.9, 'an': 0.27, 'ho': 0.0, 'hmin': -1.773
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error_code'], 'DATA_NOT_FOUND')


# =============================================================================
# Integration Tests with Mocked .NET Bridge
# =============================================================================

class CalibrateIntegrationTests(APITestCase):
    """Integration tests for calibration with mocked .NET calculator."""

    @patch('mode2.api.function_views.get_imported_data')
    @patch('mode2.api.function_views.check_required_data')
    @patch('mode2.api.function_views.get_calculator')
    def test_calibrate_automatic_success(self, mock_get_calculator, mock_check_data, mock_get_data):
        """Should successfully perform automatic calibration."""
        # Setup mocks
        mock_check_data.return_value = []  # No missing data

        # Mock rainfall and water table data
        mock_get_data.side_effect = [
            [(i, float(i * 10)) for i in range(12)],  # rainfall
            [(i, float(-1.5 + i * 0.1)) for i in range(12)],  # water table
        ]

        # Mock calculator
        mock_calculator = MagicMock()
        mock_calculator.calibrate_water_table_auto.return_value = {
            'hs': 161.9,
            'kt': 2.9,
            'an': 0.27,
            'ho': 0.0,
            'hmin': -1.773,
            'calculated_water_table': [-1.75 + i * 0.1 for i in range(12)],
        }
        mock_get_calculator.return_value = mock_calculator

        response = self.client.post('/functions/calibrate/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'mode': 'automatic',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('calibrated_params', response.data)
        self.assertIn('calculated_water_table', response.data)
        self.assertEqual(response.data['calibrated_params']['hs'], 161.9)

    @patch('mode2.api.function_views.get_imported_data')
    @patch('mode2.api.function_views.check_required_data')
    @patch('mode2.api.function_views.get_calculator')
    def test_calibrate_manual_success(self, mock_get_calculator, mock_check_data, mock_get_data):
        """Should successfully perform manual calibration."""
        mock_check_data.return_value = []

        mock_get_data.side_effect = [
            [(i, float(i * 10)) for i in range(12)],
            [(i, float(-1.5 + i * 0.1)) for i in range(12)],
        ]

        mock_calculator = MagicMock()
        mock_calculator.calculate_water_table.return_value = [-1.75 + i * 0.1 for i in range(12)]
        mock_get_calculator.return_value = mock_calculator

        response = self.client.post('/functions/calibrate/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'mode': 'manual',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            },
            'calibration_params': {
                'hs': 161.9, 'kt': 2.9, 'an': 0.27, 'ho': 0.0, 'hmin': -1.773
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])


class PrevisionIntegrationTests(APITestCase):
    """Integration tests for prevision with mocked .NET calculator."""

    @patch('mode2.api.function_views.get_imported_data')
    @patch('mode2.api.function_views.check_required_data')
    @patch('mode2.api.function_views.get_calculator')
    def test_prevision_standard_success(self, mock_get_calculator, mock_check_data, mock_get_data):
        """Should successfully perform standard prevision."""
        mock_check_data.return_value = []

        mock_get_data.side_effect = [
            [(i, float(i * 10)) for i in range(12)],  # rainfall
            [(i, float(-1.5 + i * 0.1)) for i in range(12)],  # water table
            [(i, float(i * 2)) for i in range(12)],  # displacement
        ]

        mock_calculator = MagicMock()
        mock_calculator.calculate_water_table.return_value = [-1.75 + i * 0.1 for i in range(12)]
        mock_calculator.run_prevision.return_value = {
            'time': [float(i) for i in range(12)],
            'displacement_calculated': [float(i * 2) for i in range(12)],
            'velocity': [0.0] * 12,
            'critical_water_table': [-1.25] * 12,
            'safety_factor': [1.2] * 12,
        }
        mock_get_calculator.return_value = mock_calculator

        response = self.client.post('/functions/prevision/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'prevision_type': 'standard',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            },
            'geotechnical_params': {
                'gamma_sat': 20.5, 'gamma_w': 10.0, 'fi': 13.8,
                'c': 0.0, 'mu': 4.44e10
            },
            'model_params': {
                'hs': 161.9, 'kt': 2.9, 'an': 0.27, 'ho': 0.0, 'hmin': -1.773
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('results', response.data)
        self.assertIn('displacement_calculated', response.data['results'])
        self.assertIn('velocity', response.data['results'])

    @patch('mode2.api.function_views.get_imported_data')
    @patch('mode2.api.function_views.check_required_data')
    @patch('mode2.api.function_views.get_calculator')
    def test_prevision_best_fit_viscosity(self, mock_get_calculator, mock_check_data, mock_get_data):
        """Should perform prevision with viscosity calibration."""
        mock_check_data.return_value = []

        mock_get_data.side_effect = [
            [(i, float(i * 10)) for i in range(12)],
            [(i, float(-1.5 + i * 0.1)) for i in range(12)],
            [(i, float(i * 2)) for i in range(12)],
        ]

        mock_calculator = MagicMock()
        mock_calculator.calculate_water_table.return_value = [-1.75 + i * 0.1 for i in range(12)]
        mock_calculator.run_prevision.return_value = {
            'time': [float(i) for i in range(12)],
            'displacement_calculated': [float(i * 2) for i in range(12)],
            'velocity': [0.0] * 12,
            'critical_water_table': [-1.25] * 12,
            'safety_factor': [1.2] * 12,
            'mu': 4.5e10,  # Calibrated viscosity
        }
        mock_get_calculator.return_value = mock_calculator

        response = self.client.post('/functions/prevision/', {
            'dataset_uuid': '550e8400-e29b-41d4-a716-446655440000',
            'prevision_type': 'best_fit_viscosity',
            'geometry': {
                'l1': 409.71, 'l2': 314.46, 'h': 20.31,
                'beta1': 5.18, 'beta2': 11.66, 'i_pc': 7.99
            },
            'geotechnical_params': {
                'gamma_sat': 20.5, 'gamma_w': 10.0, 'fi': 13.8,
                'c': 0.0, 'mu': 4.44e10
            },
            'model_params': {
                'hs': 161.9, 'kt': 2.9, 'an': 0.27, 'ho': 0.0, 'hmin': -1.773
            }
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('calibrated_viscosity', response.data)
        self.assertEqual(response.data['calibrated_viscosity']['mu'], 4.5e10)
