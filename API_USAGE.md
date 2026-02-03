# MODE II API Usage Guide

This API provides REST endpoints for landslide mobility prediction, replicating the functionality of the MODE II .NET desktop application developed by Universita della Calabria.

## Overview

MODE II is a software for studying rainfall-induced landslide mobility. It predicts the reactivation of landslide bodies due to water table rise caused by rainfall. The methodology links landslide body mobility directly to rainfall measurements and allows prediction of future displacements based on expected rainfall scenarios.

## API Endpoints

### 1. Data Validation

**Endpoint:** `POST /datasets/{dataset_ref_name}/{uuid}/data/{data_ref_name}/validate`

Validates a MODE II data file without importing it.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` - The data file to validate

**Data File Format:**
- Tab-delimited text file
- No headers
- Column 1: Sequential integer index (0-11)
- Column 2: Float value with comma as decimal separator (European format)
- Exactly 12 rows (representing 12 months)

**Example data file (Pioggia.txt):**
```
0	6,13599536
1	161,902106
2	140,762227
...
11	5,29880969
```

**Response (200 OK):**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "data": [
    {"index": 0, "value": 6.13599536},
    {"index": 1, "value": 161.902106},
    ...
  ]
}
```

**Response (400 Bad Request - validation failed):**
```json
{
  "valid": false,
  "errors": [
    {
      "it": "Il file deve contenere esattamente 12 righe. Trovate: 10",
      "en": "File must contain exactly 12 rows. Found: 10"
    }
  ],
  "warnings": []
}
```

### 2. Data Import

**Endpoint:** `POST /datasets/{dataset_ref_name}/{uuid}/data/{data_ref_name}/import`

Validates and imports a MODE II data file into the database.

