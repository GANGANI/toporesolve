import transformers
import torch
import re
import json
from transformers import AutoTokenizer
import argparse
    
model_id = "meta-llama/Llama-2-7b-chat-hf"
tokenizer = AutoTokenizer.from_pretrained(model_id, token=True)

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    torch_dtype= torch.float16,  # Using mixed precision for speed
    device_map="auto",
)


def disambiguate_entity_with_coords(entity_type, entity, sentence, city, state):

    messages = [
        {"role": "user", "content": f"The following sentence is from a news article located in {city}, {state}. Disambiguate the {entity_type} toponym entity '{entity}' and provide its coordinates in decimal format (latitude and longitude), no other information is needed. For example, output should be like this: 'latitude: 90.00, longitude: 90.00': {sentence}"}
    ]

    outputs = pipeline(
        messages,
        eos_token_id=tokenizer.eos_token_id,
        max_new_tokens=128,
    )

    response_text = outputs[0]["generated_text"][-1]["content"].strip()
    
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