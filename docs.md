  POST /functions/calibrate/

  Water table model calibration using the Best Fit Pioggia algorithm (automatic) or direct calculation with user-supplied parameters (manual).

  Requires imported data: pioggia (rainfall) + falda (water table)

  Request body

  ┌────────────────────┬────────────────────────┬─────────────┬─────────────┬────────────────────────────────────────────────────────────────┐
  │       Field        │          Type          │  Required   │   Default   │                          Description                           │
  ├────────────────────┼────────────────────────┼─────────────┼─────────────┼────────────────────────────────────────────────────────────────┤
  │ dataset_uuid       │ string (UUID)          │ yes         │ —           │ Dataset containing imported rainfall and water table data      │
  ├────────────────────┼────────────────────────┼─────────────┼─────────────┼────────────────────────────────────────────────────────────────┤
  │ mode               │ "automatic" | "manual" │ no          │ "automatic" │ Automatic finds optimal params; manual uses calibration_params │
  ├────────────────────┼────────────────────────┼─────────────┼─────────────┼────────────────────────────────────────────────────────────────┤
  │ geometry           │ object                 │ yes         │ —           │ See geometry fields below                                      │
  ├────────────────────┼────────────────────────┼─────────────┼─────────────┼────────────────────────────────────────────────────────────────┤
  │ calibration_params │ object                 │ manual only │ —           │ See calibration param fields below                             │
  └────────────────────┴────────────────────────┴─────────────┴─────────────┴────────────────────────────────────────────────────────────────┘

  geometry fields (all required):

  ┌───────┬────────┬──────────────────────────────────┐
  │ Field │  Type  │           Description            │
  ├───────┼────────┼──────────────────────────────────┤
  │ l1    │ number │ Block 1 length (m)               │
  ├───────┼────────┼──────────────────────────────────┤
  │ l2    │ number │ Block 2 length (m)               │
  ├───────┼────────┼──────────────────────────────────┤
  │ h     │ number │ Layer height (m)                 │
  ├───────┼────────┼──────────────────────────────────┤
  │ beta1 │ number │ Block 1 slope angle (°)          │
  ├───────┼────────┼──────────────────────────────────┤
  │ beta2 │ number │ Block 2 slope angle (°)          │
  ├───────┼────────┼──────────────────────────────────┤
  │ i_pc  │ number │ Ground surface slope / alpha (°) │
  └───────┴────────┴──────────────────────────────────┘

  calibration_params fields (required when mode = "manual"):


  ┌───────┬────────┬───────────────────────────────┐
  │ Field │  Type  │          Description          │
  ├───────┼────────┼───────────────────────────────┤
  │ hs    │ number │ Source height (mm)            │
  ├───────┼────────┼───────────────────────────────┤
  │ kt    │ number │ Transmissivity coefficient    │
  ├───────┼────────┼───────────────────────────────┤
  │ an    │ number │ Storage coefficient           │
  ├───────┼────────┼───────────────────────────────┤
  │ ho    │ number │ Initial water table level (m) │
  ├───────┼────────┼───────────────────────────────┤
  │ hmin  │ number │ Minimum water table level (m) │
  └───────┴────────┴───────────────────────────────┘

  Response 200 OK

  {
    "success": true,
    "calibrated_params": { "hs": 0.0, "kt": 0.0, "an": 0.0, "ho": 0.0, "hmin": 0.0 },
    "calculated_water_table": [{ "index": 0, "value": 0.0 }],
    "measured_water_table":   [{ "index": 0, "value": 0.0 }],
    "rainfall_data":          [{ "index": 0, "value": 0.0 }]
  }

  Error responses

  ┌────────┬────────────────────┬────────────────────────────────────────────────┐
  │ Status │     error_code     │                     Cause                      │
  ├────────┼────────────────────┼────────────────────────────────────────────────┤
  │ 400    │ —                  │ Missing/invalid fields                         │
  ├────────┼────────────────────┼────────────────────────────────────────────────┤
  │ 404    │ DATA_NOT_FOUND     │ pioggia or falda data not imported for dataset │
  ├────────┼────────────────────┼────────────────────────────────────────────────┤
  │ 500    │ CALIBRATION_FAILED │ .NET backend error                             │
  └────────┴────────────────────┴────────────────────────────────────────────────┘

  ---
  POST /functions/prevision/

  Slope stability analysis using the multi-block model. Computes displacement, velocity, safety factor, and critical water table. Optionally calibrates the viscosity coefficient
  (best_fit_viscosity mode).

  Requires imported data: pioggia + falda + spostamento (displacement)

  Request body

  ┌─────────────────────┬───────────────────────────────────┬──────────┬────────────┬─────────────────────────────────────────────────────────────────────────────────────────────┐
  │        Field        │               Type                │ Required │  Default   │                                         Description                                         │
  ├─────────────────────┼───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┤
  │ dataset_uuid        │ string (UUID)                     │ yes      │ —          │ Dataset containing all three imported data series                                           │
  ├─────────────────────┼───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┤
  │ prevision_type      │ "standard" | "best_fit_viscosity" │ no       │ "standard" │ Standard uses the mu value provided; best_fit_viscosity also computes the optimal viscosity │
  ├─────────────────────┼───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┤
  │ geometry            │ object                            │ yes      │ —          │ Same fields as calibrate (l1, l2, h, beta1, beta2, i_pc)                                    │
  ├─────────────────────┼───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┤
  │ geotechnical_params │ object                            │ yes      │ —          │ See fields below                                                                            │
  ├─────────────────────┼───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┤
  │ model_params        │ object                            │ yes      │ —          │ Water table model params from calibration (hs, kt, an, ho, hmin)                            │
  ├─────────────────────┼───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┤
  │ analysis_settings   │ object                            │ no       │ —          │ See fields below                                                                            │
  ├─────────────────────┼───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┤
  │ displacement_unit   │ "mm" | "cm" | "m"                 │ no       │ "cm"       │ Unit of the imported displacement data                                                      │
  ├─────────────────────┼───────────────────────────────────┼──────────┼────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┤
  │ time_unit           │ "giorni" | "mesi" | "anni"        │ no       │ "mesi"     │ Time step unit of the dataset                                                               │
  └─────────────────────┴───────────────────────────────────┴──────────┴────────────┴─────────────────────────────────────────────────────────────────────────────────────────────┘

  geotechnical_params fields:

  ┌──────────────┬────────┬──────────┬─────────────────────────────────────┐
  │    Field     │  Type  │ Required │             Description             │
  ├──────────────┼────────┼──────────┼─────────────────────────────────────┤
  │ gamma_sat    │ number │ yes      │ Saturated unit weight (kN/m³)       │
  ├──────────────┼────────┼──────────┼─────────────────────────────────────┤
  │ gamma_w      │ number │ yes      │ Water unit weight (kN/m³)           │
  ├──────────────┼────────┼──────────┼─────────────────────────────────────┤
  │ fi           │ number │ yes      │ Internal friction angle (°)         │
  ├──────────────┼────────┼──────────┼─────────────────────────────────────┤
  │ c            │ number │ yes      │ Cohesion (kN/m²)                    │
  ├──────────────┼────────┼──────────┼─────────────────────────────────────┤
  │ mu           │ number │ yes      │ Viscosity coefficient (kN·month/m²) │
  ├──────────────┼────────┼──────────┼─────────────────────────────────────┤
  │ fi_interface │ number │ no       │ Interface friction angle (°)        │
  └──────────────┴────────┴──────────┴─────────────────────────────────────┘

  analysis_settings fields:

  ┌───────────────┬─────────┬─────────┬──────────────────────────────────────────┐
  │     Field     │  Type   │ Default │               Description                │
  ├───────────────┼─────────┼─────────┼──────────────────────────────────────────┤
  │ num_harmonics │ integer │ 100     │ Number of harmonics for Fourier analysis │
  └───────────────┴─────────┴─────────┴──────────────────────────────────────────┘

  Response 200 OK
  {
    "success": true,
    "results": {
      "time":                   [{ "index": 0, "value": 0.0 }],
      "displacement_calculated":[{ "index": 0, "value": 0.0 }],
      "displacement_measured":  [{ "index": 0, "value": 0.0 }],
      "velocity":               [{ "index": 0, "value": 0.0 }],
      "critical_water_table":   [{ "index": 0, "value": 0.0 }],
      "safety_factor":          [{ "index": 0, "value": 0.0 }],
      "water_table_calculated": [{ "index": 0, "value": 0.0 }],
      "water_table_measured":   [{ "index": 0, "value": 0.0 }]
    },
    "calibrated_viscosity": { "mu": 0.0, "unit": "kN*month/m2" }
  }

  calibrated_viscosity is only present when prevision_type = "best_fit_viscosity".

  Output notes:
  - displacement_calculated and displacement_measured are in the unit specified by displacement_unit
  - critical_water_table is depth below ground surface (negative = below surface), derived as hw_crit - h

  Error responses

  ┌────────┬──────────────────┬───────────────────────────────────────────────┐
  │ Status │    error_code    │                     Cause                     │
  ├────────┼──────────────────┼───────────────────────────────────────────────┤
  │ 400    │ —                │ Missing/invalid fields                        │
  ├────────┼──────────────────┼───────────────────────────────────────────────┤
  │ 404    │ DATA_NOT_FOUND   │ One or more required data series not imported │
  ├────────┼──────────────────┼───────────────────────────────────────────────┤
  │ 500    │ PREVISION_FAILED │ .NET backend error                            │
  └────────┴──────────────────┴───────────────────────────────────────────────┘

  ---
  Typical workflow: import data → calibrate (to get calibrated_params) → use those params as model_params in prevision.
