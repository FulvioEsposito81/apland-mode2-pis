"""
Capabilities descriptor for MODE II API.

Describes the datasets, data definitions, and functions supported by this API.
"""

CAPABILITIES = {
    "capabilitiesVersion": "1.0",
    "apiVersion": "1.0",
    "changeLog": ["Prima versione."],
    "documentationUrl": "https://mode2.local/docs",
    "contactEmail": "info@campaniasistemi.it",
    "datasets": [
        {
            "name": "landslide",
            "supportedOperations": ["import", "execute"],
            "description": "Dataset frana - Dati di monitoraggio per l'analisi di stabilità dei pendii (pioggia, falda, spostamento).",
            "importable": True,
            "exportable": False,
            "dataDefinitions": [
                {
                    "name": "pioggia",
                    "label": {"it": "Pioggia mensile", "en": "Monthly rainfall"},
                    "description": {
                        "it": "Serie mensile di precipitazioni in mm (12 valori, indice 0-11).",
                        "en": "Monthly rainfall series in mm (12 values, index 0-11)."
                    },
                    "required": True,
                    "columns": [
                        {
                            "key": "index",
                            "type": "integer",
                            "description": {
                                "it": "Indice mese (0-11)",
                                "en": "Month index (0-11)"
                            }
                        },
                        {
                            "key": "value",
                            "type": "number",
                            "description": {
                                "it": "Precipitazione (mm)",
                                "en": "Rainfall (mm)"
                            }
                        }
                    ],
                    "templates": {
                        "importFormats": ["txt", "tsv"],
                        "expectedImportFiles": ["pioggia.txt"],
                        "exportFormats": [],
                        "metadata": {
                            "name": {"it": "File pioggia mensile", "en": "Monthly rainfall file"},
                            "value": "2 colonne separate da tab, separatore decimale virgola, 12 righe (indice 0-11)"
                        }
                    }
                },
                {
                    "name": "falda",
                    "label": {"it": "Livello falda mensile", "en": "Monthly water table level"},
                    "description": {
                        "it": "Serie mensile del livello di falda in m dal piano campagna (12 valori, indice 0-11, valori negativi = sotto piano campagna).",
                        "en": "Monthly water table level series in m from ground surface (12 values, index 0-11, negative values = below ground)."
                    },
                    "required": True,
                    "columns": [
                        {
                            "key": "index",
                            "type": "integer",
                            "description": {
                                "it": "Indice mese (0-11)",
                                "en": "Month index (0-11)"
                            }
                        },
                        {
                            "key": "value",
                            "type": "number",
                            "description": {
                                "it": "Livello falda (m dal piano campagna)",
                                "en": "Water table level (m from ground surface)"
                            }
                        }
                    ],
                    "templates": {
                        "importFormats": ["txt", "tsv"],
                        "expectedImportFiles": ["falda.txt"],
                        "exportFormats": [],
                        "metadata": {
                            "name": {"it": "File falda mensile", "en": "Monthly water table file"},
                            "value": "2 colonne separate da tab, separatore decimale virgola, 12 righe (indice 0-11)"
                        }
                    }
                },
                {
                    "name": "spostamento",
                    "label": {"it": "Spostamento mensile", "en": "Monthly displacement"},
                    "description": {
                        "it": "Serie mensile degli spostamenti misurati (cm per default). Richiesto per la funzione di previsione.",
                        "en": "Monthly measured displacement series (cm by default). Required for the prevision function."
                    },
                    "required": False,
                    "columns": [
                        {
                            "key": "index",
                            "type": "integer",
                            "description": {
                                "it": "Indice mese (0-11)",
                                "en": "Month index (0-11)"
                            }
                        },
                        {
                            "key": "value",
                            "type": "number",
                            "description": {
                                "it": "Spostamento (cm)",
                                "en": "Displacement (cm)"
                            }
                        }
                    ],
                    "templates": {
                        "importFormats": ["txt", "tsv"],
                        "expectedImportFiles": ["spostamento.txt"],
                        "exportFormats": [],
                        "metadata": {
                            "name": {"it": "File spostamento mensile", "en": "Monthly displacement file"},
                            "value": "2 colonne separate da tab, separatore decimale virgola, 12 righe (indice 0-11)"
                        }
                    }
                }
            ]
        }
    ],
    "functions": [
        {
            "name": "calibrate",
            "title": {
                "it": "Calibrazione falda",
                "en": "Water table calibration"
            },
            "description": {
                "it": "Calibrazione del modello di falda tramite algoritmo Best Fit Pioggia (modalità automatica) o calcolo diretto con parametri forniti (modalità manuale). Richiede i dati di pioggia e falda importati.",
                "en": "Water table model calibration using Best Fit Pioggia algorithm (automatic mode) or direct calculation with provided parameters (manual mode). Requires imported rainfall and water table data."
            },
            "method": "POST",
            "bodyType": "application/json",
            "parameters": [
                {
                    "name": "dataset_uuid",
                    "type": "string",
                    "description": "UUID del dataset contenente i dati importati (pioggia e falda).",
                    "required": True
                },
                {
                    "name": "mode",
                    "type": "enum",
                    "description": "Modalità di calibrazione: 'automatic' (Best Fit) o 'manual' (parametri forniti).",
                    "required": False,
                    "default": "automatic",
                    "enum": ["automatic", "manual"]
                },
                {
                    "name": "geometry",
                    "type": "object",
                    "description": "Parametri geometrici del pendio.",
                    "required": True,
                    "properties": [
                        {"name": "l1", "type": "number", "description": "Lunghezza blocco 1 (m)"},
                        {"name": "l2", "type": "number", "description": "Lunghezza blocco 2 (m)"},
                        {"name": "h", "type": "number", "description": "Altezza dello strato (m)"},
                        {"name": "beta1", "type": "number", "description": "Pendenza blocco 1 (°)"},
                        {"name": "beta2", "type": "number", "description": "Pendenza blocco 2 (°)"},
                        {"name": "i_pc", "type": "number", "description": "Pendenza piano campagna / alpha (°)"}
                    ]
                },
                {
                    "name": "calibration_params",
                    "type": "object",
                    "description": "Parametri di calibrazione forniti dall'utente (obbligatori in modalità 'manual').",
                    "required": False,
                    "properties": [
                        {"name": "hs", "type": "number", "description": "Altezza sorgente (mm)"},
                        {"name": "kt", "type": "number", "description": "Coefficiente di trasmissività"},
                        {"name": "an", "type": "number", "description": "Coefficiente di immagazzinamento"},
                        {"name": "ho", "type": "number", "description": "Livello falda iniziale (m)"},
                        {"name": "hmin", "type": "number", "description": "Livello falda minimo (m)"}
                    ]
                }
            ]
        },
        {
            "name": "prevision",
            "title": {
                "it": "Previsione stabilità pendio",
                "en": "Slope stability prevision"
            },
            "description": {
                "it": "Analisi di stabilità del pendio con modello multi-blocco. Calcola spostamento, velocità, fattore di sicurezza e livello di falda critico. Richiede i dati di pioggia, falda e spostamento importati.",
                "en": "Slope stability analysis using the multi-block model. Computes displacement, velocity, safety factor, and critical water table. Requires imported rainfall, water table, and displacement data."
            },
            "method": "POST",
            "bodyType": "application/json",
            "parameters": [
                {
                    "name": "dataset_uuid",
                    "type": "string",
                    "description": "UUID del dataset contenente i dati importati (pioggia, falda, spostamento).",
                    "required": True
                },
                {
                    "name": "prevision_type",
                    "type": "enum",
                    "description": "Tipo di analisi: 'standard' (viscosità fornita) o 'best_fit_viscosity' (viscosità calibrata).",
                    "required": False,
                    "default": "standard",
                    "enum": ["standard", "best_fit_viscosity"]
                },
                {
                    "name": "geometry",
                    "type": "object",
                    "description": "Parametri geometrici del pendio.",
                    "required": True,
                    "properties": [
                        {"name": "l1", "type": "number", "description": "Lunghezza blocco 1 (m)"},
                        {"name": "l2", "type": "number", "description": "Lunghezza blocco 2 (m)"},
                        {"name": "h", "type": "number", "description": "Altezza dello strato (m)"},
                        {"name": "beta1", "type": "number", "description": "Pendenza blocco 1 (°)"},
                        {"name": "beta2", "type": "number", "description": "Pendenza blocco 2 (°)"},
                        {"name": "i_pc", "type": "number", "description": "Pendenza piano campagna / alpha (°)"}
                    ]
                },
                {
                    "name": "geotechnical_params",
                    "type": "object",
                    "description": "Parametri geotecnici del terreno.",
                    "required": True,
                    "properties": [
                        {"name": "gamma_sat", "type": "number", "description": "Peso di volume saturo (kN/m³)"},
                        {"name": "gamma_w", "type": "number", "description": "Peso specifico acqua (kN/m³)"},
                        {"name": "fi", "type": "number", "description": "Angolo di attrito interno (°)"},
                        {"name": "c", "type": "number", "description": "Coesione (kN/m²)"},
                        {"name": "mu", "type": "number", "description": "Viscosità (kN·mese/m²)"},
                        {"name": "fi_interface", "type": "number", "description": "Angolo di attrito all'interfaccia (°)", "required": False}
                    ]
                },
                {
                    "name": "model_params",
                    "type": "object",
                    "description": "Parametri del modello di falda (ottenuti dalla calibrazione).",
                    "required": True,
                    "properties": [
                        {"name": "hs", "type": "number", "description": "Altezza sorgente (mm)"},
                        {"name": "kt", "type": "number", "description": "Coefficiente di trasmissività"},
                        {"name": "an", "type": "number", "description": "Coefficiente di immagazzinamento"},
                        {"name": "ho", "type": "number", "description": "Livello falda iniziale (m)"},
                        {"name": "hmin", "type": "number", "description": "Livello falda minimo (m)"}
                    ]
                },
                {
                    "name": "analysis_settings",
                    "type": "object",
                    "description": "Impostazioni opzionali dell'analisi.",
                    "required": False,
                    "properties": [
                        {"name": "num_harmonics", "type": "integer", "description": "Numero di armoniche per l'analisi (default: 100)", "default": 100}
                    ]
                },
                {
                    "name": "displacement_unit",
                    "type": "enum",
                    "description": "Unità di misura degli spostamenti importati.",
                    "required": False,
                    "default": "cm",
                    "enum": ["mm", "cm", "m"]
                },
                {
                    "name": "time_unit",
                    "type": "enum",
                    "description": "Unità di misura temporale dei passi del dataset.",
                    "required": False,
                    "default": "mesi",
                    "enum": ["giorni", "mesi", "anni"]
                }
            ]
        }
    ]
}
