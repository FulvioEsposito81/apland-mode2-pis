"""
API views for MODE II calibration and prevision functions.
"""

from uuid import UUID

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .data_retrieval import DataNotFoundError, check_required_data, get_imported_data
from .dotnet_bridge import DotNetError, get_calculator


def format_indexed_data(data: list[tuple[int, float]]) -> list[dict[str, float]]:
    """Format (index, value) tuples as list of dicts for JSON response."""
    return [{'index': idx, 'value': val} for idx, val in data]


def format_array_as_indexed(values: list[float]) -> list[dict[str, float]]:
    """Format a list of values as indexed dicts for JSON response."""
    return [{'index': i, 'value': val} for i, val in enumerate(values)]


def interpolate_to_integer_grid(
    data: list[tuple[int, float]], grid_size: int
) -> list[float]:
    """Interpolate (index, value) data onto an integer grid [0, 1, ..., grid_size-1].

    Replicates the C# CalcolaVettoriMetodo / InterpolazioneLineare preprocessing
    that aligns displacement data to the water table time grid before computation.

    For each integer time point, linearly interpolates between the bracketing
    data points. Points beyond the data range use the nearest boundary value.

    Args:
        data: List of (index, value) tuples, sorted by index ascending.
        grid_size: Number of integer grid points to produce.

    Returns:
        List of interpolated values at [0, 1, ..., grid_size-1].
    """
    if not data:
        return [0.0] * grid_size

    x_vals = [float(idx) for idx, _ in data]
    y_vals = [val for _, val in data]

    result = []
    for i in range(grid_size):
        x = float(i)

        # Clamp to data range
        if x <= x_vals[0]:
            result.append(y_vals[0])
            continue
        if x >= x_vals[-1]:
            result.append(y_vals[-1])
            continue

        # Find bracketing interval: x_vals[k-1] <= x < x_vals[k]
        k = 0
        while k < len(x_vals) and x_vals[k] <= x:
            k += 1

        x0, y0 = x_vals[k - 1], y_vals[k - 1]
        x1, y1 = x_vals[k], y_vals[k]

        # Linear interpolation (matches C# formula)
        y = y0 * (x - x1) / (x0 - x1) + y1 * (x - x0) / (x1 - x0)
        result.append(y)

    return result


