# 🌍 address-geocoder

Address Geocoder is a powerful Python-based solution for geocoding raw addresses. Designed for efficiency and accuracy, it supports batch processing and integrates multiple geocoding services to ensure high reliability. Whether you're working with large datasets or need precise location data, this tool is built to handle your geocoding needs seamlessly.

## ✨ Key Features

### Multi-Provider Geocoding
Utilizes three powerful geocoding APIs, each with its unique strengths :
- **Nominatim (OpenStreetMap)** : Free, open-source solution ideal for small-scale projects
- **Photon** : Lightning-fast geocoder powered by OpenStreetMap data
- **Open Cage** : Commercial geocoding service with high accuracy and global coverage (2,500 free requests/day)

Each request is processed using a fallback strategy, ensuring a response even if one provider fails.

### Core Capabilities
- **Optimized parallel processing** : Uses multiple workers to process requests in parallel, reducing latency and improving throughput, ensuring efficient load distribution and API rate-limit compliance
- **Address geocoding** : Takes raw addresses as input and retrieves their detailled location attributes
- **Spatial join with IRIS data (French administrative divisions)** (Optional) : If enabled, the script perform a spatial join to associate the geocoded locations with predefined IRIS geographical zones, enriching your data with additional context
- **Structured and readable output** : Results are standardized into a consistent structure, regardless of the geocoding provider used. If IRIS geocoding is enabled, additional fields related to IRIS zones are included

### Output Data Structure

#### Address Information
| Field | Description |
|-------|-------------|
| `street_number` | Building/house number |
| `street_name` | Street name |
| `postal_code` | Postal/ZIP code |
| `city` | City/town name |
| `admin_level_1` | Primary administrative division (e.g., county) |
| `admin_level_2` | Secondary administrative division (e.g., state) |
| `country` | Country name |
| `latitude` | Latitude coordinate |
| `longitude` | Longitude coordinate |
| `location_type` | Location classification |
| `address_type` | Address category |
| `raw_address` | Original input address |
| `encoder` | Geocoding provider used |

#### IRIS Data (Optional)
| Field | Description |
|-------|-------------|
| `iris_code` | Unique IRIS zone identifier |
| `municipality_code` | INSEE municipality code |
| `municipality_name` | Municipality name |
| `iris` | IRIS identifier |
| `iris_name` | IRIS zone name |
| `iris_type` | IRIS zone classification |

## 🚀 Getting Started

### Prerequisites
1. **Install Python (version 3.13 or higher)** : Follow the official instructions at https://python.org/downloads
2. **Obtain an OpenCage API key** : Sign up at https://opencagedata.com/users/sign_up and add your API key to the `.env` file
3. **Prepare data for geocoding** : Prepare a CSV or PARQUET file with exactly 2 columns : 
   - `id` : unique identifier for each address
   - `address` : complete address to be geocoded

### Project Structure
```
address-geocoder/
├── data/                                 # Input and output data files
├── src/
│   ├── config/                           # Configuration files
│   │   ├── iris_geojson/                 # IRIS geospatial data (GeoJSON files)
│   │   ├── address_geocoding.py          # Core address geocoding logic and providers
│   │   ├── app.py                        # Application settings
│   │   ├── config_validator.py           # Configuration validation utilities
│   │   ├── input.py                      # Input file handling and validation
│   │   ├── iris_geocoding.py             # IRIS geocoding process
│   │   └── logger.py                     # Logging configuration
│   ├── utils/                            # Utility functions
│   │   ├── geocoder.py                   # Geocoding functions
│   │   ├── helpers.py                    # General-purpose utility functions
│   │   └── orchestrator.py               # Workflow orchestration
│   └── api.py                            # Main entry point of the FastAPI application
├── .env.example                          # Example .env file
├── .gitattributes                        # Git attributes configuration
├── .gitignore                            # Git ignore rules
├── .pre-commit-config.yaml               # Pre-commit hooks configuration
├── .python-version                       # Python version specification
├── LICENSE                               # License file
├── pyproject.toml                        # Project configuration and dependencies
├── README.md                             # Project documentation
└── uv.lock                               # Dependency lock file
```

### Quick Start Guide
1. **Clone the repository** :
```bash
git clone https://github.com/mohamedehouran/address-geocoder.git
cd address-geocoder
```
2. **Configure environment variables** :
```bash
cp .env.example .env
# Edit .env with your settings
```
3. **Create and activate a virtual environment** : 
```bash
pip install --upgrade uv
uv venv

# Activate the environment
.venv\Scripts\activate        # For Windows
source .venv/bin/activate     # For macOS/Linux

# Install dependencies
uv sync
```
4. **Run the application** :
```bash
uv run uvicorn src.api:app --reload
```
- This command starts the FastAPI application using Uvicorn
- Open your browser and go to `http://localhost:8000/docs` to access the interactive API documentation
5. **Upload your file for geocoding** : Use the interactive API documentation to upload your file and start the geocoding process
6. **Retrieve the output file** : Once the process is complete, the geocoded results will be saved in the `data/` directory. You can also download the results as a CSV file through the API endpoint

## ⚙️ Customization
- **Adjust data processing parameters** in `.env` : Modify the `MAX_WORKERS` or `CHUNKSIZE` values to optimize performance based on your system's capabilities
- **Add new geocoders** in `src/config/address_geocoding.py` : Extend the list of geocoders and implement provider-specific formatting logic
- **Modify output format** in `src/config/address_geocoding.py` : Update the `GeocodingResponseSchema.Output` enum to customize the output fields and structure
- **Update IRIS data** in `src/config/iris_geojson/` : The project uses IRIS 2021 data by default. You can update this by replacing the files in this directory

## 📈 Use Cases
- **Batch address processing** : Efficiently handle large address datasets
- **Location intelligence** : Enhance data with precise geographical coordinates
- **Spatial data enrichment** : Combine with IRIS zones for advanced geographical insights
- **Address validation** : Verify and standardize address data
- **GIS integration** : Export standardized location data for GIS applications

## 📝 Third-Party Services & Licenses
This project integrates with several geocoding services, each with its own terms of service and usage conditions. When using this tool, you must comply with each service's terms of use and attribution requirements.

- **OpenStreetMap/Nominatim** : Data is © OpenStreetMap contributors and available under the [Open Database License (ODbL)](https://www.openstreetmap.org/copyright)
- **Photon** : Powered by OpenStreetMap data, subject to [ODbL](https://www.openstreetmap.org/copyright)
- **OpenCage** : Commercial service requiring an API key. Usage is subject to [OpenCage's terms of service](https://www.opencagedata.com/terms)

### IRIS Data
The IRIS geographical data (French administrative divisions) is provided by INSEE and IGN, subject to their respective terms of use and licenses.

## 🤝 Contributing
Contributions are welcome ! Please feel free to submit a Pull Request.

## 📄 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.