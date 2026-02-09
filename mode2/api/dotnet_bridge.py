"""
Bridge to MODE II .NET calculations via pythonnet.

Provides a Python wrapper around the MODE II .NET executable for landslide
calibration and prevision calculations.
"""

from pathlib import Path
from typing import Any

# Configure pythonnet to use CoreCLR before importing clr
import pythonnet

# Explicitly load CoreCLR runtime (required for .NET Core/.NET 5+)
# This must be done before importing clr
try:
    pythonnet.load("coreclr")
except Exception as e:
    raise RuntimeError(
        f"Failed to load CoreCLR runtime. Ensure .NET runtime is installed and "
        f"DOTNET_ROOT environment variable is set. Error: {e}"
    ) from e

import clr  # noqa: F401 - loaded at runtime

# Path to the MODE II .NET executable
MODE2_EXE_PATH = Path(__file__).parent.parent.parent / 'mode2.exe'


class DotNetError(Exception):
    """Raised when a .NET calculation fails."""

    def __init__(self, message_it: str, message_en: str, details: str | None = None):
        self.message_it = message_it
        self.message_en = message_en
        self.details = details
        super().__init__(message_en)


def _load_assembly_types() -> tuple[Any, Any]:
    """Load the MODE II .NET assembly and return the calculation types.

    Returns the types directly via assembly reflection to avoid triggering
    a full namespace import, which fails because the assembly also contains
    GUI types that depend on System.Windows.Forms (not available on Linux).
    """
    if not MODE2_EXE_PATH.exists():
        raise DotNetError(
            "Assembly MODE II non trovato.",
            "MODE II assembly not found.",
            f"Expected at: {MODE2_EXE_PATH}"
        )

    assembly = clr.AddReference(str(MODE2_EXE_PATH))

    from System import Activator

    elab_type = assembly.GetType('ProgrammaMultiblocco.CElaboration')
    elab_multi_type = assembly.GetType('ProgrammaMultiblocco.CElaboration_Multiblocco')

    if elab_type is None or elab_multi_type is None:
        raise DotNetError(
            "Tipi di calcolo non trovati nell'assembly.",
            "Calculation types not found in assembly.",
        )

    return Activator.CreateInstance(elab_type), Activator.CreateInstance(elab_multi_type)


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
    """Convert .NET rectangular 2D array (Double[,]) to Python list of lists."""
    result = []
    for i in range(rows):
        row = []
        for j in range(cols):
            row.append(float(dotnet_array[i, j]))
        result.append(row)
    return result


def _convert_from_dotnet_jagged_array(dotnet_array: Any, rows: int) -> list[list[float]]:
    """Convert .NET jagged array (Double[][]) to Python list of lists.

    Each inner array may have a different length (true jagged array).
    """
    result = []
    for i in range(rows):
        inner = dotnet_array[i]
        row = [float(inner[j]) for j in range(inner.Length)]
        result.append(row)
    return result


