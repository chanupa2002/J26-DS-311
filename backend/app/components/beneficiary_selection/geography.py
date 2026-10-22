"""User-approved province and district display names for the research UI."""

PROVINCES = (
    {"code": 1, "name": "Western"},
    {"code": 2, "name": "Southern"},
    {"code": 3, "name": "Northern"},
    {"code": 4, "name": "Eastern"},
    {"code": 5, "name": "North Central"},
    {"code": 6, "name": "Central"},
    {"code": 7, "name": "North Western"},
    {"code": 8, "name": "Uva"},
    {"code": 9, "name": "Sabaragamuwa"},
)

DISTRICTS = (
    {"code": 1, "name": "Colombo", "province_code": 1},
    {"code": 2, "name": "Gampaha", "province_code": 1},
    {"code": 3, "name": "Kaluthara", "province_code": 1},
    {"code": 4, "name": "Galle", "province_code": 2},
    {"code": 5, "name": "Hambanthota", "province_code": 2},
    {"code": 6, "name": "Matara", "province_code": 2},
    {"code": 7, "name": "Jaffna", "province_code": 3},
    {"code": 8, "name": "Kilinochchi", "province_code": 3},
    {"code": 9, "name": "Mannar", "province_code": 3},
    {"code": 10, "name": "Mulativu", "province_code": 3},
    {"code": 11, "name": "Vavuniya", "province_code": 3},
    {"code": 12, "name": "Ampara", "province_code": 4},
    {"code": 13, "name": "Batticaloa", "province_code": 4},
    {"code": 14, "name": "Trincomalee", "province_code": 4},
    {"code": 15, "name": "Anuradhapura", "province_code": 5},
    {"code": 16, "name": "Polonnaruwa", "province_code": 5},
    {"code": 17, "name": "Kandy", "province_code": 6},
    {"code": 18, "name": "Matale", "province_code": 6},
    {"code": 19, "name": "Nuwara Eliya", "province_code": 6},
    {"code": 20, "name": "Kurunegala", "province_code": 7},
    {"code": 21, "name": "Puttalam", "province_code": 7},
    {"code": 22, "name": "Badulla", "province_code": 8},
    {"code": 23, "name": "Monaragala", "province_code": 8},
    {"code": 24, "name": "Kegalla", "province_code": 9},
    {"code": 25, "name": "Rathnapura", "province_code": 9},
)

PROVINCE_BY_CODE = {row["code"]: row for row in PROVINCES}
DISTRICT_BY_CODE = {row["code"]: row for row in DISTRICTS}


def validate_pair(province_code, district_code):
    """Return false for unknown or cross-province codes; accepts numeric strings."""
    try:
        province = int(province_code)
        district = int(district_code)
    except (TypeError, ValueError):
        return False
    return (
        province in PROVINCE_BY_CODE
        and district in DISTRICT_BY_CODE
        and DISTRICT_BY_CODE[district]["province_code"] == province
    )
