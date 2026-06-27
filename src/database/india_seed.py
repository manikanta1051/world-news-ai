from typing import TypedDict


class IndiaRegionSeed(TypedDict):
    """Seed structure for an Indian state or territory."""

    code: str
    short_code: str
    name: str
    region_type: str
    display_order: int


INDIA_STATE_AND_UT_SEED: tuple[
    IndiaRegionSeed,
    ...,
] = (
    {
        "code": "IN-AP",
        "short_code": "AP",
        "name": "Andhra Pradesh",
        "region_type": "state",
        "display_order": 1,
    },
    {
        "code": "IN-AR",
        "short_code": "AR",
        "name": "Arunachal Pradesh",
        "region_type": "state",
        "display_order": 2,
    },
    {
        "code": "IN-AS",
        "short_code": "AS",
        "name": "Assam",
        "region_type": "state",
        "display_order": 3,
    },
    {
        "code": "IN-BR",
        "short_code": "BR",
        "name": "Bihar",
        "region_type": "state",
        "display_order": 4,
    },
    {
        "code": "IN-CT",
        "short_code": "CT",
        "name": "Chhattisgarh",
        "region_type": "state",
        "display_order": 5,
    },
    {
        "code": "IN-GA",
        "short_code": "GA",
        "name": "Goa",
        "region_type": "state",
        "display_order": 6,
    },
    {
        "code": "IN-GJ",
        "short_code": "GJ",
        "name": "Gujarat",
        "region_type": "state",
        "display_order": 7,
    },
    {
        "code": "IN-HR",
        "short_code": "HR",
        "name": "Haryana",
        "region_type": "state",
        "display_order": 8,
    },
    {
        "code": "IN-HP",
        "short_code": "HP",
        "name": "Himachal Pradesh",
        "region_type": "state",
        "display_order": 9,
    },
    {
        "code": "IN-JH",
        "short_code": "JH",
        "name": "Jharkhand",
        "region_type": "state",
        "display_order": 10,
    },
    {
        "code": "IN-KA",
        "short_code": "KA",
        "name": "Karnataka",
        "region_type": "state",
        "display_order": 11,
    },
    {
        "code": "IN-KL",
        "short_code": "KL",
        "name": "Kerala",
        "region_type": "state",
        "display_order": 12,
    },
    {
        "code": "IN-MP",
        "short_code": "MP",
        "name": "Madhya Pradesh",
        "region_type": "state",
        "display_order": 13,
    },
    {
        "code": "IN-MH",
        "short_code": "MH",
        "name": "Maharashtra",
        "region_type": "state",
        "display_order": 14,
    },
    {
        "code": "IN-MN",
        "short_code": "MN",
        "name": "Manipur",
        "region_type": "state",
        "display_order": 15,
    },
    {
        "code": "IN-ML",
        "short_code": "ML",
        "name": "Meghalaya",
        "region_type": "state",
        "display_order": 16,
    },
    {
        "code": "IN-MZ",
        "short_code": "MZ",
        "name": "Mizoram",
        "region_type": "state",
        "display_order": 17,
    },
    {
        "code": "IN-NL",
        "short_code": "NL",
        "name": "Nagaland",
        "region_type": "state",
        "display_order": 18,
    },
    {
        "code": "IN-OR",
        "short_code": "OR",
        "name": "Odisha",
        "region_type": "state",
        "display_order": 19,
    },
    {
        "code": "IN-PB",
        "short_code": "PB",
        "name": "Punjab",
        "region_type": "state",
        "display_order": 20,
    },
    {
        "code": "IN-RJ",
        "short_code": "RJ",
        "name": "Rajasthan",
        "region_type": "state",
        "display_order": 21,
    },
    {
        "code": "IN-SK",
        "short_code": "SK",
        "name": "Sikkim",
        "region_type": "state",
        "display_order": 22,
    },
    {
        "code": "IN-TN",
        "short_code": "TN",
        "name": "Tamil Nadu",
        "region_type": "state",
        "display_order": 23,
    },
    {
        "code": "IN-TG",
        "short_code": "TG",
        "name": "Telangana",
        "region_type": "state",
        "display_order": 24,
    },
    {
        "code": "IN-TR",
        "short_code": "TR",
        "name": "Tripura",
        "region_type": "state",
        "display_order": 25,
    },
    {
        "code": "IN-UP",
        "short_code": "UP",
        "name": "Uttar Pradesh",
        "region_type": "state",
        "display_order": 26,
    },
    {
        "code": "IN-UT",
        "short_code": "UT",
        "name": "Uttarakhand",
        "region_type": "state",
        "display_order": 27,
    },
    {
        "code": "IN-WB",
        "short_code": "WB",
        "name": "West Bengal",
        "region_type": "state",
        "display_order": 28,
    },
    {
        "code": "IN-AN",
        "short_code": "AN",
        "name": "Andaman and Nicobar Islands",
        "region_type": "union_territory",
        "display_order": 29,
    },
    {
        "code": "IN-CH",
        "short_code": "CH",
        "name": "Chandigarh",
        "region_type": "union_territory",
        "display_order": 30,
    },
    {
        "code": "IN-DH",
        "short_code": "DH",
        "name": (
            "Dadra and Nagar Haveli "
            "and Daman and Diu"
        ),
        "region_type": "union_territory",
        "display_order": 31,
    },
    {
        "code": "IN-DL",
        "short_code": "DL",
        "name": "Delhi",
        "region_type": "union_territory",
        "display_order": 32,
    },
    {
        "code": "IN-JK",
        "short_code": "JK",
        "name": "Jammu and Kashmir",
        "region_type": "union_territory",
        "display_order": 33,
    },
    {
        "code": "IN-LA",
        "short_code": "LA",
        "name": "Ladakh",
        "region_type": "union_territory",
        "display_order": 34,
    },
    {
        "code": "IN-LD",
        "short_code": "LD",
        "name": "Lakshadweep",
        "region_type": "union_territory",
        "display_order": 35,
    },
    {
        "code": "IN-PY",
        "short_code": "PY",
        "name": "Puducherry",
        "region_type": "union_territory",
        "display_order": 36,
    },
)


def validate_india_region_seed() -> None:
    """Validate uniqueness and expected region counts."""

    codes = {
        region["code"]
        for region in INDIA_STATE_AND_UT_SEED
    }

    short_codes = {
        region["short_code"]
        for region in INDIA_STATE_AND_UT_SEED
    }

    names = {
        region["name"]
        for region in INDIA_STATE_AND_UT_SEED
    }

    state_count = sum(
        1
        for region in INDIA_STATE_AND_UT_SEED
        if region["region_type"] == "state"
    )

    territory_count = sum(
        1
        for region in INDIA_STATE_AND_UT_SEED
        if region["region_type"]
        == "union_territory"
    )

    if len(INDIA_STATE_AND_UT_SEED) != 36:
        raise ValueError(
            "India seed must contain 36 regions."
        )

    if state_count != 28:
        raise ValueError(
            "India seed must contain 28 states."
        )

    if territory_count != 8:
        raise ValueError(
            "India seed must contain 8 Union Territories."
        )

    if len(codes) != 36:
        raise ValueError(
            "India region codes must be unique."
        )

    if len(short_codes) != 36:
        raise ValueError(
            "India short codes must be unique."
        )

    if len(names) != 36:
        raise ValueError(
            "India region names must be unique."
        )


validate_india_region_seed()