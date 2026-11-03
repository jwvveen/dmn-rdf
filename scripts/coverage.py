"""Which shape or check tests which normative sentence of DMN 1.6.

Key: the position of the sentence in sources/dmn-rules.json
(dmn:statement-NNN in dmn-rules.ttl). Value: one or more shapes or computed
checks ("dmnsh:..."), or the reason nothing checks it. Filled in by hand: this
is the coverage of the work, and the SemanticXL tests hold it complete.
"""

_NOTATIE = "Notation of the diagram (DRD); diagram interchange is left out on purpose, so the RDF form holds no layout to check."
_FEEL = "Needs FEEL name resolution or a full FEEL parser; the checker decides S-FEEL cells only, and dmnsh:NotDecided reports the rest."
_STRUCTUUR = "Holds by construction: the metamodel (dmn.ttl) offers no other place for it, and the converter reports anything it cannot place."
_ID = ("In RDF an id is an IRI, so two elements with one id become one resource. The converter "
       "(scripts/dmn2rdf.py) reports a duplicate id before that happens.")
_URI = "The value is text in the metamodel; a URI check would repeat what xsd:anyURI in the schema already says."
_DEF = "A definition, used by the computed checks."
_NOG = "Not checked yet."

REQ = "dmnsh:InformationRequirementShape, dmnsh:KnowledgeRequirementShape, dmnsh:AuthorityRequirementShape"