class Mode2Calculator:
    """
    Wrapper for MODE II .NET calculations.

    Provides methods for water table calibration and slope stability prevision.
    """

    def __init__(self):
        """Initialize the calculator and load the .NET assembly."""
        elab, elab_multi = _load_assembly_types()
        self._elaboration = elab
        self._elaboration_multiblocco = elab_multi

    def calibrate_water_table_auto(
        self,
        rainfall: list[float],
        water_table_measured: list[float],
        geometry: dict[str, float],
    ) -> dict[str, Any]:
        """
        Perform automatic water table calibration (Best Fit Pioggia).

        Calls CElaboration.MetBestFitPioggia to find optimal calibration parameters.

        Args:
            rainfall: List of rainfall values (mm)
            water_table_measured: List of measured water table values (m from ground)
            geometry: Dictionary with keys 'l1', 'l2', 'h', 'beta1', 'beta2', 'i_pc'

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
            alpha = geometry['i_pc']  # slope angle in degrees

            # X array (time indices)
            x_arr = _convert_to_dotnet_array([float(i) for i in range(n)])

            # Initial Kt and AN guesses
            kt_init = 2.9
            an_init = 0.27
            hs_init = max(rainfall)

            # Call .NET method — returns Double[] {AN, Kt, hs} (optimized params)
            params = self._elaboration.MetBestFitPioggia(
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

            # Extract optimized parameters from result array
            an_opt = float(params[0])
            kt_opt = float(params[1])
            hs_opt = float(params[2])

            # Calculate water table with optimized parameters
            calculated_wt = self.calculate_water_table(
                rainfall=rainfall,
                hs=hs_opt,
                kt=kt_opt,
                an=an_opt,
                ho=ho,
                hmin=hmin,
                alpha=alpha,
            )

            return {
                'hs': hs_opt,
                'kt': kt_opt,
                'an': an_opt,
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
        alpha: float = 7.99,
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
            alpha: Ground surface inclination angle (degrees)

        Returns:
            List of calculated water table values (m from ground)
        """
        try:
            n = len(rainfall)
            x_arr = _convert_to_dotnet_array([float(i) for i in range(n)])
            rainfall_arr = _convert_to_dotnet_array(rainfall)

            result = self._elaboration.CalcolaPioggiaFOR(
                ho,          # ho
                hmin,        # Hmin
                alpha,       # alpha (slope angle in degrees)
                hs,          # hs
                kt,          # Kt
                an,          # AN
                x_arr,       # PX (time indices)
                rainfall_arr # PY (rainfall values)
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
        molt_spost: float = 1.0,
        molt_out_spost: float = 1.0,
        sec: float = 2592000.0,
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
            displacement_measured: List of measured displacement values (in user units)
            num_harmonics: Number of harmonics for Fourier analysis
            calculate_viscosity: If True, use MetodoBestFitting_MultiBloc for best-fit viscosity
            molt_spost: Input displacement unit conversion factor (user units -> meters)
            molt_out_spost: Output displacement unit conversion factor (meters -> user units)

        Returns:
            Dictionary with results:
            - displacement_calculated: List of calculated displacements (in meters)
            - velocity: List of velocity values (m/s)
            - critical_water_table: List of critical water table heights (absolute, in meters)
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
            n1 = 0.0    # number of piles row 1
            n2 = 0.0    # number of piles row 2
            # sec is seconds per time step, passed from caller
            alpha = phi_interface  # use interface friction angle for alpha
            phi_strato = 0.0
            OCR = 1.0
            c_strato = 0.0

            # Convert measured displacement to meters for computation
            displacement_in_meters = [v * molt_spost for v in displacement_measured]

            # Convert to .NET arrays
            time_arr = _convert_to_dotnet_array(time_array)
            falda_calc_arr = _convert_to_dotnet_array(water_table_calculated)
            spost_x_arr = _convert_to_dotnet_array(time_array)  # X-axis is time
            spost_y_arr = _convert_to_dotnet_array(displacement_in_meters)

            # Additional parameters for CElaboration.CalcoloPendio (non-piled slopes)
            deltap1 = 0.0
            phi_interfaccia = phi_interface

            if calculate_viscosity:
                # Use MetodoBestFitting_MultiBloc for full best-fit workflow:
                # 1. Runs CalcoloPendio with mu=10^9 (ideal, no damping)
                # 2. Scales mu proportionally to match measured displacement
                # 3. Fine-tunes with CalcoloCoeffVisc grid search
                # 4. Runs final CalcoloPendio with optimized mu
                spost_y_misu_arr = _convert_to_dotnet_array(displacement_measured)

                result = self._elaboration_multiblocco.MetodoBestFitting_MultiBloc(
                    l1, l2, h, beta1, beta2, i_pc,
                    gamma_sat, fi, c, mu,
                    gamma_w, g, D, interasse, Hp, n1, n2,
                    time_arr, falda_calc_arr,
                    spost_x_arr, spost_y_arr,
                    sec, alpha, phi_strato, OCR, c_strato,
                    num_harmonics,
                    spost_y_misu_arr, molt_out_spost, molt_spost
                )
                # MetodoBestFitting_MultiBloc returns Double[,] (rectangular)
                n_points = len(time_array)
                result_matrix = _convert_from_dotnet_2d_array(result, 5, n_points)
            else:
                # Standard analysis: use CElaboration.CalcoloPendio (29 params)
                # matching the original C# Form1.btnAnalisiCsharp_Click flow
                result = self._elaboration.CalcoloPendio(
                    l1, l2, h, beta1, beta2, i_pc,
                    gamma_sat, fi, c, mu,
                    gamma_w, g, D, interasse, Hp, n1, n2,
                    time_arr, falda_calc_arr,
                    spost_x_arr, spost_y_arr,
                    sec, alpha, phi_strato, OCR, c_strato,
                    num_harmonics,
                    deltap1, phi_interfaccia
                )
                # CElaboration.CalcoloPendio returns Double[][] (jagged)
                result_matrix = _convert_from_dotnet_jagged_array(result, 5)

            # Result matrix [5, N]:
            # Row 0: Horizontal displacement = cos(beta1) * cumulative displacement
            # Row 1: Critical water height (hwcrit, absolute above sliding surface)
            # Row 2: Horizontal velocity = cos(beta1) * velocity
            # Row 3: Safety factor
            # Row 4: Summary metrics [MaxSpost, Error, Ks1, deltap1, ca1, mu, ...]

            response = {
                'displacement_calculated': result_matrix[0],
                'critical_water_table': result_matrix[1],
                'velocity': result_matrix[2],
                'safety_factor': result_matrix[3],
            }

            if calculate_viscosity:
                # Calibrated mu is stored at row 4, index 5
                response['mu'] = result_matrix[4][5] if len(result_matrix[4]) > 5 else mu

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
