# Toponym disambiguation in news text using traditional geoparsers and LLMs

Identifying the names of places (*toponyms*) is essential to processing news text, but place names in news text are notoriously ambiguous. For example, the toponym *Paris* could refer to Paris, France or Paris, Texas, or Paris, Virginia, [etc](https://en.wikipedia.org/wiki/Paris_(disambiguation)). Toponym disambiguation or toponym resolution is defined as resolving toponyms to their precise locations (geo-coordinates).

Traditional geoparsers like [Mordecai3](https://github.com/ahalterman/mordecai3), [Cliff Clavin](https://github.com/mediacloud/cliff-annotator), [the Edinburgh Parser](https://www.ltg.ed.ac.uk/software/geoparser/), and [DBpedia Spotlight](https://github.com/dbpedia-spotlight/dbpedia-spotlight-model) use rule-based methods, knowledge bases, and statistical models for toponym disambiguation. While effective with domain-specific datasets, these tools often struggle with understanding complex contexts. Large Language Models (LLMs) like GPT and Llama excel at contextual reasoning, and often outperform traditional geoparsers in accuracy and flexibility. However, their high computational demands (powerful GPUs and optimized setups) limit their practicality.

What follows is an exploration of various toponym disambiguation tools (traditional geoparsers and general-purpose/fine-tuned LLMs). Specifically, we explore how to install and use them, and in some cases evaluate their performance.

**TL;DR**

For traditional geoparsers, our results show that geopolitical (`GPE`) entities (e.g., countries, states, counties, cities) are the easiest to disambiguate, next are location (`LOC`) entities (e.g., Non-GPE locations, mountain ranges, bodies of water), and then facility (`FAC`) entities (e.g., Buildings, airports, highways, bridges, etc.). Cliff Clavin out-performed other geoparsers for both disambiguating GPEs and LOCs. DBPedia spotlight was the best-performing geoparser for FACs.

LLMs out-performed traditional geoparsers, with gpt-4o outperforming other general-purpose and fine-tuned LLMs. Gpt-4o API was fast and efficient and cost less $ use.

## Table of Contents

* [Using Windows? Read this.](#using-windows-read-this)

* [Datasets (Gold standards)](#datasets-gold-standards)

* <details>
  <summary>Traditional Geoparsers</summary>
  <ul>
    <li><a href="#1-gate-yodie">GATE YODIE</a></li>
    <li><a href="#2-geoparsepy-using-windows-terminal-pipenv">Geoparsepy</a></li>
    <li><a href="#3-cliff-clavin-see-also">Cliff-Clavin</a></li>
    <li><a href="#4-dbpedia-spotlight">DBpedia Spotlight</a></li>
    <li><a href="#5-edinburgh-geoparser">Edinburgh Geoparser</a></li>
    <li><a href="#6-mordecai3">Mordecai</a></li>
    <li><a href="#evaluation-of-traditional-geoparsers">Evaluation</a></li>
  </ul>
</details>

* <details>
  <summary>Large Language Models</summary>
  <ul>
    <li><a href="#general-purpose-non-finetuned-llms">General-purpose (non-finetuned) LLMs</a>
      <ul>
        <li><a href="#7-gpt-4o-mini">GPT4o-mini</a></li>
        <li><a href="#8-llama2-7b">Llama2-7B</a></li>
        <li><a href="#9-phi3-mini-4k">Phi3-mini-4k</a></li>
      </ul>
    </li>
    <li><a href="#fine-tuned-models">Finetuned Models</a>
      <ul>
        <li><a href="#10-llama2-7b-lora-toponym-resolution">Llama2-7B-LoRA-Toponym-Resolution</a></li>
        <li><a href="#11-llama2-13b-lora-toponym-resolution">Llama2-13B-LoRA-Toponym-Resolution</a></li>
        <li><a href="#12-mistral-7b-lora-toponym-resolution">Mistral-7B-LoRA-Toponym-Resolution</a></li>
      </ul>
    </li>
    <li><a href="#evaluation-results">LLMs Evaluation</a></li>
  </ul>
</details>

# Using Windows? Read this.

Most of the tools were developed with Unix (i.e., Linux, Mac) users in mind. We recommend the following to simplify usage for Windows (Windows 11 PC with PowerShell) users:

1. Install Windows Subsystem for Linux (WSL). Open PowerShell as an Administrator and run the following command:
```powershell
wsl --install
```

2. Install a Linux distribution: Installing WSL often comes with Ubuntu pre-installed. If it doesn’t, open the Microsoft Store app and search for "WSL." You’ll find several Linux distributions available. We recommend Ubuntu, alternatively, Debian or other distributions of your choice.

3. Set up the Linux distribution: After installation, open the Linux distribution (e.g., Ubuntu) and set it up by creating a username and password. Make sure to save or memorize these credentials.

4. You now have access to a full Ubuntu terminal within Windows, where you can run Linux commands seamlessly.

5. To work with files on your Windows filesystem via the Ubuntu terminal, navigate to the **/mnt/c** directory:
```bash
cd /mnt/c/Users/<Your_Windows_Username>/<Windows_Folder>/filename.txt
```
Replace `<Your_Windows_Username>` and `<Windows_Folder>` with your actual username and folder path, respectively.

All the tools and commands below were run using Ubuntu terminal via WSL, except when explicitly stated otherwise.

# [Datasets (Gold standards)](data/gold_standards)

We created three [gold-standard datasets](data/gold_standards) files for three classes of ambiguous toponyms --- `GPE`s, `LOC`s, and `FAC`s --- to evaluate the toponym disambiguation tools. Each file contains 102 randomly selected JSON objects of ambiguous toponyms and their corresponding disambiguated forms - geo-coordinates. To maximize diversity, we randomly extracted two toponyms from local news articles from the state.

Specifically, the `GPE` gold-standard file, GPE_2024_05_21T134100Z.jsonl, consists of the geo-coordinates of ambiguous `GPE`s. Similarly, the `LOC` gold-standard file, LOC_2024_05_21T134100Z.jsonl, contains the geo-coordinates of ambiguous `LOC`s, and [FAC_2024_05_21T134100Z.jsonl](https://github.com/wm-newslab/toponym-disambiguation/blob/nwala_edits/data/gold_standards/FAC_2024_05_21T134100Z.jsonl) - geo-coordinates of ambiguous `FAC`s. The ambiguous toponyms were manually disambiguated using Google search, GeoNames, or OpenStreetMap.

## Data Structure
Each line of a gold-standard file contains a JSON object with the following fields:
- `lat_long`: Latitude and longitude values of the ambiguous toponym (`entity`).
- `entity`: Ambiguous toponym (e.g., "Newfane" or "Pennsylvania").
- `entity_label`: The toponym class (e.g., `GPE`, `LOC`, `FAC`).
- `context`:
  - `sents`: Sentences containing mentions of the toponym, providing context.
- `link`: URL of the source material.
- `title`: Title of the source document.
- `published`: Publication date of the source material.
- `link_extracted_from`: Where the link was sourced (e.g., a news website).
- `media_dets`: Details about the media outlet (e.g., name, type).

## Evaluation Process

For a single toponym, e.g., `Williamsburg`, a single evaluation for a given geoparser involved passing the toponym (and any required information) to the geoparser and then comparing the geo-coordinates it returns to the correct geo-coordinate within the gold-standard.

1. **Evaluation function**: The core evaluation function takes two arguments: a path to the gold standard dataset file, and a `match_proximity_radius_miles` parameter with a default value of 25 miles. If the geocoordinates produced by a toponym disambiguation tool is within 25 miles of the reference (gold-standard) coordinate, it is counted as a **True** match, else **False**. If the toponym disambiguation tools doesn't return a coordinate, it counted as a **null**. 

Note: For GPEs such as states, countries, continents, etc, the `match_proximity_radius_miles` radius is not used. Instead, the entire geographical polygon of the state or country was used as the radius. This is because any point within the state counts as the state, even if it is more than 25 miles away from the reference (gold-standard) coordinate.

2. **Reading and processing data**: The script reads the gold-standard files line by line. Each line corresponding to a toponym is processed as follows:
    - Extract toponym (e.g., `Williamsburg`) and actual (gold-standard) geo-coordinate (`37.271133, -76.716614`) and context sentences.
    - Issue toponym to toponym disambiguation tool
    - Compare actual geo-coordinates with the coordinate returned by the tool
    - Update `TP: True Positive`, `FP: False Positive`, and `FN: False Negative` counts. (No `TN: True Negative`) 

3. **Result Analysis**: Use `TP`, `FP`, and `TN` counts to compute evaluation metrics (Precision, Recall, F1)

To evaluate the [traditional geoparsers](https://github.com/wm-newslab/toporesolve/tree/main/models/traditional-geoparsers) with our [gold-standard dataset](https://github.com/wm-newslab/toporesolve#datasets-gold-standards), we've provided an evaluation function, [evaluate_place_resolver()](https://github.com/wm-newslab/toporesolve/tree/main/models/traditional-geoparsers) for each geoparser. You may need to install the following to use it: [geopy](https://geopy.readthedocs.io/en/stable/#installation), [shapely](https://shapely.readthedocs.io/en/stable/installation.html), and [NwalaTextUtils](https://github.com/oduwsdl/NwalaTextUtils).

To evaluate the LLMs with our [gold-standard dataset](https://github.com/wm-newslab/toporesolve#datasets-gold-standards), we've provided [evaluate_llm_disambiguation.py](https://github.com/wm-newslab/toporesolve/blob/main/models/llms/evaluate_llm_disambiguation.py).

# Traditional Geoparsers

## 1. [GATE YODIE](https://cloud.gate.ac.uk/info/help/online-api.html)

### Installation:
- Create an account at [https://cloud.gate.ac.uk/login/full](https://cloud.gate.ac.uk/login/full)
- Request an API key
- Once you have the API key ID and password, make an HTTP POST request to the API endpoint: [https://cloud-api.gate.ac.uk/process/yodie-en](https://cloud-api.gate.ac.uk/process/yodie-en)
- **Note:** You can make 800 free header requests a day.

First convert your API ID and password to base64:

```bash
$ echo -n "api-id" | base64
```

Example POST request, with content of `example.txt` set to `"The University of Oklahoma has received a  million gift from Delta Dental of Oklahoma and Delta Dental of Oklahoma Foundation to the OU College of Dentistry to fund a dental clinic on the OU-Tulsa campus."`:
```bash
curl -X POST -H "Authorization: Basic base64-api-id" -H "Content-Type: text/plain" -H "Accept: application/json" -m 60 --data-binary @example.txt https://cloud-api.gate.ac.uk/process/yodie-en -o output.json
```

<details>
    <summary>Programmatically, you may also use python's <a href="https://pypi.org/project/requests/"><code>requests</code></a> library:</summary>

```py
import requests

url = "https://cloud-api.gate.ac.uk/process/yodie-en"
headers = {
    "Authorization": "Basic base64-api-id",
    "Content-Type": "text/plain",
    "Accept": "application/json"
}
requests.post(url, headers=headers, data={text}, timeout=60)
```
</details>

<details>
    <summary>Output:</summary>

```json
{
    "text": "The University of Oklahoma has received a  million gift from Delta Dental of Oklahoma and Delta Dental of Oklahoma Foundation to the OU College of Dentistry to fund a dental clinic on the OU-Tulsa campus.",
    "entities": {
        "Mention": [
            {
                "indices": [
                    4,
                    26
                ],
                "inst": "http://dbpedia.org/resource/University_of_Oklahoma",
                "dbpInterestingClasses": "dbpedia-owl:Organisation|dbpedia-owl:Person",
                "dbpSpecificClasses": "dbpedia-owl:College|dbpedia-owl:Person",
                "confidence": 0.53
            },
            {
                "indices": [
                    61,
                    73
                ],
                "inst": "http://dbpedia.org/resource/Delta_Dental",
                "dbpInterestingClasses": "owl:Thing",
                "dbpSpecificClasses": "owl:Thing",
                "confidence": -0.8
            }
        ]
    }
}
```
</details>

Dbpedia entities are returned so further parsing is required to get the coordinates:
`result = get_dbpedia_coords( dbpedia["entities"]["Mention"][0] )`. See [gate.py](models/traditional-geoparsers/gate.py) for complete code using Gate Yodie on the datasets.

## 2. [Geoparsepy (using windows terminal pipenv)](https://github.com/stuartemiddleton/geoparsepy)

### Installation:

- [Download PostgreSQL](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads): when you install, you will be asked to give a password, take note of this, also you will be asked to select a port: choose `5432`
- Install `requests` and the `geoparsepy` library

```bash
pip install requests
pip install geoparsepy
```

Installing these should also automatically install `psycopg2>=2.8`, `nltk>=3.4`, `numpy>=1.18`, `shapely>=1.6`, `setuptools>=46`, `soton-corenlppy>=1.0`, but if not, install them.

- Download NLTK corpora:

```python
import nltk
nltk.download('names')
nltk.download('stopwords')
nltk.download('wordnet')
```

- Download [pre-processed UTF-8 encoded SQL table dumps](https://drive.google.com/file/d/1xyCjQox6gCoN8e0upHHyeMLV-uLirthS/view?usp=sharing):
- Then unzip the files manually or by running the following in bash
```bash
unzip geoparsepy_preprocessed_tables.tar.zip
tar -xvf geoparsepy_preprocessed_tables.tar
```

- Create openstreetmap database and extensions by running this in psql:
```sql
psql -U postgres
CREATE DATABASE openstreetmap;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
CREATE EXTENSION IF NOT EXISTS hstore;
```

Alternatively, open pgAdmin, click Databases and then Create. Input the database name and save. While still in the app, select your database, click the psql tool icon and run the create extension commands above.

- Import the precomputed database tables for global cities and places. In powershell, navigate to the folder where your SQL tables are saved and run the following:
```powershell
& 'C:\Program Files\PostgreSQL\16\bin\psql' -U postgres -d openstreetmap -f global_cities.sql
& 'C:\Program Files\PostgreSQL\16\bin\psql' -U postgres -d openstreetmap -f uk_places.sql
& 'C:\Program Files\PostgreSQL\16\bin\psql' -U postgres -d openstreetmap -f north_america_places.sql
& 'C:\Program Files\PostgreSQL\16\bin\psql' -U postgres -d openstreetmap -f europe_places.sql
```

You may run [the example code](https://github.com/stuartemiddleton/geoparsepy/blob/master/example.py) and attempt to get the same results. Note that the example contains a line: 
```py
databaseHandle = soton_corenlppy
    .PostgresqlHandler
    .PostgresqlHandler('postgres', 'password', 
                     'localhost', 5432, 
                     'openstreetmap', 600)
```

Ensure to replace the `password` string with whatever password you chose when downloading PostgreSQL.

Note: Geoparsepy returns OSM IDs, not coordinates. The Overpass API may be used to convert OSM IDs to coordinates:
```py
import requests 

overpass_url = "http://overpass-api.de/api/interpreter"
overpass_query = f"""
    [out:json];
    {osm_type}({osm_id});
    out geom;
    """
requests.get(overpass_url, params={'data': overpass_query})
```

See [geopaserpy.py](models/traditional-geoparsers/geopaserpy.py) for complete code using Geoparsepy on the datasets.

## 3. [Cliff-Clavin](https://github.com/mediacloud/cliff-annotator) ([see also](https://pypi.org/project/mediacloud-cliff/))

**Using via Cliff server:**
- Ensure to run Docker Desktop
- In Bash, run the cliff server:
```bash
docker run -p 8080:8080 -m 8G --platform=linux/amd64 -d rahulbot/cliff-clavin:2.6.1
```
- Run `'http://localhost:8080/cliff-2.6.1/parse/text?q={text_for_parsing}`

**Using Cliff programmatically:**

First, install,
```bash
pip install mediacloud-cliff
```

Next:
```py
from cliff.api import Cliff
my_cliff = Cliff('http://myserver.com:8080')
my_cliff.parse_text("This is about Einstien at the IIT in New Delhi.")
```

<details>
    <summary>Output:</summary>

```json
{
  "results": {
    "organizations": [
      {
        "count": 1,
        "name": "IIT"
      }
    ],
    "places": {
      "focus": {
        "cities": [
          {
            "id": 1261481,
            "lon": 77.22445,
            "name": "New Delhi",
            "score": 1,
            "countryGeoNameId": "1269750",
            "countryCode": "IN",
            "featureCode": "PPLC",
            "featureClass": "P",
            "stateCode": "07",
            "lat": 28.63576,
            "stateGeoNameId": "1273293",
            "population": 317797
          }
        ],
        "states": [
          {
            "id": 1273293,
            "lon": 77.1,
            "name": "National Capital Territory of Delhi",
            "score": 1,
            "countryGeoNameId": "1269750",
            "countryCode": "IN",
            "featureCode": "ADM1",
            "featureClass": "A",
            "stateCode": "07",
            "lat": 28.6667,
            "stateGeoNameId": "1273293",
            "population": 16787941
          }
        ],
        "countries": [
          {
            "id": 1269750,
            "lon": 79,
            "name": "Republic of India",
            "score": 1,
            "countryGeoNameId": "1269750",
            "countryCode": "IN",
            "featureCode": "PCLI",
            "featureClass": "A",
            "stateCode": "00",
            "lat": 22,
            "stateGeoNameId": "",
            "population": 1173108018
          }
        ]
      }
    },
    "people": [
      {
        "count": 1,
        "name": "Einstien"
      }
    ]
  },
  "status": "ok",
  "milliseconds": 22,
  "version": "2.6.0"
}
```
</details>

See [cliff.py](models/traditional-geoparsers/cliff.py) for complete code.

## 4. [DBpedia Spotlight](https://github.com/dbpedia-spotlight/dbpedia-spotlight-model)

- Go to Bash terminal and run curl command 
- E.g.,: 
```bash
curl https://api.dbpedia-spotlight.org/en/annotate  \
  --data-urlencode "text=The University of Oklahoma has received a $2 million gift from Delta Dental of Oklahoma and Delta Dental of Oklahoma Foundation to the OU College of Dentistry to fund a dental clinic on the OU-Tulsa campus." \
  --data "confidence=0.35" \
  -H "Accept: application/json"
```

<details>
    <summary>Output:</summary>

```json
{
    "@text": "The University of Oklahoma has received a  million gift from Delta Dental of Oklahoma and Delta Dental of Oklahoma Foundation to the OU College of Dentistry to fund a dental clinic on the OU-Tulsa campus.",
    "@confidence": "0.35",
    "@support": "0",
    "@types": "",
    "@sparql": "",
    "@policy": "whitelist",
    "Resources": [
        {
            "@URI": "http://dbpedia.org/resource/Oklahoma",
            "@support": "47520",
            "@types": "Wikidata:Q3455524,Schema:Place,Schema:AdministrativeArea,DBpedia:Region,DBpedia:PopulatedPlace,DBpedia:Place,DBpedia:Location,DBpedia:AdministrativeRegion",
            "@surfaceForm": "Oklahoma",
            "@offset": "18",
            "@similarityScore": "0.7628718792600525",
            "@percentageOfSecondRank": "0.31083199190989347"
        },
        {
            "@URI": "http://dbpedia.org/resource/Delta_Dental",
            "@support": "31",
            "@types": "Wikidata:Q4830453,Wikidata:Q43229,Wikidata:Q24229398,DUL:SocialPerson,DUL:Agent,Schema:Organization,DBpedia:Organisation,DBpedia:Agent,DBpedia:Company",
            "@surfaceForm": "Delta Dental",
            "@offset": "61",
            "@similarityScore": "0.9999999999943725",
            "@percentageOfSecondRank": "0.0"
        },
        {
            "@URI": "http://dbpedia.org/resource/Oklahoma",
            "@support": "47520",
            "@types": "Wikidata:Q3455524,Schema:Place,Schema:AdministrativeArea,DBpedia:Region,DBpedia:PopulatedPlace,DBpedia:Place,DBpedia:Location,DBpedia:AdministrativeRegion",
            "@surfaceForm": "Oklahoma",
            "@offset": "77",
            "@similarityScore": "0.7628718792600525",
            "@percentageOfSecondRank": "0.31083199190989347"
        }  
    ]
}
```
</details>

The same outcome can be gotten by sending an HTTP POST [request via python](models/traditional-geoparsers/dbpedia.py).

## 5. [Edinburgh Geoparser](https://www.ltg.ed.ac.uk/software/geoparser/)

### Installation
- Install [networkx](https://networkx.org/documentation/stable/install.html), [xmltodict](https://pypi.org/project/xmltodict/), [BeautifulSoup4](https://pypi.org/project/beautifulsoup4/)
- Download and extract [geoparser-1.3.tar.gz](https://www.ltg.ed.ac.uk/software/geoparser/)
- Navigate to the `Script` Directory in terminal
- Process news text from a file example.txt
```bash
cat ../in/example.txt | ./run -t plain -g geonames -o ../out example
```

<details>
    <summary>Run command options:</summary>

```
Input type
-t   plain          (plain text)
     ltgxml         (xml file in a certain format with paragraphs marked up)
     gb             (Google Books html files)

Gazetteer options

-g   unlock         (Edina's Unlock gazetteer)
     os             (Just the OS part of Unlock)
     naturalearth   (Just the Natural Earth part of Unlock)
     unlockgeonames (Just the GeoNames part of Unlock)
     geonames       (online world-wide gazetteer)
     plplus         (Pleiades+ gazetteer of ancient places)
     deep           (DEEP gazetteer of historical placenames in England)

     [ geonames-local (locally maintained copy on ed.ac.uk network) ]
     [ plplus-local   (locally maintained Pleiades+, with geonames lookup) ]

-l lat long radius score (use this if you know what geographical area your ambiguous toponym is likely to be in)
```
</details>

See [edinburgh.py](models/traditional-geoparsers/edinburgh.py) for more details on using the Edinburgh Geoparser.

## 6. [Mordecai3](https://github.com/ahalterman/mordecai3)

- Install these
```bash 
$ pip install textacy mordecai3 unzip
```

If you ran into error: `DocTransformerOutput' object has no attribute 'tensors'`, resolve by rolling back spacy:
```bash
pip install spacy==3.6.1
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_trf-3.6.1/en_core_web_trf-3.6.1.tar.gz
```

- Create a Geonames index running locally in Elasticsearch container (make sure Docker Desktop is open, and resources integration for Ubuntu is selected).
```bash
$ git clone https://github.com/openeventdata/es-geonames.git
$ cd es-geonames
$ bash create_index.sh
```
Make sure this completes successfully. To test, open python in your terminal (ubuntu) and run the below:
```py
>>> from mordecai3 import Geoparser
>>> geo = Geoparser()
>>> geo.geoparse_doc("I visited Alexanderplatz in Berlin.")
```

<details>
    <summary>Output:</summary>

```json
{"doc_text": "I visited Alexanderplatz in Berlin.", "event_location_raw": "", "geolocated_ents": [
        {
            "feature_code": "SQR",
            "feature_class": "S",
            "country_code3": "DEU",
            "lat": 52.5225,
            "lon": 13.415,
            "name": "Alexanderplatz",
            "admin1_code": "16",
            "admin1_name": "Berlin",
            "admin2_code": "00",
            "admin2_name": "",
            "geonameid": "6944049",
            "admin1_parent_match": 0,
            "country_code_parent_match": 0,
            "alt_name_length": 3.1354942159291497,
            "min_dist": 0.0,
            "max_dist": 0.16216216216216217,
            "avg_dist": 0.21824381926683717,
            "ascii_dist": 0.0,
            "adm1_count": 1.0,
            "country_count": 1.0,
            "score": 1.0,
            "search_name": "Alexanderplatz",
            "start_char": 10,
            "end_char": 24,
            "city_id": "",
            "city_name": ""
        },
        {
            "feature_code": "PPLC",
            "feature_class": "P",
            "country_code3": "DEU",
            "lat": 52.52437,
            "lon": 13.41053,
            "name": "Berlin",
            "admin1_code": "16",
            "admin1_name": "Berlin",
            "admin2_code": "00",
            "admin2_name": "",
            "geonameid": "2950159",
            "admin1_parent_match": 0,
            "country_code_parent_match": 0,
            "alt_name_length": 4.0943445622221,
            "min_dist": 0.0,
            "max_dist": 0.14492753623188406,
            "avg_dist": 0.09058940069341258,
            "ascii_dist": 0.0,
            "adm1_count": 1.0,
            "country_count": 1.0,
            "score": 0.9999998807907104,
            "search_name": "Berlin",
            "start_char": 28,
            "end_char": 34,
            "city_id": "2950159",
            "city_name": "Berlin"
        }
    ]
}
```
</details>

Once built, the index can be started by running:
```bash
docker run -d -p 127.0.0.1:9200:9200 -e "discovery.type=single-node" 
-v $PWD/geonames_index/:/usr/share/elasticsearch/data elasticsearch:7.10.1
```

See [mordecai.py](models/traditional-geoparsers/mordecai.py) for more details on running Mordecai.

## Evaluation of traditional geoparsers

Recall that we created [three gold-standard files](#datasets-gold-standards) corresponding to the toponym classes (`GPE`s, `LOC`s, and `FAC`s) to [evaluate](#evaluation-process) the traditional geoparsers. For a single toponym, e.g., `Williamsburg`, a single evaluation for a given geoparser involved passing the toponym (and any required information) to the geoparser and then comparing the geo-coordinates it returns to the correct geo-coordinate within the gold-standard.

Here are the results:

### [GPE](data/gold_standards/GPE_2024_05_21T134100Z.jsonl)s
|| Mordecai3 | Edinburgh Geoparser | Geoparsepy | Cliff Clavin | Gate Yodie | Dbpedia Spotlight
|---|---|---|---|---|---|---|
|Precision| **0.8182** | 0.7011 | 0.5543 | 0.7526 | 0.7544 | 0.6867
|Recall| 0.7159 | 0.8026 | 0.8361| **0.9359** | 0.4886 | 0.7500
|F1-Score| 0.7629 | 0.7484 | 0.6668 | **0.834**| 0.5928 | 0.7170


### [LOC](data/gold_standards/LOC_2024_05_21T134100Z.jsonl)s
|| Mordecai3 | Edinburgh Geoparser | Geoparsepy | Cliff Clavin | Gate Yodie | Dbpedia Spotlight
|---|---|---|---|---|---|---|
|Precision| 0.4839 | 0.4286 | 0.253 | **0.5542** | 0.5098 | 0.4725
|Recall| 0.4286 | 0.4839 | 0.525| 0.7077 | 0.3377 | **0.7963**|
|F1-Score| 0.4545 | 0.4544 | 0.3414 | **0.6216** | 0.4064 | 0.5930


### [FAC](data/gold_standards/FAC_2024_05_21T134100Z.jsonl)s
|| Mordecai3 | Edinburgh Geoparser | Geoparsepy | Cliff Clavin | Gate Yodie | Dbpedia Spotlight
|---|---|---|---|---|---|---|
|Precision| 0.3611 | 0.3750 | 0.2262 | 0.4857 | **0.5818** | 0.4271
|Recall| 0.4643 | 0.4737 | 0.5135 | 0.5152 | 0.4051 | **0.8723**|
|F1-Score| 0.4064 | 0.4184 | 0.3140 | 0.5 | 0.4778 | **0.5734**|

# Large Language Models

We evaluated 1 proprietary general-purpose LLM (GPT-4o-mini), 2 open-source general-purpose ones (Llama2-7B, Phi3-mini-4k), and 3 open-source LLMs (Llama2-7B-LoRA-Toponym-Resolution, Llama2-13B-LoRA-Toponym-Resolution, and Mistral-7B-LoRA-Toponym-Resolution) [fined tuned specifically for the toponym disambiguation](https://doi.org/10.1080/13658816.2024.2405182) task.

## General-purpose (non-finetuned) LLMs

## 7. gpt-4o-mini

This GPT model is a more affordable and faster option than **gpt-4o** (which is for more complex tasks, and hence, more expensive), and is perfect for lightweight tasks. It costs $0.150 per 1M input tokens as compared to gpt-4o's $2.50 per 1M input tokens. See https://openai.com/api/pricing/ for details.

### Requirements
- Create an account on OpenAI's development platform (https://platform.openai.com/)
- Go to Settings. Under Organization, select Billing. Click Add payment details.
- Fill in necessary info (such as payment information, etc)
- Select credit limit (upper limit of $100), and set auto-renewal options. (We didn't use auto-renewal).
- You can perform tasks on the user interface, or you can create an API key (with necessary permissions) [here](https://platform.openai.com/api-keys) to use within your code.
- You can view your usage details, how much credit you have left, etc on the [dashboard](https://platform.openai.com/usage).

### Python usage of gpt-4o-mini

```py
client = OpenAI(api_key = 'api-key') # replace with your api key
messages = [
    {"role": "user", "content": "your-prompt-here"}
]
response = client.chat.completions.create(
    model="gpt-4o-mini", # use preferred model
    messages=messages,
    max_tokens=200
)
```

See [gpt-4o-mini.py](gpt-4o-mini.py) for complete code using the gpt4o-mini to perform toponym disambiguation on the gold-standard datasets.

*Note: Using this API is really fast and efficient. Takes seconds to a few minutes for hundreds of data. Good for those who want quick results and don't mind the cost.*

## 8. Llama2-7B

This model was developed by Meta. It can be accessed via HuggingFace in 2 ways:

- Pipeline
```py
# Use a pipeline as a high-level helper
from transformers import pipeline

messages = [
    {"role": "user", "content": "prompt-here"},
]
pipe = pipeline("text-generation", model="meta-llama/Llama-2-7b-chat-hf")
pipe(messages)
```

- Directly
```py
# Load model directly
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-chat-hf")
model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-7b-chat-hf")
```

See [llama2-7b.py](models/llama2-7b.py) for complete code using Llama2-7B for toponym disambiguation on the gold-standard datasets.

* *Note: You need to have a HuggingFace account, access to the model, and an access token. You can request access from the [model card](https://huggingface.co/meta-llama/Llama-2-7b-chat-hf). And you can [create an access token]( https://huggingface.co/settings/tokens) with the needed permissions. This functions similarly to an API key. You can use one access token for as many models you want.*

## 9. Phi3-mini-4k

This model was developed by Microsoft. Similar to Llama2-7b, it can be accessed via HuggingFace. View the model details on the [card](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct).

```py
# Use a pipeline as a high-level helper
from transformers import pipeline

messages = [
    {"role": "user", "content": "Who are you?"},
]
pipe = pipeline("text-generation", model="microsoft/Phi-3-mini-4k-instruct", trust_remote_code=True)
pipe(messages)

# Load model directly
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct", trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained("microsoft/Phi-3-mini-4k-instruct", trust_remote_code=True)
```

See [phi3-mini-4k.py](models/phi3-mini-4k.py) for complete code using the Phi3-mini-4k to perform toponym disambiguation on the gold-standard.

## Fine-tuned models

The fine-tuned models (Llama2-7B-LoRA-Toponym-Resolution, Llama2-13B-LoRA-Toponym-Resolution, and Mistral-7B-LoRA-Toponym-Resolution) were sourced from [https://github.com/uhuohuy/LLM-geocoding/blob/main/README.md](https://github.com/uhuohuy/LLM-geocoding/blob/main/README.md). The [authors](https://doi.org/10.1080/13658816.2024.2405182) trained 5 LLMs on comprehensive datasets derived from news articles, tweets, Wikipedia, etc.. Their data, training, testing code, and instructions for running their fine-tuned models are [available online](https://github.com/uhuohuy/LLM-geocoding/blob/main/README.md).

### 10. Llama2-7B-LoRA-Toponym-Resolution

This model uses **meta-llama/Llama-2-7b-chat-hf** as a base model and builds on top of it by training it on geographic entities within texts. See the [HuggingFace model card](https://huggingface.co/xukehu/Llama2-7B-LoRA-Toponym-Resolution).

- Start by loading the model and saving it
```py
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Load the base model and tokenizer
model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-7b-chat-hf")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-chat-hf")

# Load LoRA weights for toponym resolution
model = PeftModel.from_pretrained(model, "xukehu/Llama2-7B-LoRA-Toponym-Resolution")

model.save_pretrained("path_of_the_lora_weights")
```

- Run the [**prediction.py**](https://github.com/uhuohuy/LLM-geocoding/blob/main/prediction.py) from your terminal. Ensure to edit the code to run on your dataset. Depending on the format of your datasets, you may need to modify the code.

```bash
$BASE_MODEL="meta-llama/Llama-2-7b-chat-hf"
$LORA_WEIGHTS="path_of_the_lora_weights" 

python prediction.py --load_8bit False --base_model "$BASE_MODEL" --lora_weights "$LORA_WEIGHTS" 
```

### 11. Llama2-13B-LoRA-Toponym-Resolution

This model uses **Llama-2-13b-chat-hf** as a base model and builds on top of it by training it on geographic entities within texts. See the [HuggingFace model card](https://huggingface.co/xukehu/Llama2-13B-LoRA-Toponym-Resolution).

Following same steps as before:
- Start by loading the model and saving it
```py
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Load the base model and tokenizer
model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-2-13b-chat-hf")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-13b-chat-hf")

# Load LoRA weights for toponym resolution
model = PeftModel.from_pretrained(model, "xukehu/Llama2-13B-LoRA-Toponym-Resolution")

model.save_pretrained("path_of_the_lora_weights")
```

- Run the [**prediction.py**](https://github.com/uhuohuy/LLM-geocoding/blob/main/prediction.py) from your terminal. Ensure to edit the code to use the correct model and to run on your dataset. Depending on the format of your datasets, you may need to modify the code.

```bash
$BASE_MODEL="meta-llama/Llama-2-13b-chat-hf"
$LORA_WEIGHTS="path_of_the_lora_weights" 

python prediction.py --load_8bit False --base_model "$BASE_MODEL" --lora_weights "$LORA_WEIGHTS" 
```

### 12. Mistral-7B-LoRA-Toponym-Resolution

This model uses **mistral-7B-v0.1-hf** as a base model and builds on top of it by training it on geographic entities within texts. See the [HuggingFace model card](https://huggingface.co/xukehu/Mistral-7B-LoRA-Toponym-Resolution).

Following the same steps as before:
- Start by loading the model and saving it
```py
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Load the base model and tokenizer
model = AutoModelForCausalLM.from_pretrained("kittn/mistral-7B-v0.1-hf")
tokenizer = AutoTokenizer.from_pretrained("kittn/mistral-7B-v0.1-hf")

# Load LoRA weights for toponym resolution
model = PeftModel.from_pretrained(model, "xukehu/Mistral-7B-LoRA-Toponym-Resolution")

model.save_pretrained("path_of_the_lora_weights")
```

- Run the [**prediction.py**](https://github.com/uhuohuy/LLM-geocoding/blob/main/prediction.py) from your terminal. Ensure to edit the code to use the correct model and to run on your dataset. Depending on the format of your datasets, you may need to modify the code.

```bash
$BASE_MODEL="kittn/mistral-7B-v0.1-hf"
$LORA_WEIGHTS="path_of_the_lora_weights" 

python prediction.py --load_8bit False --base_model "$BASE_MODEL" --lora_weights "$LORA_WEIGHTS" 
```

### Important note

Though free to use, loading HuggingFace models take a good amount of time and requires substantial available memory. It is advisable to use GPUs when running the models. For running and testing all the models (with the exception of gpt-4o-mini), High Performance Computing (HPC) systems provided by William and Mary were utilized. These systems are accessible to W&M students and faculty and provide access to [GPUs for data intense projects](https://www.wm.edu/offices/it/services/researchcomputing/atwm/).

## Evaluation results

### [GPE](data/gold_standards/GPE_2024_05_21T134100Z.jsonl)s
|| gpt-4o-mini|Llama-2-7b-chat-hf|Phi-3-mini-4k-instruct|Llama2-7B-LoRA-Toponym-Resolution|Mistral-7B-LoRA-Toponym-Resolution|Llama2-13B-LoRA-Toponym-Resolution|
|---|---|---|---|---|---|---|
|Precision| **0.902**|0.784|0.765|0.8586|0.85|0.8788
|Recall| **1.0** |**1.0**|0.949|0.9659 |0.977|0.9667
|F1-Score| **0.948**|0.879|0.847|0.9096|0.909|0.9188

### [LOC](data/gold_standards/LOC_2024_05_21T134100Z.jsonl)s
|| gpt-4o-mini|Llama-2-7b-chat-hf|Phi-3-mini-4k-instruct|Llama2-7B-LoRA-Toponym-Resolution|Mistral-7B-LoRA-Toponym-Resolution|Llama2-13B-LoRA-Toponym-Resolution|
|---|---|---|---|---|---|---|
|Precision| **0.7**|0.45|0.495| 0.5281|0.5778|0.5435
|Recall| **0.972**|0.957|0.870| 0.7833|0.8125|0.8333
|F1-Score| **0.813**|0.613|0.632| 0.6297|0.6757|0.6577

### [FAC](data/gold_standards/FAC_2024_05_21T134100Z.jsonl)s
|| gpt-4o-mini|Llama-2-7b-chat-hf|Phi-3-mini-4k-instruct|Llama2-7B-LoRA-Toponym-Resolution|Mistral-7B-LoRA-Toponym-Resolution|Llama2-13B-LoRA-Toponym-Resolution|
|---|---|---|---|---|---|---|
|Precision| **0.931**|0.667|0.693| 0.7561|0.8429|0.8
|Recall| **1.0**|0.957|0.813| 0.7561|0.6484|0.7442
|F1-Score| **0.964**|0.785|0.748| 0.7561|0.7323|0.7707