DEKKING: dict[int, str] = {
    1: REQ,
    2: "dmnsh:RequirementMatrixShape", 3: "dmnsh:InformationAcyclicShape", 4: "dmnsh:RequirementMatrixShape",
    5: _FEEL, 6: "dmnsh:RequirementMatrixShape", 7: "dmnsh:RequirementMatrixShape",
    8: "dmnsh:RequirementMatrixShape", 9: "dmnsh:RequirementMatrixShape",
    10: _NOTATIE, 11: _NOTATIE, 12: _NOTATIE, 13: _NOTATIE, 14: _NOTATIE,
    15: _ID, 16: _ID, 17: _URI, 18: _URI, 19: _NOG, 20: _NOG, 21: _ID, 22: _STRUCTUUR, 23: _STRUCTUUR, 24: _ID,
    25: REQ, 26: _NOG,
    27: "dmnsh:UniqueNameShape",
    28: "dmnsh:InformationAcyclicShape", 29: "dmnsh:InformationAcyclicShape, dmnsh:KnowledgeAcyclicShape",
    30: _DEF, 31: "dmnsh:UniqueNameShape", 32: "dmnsh:KnowledgeAcyclicShape", 33: "dmnsh:VariableNameShape",
    34: _ID, 35: "dmnsh:VariableNameShape", 36: "dmnsh:DecisionServiceOutputShape",
    37: "dmnsh:DecisionServiceContentShape", 38: _NOG, 39: "dmnsh:UniqueNameShape", 40: _STRUCTUUR,
    41: _URI,
    42: "dmnsh:InformationRequirementShape", 43: "dmnsh:InformationRequirementShape",
    44: "dmnsh:InformationRequirementShape", 45: "dmnsh:InformationRequirementShape",
    46: "dmnsh:InformationAcyclicShape", 47: "dmnsh:InformationRequirementShape",
    48: "dmnsh:KnowledgeRequirementShape, dmnsh:RequirementMatrixShape", 49: "dmnsh:KnowledgeRequirementShape",
    50: "dmnsh:KnowledgeRequirementShape", 51: "dmnsh:KnowledgeRequirementShape",
    52: "dmnsh:KnowledgeAcyclicShape", 53: "dmnsh:KnowledgeRequirementShape",
    54: "dmnsh:AuthorityRequirementShape, dmnsh:RequirementMatrixShape", 55: "dmnsh:AuthorityRequirementShape",
    56: "dmnsh:RequirementMatrixShape", 57: "dmnsh:RequirementMatrixShape",
    58: _FEEL, 59: _FEEL, 60: _FEEL, 61: _FEEL, 62: "dmnsh:VariableNameShape", 63: _FEEL,
    64: _NOTATIE, 65: _FEEL, 66: _FEEL, 67: _FEEL, 68: _STRUCTUUR, 69: _NOG,
    70: "dmnsh:UnaryTestsTypeRefShape", 71: _URI, 72: "dmnsh:NotDecided", 73: "dmnsh:NotDecided",
    74: _NOG, 75: _NOG, 76: _NOG, 77: _NOG, 78: "dmnsh:AllowedValuesDeprecatedShape", 79: _NOG,
    80: "dmnsh:ItemDefinitionShape", 81: _STRUCTUUR, 82: _NOG, 83: "dmnsh:ItemDefinitionShape",
    84: "dmnsh:InformationItemNameShape", 85: _NOG, 86: _FEEL, 87: _FEEL, 88: _NOG,
    89: "dmnsh:LiteralExpressionShape", 90: _NOG, 91: _FEEL, 92: _FEEL, 93: _FEEL, 94: _DEF,
    95: _FEEL, 96: _FEEL, 97: _STRUCTUUR, 98: _FEEL,
    99: "dmnsh:Gap", 100: "dmnsh:SingleOutputNameShape", 101: "dmnsh:OutputNameShape",
    102: "dmnsh:OutputNameShape", 103: "dmnsh:EntryCountShape", 104: "dmnsh:AnnotationClauseNameShape",
    105: "dmnsh:DecisionTableOutputShape", 106: "dmnsh:DecisionTableRulesShape",
    107: "dmnsh:UniqueOverlap", 108: "dmnsh:UniqueOverlap", 109: "dmnsh:UniqueOverlap, dmnsh:AnyConflict",
    110: "dmnsh:UniqueOverlap",
    111: "Holds by construction: the converter keeps the order of rules as dmn:position (1-based).",
    112: _NOTATIE, 113: "dmnsh:CrosstabShape", 114: _NOTATIE, 115: _NOTATIE, 116: _NOTATIE, 117: _NOTATIE,
    118: "dmnsh:Gap", 119: _NOG, 120: _DEF, 121: _DEF, 122: "dmnsh:EntryOutsideInputValues",
    123: "dmnsh:OutputNameShape", 124: _NOG, 125: "dmnsh:OutputOutsideOutputValues",
    126: "dmnsh:OutputValuesNeededShape", 127: "dmnsh:OutputValuesNeededShape",
    128: "dmnsh:NotDecided", 129: "dmnsh:EntryOutsideInputValues", 130: _FEEL,
    131: _NOTATIE, 132: _NOTATIE, 133: _NOTATIE, 134: _NOG,
    135: "dmnsh:UniqueOverlap", 136: "dmnsh:CrosstabShape", 137: "dmnsh:UniqueOverlap", 138: "dmnsh:UniqueOverlap",
    139: "dmnsh:UniqueOverlap", 140: _DEF, 141: "dmnsh:AnyConflict",
    142: "dmnsh:AggregationShape, dmnsh:CompoundHitPolicyShape", 143: _DEF,
    144: "dmnsh:CrosstabShape", 145: "dmnsh:MaskedRule",
    146: "Holds by construction: the converter maps the value to an individual of dmn:DecisionTableOrientation (owl:oneOf) and reports any other value.",
    147: _NOTATIE,
    148: "Holds by construction: the converter maps the value to an individual of dmn:HitPolicy (owl:oneOf) and reports any other value.",
    149: "dmnsh:UniqueOverlap",
    150: "Holds by construction: the converter keeps the order of rules as dmn:position (1-based).",
    151: "dmnsh:OutputValuesNeededShape", 152: "dmnsh:AggregationShape", 153: "dmnsh:AggregationShape",
    154: "dmnsh:OutputNameShape", 155: "dmnsh:SingleOutputNameShape", 156: "dmnsh:AnnotationClauseNameShape",
    157: "dmnsh:SingleOutputNameShape", 158: "dmnsh:EntryCountShape", 159: "dmnsh:EntryCountShape",
    160: "dmnsh:EntryCountShape", 161: _NOG, 162: _NOG,
    163: "dmnsh:NotDecided", 164: _FEEL, 165: _FEEL, 166: "dmnsh:NotDecided", 167: "dmnsh:NotDecided",
    168: "dmnsh:NotDecided", 169: _FEEL, 170: _FEEL, 171: _FEEL, 172: _FEEL, 173: "dmnsh:NotDecided",
    174: "dmnsh:DefaultOutputValue", 175: "dmnsh:AggregationShape, dmnsh:CompoundHitPolicyShape",
    176: "dmnsh:DefaultOutputValue", 177: "dmnsh:CompoundHitPolicyShape",
}
