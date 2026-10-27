"""Read model replies as JSON data, without evaluating source."""
import json
from pathlib import Path
text = Path('C:/Users/HET/.lmstudio/server-logs/2026-10/2026-10-14.1.log').read_text(encoding='utf-8')
for part in text.split('Generated prediction: ')[-10:]:
    try:
        reply = json.JSONDecoder().raw_decode(part)[0]
        content = json.loads(reply['choices'][0]['message']['content'])
        if 'handlers' in content:
            print(json.dumps({k:v[:350] for k,v in content['handlers'].items()}, indent=2))
        if 'lines' in content:
            print(json.dumps(content, indent=2))
    except (ValueError, KeyError):
        continue