class CalibrateView(APIView):
    """
    Water table calibration endpoint.

    POST /functions/calibrate/

    Performs automatic or manual water table calibration using the MODE II
    Best Fit Pioggia algorithm.

    Modes:
    - "automatic": Finds optimal calibration parameters (hs, kt, an, ho, hmin)
    - "manual": Uses provided calibration_params to calculate water table
    """

    def post(self, request):
        # Validate required fields
        errors = []

        dataset_uuid = request.data.get('dataset_uuid')
        if not dataset_uuid:
            errors.append({
                'it': "Campo 'dataset_uuid' obbligatorio.",
                'en': "'dataset_uuid' field is required."
            })
        else:
            try:
                dataset_uuid = UUID(dataset_uuid)
            except (ValueError, TypeError):
                errors.append({
                    'it': "UUID dataset non valido.",
                    'en': "Invalid dataset UUID."
                })

        mode = request.data.get('mode', 'automatic')
        if mode not in ('automatic', 'manual'):
            errors.append({
                'it': "Modalità non valida. Usare 'automatic' o 'manual'.",
                'en': "Invalid mode. Use 'automatic' or 'manual'."
            })

        geometry = request.data.get('geometry')
        if not geometry:
            errors.append({
                'it': "Campo 'geometry' obbligatorio.",
                'en': "'geometry' field is required."
            })
        else:
            required_geo = ['l1', 'l2', 'h', 'beta1', 'beta2', 'i_pc']
            missing = [k for k in required_geo if k not in geometry]
            if missing:
                errors.append({
                    'it': f"Parametri geometria mancanti: {', '.join(missing)}",
                    'en': f"Missing geometry parameters: {', '.join(missing)}"
                })

        # For manual mode, calibration_params is required
        calibration_params = request.data.get('calibration_params')
        if mode == 'manual' and not calibration_params:
            errors.append({
                'it': "Campo 'calibration_params' obbligatorio per modalità manuale.",
                'en': "'calibration_params' field is required for manual mode."
            })
        elif mode == 'manual' and calibration_params:
            required_params = ['hs', 'kt', 'an', 'ho', 'hmin']
            missing = [k for k in required_params if k not in calibration_params]
            if missing:
                errors.append({
                    'it': f"Parametri calibrazione mancanti: {', '.join(missing)}",
                    'en': f"Missing calibration parameters: {', '.join(missing)}"
                })

        if errors:
            return Response({
                'success': False,
                'errors': errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check that required data exists
        data_errors = check_required_data(dataset_uuid, ['pioggia', 'falda'])
        if data_errors:
            return Response({
                'success': False,
                'errors': data_errors,
                'error_code': 'DATA_NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

        # Retrieve data
        try:
            rainfall_data = get_imported_data(dataset_uuid, 'pioggia')
            water_table_data = get_imported_data(dataset_uuid, 'falda')
        except DataNotFoundError as e:
            return Response({
                'success': False,
                'errors': [{'it': e.message_it, 'en': e.message_en}],
                'error_code': 'DATA_NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

        # Extract values (drop indices)
        rainfall_values = [v for _, v in rainfall_data]
        water_table_values = [v for _, v in water_table_data]

        # Perform calibration
        try:
            calculator = get_calculator()

            if mode == 'automatic':
                result = calculator.calibrate_water_table_auto(
                    rainfall=rainfall_values,
                    water_table_measured=water_table_values,
                    geometry=geometry,
                )
                calibrated_params = {
                    'hs': result['hs'],
                    'kt': result['kt'],
                    'an': result['an'],
                    'ho': result['ho'],
                    'hmin': result['hmin'],
                }
                calculated_wt = result['calculated_water_table']
            else:
                # Manual mode: use provided parameters
                calibrated_params = {
                    'hs': calibration_params['hs'],
                    'kt': calibration_params['kt'],
                    'an': calibration_params['an'],
                    'ho': calibration_params['ho'],
                    'hmin': calibration_params['hmin'],
                }
                calculated_wt = calculator.calculate_water_table(
                    rainfall=rainfall_values,
                    hs=calibrated_params['hs'],
                    kt=calibrated_params['kt'],
                    an=calibrated_params['an'],
                    ho=calibrated_params['ho'],
                    hmin=calibrated_params['hmin'],
                    alpha=geometry['i_pc'],
                )

            return Response({
                'success': True,
                'calibrated_params': calibrated_params,
                'calculated_water_table': format_array_as_indexed(calculated_wt),
                'measured_water_table': format_indexed_data(water_table_data),
                'rainfall_data': format_indexed_data(rainfall_data),
            })

        except DotNetError as e:
            return Response({
                'success': False,
                'errors': [{'it': e.message_it, 'en': e.message_en}],
                'error_code': 'CALIBRATION_FAILED',
                'details': e.details,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PrevisionView(APIView):
    """
    Slope stability prevision endpoint.

    POST /functions/prevision/

    Performs slope stability analysis using the MODE II multi-block model.

    Types:
    - "standard": Uses provided viscosity parameter
    - "best_fit_viscosity": Also calculates optimal viscosity coefficient
    """

    def post(self, request):
        # Validate required fields
        errors = []

        dataset_uuid = request.data.get('dataset_uuid')
        if not dataset_uuid:
            errors.append({
                'it': "Campo 'dataset_uuid' obbligatorio.",
                'en': "'dataset_uuid' field is required."
            })
        else:
            try:
                dataset_uuid = UUID(dataset_uuid)
            except (ValueError, TypeError):
                errors.append({
                    'it': "UUID dataset non valido.",
                    'en': "Invalid dataset UUID."
                })

        prevision_type = request.data.get('prevision_type', 'standard')
        if prevision_type not in ('standard', 'best_fit_viscosity'):
            errors.append({
                'it': "Tipo previsione non valido. Usare 'standard' o 'best_fit_viscosity'.",
                'en': "Invalid prevision type. Use 'standard' or 'best_fit_viscosity'."
            })

        geometry = request.data.get('geometry')
        if not geometry:
            errors.append({
                'it': "Campo 'geometry' obbligatorio.",
                'en': "'geometry' field is required."
            })
        else:
            required_geo = ['l1', 'l2', 'h', 'beta1', 'beta2', 'i_pc']
            missing = [k for k in required_geo if k not in geometry]
            if missing:
                errors.append({
                    'it': f"Parametri geometria mancanti: {', '.join(missing)}",
                    'en': f"Missing geometry parameters: {', '.join(missing)}"
                })

        geotechnical_params = request.data.get('geotechnical_params')
        if not geotechnical_params:
            errors.append({
                'it': "Campo 'geotechnical_params' obbligatorio.",
                'en': "'geotechnical_params' field is required."
            })
        else:
            required_geo = ['gamma_sat', 'gamma_w', 'fi', 'c', 'mu']
            missing = [k for k in required_geo if k not in geotechnical_params]
            if missing:
                errors.append({
                    'it': f"Parametri geotecnici mancanti: {', '.join(missing)}",
                    'en': f"Missing geotechnical parameters: {', '.join(missing)}"
                })

        model_params = request.data.get('model_params')
        if not model_params:
            errors.append({
                'it': "Campo 'model_params' obbligatorio.",
                'en': "'model_params' field is required."
            })
        else:
            required_mp = ['hs', 'kt', 'an', 'ho', 'hmin']
            missing = [k for k in required_mp if k not in model_params]
            if missing:
                errors.append({
                    'it': f"Parametri modello mancanti: {', '.join(missing)}",
                    'en': f"Missing model parameters: {', '.join(missing)}"
                })

        analysis_settings = request.data.get('analysis_settings', {})
        num_harmonics = analysis_settings.get('num_harmonics', 100)

        if errors:
            return Response({
                'success': False,
                'errors': errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check that required data exists
        data_errors = check_required_data(dataset_uuid, ['pioggia', 'falda', 'spostamento'])
        if data_errors:
            return Response({
                'success': False,
                'errors': data_errors,
                'error_code': 'DATA_NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

        # Retrieve data
        try:
            rainfall_data = get_imported_data(dataset_uuid, 'pioggia')
            water_table_data = get_imported_data(dataset_uuid, 'falda')
            displacement_data = get_imported_data(dataset_uuid, 'spostamento')
        except DataNotFoundError as e:
            return Response({
                'success': False,
                'errors': [{'it': e.message_it, 'en': e.message_en}],
                'error_code': 'DATA_NOT_FOUND',
            }, status=status.HTTP_404_NOT_FOUND)

        # Extract values
        rainfall_values = [v for _, v in rainfall_data]

        # Displacement unit conversion factors
        # The imported displacement data is in user units; computation works in meters
        displacement_unit = request.data.get('displacement_unit', 'cm')
        unit_to_meters = {'mm': 0.001, 'cm': 0.01, 'm': 1.0}
        molt_spost = unit_to_meters.get(displacement_unit, 0.01)
        molt_out_spost = 1.0 / molt_spost

        # Time unit → seconds per time step (matches C# UnitaDiMisura)
        time_unit = request.data.get('time_unit', 'mesi')
        time_unit_to_sec = {'giorni': 86400.0, 'mesi': 2592000.0, 'anni': 31104000.0}
        sec = time_unit_to_sec.get(time_unit, 2592000.0)

        # Calculate water table with model parameters
        try:
            calculator = get_calculator()

            # First calculate water table from rainfall using model params
            calculated_wt = calculator.calculate_water_table(
                rainfall=rainfall_values,
                hs=model_params['hs'],
                kt=model_params['kt'],
                an=model_params['an'],
                ho=model_params['ho'],
                hmin=model_params['hmin'],
                alpha=geometry['i_pc'],
            )

            # Time array (indices) — defines the computation grid
            time_array = [float(i) for i in range(len(rainfall_data))]
            n_time = len(time_array)

            # Interpolate displacement data to the integer time grid.
            # This matches the C# CalcolaVettoriMetodo / InterpolazioneLineare
            # preprocessing: displacement measurements may have different time
            # points or gaps, so they must be linearly interpolated to the same
            # integer grid [0, 1, ..., N-1] used by rainfall and water table.
            displacement_values = interpolate_to_integer_grid(
                displacement_data, n_time
            )

            # Run prevision
            result = calculator.run_prevision(
                geometry=geometry,
                geotechnical_params=geotechnical_params,
                model_params=model_params,
                time_array=time_array,
                water_table_calculated=calculated_wt,
                displacement_measured=displacement_values,
                num_harmonics=num_harmonics,
                calculate_viscosity=(prevision_type == 'best_fit_viscosity'),
                molt_spost=molt_spost,
                molt_out_spost=molt_out_spost,
                sec=sec,
            )

            # Post-process results to match original C# application:
            # 1. Convert displacement from meters to user display unit
            disp_calc = [v * molt_out_spost for v in result['displacement_calculated']]
            # 2. Convert critical water table: subtract h to get depth below surface (zw)
            #    Raw hwcrit is absolute height above sliding surface base;
            #    subtracting h gives negative depth below ground surface
            h = geometry['h']
            critical_wt = [v - h for v in result['critical_water_table']]

            response = {
                'success': True,
                'results': {
                    'time': format_array_as_indexed(time_array),
                    'displacement_calculated': format_array_as_indexed(disp_calc),
                    'displacement_measured': format_indexed_data(displacement_data),
                    'velocity': format_array_as_indexed(result['velocity']),
                    'critical_water_table': format_array_as_indexed(critical_wt),
                    'safety_factor': format_array_as_indexed(result['safety_factor']),
                    'water_table_calculated': format_array_as_indexed(calculated_wt),
                    'water_table_measured': format_indexed_data(water_table_data),
                },
            }

            if 'mu' in result:
                response['calibrated_viscosity'] = {
                    'mu': result['mu'],
                    'unit': 'kN*month/m2',
                }

            return Response(response)

        except DotNetError as e:
            return Response({
                'success': False,
                'errors': [{'it': e.message_it, 'en': e.message_en}],
                'error_code': 'PREVISION_FAILED',
                'details': e.details,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
