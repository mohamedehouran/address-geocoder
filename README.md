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
- **Address Geocoding**: Takes raw addresses as input and retrieves their detailled location attributes
- **Spatial Join with IRIS Data (French administrative divisions)** (Optional): If enabled, the script perform a spatial join to associate the geocoded locations with predefined IRIS geographical zones, enriching your data with additional context
- **Structured and readable output**: Results are standardized into a consistent structure, regardless of the geocoding provider used. If IRIS geocoding is enabled, additional fields related to IRIS zones are included

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
1. **Install Docker** : Follow the official instructions at https://docs.docker.com/get-docker/
2. **Obtain an OpenCage API Key** : Sign up at https://opencagedata.com/users/sign_up and add your API key to the .env file
3. **Prepare Input Data** : The input file should be formatted as a CSV or a PARQUET with 2 columns : `id` and `address`

### Project Structure
```
address-geocoder/
├── data/
│   └── input/                            # Directory for input CSV files
├── src/
│   ├── config/                           # Configuration files
│   │   ├── iris_geojson/                 # IRIS geospatial data
│   │   ├── address_geocoding.py          # Core address geocoding logic
│   │   ├── app.py                        # Application settings
│   │   ├── config_validator.py           # Configuration validation
│   │   ├── input.py                      # Input file handling
│   │   ├── iris_geocoding.py             # IRIS geocoding process
│   │   └── logger.py                     # Logging configuration
│   ├── utils/                            # Utility functions
│   │   ├── address_geocoder.py           # Geocoding functions
│   │   ├── geocoding_orchestrator.py     # Workflow orchestration
│   │   ├── helpers.py                    # General utilities
│   │   └── iris_geocoding.py             # IRIS-specific utilities
│   └── main.py                           # Main application script
├── .dockerignore                         # Docker ignore file
├── .env.example                          # Environment variables template
├── .gitattributes                        # Git attributes file
├── .gitignore                            # Git ignore file
├── docker-compose.yml                    # Docker Compose configuration
├── Dockerfile                            # Dockerfile for building the container
├── LICENSE                               # License file
├── poetry.lock                           # Dependency lock file
├── pyproject.toml                        # Project configuration with Poetry
└── README.md
```

### Quick Start Guide
1. **Clone the Repository** :
   ```bash
   git clone https://github.com/mohamedehouran/address-geocoder.git
   cd address-geocoder
   ```
2. **Configure Environment Variables** :
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```
3. **Prepare the Input File** :
   - Place your input file in the data/input/ directory
4. **Build Docker Container** : 
   ```bash
   docker-compose build
   ```
5. **Run the Application** :
   ```bash
   docker-compose up
   ```
5. **Retrieve the Output file** :
   - Once the process is complete, the geocoded results will be saved in the data/output/ directory

## ⚙️ Customization
- **Adjust Parallel Workers** in `.env`: Modify the number of max workers or chunksize in the configuration to optimize performance based on your system's capabilities
- **Add New Geocoders** in `src/config/address_geocoding.py`: Extend the `Geocoder` enum and implement provider-specific formatting in `AddressGeocodingConfig`
- **Modify Output Format** in `src/config/address_geocoding.py`: Update `LocationColumn.Output` enum to customize output fields and format
- **Update IRIS Data** in `src/config/iris_geojson/`: The project uses IRIS 2021 data by default. You can update this by replacing the files in this directory

## 📈 Use Cases
- **Batch Address Processing**: Efficiently handle large address datasets
- **Location Intelligence**: Enhance data with precise geographical coordinates
- **Spatial Data Enrichment**: Combine with IRIS zones for advanced geographical insights
- **Address Validation**: Verify and standardize address data
- **GIS Integration**: Export standardized location data for GIS applications

## 📝 Third-Party Services & Licenses
This project integrates with several geocoding services, each with its own terms of service and usage conditions:

### Geocoding Services
- **OpenStreetMap/Nominatim**: Data is © OpenStreetMap contributors and available under the [Open Database License (ODbL)](https://openstreetmap.org/copyright)
- **Photon**: Powered by OpenStreetMap data, subject to [ODbL](https://openstreetmap.org/copyright)
- **OpenCage**: Commercial service requiring an API key. Usage is subject to [OpenCage's terms of service](https://opencagedata.com/terms)

### Usage Requirements
- When using this tool, you must comply with each service's terms of use and attribution requirements
- For OpenStreetMap data (used by Nominatim and Photon), you must provide attribution to OpenStreetMap contributors
- If you exceed OpenCage's free tier limits (2,500 requests/day), you will need to subscribe to a paid plan

### IRIS Data
The IRIS geographical data (French administrative divisions) is provided by INSEE and IGN, subject to their respective terms of use and licenses.

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.