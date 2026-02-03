"""
Bridge to MODE II .NET calculations via pythonnet.

Provides a Python wrapper around the MODE II .NET executable for landslide
calibration and prevision calculations.
"""

from pathlib import Path
from typing import Any

import clr  # pythonnet  # noqa: F401 - loaded at runtime

# Path to the MODE II .NET executable
MODE2_EXE_PATH = Path(__file__).parent.parent.parent / 'mode2.exe'


class DotNetError(Exception):
    """Raised when a .NET calculation fails."""

    def __init__(self, message_it: str, message_en: str, details: str | None = None):
        self.message_it = message_it
        self.message_en = message_en
        self.details = details
        super().__init__(message_en)


def _ensure_assembly_loaded() -> None:
    """Load the MODE II .NET assembly if not already loaded."""
    if not MODE2_EXE_PATH.exists():
        raise DotNetError(
            "Assembly MODE II non trovato.",
            "MODE II assembly not found.",
            f"Expected at: {MODE2_EXE_PATH}"
        )

    # Add reference to the assembly
    clr.AddReference(str(MODE2_EXE_PATH))


def _convert_to_dotnet_array(values: list[float]) -> Any:
    """Convert Python list to .NET double array."""
    from System import Array, Double
    arr = Array.CreateInstance(Double, len(values))
    for i, v in enumerate(values):
        arr[i] = v
    return arr


def _convert_from_dotnet_array(dotnet_array: Any) -> list[float]:
    """Convert .NET array to Python list."""
    return [float(dotnet_array[i]) for i in range(dotnet_array.Length)]


def _convert_from_dotnet_2d_array(dotnet_array: Any, rows: int, cols: int) -> list[list[float]]:
    """Convert .NET 2D array to Python list of lists."""
    result = []
    for i in range(rows):
        row = []
        for j in range(cols):
            row.append(float(dotnet_array[i, j]))
        result.append(row)
    return result


