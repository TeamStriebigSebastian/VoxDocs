"""
Classification service for dental transcriptions.
Categorizes transcribed text into dental-specific categories.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class CategoryType(str, Enum):
    """Types of classification categories."""
    FINDING = "finding"
    DIAGNOSIS = "diagnosis"
    TREATMENT = "treatment"
    MATERIAL = "material"
    INSTRUMENT = "instrument"
    ANATOMY = "anatomy"
    TOOTH = "tooth"
    SURFACE = "surface"
    OTHER = "other"


@dataclass
class ClassificationResult:
    """Result of a classification."""
    category: CategoryType
    extracted_text: str
    normalized_value: Optional[str]
    confidence: float
    start_position: int
    end_position: int
    tooth_number: Optional[str] = None
    surface: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DentalClassifier:
    """Rule-based classifier for dental terminology."""

    def __init__(self):
        self._patterns = self._build_patterns()
        self._normalizations = self._build_normalizations()

    def _build_patterns(self) -> Dict[CategoryType, List[Tuple[str, str]]]:
        """Build regex patterns for each category."""
        return {
            CategoryType.TOOTH: [
                # FDI notation: Zahn [1-4][1-8] or Zahn [5-8][1-5] (milk teeth)
                (r"[Zz]ahn\s+(\d)\s*(\d)", "tooth_fdi"),
                (r"[Zz]ahn\s+(\d{2})", "tooth_fdi_compact"),
                # Quadrant references
                (r"[Qq]uadrant\s+(\d)", "quadrant"),
                # Region references
                (r"(Oberkiefer|Unterkiefer)\s*(rechts|links)?", "jaw_region"),
            ],
            CategoryType.SURFACE: [
                (r"\b(mesial|distal|bukkal|palatinal|okklusal|vestibulär|oral|inzisal|approximal|zervikal|koronal|lingual)\b", "surface"),
                (r"\b(MOD|MO|OD|DO|BOD|MOB)\b", "surface_abbrev"),  # Common abbreviations
            ],
            CategoryType.DIAGNOSIS: [
                (r"[Kk]aries\s*[Gg]rad\s*(\d)", "caries_grade"),
                (r"[Kk]aries\s*(profunda|media|superficialis)?", "caries"),
                (r"[Pp]arodontitis\s*(apicalis)?\s*(chronica|acuta)?", "periodontitis"),
                (r"[Pp]ulpitis\s*(reversibel|irreversibel)?", "pulpitis"),
                (r"[Gg]ingivitis", "gingivitis"),
                (r"[Pp]eriimplantitis", "periimplantitis"),
                (r"[Ww]urzelkaries", "root_caries"),
                (r"[Aa]brasion", "abrasion"),
                (r"[Ee]rosion", "erosion"),
                (r"[Ff]raktur", "fracture"),
            ],
            CategoryType.FINDING: [
                (r"[Ll]ockerungsgrad\s*(\d|eins|zwei|drei)", "mobility_grade"),
                (r"[Tt]aschentiefe\s*(\d+)\s*([Mm]illimeter|mm)?", "pocket_depth"),
                (r"[Bb]lutung\s*(auf\s+)?[Ss]ondierung", "bleeding_on_probing"),
                (r"[Ff]urkationsbefall\s*[Gg]rad\s*(\d)?", "furcation"),
                (r"[Ff]istel", "fistula"),
                (r"[Ss]chwellung", "swelling"),
                (r"[Rr]ezession\s*(\d+\s*mm)?", "recession"),
                (r"[Ss]ensibilität\s*(positiv|negativ|vermindert)", "sensitivity"),
                (r"[Pp]erkussion\s*(positiv|negativ|schmerzhaft)", "percussion"),
            ],
            CategoryType.TREATMENT: [
                (r"[Ww]urzelkanalbehandlung", "root_canal"),
                (r"[Kk]avitätenpräparation", "cavity_prep"),
                (r"[Cc]omposite[-\s]?[Ff]üllung", "composite_filling"),
                (r"[Aa]malgam[-\s]?[Ff]üllung", "amalgam_filling"),
                (r"[Kk]ronenversorgung", "crown"),
                (r"[Bb]rückenversorgung", "bridge"),
                (r"[Ee]xtraktion", "extraction"),
                (r"[Ii]mplantation", "implantation"),
                (r"[Pp]rofessionelle\s+[Zz]ahnreinigung|PZR", "prophylaxis"),
                (r"[Ss]kaling|[Ss]caling", "scaling"),
                (r"[Ww]urzelglättung", "root_planing"),
                (r"[Nn]aht", "suture"),
                (r"[Ii]nzision", "incision"),
            ],
            CategoryType.MATERIAL: [
                (r"\b[Cc]omposite\b", "composite"),
                (r"\b[Aa]malgam\b", "amalgam"),
                (r"[Gg]lasionomerzement|GIZ", "glass_ionomer"),
                (r"[Zz]irkonoxid", "zirconia"),
                (r"[Tt]itan[-\s]?[Ii]mplantat", "titanium_implant"),
                (r"[Gg]uttapercha", "guttapercha"),
                (r"\bMTA\b|[Mm]ineral\s*[Tt]rioxide\s*[Aa]ggregate", "mta"),
                (r"[Aa]rtikain|[Uu]ltracain", "articaine"),
                (r"[Ll]idocain", "lidocaine"),
                (r"[Mm]epilivacain|[Ss]candicain", "mepivacaine"),
            ],
            CategoryType.INSTRUMENT: [
                (r"[Rr]osenbohrer", "rose_bur"),
                (r"[Ff]issurenbohrer", "fissure_bur"),
                (r"[Dd]iamantschleifer", "diamond_bur"),
                (r"[Hh][-\s]?[Ff]eile", "h_file"),
                (r"[Kk][-\s]?[Ff]eile", "k_file"),
                (r"[Ss]caler", "scaler"),
                (r"[Kk]ürette", "curette"),
                (r"[Ee]xkavator", "excavator"),
                (r"[Ss]topfer", "plugger"),
            ],
            CategoryType.ANATOMY: [
                (r"[Ss]chmelz", "enamel"),
                (r"[Dd]entin", "dentin"),
                (r"[Pp]ulpa", "pulp"),
                (r"[Pp]arodontalspalt", "pdl"),
                (r"[Aa]lveolarknochen", "alveolar_bone"),
                (r"[Gg]ingiva", "gingiva"),
                (r"[Ss]ulkus", "sulcus"),
                (r"[Aa]pex", "apex"),
                (r"[Bb]ifurkation", "bifurcation"),
                (r"[Tt]rifurkation", "trifurcation"),
                (r"[Ff]oramen", "foramen"),
            ],
        }

    def _build_normalizations(self) -> Dict[str, str]:
        """Build normalization mappings for common terms."""
        return {
            # Number words to digits
            "eins": "1", "zwei": "2", "drei": "3", "vier": "4",
            "fünf": "5", "sechs": "6", "sieben": "7", "acht": "8",
            # Surface normalizations
            "mesial": "M", "distal": "D", "bukkal": "B",
            "palatinal": "P", "okklusal": "O", "lingual": "L",
            "vestibulär": "V", "oral": "Or", "inzisal": "I",
        }

    def classify(self, text: str) -> List[ClassificationResult]:
        """
        Classify a transcription text into dental categories.

        Args:
            text: The transcription text to classify

        Returns:
            List of ClassificationResult objects
        """
        results = []

        for category, patterns in self._patterns.items():
            for pattern, pattern_type in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    result = self._create_result(
                        category=category,
                        match=match,
                        pattern_type=pattern_type,
                        full_text=text
                    )
                    if result:
                        results.append(result)

        # Sort by position in text
        results.sort(key=lambda r: r.start_position)

        # Detect compound expressions (e.g., "Zahn 16 mesial Karies Grad 2")
        results = self._detect_compound_expressions(results, text)

        logger.debug(f"Classified {len(results)} entities from text")
        return results

    def _create_result(
        self,
        category: CategoryType,
        match: re.Match,
        pattern_type: str,
        full_text: str
    ) -> Optional[ClassificationResult]:
        """Create a classification result from a regex match."""
        extracted_text = match.group(0)
        groups = match.groups()

        # Calculate confidence based on match quality
        confidence = 0.9  # Base confidence for exact pattern match

        # Normalize the value
        normalized = self._normalize_value(extracted_text, pattern_type, groups)

        # Extract tooth number if applicable
        tooth_number = None
        if pattern_type in ["tooth_fdi", "tooth_fdi_compact"]:
            if len(groups) >= 2:
                tooth_number = f"{groups[0]}{groups[1]}"
            elif len(groups) == 1:
                tooth_number = groups[0]

        # Extract surface if applicable
        surface = None
        if category == CategoryType.SURFACE:
            surface = self._normalizations.get(extracted_text.lower(), extracted_text)

        return ClassificationResult(
            category=category,
            extracted_text=extracted_text,
            normalized_value=normalized,
            confidence=confidence,
            start_position=match.start(),
            end_position=match.end(),
            tooth_number=tooth_number,
            surface=surface,
            metadata={"pattern_type": pattern_type}
        )

    def _normalize_value(
        self,
        text: str,
        pattern_type: str,
        groups: Tuple
    ) -> str:
        """Normalize extracted values."""
        # Replace word numbers with digits
        normalized = text.lower()
        for word, digit in self._normalizations.items():
            normalized = normalized.replace(word, digit)

        # Specific normalizations by pattern type
        if pattern_type == "tooth_fdi" and len(groups) >= 2:
            return f"{groups[0]}{groups[1]}"
        elif pattern_type == "pocket_depth" and groups:
            return f"{groups[0]}mm"
        elif pattern_type == "caries_grade" and groups:
            return f"Karies G{groups[0]}"
        elif pattern_type == "mobility_grade" and groups:
            grade = self._normalizations.get(groups[0], groups[0])
            return f"LG{grade}"

        return normalized

    def _detect_compound_expressions(
        self,
        results: List[ClassificationResult],
        text: str
    ) -> List[ClassificationResult]:
        """
        Detect compound dental expressions and enrich results.

        For example: "Zahn 16 mesial Karies Grad 2" should link
        the tooth number to the diagnosis and surface.
        """
        # Group results by proximity (within 50 characters)
        enhanced_results = []
        current_tooth = None

        for result in results:
            # Track current tooth context
            if result.category == CategoryType.TOOTH:
                current_tooth = result.tooth_number

            # Enrich findings/diagnoses with tooth context
            if current_tooth and result.category in [
                CategoryType.FINDING,
                CategoryType.DIAGNOSIS,
                CategoryType.TREATMENT
            ]:
                if not result.tooth_number:
                    result.tooth_number = current_tooth

            enhanced_results.append(result)

        return enhanced_results

    def get_summary(self, results: List[ClassificationResult]) -> Dict[str, Any]:
        """
        Generate a summary of classification results.

        Args:
            results: List of classification results

        Returns:
            Summary dictionary with counts and key findings
        """
        summary = {
            "total_entities": len(results),
            "by_category": {},
            "teeth_mentioned": set(),
            "diagnoses": [],
            "treatments": [],
            "findings": [],
        }

        for result in results:
            # Count by category
            cat_name = result.category.value
            if cat_name not in summary["by_category"]:
                summary["by_category"][cat_name] = 0
            summary["by_category"][cat_name] += 1

            # Collect teeth
            if result.tooth_number:
                summary["teeth_mentioned"].add(result.tooth_number)

            # Collect key clinical data
            if result.category == CategoryType.DIAGNOSIS:
                summary["diagnoses"].append({
                    "text": result.extracted_text,
                    "tooth": result.tooth_number,
                    "normalized": result.normalized_value
                })
            elif result.category == CategoryType.TREATMENT:
                summary["treatments"].append({
                    "text": result.extracted_text,
                    "tooth": result.tooth_number,
                    "normalized": result.normalized_value
                })
            elif result.category == CategoryType.FINDING:
                summary["findings"].append({
                    "text": result.extracted_text,
                    "tooth": result.tooth_number,
                    "normalized": result.normalized_value
                })

        # Convert set to list for JSON serialization
        summary["teeth_mentioned"] = sorted(list(summary["teeth_mentioned"]))

        return summary


# Global service instance
classifier = DentalClassifier()
