1. **JSONL gold standard files**

Each JSONL file is designed to provide both the geolocation information of various entities and the context in which these entities are mentioned. This is useful for the geoparser evaluation script, as it allows the script to compare the geolocation results from the parser against this gold standard dataset. The evaluation involves checking how accurately the geoparser can identify and geolocate the entities mentioned in these contexts

- Gold standard files are in the format: `evaluation/merged/disambuigated/*.TOP_2023-06-07T160700Z.jsonl` where TOP = GPE or LOC or FAC

- Each line (i.e., each JSON object) represents a geographical entity and its context.
- Each entry has `lat_long` field with latitude and longitude values, indicating the geographic location related to the entry.

- The `entity` field represents a geographic entity (like "Newfane" or "Pennsylvania"), and the `entity_label` field contains a label for this entity, such as "GPE" (Geopolitical Entity).

- The `context` field contains contextual information where the entity is mentioned. This includes the sentences (`sents`) where the entity is mentioned.
- Other Information:
    - The link field provides a URL to the source of the information.
    - The title field contains the title of the source material.
    - Additional fields like published, link_extracted_from, and media_dets provide more context about the source, such as the publishing date, where the link was extracted from, and details about the media outlet.