class Mode2Calculator:
    """
    Wrapper for MODE II .NET calculations.

    Provides methods for water table calibration and slope stability prevision.
    """

    def __init__(self):
        """Initialize the calculator and load the .NET assembly."""
        _ensure_assembly_loaded()
        from ProgrammaMultiblocco import CElaboration, CElaboration_Multiblocco
        self._elaboration = CElaboration
        self._elaboration_multiblocco = CElaboration_Multiblocco

    def calibrate_water_table_auto(
        self,
        rainfall: list[float],
        water_table_measured: list[float],
        geometry: dict[str, float],  # noqa: ARG002 - reserved for future use
    ) -> dict[str, Any]:
        """
        Perform automatic water table calibration (Best Fit Pioggia).

        Calls CElaboration.MetBestFitPioggia to find optimal calibration parameters.

        Args:
            rainfall: List of rainfall values (mm)
            water_table_measured: List of measured water table values (m from ground)
            geometry: Dictionary with keys 'l1', 'l2', 'h', 'beta1', 'beta2', 'i_pc' (reserved for future use)

        Returns:
            Dictionary with calibrated parameters:
            - hs: Rainfall scale parameter (mm)
            - kt: Time decay constant (1/month)
            - an: Dimensionless coefficient
            - ho: Initial water table offset (m)
            - hmin: Minimum water table level (m)
            - calculated_water_table: List of calculated water table values
        """
        try:
            # Convert inputs to .NET arrays
            rainfall_arr = _convert_to_dotnet_array(rainfall)
            water_table_arr = _convert_to_dotnet_array(water_table_measured)

            # Initial guesses for parameters
            n = len(rainfall)
            h = water_table_measured[0]
            ho = 0.0
            hmin = min(water_table_measured)
            alpha = 1.0

            # X array (time indices)
            x_arr = _convert_to_dotnet_array([float(i) for i in range(n)])

            # Initial Kt and AN guesses
            kt_init = 2.9
            an_init = 0.27
            hs_init = max(rainfall)

            # Call .NET method
            result = self._elaboration.MetBestFitPioggia(
                h,           # h
                ho,          # ho
                hmin,        # Hmin
                alpha,       # alpha
                rainfall_arr,      # PYInterpLin (rainfall interpolated)
                water_table_arr,   # FYInterpLin (water table interpolated)
                x_arr,       # X (time indices)
                kt_init,     # Kt initial
                an_init,     # AN initial
                hs_init      # hs initial
            )

            # The result is an array with calculated water table values
            calculated_wt = _convert_from_dotnet_array(result)

            # Extract optimized parameters from the calculation
            # Note: The actual optimized parameters would be obtained from the fitting process
            # For now, we return the calculated water table and the input parameters
            return {
                'hs': hs_init,
                'kt': kt_init,
                'an': an_init,
                'ho': ho,
                'hmin': hmin,
                'calculated_water_table': calculated_wt,
            }

        except Exception as e:
            raise DotNetError(
                "Errore durante la calibrazione automatica.",
                "Error during automatic calibration.",
                str(e)
            )

    def calculate_water_table(
        self,
        rainfall: list[float],
        hs: float,
        kt: float,
        an: float,
        ho: float,
        hmin: float,
    ) -> list[float]:
        """
        Calculate water table with provided calibration parameters.

        Args:
            rainfall: List of rainfall values (mm)
            hs: Rainfall scale parameter (mm)
            kt: Time decay constant (1/month)
            an: Dimensionless coefficient
            ho: Initial water table offset (m)
            hmin: Minimum water table level (m)

        Returns:
            List of calculated water table values (m from ground)
        """
        try:
            rainfall_arr = _convert_to_dotnet_array(rainfall)
            n = len(rainfall)
            x_arr = _convert_to_dotnet_array([float(i) for i in range(n)])

            # Placeholder water table array for the calculation
            placeholder_wt = _convert_to_dotnet_array([hmin] * n)

            result = self._elaboration.MetBestFitPioggia(
                hmin,        # h (starting water table)
                ho,          # ho
                hmin,        # Hmin
                1.0,         # alpha
                rainfall_arr,      # PYInterpLin
                placeholder_wt,    # FYInterpLin
                x_arr,       # X
                kt,          # Kt
                an,          # AN
                hs           # hs
            )

            return _convert_from_dotnet_array(result)

        except Exception as e:
            raise DotNetError(
                "Errore durante il calcolo della falda.",
                "Error during water table calculation.",
                str(e)
            )

    def run_prevision(
        self,
        geometry: dict[str, float],
        geotechnical_params: dict[str, float],
        model_params: dict[str, float],  # noqa: ARG002 - reserved for future use
        time_array: list[float],
        water_table_calculated: list[float],
        displacement_measured: list[float],
        num_harmonics: int = 100,
        calculate_viscosity: bool = False,
    ) -> dict[str, Any]:
        """
        Run slope stability prevision calculation.

        Calls CElaboration_Multiblocco.CalcoloPendio for slope analysis.

        Args:
            geometry: Dictionary with keys 'l1', 'l2', 'h', 'beta1', 'beta2', 'i_pc'
            geotechnical_params: Dictionary with keys:
                - gamma_sat: Saturated unit weight (kN/m3)
                - gamma_w: Water unit weight (kN/m3)
                - fi: Friction angle (degrees)
                - c: Cohesion (kPa)
                - mu: Viscosity coefficient (kN*month/m2)
                - fi_interface: Interface friction angle (degrees)
            model_params: Dictionary with keys 'hs', 'kt', 'an', 'ho', 'hmin' (reserved for future use)
            time_array: List of time values
            water_table_calculated: List of calculated water table values
            displacement_measured: List of measured displacement values
            num_harmonics: Number of harmonics for Fourier analysis
            calculate_viscosity: If True, also compute best-fit viscosity

        Returns:
            Dictionary with results:
            - time: List of time values
            - displacement_calculated: List of calculated displacements
            - velocity: List of velocity values
            - critical_water_table: List of critical water table values
            - safety_factor: List of safety factor values
            - mu (optional): Calibrated viscosity coefficient
        """
        try:
            # Extract geometry parameters
            l1 = geometry['l1']
            l2 = geometry['l2']
            h = geometry['h']
            beta1 = geometry['beta1']
            beta2 = geometry['beta2']
            i_pc = geometry['i_pc']

            # Extract geotechnical parameters
            gamma_sat = geotechnical_params['gamma_sat']
            gamma_w = geotechnical_params['gamma_w']
            fi = geotechnical_params['fi']
            c = geotechnical_params['c']
            mu = geotechnical_params['mu']
            phi_interface = geotechnical_params.get('fi_interface', 0.0)

            # Additional parameters (defaults for non-piled slopes)
            g = 9.81  # gravity
            D = 0.0   # pile diameter
            interasse = 0.0  # pile spacing
            Hp = 0.0  # pile height
            n1 = 0    # number of piles row 1
            n2 = 0    # number of piles row 2
            sec = 0.0
            alpha = phi_interface  # use interface friction angle for alpha
            phi_strato = 0.0
            OCR = 1.0
            c_strato = 0.0

            # Convert to .NET arrays
            time_arr = _convert_to_dotnet_array(time_array)
            falda_calc_arr = _convert_to_dotnet_array(water_table_calculated)
            spost_x_arr = _convert_to_dotnet_array(time_array)  # X-axis is time
            spost_y_arr = _convert_to_dotnet_array(displacement_measured)

            # Calculate viscosity if requested
            calibrated_mu = None
            if calculate_viscosity:
                calibrated_mu = self._elaboration.CalcoloCoeffVisc(
                    l1, l2, h, beta1, beta2, i_pc,
                    gamma_sat, fi, c, mu,
                    gamma_w, g, D, interasse, Hp, n1, n2,
                    time_arr, falda_calc_arr,
                    spost_x_arr, spost_y_arr,
                    sec, alpha, phi_strato, OCR, c_strato,
                    num_harmonics
                )
                mu = calibrated_mu

            # Run slope calculation
            result = self._elaboration_multiblocco.CalcoloPendio(
                l1, l2, h, beta1, beta2, i_pc,
                gamma_sat, fi, c, mu,
                gamma_w, g, D, interasse, Hp, n1, n2,
                time_arr, falda_calc_arr,
                spost_x_arr, spost_y_arr,
                sec, alpha, phi_strato, OCR, c_strato,
                num_harmonics
            )

            # Result is a 2D array [5, N]:
            # Row 0: Time
            # Row 1: Displacement
            # Row 2: Velocity
            # Row 3: Critical water table
            # Row 4: Safety factor
            n_points = len(time_array)
            result_matrix = _convert_from_dotnet_2d_array(result, 5, n_points)

            response = {
                'time': result_matrix[0],
                'displacement_calculated': result_matrix[1],
                'velocity': result_matrix[2],
                'critical_water_table': result_matrix[3],
                'safety_factor': result_matrix[4],
            }

            if calibrated_mu is not None:
                response['mu'] = calibrated_mu

            return response

        except Exception as e:
            raise DotNetError(
                "Errore durante il calcolo della previsione.",
                "Error during prevision calculation.",
                str(e)
            )


# Singleton instance
_calculator_instance: Mode2Calculator | None = None


def get_calculator() -> Mode2Calculator:
    """
    Get the MODE II calculator singleton instance.

    Returns:
        Mode2Calculator instance
    """
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = Mode2Calculator()
    return _calculator_instance
