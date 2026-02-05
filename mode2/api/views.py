"""
API views for MODE II data validation and import.
"""

from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view

from .importers import import_data
from .validators import validate_data_file


@api_view(['GET'])
def health(request):
    return Response()

class DataValidateView(APIView):
    """
    Validate a MODE II data file without importing.

    POST /<dataset_ref_name>/<uuid>/data/<data_ref_name>/validate

    Accepts multipart/form-data with a 'file' field containing the data file.

    Returns:
        {
            "valid": true/false,
            "errors": [{"it": "...", "en": "..."}, ...],
            "warnings": [{"it": "...", "en": "..."}, ...],
            "data": [{"index": 0, "value": 1.23}, ...] (only if valid)
        }
    """

    parser_classes = [MultiPartParser]

    def post(self, request, dataset_ref_name: str, uuid, data_ref_name: str):
        # Check for file in request
        if 'file' not in request.FILES:
            return Response(
                {
                    'valid': False,
                    'errors': [
                        {
                            'it': "Nessun file caricato. Utilizzare il campo 'file'.",
                            'en': "No file uploaded. Use the 'file' field."
                        }
                    ],
                    'warnings': [],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES['file']
        file_content = uploaded_file.read()

        # Validate the file
        result = validate_data_file(file_content)

        return Response(result.to_dict())


class DataImportView(APIView):
    """
    Validate and import a MODE II data file.

    POST /<dataset_ref_name>/<uuid>/data/<data_ref_name>/import

    Accepts multipart/form-data with a 'file' field containing the data file.

    Returns on success:
        {
            "success": true,
            "table_name": "import_<uuid>_<data_ref_name>",
            "rows_imported": 12
        }

    Returns on validation failure:
        {
            "success": false,
            "valid": false,
            "errors": [...],
            "warnings": [...]
        }
    """

    parser_classes = [MultiPartParser]

    def post(self, request, dataset_ref_name: str, uuid, data_ref_name: str):
        # Check for file in request
        if 'file' not in request.FILES:
            return Response(
                {
                    'success': False,
                    'valid': False,
                    'errors': [
                        {
                            'it': "Nessun file caricato. Utilizzare il campo 'file'.",
                            'en': "No file uploaded. Use the 'file' field."
                        }
                    ],
                    'warnings': [],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES['file']
        file_content = uploaded_file.read()

        # Validate the file first
        validation_result = validate_data_file(file_content)

        if not validation_result.valid:
            return Response(
                {
                    'success': False,
                    **validation_result.to_dict()
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Import the data
        import_result = import_data(uuid, data_ref_name, validation_result.data)

        return Response({
            'success': True,
            **import_result
        })
