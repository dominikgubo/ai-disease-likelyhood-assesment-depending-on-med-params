# About

Script is used for initial disease likelyhood assesment depending on the available medicine parameter list. This information is quite useful as it will be used further on for more complex disease diagnosis. 

Specifically this project focuses on hematology area of medicine, although it is fairly-easy adjustable for other medicine areas; given that you have proper data for it.

It is **quite important** to mention that assesment precision of this initial code is rough, more of a 'stepping-stone', and definitely won't be used as main diagnosis criteria further on. My team and myself are quite aware of the assesment limitations of this approach (e.g. each time script is ran different results received), and in regards to this;
1) upgraded data driven approach is used privately
2) for best precision medical staff is looking once more through output data and filtering it

  
## Workflow

Disease and available medical parameter data is loaded in the project and each separate disease is assesed via ChatGPT API iteratively, achieving greater precision. Used AI model is ```gpt-4o-mini``` (might be a subject of change further on), with temperature parameter set to "0.0" resulting in strict & predictable data. Input Data is in specific .csv format loaded, scraped from [NHANES (medical parameters)](https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component=Laboratory) and [ICD datasources (disease clarification)](https://icd.who.int/browse/2025-01/mms/en). 

After each assesment output is generated in ```out/results_all.csv, results_not_possible.csv, results_possible```. Specifically basic disease data is stored and medical reasoning behind the approach (depending of likelyhood possibility state).

  
## Usage
1) Install required Python dependencies
2) By default script uses existing input data (```input/icd_codes.csv, nhanes_variables.csv```), modify for your needs if needed
3) As [OpenAI API](https://platform.openai.com/docs/overview) is used, you need to store the API key in the environment variables of your PC (or modify the code for straight injection in code, or any other way fetching the key really).  

   a) Windows =>```setx OPENAI_API_KEY "<your_api_key>"```  
   b) Linux or macOs => ```export OPENAI_API_KEY="<your_api_key>"```
4) *Optional: if needed, refine the config parameters in ```config.py```, e.g. change the used OpenAI LLM model*
5) Execute the ```main.py```


## Output result example

| Code    | Parent Code | Name                                                        | Possibility   | Medical Reasoning                                                                                                                                                                                                                                                                           |
|----------|------------|------------------------------------------------------------|---------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 3A00.0   | 3A00       | Acquired iron deficiency anaemia due to blood loss         | Possible      | The available features include key hematological parameters such as hemoglobin (LBXHGB), red blood cell count (LBXRBCSI), hematocrit (LBXHCT), and iron levels (LBXSIR), which are essential for screening and assessing iron deficiency anemia. These features can help identify anemia and suggest iron deficiency, thus enabling a probabilistic model for the disease. |
| 3A00.01  | 3A00       | Chronic posthaemorrhagic anaemia                           | Possible      | Key hematological parameters such as hemoglobin (LBXHGB), hematocrit (LBXHCT), red blood cell count (LBXRBCSI), and red cell distribution width (LBXRDW) are available, which are essential for screening chronic posthaemorrhagic anemia. These features can help assess anemia severity and differentiate it from other types of anemia. |
| 3B50.1   | 3B50       | Congenital plasminogen activator inhibitor type 1 deficiency | Not Possible  | Key signals for screening congenital plasminogen activator inhibitor type 1 deficiency, such as specific genetic testing or functional assays to measure plasminogen activator inhibitor levels, are not available in the listed features.                                                                                         |

[**View full data**](output/results_all.csv)

  
## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.


## License

[MIT](https://choosealicense.com/licenses/mit/)
