- GET /datasets/{dataset_ref_name}/data/{data_definition_name}/template

- POST POST /datasets/{dataset_ref_name}/{uuid7}/data/{data_definition_name}/validate
200 OK answer
{ 

  "valid": true, 
  "errors": [], 
  "warnings": [ 
    { 
      "line": 5, 
      "column": "C", 
      "message": { 
        "it": "Elevazione fuori range usuale: 4100.0.", 
        "en": "Elevation outside usual range: 4100.0." 
      } 
    } 
  ] 
}  

- POST /datasets/{dataset_ref_name}/{uuid7}/data/{data_definition_name}/import 

- POST /functions/calibrate/ 
- POST /functions/analysis/ 