**Data Reference Names:**
- `pioggia` - Rainfall data (mm)
- `falda` - Water table measurements (m from ground surface, negative values)
- `spostamento` - Displacement measurements (cm)

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` - The data file to import

**Response (200 OK):**
```json
{
  "success": true,
  "table_name": "import_<uuid>_<data_ref_name>",
  "rows_imported": 12
}
```

### 3. Water Table Calibration

**Endpoint:** `POST /functions/calibrate/`

Performs water table calibration using the Best Fit algorithm.

**Request Body:**
```json
{
  "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "mode": "automatic",
  "geometry": {
    "l1": 409.71,
    "l2": 314.46,
    "h": 20.31,
    "beta1": 5.18,
    "beta2": 11.66,
    "i_pc": 7.99
  }
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `dataset_uuid` | UUID | Yes | Dataset identifier |
| `mode` | string | No | `"automatic"` (default) or `"manual"` |
| `geometry` | object | Yes | Slope geometry parameters |
| `calibration_params` | object | Manual mode only | Pre-defined calibration parameters |

**Geometry Parameters:**
- `l1`: Length of downstream sliding surface (m)
- `l2`: Length of upstream sliding surface (m)
- `h`: Height of contact surface between blocks (m)
- `beta1`: Downstream sliding surface inclination (degrees)
- `beta2`: Upstream sliding surface inclination (degrees)
- `i_pc`: Ground surface inclination (degrees)

**Calibration Parameters (for manual mode):**
- `hs`: Rainfall scale parameter (mm)
- `kt`: Time decay constant (1/month)
- `an`: Dimensionless coefficient
- `ho`: Initial water table offset (m)
- `hmin`: Minimum water table level (m)

**Response (200 OK):**
```json
{
  "success": true,
  "calibrated_params": {
    "hs": 161.902106,
    "kt": 2.9,
    "an": 0.27,
    "ho": 0.0,
    "hmin": -1.773
  },
  "calculated_water_table": [
    {"index": 0, "value": -1.75},
    {"index": 1, "value": -1.158},
    ...
  ],
  "measured_water_table": [
    {"index": 0, "value": -1.77325353},
    ...
  ],
  "rainfall_data": [
    {"index": 0, "value": 6.13599536},
    ...
  ]
}
```

### 4. Slope Stability Prevision

**Endpoint:** `POST /functions/prevision/`

Performs slope stability analysis and displacement prediction.

**Request Body:**
```json
{
  "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "prevision_type": "standard",
  "geometry": {
    "l1": 409.71,
    "l2": 314.46,
    "h": 20.31,
    "beta1": 5.18,
    "beta2": 11.66,
    "i_pc": 7.99
  },
  "geotechnical_params": {
    "gamma_sat": 20.5,
    "gamma_w": 10.0,
    "fi": 13.8,
    "c": 0.0,
    "mu": 4.44e10,
    "fi_interface": 23.0
  },
  "model_params": {
    "hs": 161.902106,
    "kt": 2.9,
    "an": 0.27,
    "ho": 0.0,
    "hmin": -1.773
  },
  "analysis_settings": {
    "num_harmonics": 100
  }
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `dataset_uuid` | UUID | Yes | Dataset identifier |
| `prevision_type` | string | No | `"standard"` (default) or `"best_fit_viscosity"` |
| `geometry` | object | Yes | Slope geometry (same as calibration) |
| `geotechnical_params` | object | Yes | Geotechnical parameters |
| `model_params` | object | Yes | Calibrated model parameters |
| `analysis_settings` | object | No | Analysis configuration |

**Geotechnical Parameters:**
- `gamma_sat`: Saturated unit weight (kN/m3)
- `gamma_w`: Water unit weight (kN/m3)
- `fi`: Residual friction angle (degrees)
- `c`: Effective cohesion (kPa)
- `mu`: Viscosity coefficient (kN*month/m2)
- `fi_interface`: Interface friction angle between blocks (degrees)

**Response (200 OK):**
```json
{
  "success": true,
  "results": {
    "time": [{"index": 0, "value": 0}, ...],
    "displacement_calculated": [{"index": 0, "value": 0}, ...],
    "displacement_measured": [{"index": 0, "value": 0}, ...],
    "velocity": [{"index": 0, "value": 0}, ...],
    "critical_water_table": [{"index": 0, "value": -1.255}, ...],
    "safety_factor": [{"index": 0, "value": 1.2}, ...],
    "water_table_calculated": [{"index": 0, "value": -1.75}, ...],
    "water_table_measured": [{"index": 0, "value": -1.773}, ...]
  },
  "calibrated_viscosity": {
    "mu": 4.44e10,
    "unit": "kN*month/m2"
  }
}
```

## Workflow

### Calibration Workflow

1. **Import rainfall data:** `POST /datasets/.../data/pioggia/import`
2. **Import water table data:** `POST /datasets/.../data/falda/import`
3. **Run calibration:** `POST /functions/calibrate/`
4. Save calibrated parameters (hs, kt, an, ho, hmin) for prevision

### Prevision Workflow

1. **Import rainfall data:** `POST /datasets/.../data/pioggia/import`
2. **Import water table data:** `POST /datasets/.../data/falda/import`
3. **Import displacement data:** `POST /datasets/.../data/spostamento/import`
4. **Run prevision:** `POST /functions/prevision/`

## Error Handling

All endpoints return bilingual error messages (Italian and English):

```json
{
  "success": false,
  "errors": [
    {
      "it": "Dati di pioggia non trovati per questo dataset.",
      "en": "Rainfall data not found for this dataset."
    }
  ],
  "error_code": "DATA_NOT_FOUND"
}
```

**Error Codes:**
- `DATA_NOT_FOUND` - Required data has not been imported
- `CALIBRATION_FAILED` - Error during calibration calculation
- `PREVISION_FAILED` - Error during prevision calculation

## Data Units

### Input Units
- Time interval: months
- Rainfall (pioggia): mm
- Water table (falda): m from ground surface (negative values)
- Displacement (spostamento): cm

### Output Units
- Displacement: configurable (mm, cm, or m)
- Velocity: m/s
- Water table: m from ground surface
- Safety factor: dimensionless

## Example: Complete Analysis

```bash
# 1. Import rainfall data
curl -X POST "http://localhost:8000/datasets/landslide/550e8400.../data/pioggia/import" \
  -F "file=@Pioggia.txt"

# 2. Import water table data
curl -X POST "http://localhost:8000/datasets/landslide/550e8400.../data/falda/import" \
  -F "file=@Falda.txt"

# 3. Import displacement data
curl -X POST "http://localhost:8000/datasets/landslide/550e8400.../data/spostamento/import" \
  -F "file=@Spostamento.txt"

# 4. Run calibration
curl -X POST "http://localhost:8000/functions/calibrate/" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "mode": "automatic",
    "geometry": {
      "l1": 409.71, "l2": 314.46, "h": 20.31,
      "beta1": 5.18, "beta2": 11.66, "i_pc": 7.99
    }
  }'

# 5. Run prevision with calibrated parameters
curl -X POST "http://localhost:8000/functions/prevision/" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "prevision_type": "best_fit_viscosity",
    "geometry": {
      "l1": 409.71, "l2": 314.46, "h": 20.31,
      "beta1": 5.18, "beta2": 11.66, "i_pc": 7.99
    },
    "geotechnical_params": {
      "gamma_sat": 20.5, "gamma_w": 10.0, "fi": 13.8,
      "c": 0.0, "mu": 4.44e10, "fi_interface": 23.0
    },
    "model_params": {
      "hs": 161.902106, "kt": 2.9, "an": 0.27,
      "ho": 0.0, "hmin": -1.773
    }
  }'
```
