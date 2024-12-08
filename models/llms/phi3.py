import torch
import re
import json
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import argparse

model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Phi-3-mini-4k-instruct",
    device_map="auto",
    torch_dtype="auto",
    trust_remote_code=True,
)

tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
)

generation_args = {"max_new_tokens": 200,
                "return_full_text": False,
                "temperature": 0.0,
                "do_sample": False,
}

def disambiguate_entity_with_coords(entity_type, entity, sentence, city, state):

    messages = [
        {"role": "user", "content": f"The following sentence is from a news article located in {city}, {state}. Disambiguate the {entity_type} toponym entity '{entity}' and provide its coordinates in decimal format (latitude and longitude), no other information is needed. For example, output should be like this: 'latitude: 90.00, longitude: 90.00': {sentence}"}
    ]

    outputs = pipe(messages, **generation_args)

    response_text = outputs[0]["generated_text"].strip()
    
    # Extract the disambiguated entity and coordinates using regex
    lat_lon_pattern = r"latitude\s*:\s*([-+]?\d*\.\d+|\d+)(?:°\s*[NS])?.*?longitude\s*:\s*([-+]?\d*\.\d+|\d+)(?:°\s*[EW])?"

    lat_lon_match = re.search(lat_lon_pattern, response_text, re.IGNORECASE | re.DOTALL)
    
    latitude = float(lat_lon_match.group(1)) if lat_lon_match else None
    longitude = float(lat_lon_match.group(2)) if lat_lon_match else None

    return {
        "complete_response": response_text,
        "latitude": latitude,
        "longitude": longitude
    }

def process_jsonl(input_file, output_file, entity_type):
    results = []
    
    with open(input_file, 'r', encoding='utf-8') as file:
        for line in file:
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {e} for line: {line}")
                continue
            
            entity = data['entity']
            city = data['media_dets']['location_name']
            state = data['media_dets']['state']
            
            # Combine all sentences into one
            combined_sentence = ". ".join(sent_obj['sent'] for sent_obj in data['context']['sents'])
            
            if entity in combined_sentence:
                disambiguated_info = disambiguate_entity_with_coords(entity_type, entity, combined_sentence, city, state)
                result = {
                    'entity': entity,
                    'disambiguated_info': disambiguated_info,
                    'source': data
                }
                results.append(result)
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(results, outfile, indent=4, ensure_ascii=False) 


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Disambiguate an entity and retrieve its coordinates.")
    
    # Define command-line arguments
    parser.add_argument('input_file', help="Path to the input JSONL file")
    parser.add_argument('output_file', help="Path to the output JSON file")
    parser.add_argument('entity_type', choices=['geopolitical (GPE)', 'location (LOC)', 'facility (FAC)'], help="either of 'geopolitical (GPE)', 'location (LOC)', 'facility (FAC)")

    args = parser.parse_args()

    process_jsonl(args.input_file, args.output_file, args.entity_type)