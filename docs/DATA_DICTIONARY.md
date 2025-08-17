# Data Dictionary - Myanmar Election Data

## Source Data Structure

### Original Excel File: `MAL-ELECTION-PLAN.xlsx`

The source data contains 872 constituency records with the following structure:

| Column Index | Myanmar Header | English Translation | Data Type | Description |
|--------------|----------------|-------------------|-----------|-------------|
| 0 | [Unnamed] | Constituency ID | Integer | Sequential number (1-872) |
| 1 | တိုင်း/ပြည်နယ် | State/Region | String | Myanmar state or region name |
| 2 | မဲဆန္ဒနယ် | Constituency | String | Constituency/township name |
| 3 | [Unnamed] | Assembly Type | String | Always "ပြည်သူ့လွှတ်တော်မဲဆန္ဒနယ်" (Pyithu Hluttaw) |
| 4 | မဲဆန္ဒနယ်မြေတွင်ပါဝင်သည့်နယ်မြေများ | Areas Included | String | Geographic areas within constituency |
| 5 | ကိုယ်စားလှယ် | Representatives | Integer | Number of representatives (always 1) |
| 6 | [Unnamed] | [Empty] | - | Empty column |
| 7 | မဲစနစ် | Electoral System | String | Always "မဲအများဆုံးရသူ အနိုင်ယူစနစ် ( FPTP )" |

## Processed Data Structure

### Clean Data Format (JSON/CSV)

After processing, the data is transformed into a standardized format:

```json
{
  "id": "integer",
  "state_region_mm": "string",
  "state_region_en": "string", 
  "constituency_mm": "string",
  "constituency_en": "string",
  "assembly_type": "pyithu",
  "areas_included_mm": "string",
  "areas_included_en": "string",
  "representatives": 1,
  "electoral_system": "FPTP",
  "coordinates": {
    "lat": "float",
    "lng": "float"
  }
}
```

### Field Descriptions

#### `id`
- **Type**: Integer
- **Range**: 1-872
- **Description**: Unique constituency identifier
- **Example**: `1`

#### `state_region_mm` / `state_region_en`
- **Type**: String
- **Description**: Myanmar state or region name in Myanmar and English
- **Examples**: 
  - Myanmar: `"ကချင်ပြည်နယ်"`
  - English: `"Kachin State"`

#### `constituency_mm` / `constituency_en`
- **Type**: String
- **Description**: Constituency/township name in Myanmar and English
- **Examples**:
  - Myanmar: `"ချီဖွေမြို့နယ်"`
  - English: `"Chipwi Township"`

#### `assembly_type`
- **Type**: String (Enum)
- **Values**: 
  - `"pyithu"` - Pyithu Hluttaw (Lower House)
  - `"amyotha"` - Amyotha Hluttaw (Upper House) 
  - `"state_regional"` - State/Regional Assembly
- **Description**: Type of legislative assembly
- **Note**: Current dataset only contains Pyithu Hluttaw constituencies

#### `areas_included_mm` / `areas_included_en`
- **Type**: String
- **Description**: Detailed description of geographic areas within the constituency
- **Examples**:
  - Myanmar: `"ချီဖွေမြို့နယ်တစ်ခုလုံး။"`
  - English: `"Entire Chipwi Township."`

#### `representatives`
- **Type**: Integer
- **Value**: Always `1`
- **Description**: Number of representatives elected from this constituency
- **Note**: Myanmar uses single-member constituencies

#### `electoral_system`
- **Type**: String
- **Value**: Always `"FPTP"`
- **Description**: Electoral system used (First Past The Post)

#### `coordinates`
- **Type**: Object
- **Properties**:
  - `lat`: Float (-90 to 90)
  - `lng`: Float (-180 to 180)
- **Description**: Approximate geographic center of constituency
- **Source**: Derived from township/constituency name geocoding

## Geographic Data

### Myanmar States and Regions

The data covers all 15 states and regions of Myanmar:

#### States (7)
1. Kachin State (ကချင်ပြည်နယ်)
2. Kayah State (ကယားပြည်နယ်)
3. Kayin State (ကရင်ပြည်နယ်)
4. Chin State (ချင်းပြည်နယ်)
5. Mon State (မွန်ပြည်နယ်)
6. Rakhine State (ရခိုင်ပြည်နယ်)
7. Shan State (ရှမ်းပြည်နယ်)

#### Regions (7)
1. Sagaing Region (စစ်ကိုင်းတိုင်း)
2. Tanintharyi Region (တနင်္သာရီတိုင်း)
3. Bago Region (ပဲခူးတိုင်း)
4. Magway Region (မကွေးတိုင်း)
5. Mandalay Region (မန္တလေးတိုင်း)
6. Yangon Region (ရန်ကုန်တိုင်း)
7. Ayeyarwady Region (ဧရာဝတီတိုင်း)

#### Union Territory (1)
1. Naypyitaw Union Territory (နေပြည်တော်ပြည်ထောင်စုနယ်မြေ)

## Data Quality Notes

### Completeness
- **Records**: 872 constituencies (complete)
- **Required Fields**: All core fields populated
- **Missing Data**: Column 6 is empty in source data

### Consistency
- **Electoral System**: Uniform FPTP across all constituencies
- **Representatives**: Consistent value of 1 per constituency
- **Naming**: Myanmar language names are original source of truth

### Data Validation Rules

1. **ID Uniqueness**: Each constituency must have unique ID
2. **Representative Count**: Must equal 1 for all records
3. **State/Region Names**: Must match official Myanmar administrative divisions
4. **Electoral System**: Must be "FPTP" for all records
5. **Coordinates**: Must be valid lat/lng within Myanmar boundaries

### Known Data Limitations

1. **Assembly Coverage**: Only includes Pyithu Hluttaw constituencies
2. **Temporal Scope**: Represents 2025 electoral plan only
3. **Geographic Precision**: Approximate coordinates, not precise boundaries
4. **Language**: Primary source is Myanmar language, English translations added

## Translation Guidelines

### Myanmar to English Name Mapping

- **State/Region Suffixes**:
  - `ပြည်နယ်` → `State`
  - `တိုင်း` → `Region`
  - `နယ်မြေ` → `Territory`

- **Township Suffixes**:
  - `မြို့နယ်` → `Township`
  - `မြို့` → `Town`

- **Geographic Terms**:
  - `တစ်ခုလုံး` → `Entire`
  - `အစိတ်အပိုင်း` → `Part of`
  - `ပတ်ဝန်းကျင်` → `Surrounding area`

## Usage Examples

### Filtering by State/Region
```python
# Get all constituencies in Yangon Region
yangon_constituencies = df[df['state_region_en'] == 'Yangon Region']
```

### Aggregating by Assembly Type
```python
# Count constituencies by assembly type
assembly_counts = df.groupby('assembly_type').size()
```

### Geographic Analysis
```python
# Calculate center point for each state/region
state_centers = df.groupby('state_region_en')[['lat', 'lng']].mean()
```

## Future Enhancements

1. **Additional Assembly Types**: Include Amyotha Hluttaw and State/Regional data
2. **Historical Data**: Add previous election constituency data
3. **Demographic Overlay**: Population, ethnic composition, economic indicators
4. **Precise Boundaries**: GeoJSON polygons for exact constituency boundaries
5. **Multi-language Support**: Additional language translations beyond Myanmar/English