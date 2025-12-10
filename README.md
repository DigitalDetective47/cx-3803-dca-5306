# Truck Loading Tetris

A 3D truck loading visualization and optimization application. Plan and visualize how handling units (HUs) are loaded into a 53-foot truck trailer.

## Features

- **3D Visualization** - Interactive 3D view of the truck and cargo using Three.js with orbit controls
- **Loading Animation** - Watch items load into the truck sequentially with play, pause, and rewind controls
- **Packing Algorithm** - Automated bin-packing algorithm that optimizes placement by stop and weight
- **Save/Load Configurations** - Save loading arrangements and restore them later
- **Manual Positioning** - Select items in the 3D view and adjust their positions using transform controls
- **Item Restrictions** - Set "No Stacking" and "This Side Up" constraints on handling units
- **Stop-Based Color Coding** - Items are color-coded by delivery stop for easy identification
- **CSV Import** - Create new loads by importing handling unit data from CSV files

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.2.7 |
| Database | SQLite |
| 3D Graphics | Three.js |
| Frontend | HTML, CSS, JavaScript |

## Project Structure

```
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── tetris/                # Django project settings
│   ├── settings.py
│   └── urls.py
└── viewer/                # Main application
    ├── models.py          # Data models (Shipment, Simulation, HandlingUnit, etc.)
    ├── views.py           # API endpoints and views
    ├── algo.py            # Bin-packing optimization algorithm
    ├── rotation.py        # Item rotation handling
    ├── restrictions.py    # Item constraint definitions
    ├── templates/         # HTML templates
    └── static/            # JavaScript and CSS
```

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/DigitalDetective47/cx-3803-dca-5306.git
   cd cx-3803-dca-5306
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Start the server:
   ```bash
   python manage.py runserver
   ```

5. Open `http://localhost:8000/` in your browser

## Usage

1. **Create a Load** - From the dashboard, enter a load name and upload a CSV file with handling unit data
2. **Open the Viewer** - Click on a load to open the 3D visualization
3. **Run the Algorithm** - Click "Run Algorithm" to compute optimal placements
4. **Animate** - Use "Animate" to watch items load into the truck; use "Rewind" to step backwards
5. **Select Items** - Click on any item to view its details and manually adjust its position
6. **Save Configuration** - Save the current arrangement to restore it later

## CSV Format

The CSV file should contain the following columns:

| Column | Description |
|--------|-------------|
| HU Number | Unique identifier for the handling unit |
| Shipment | Shipment ID |
| Gross Weight | Weight in pounds |
| Length | Length in inches |
| Width | Width in inches |
| Height | Height in inches |
| Stop | Delivery stop (e.g., 1A, 2A, 3A) |

## Keyboard Shortcuts (3D Viewer)

- `T` - Switch to translate mode (move items)
- `R` - Switch to rotate mode
- `+` - Increase gizmo size
- `-` - Decrease gizmo size

## License

See [LICENSE.txt](LICENSE.txt) for details.
