"""Environmental impact score, ported from the Flutter EnvironmentalImpactPage._calculateImpact."""

# Class names the detector or the segmenter may use for each land-cover group.
BUILDING = ("building", "buildings", "house", "structure")
TREE = ("tree", "trees", "tree/forest", "forest", "vegetation")
ROAD = ("road", "roads", "street")
WATER = ("water", "lake", "lakes", "river")
# Only produced by the U-Net++ model; weighted like water / roads in the original formula.
OTHER_GREEN = ("rangeland", "agriculture land")
OTHER_URBAN = ("developed space",)


def _sum(coverage: dict[str, float], names: tuple[str, ...]) -> float:
    return sum(coverage.get(n, 0.0) for n in names)


def calculate_impact(coverage: dict[str, float]) -> dict:
    cov = {k.lower(): v for k, v in coverage.items()}
    building, tree = _sum(cov, BUILDING), _sum(cov, TREE)
    road, water = _sum(cov, ROAD), _sum(cov, WATER)

    green_score = tree + water * 0.5 + _sum(cov, OTHER_GREEN) * 0.5
    urban_score = building + road * 0.7 + _sum(cov, OTHER_URBAN) * 0.7

    # Same thresholds as the app. "critical" is checked before "danger": in the Dart code the
    # danger branch came first, so the critical result could never appear for low green cover.
    if tree == 0 and building == 0 and green_score == 0 and urban_score == 0:
        status, level, recs = "No detectable land features", "unknown", [
            "Try uploading a clearer satellite/aerial image.",
            "Ensure the image shows land features like buildings, roads, or vegetation.",
            "Use images with at least 300×300 resolution for best detection.",
        ]
    elif green_score >= 60:
        status, level, recs = "Excellent — Healthy Green Cover 🌿", "healthy", [
            "This region has outstanding green coverage. Protect forested areas from encroachment.",
            "Continue conserving biodiversity corridors and wildlife habitats.",
            "Implement buffer zones around dense vegetation to prevent urban sprawl.",
            "Encourage eco-tourism as a sustainable alternative to development.",
        ]
    elif green_score >= 35 and urban_score <= 40:
        status, level, recs = "Good — Balanced Ecosystem ✅", "balanced", [
            "Maintain current green-to-urban balance — it's close to ideal.",
            "Introduce urban greening: rooftop gardens, tree-lined streets, mini forests.",
            "Set a goal: at least 40% natural cover within the next 5 years.",
            "Regulate new construction permits to protect remaining vegetation.",
        ]
    elif urban_score >= 70:
        status, level, recs = "Critical — Severe Environmental Degradation 🔴", "critical", [
            "URGENT: This region shows extreme urbanization with minimal natural cover.",
            "Immediately impose a moratorium on further construction.",
            "Launch large-scale afforestation programs — at least 10,000 trees needed.",
            "Restore wetlands and natural water bodies to counter urban heat islands.",
            "Implement mandatory green space ratios in all future urban planning.",
            "Engage local government and NGOs for environmental rehabilitation.",
        ]
    elif urban_score >= 50 and green_score < 35:
        status, level, recs = "Warning — Urban Pressure Detected 🚨", "danger", [
            "Halt unplanned construction — vegetation cover is critically low.",
            "Plant at least 5 trees for every new structure built in this area.",
            "Restore degraded land with native plant species to revive biodiversity.",
            "Develop green corridors connecting fragmented patches of vegetation.",
            "Introduce stormwater management systems to prevent urban flooding.",
        ]
    else:
        status, level, recs = "Moderate — Unbalanced Land Use ⚠️", "warning", [
            "Land use is unbalanced — urban and green areas need better ratio.",
            "Promote vertical gardens and green rooftops in densely built areas.",
            "Protect remaining tree cover from being cleared for roads or buildings.",
            "Encourage community-level composting and urban farming initiatives.",
            "Map and monitor green cover changes every 6 months via satellite imaging.",
        ]

    return {"status": status, "level": level, "recommendations": recs,
            "green_score": round(green_score, 2), "urban_score": round(urban_score, 2)}
