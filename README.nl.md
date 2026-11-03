# DMN 1.6 in RDF (concept)

Een concept-OWL-ontologie, een SHACL-validatieset en een controle van
beslistabellen voor DMN 1.6 (OMG, formal/25-12-02), op dezelfde manier gebouwd als
[ArchiMate 4.0 in RDF](https://github.com/jwvveen/archimate-rdf) en
[BPMN 2.0 in RDF](https://github.com/jwvveen/bpmn-rdf): de regels van de
specificatie zijn data, validatie staat los van betekenis, en beslismodellen
hangen aan processen, de wet, begrippen en architectuur.

*English version: [README.md](README.md).*

Status: **0.1.0-concept**. Een discussiestuk, geen standaard; geen publicatie van
de Object Management Group. Namespace: `https://w3id.org/dmn#` (registratie aangevraagd in
[perma-id/w3id.org#7065](https://github.com/perma-id/w3id.org/pull/7065)).

## In het kort

* **Het metamodel is data**, gegenereerd uit OMG's `DMN16.xmi`. Drie gebreken in
  dat bestand zijn zichtbaar gecorrigeerd.
* **Tabel 2 is data**, met per cel wat de specificatie toestaat en wat het
  XML-schema accepteert. Het schema keurt vier autoriteitsvereisten goed die
  Tabel 2 verbiedt.
* **177 normatieve zinnen** staan letterlijk in de graaf, elk met de controle die
  ze toetst (94) of de reden waarom niet (83).
* **Volgorde is data** (`dmn:position`): bij FIRST en RULE ORDER telt de volgorde
  van de regels.
* **Beslistabellen worden uitgerekend** over hun S-FEEL-cellen: overlap, gaten,
  regels die nooit gelden, waarden buiten de lijst. Een cel buiten S-FEEL wordt
  niet beoordeeld, en het rapport zegt dat.
* **Bruggen** naar BPMN (in de kern), de wet (`dmn:legalBasis`), begrippen
  (`dmn:meaning`) en ArchiMate 4.0 (brugregels als data).
* **Vier talen**: elke melding in het Engels, Nederlands, Duits en Frans.

## Valideren

```
pip install rdflib pyshacl
python validate.py --lang nl
python validate.py --lang nl model.dmn
```

Het voorbeeld `example.dmn` geeft precies acht meldingen. Op 168 echte modellen
(de OMG-voorbeelden bij DMN 1.6 en de DMN TCK) geen enkele valse matrixmelding;
wel naamloze annotatiekolommen in OMG's eigen voorbeeld, beslisservices zonder
ingesloten of invoerbeslissingen, en volledige tabellen met een standaarduitkomst.

## Licentie

Code: Apache 2.0. Ontologiebestanden: CC BY 4.0.
