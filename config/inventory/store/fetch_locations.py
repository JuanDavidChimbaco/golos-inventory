import json
import urllib.request
import os

def fetch_json(url):
    print(f"Fetching {url}...")
    with urllib.request.urlopen(url) as response:
        return json.load(response)['data']

def main():
    try:
        deps = fetch_json('https://raw.githubusercontent.com/proyecto26/colombia/master/departments.json')
        cities = fetch_json('https://raw.githubusercontent.com/proyecto26/colombia/master/cities.json')

        output = {
            'departments': [],
            'cities': {}
        }

        for d in deps:
            d_id = str(d['id'])
            d_name = d['name']
            output['departments'].append({'code': d_id, 'name': d_name})
            output['cities'][d_id] = []

        for c in cities:
            d_id = str(c['departmentId'])
            if d_id in output['cities']:
                output['cities'][d_id].append({'code': str(c['id']), 'name': c['name']})

        # Sort everything
        output['departments'].sort(key=lambda x: x['name'])
        for d_id in output['cities']:
            output['cities'][d_id].sort(key=lambda x: x['name'])

        # Check for Palermo in Huila (41)
        huila_cities = [c['name'].lower() for c in output['cities'].get('41', [])]
        if 'palermo' not in huila_cities:
             print("Adding Palermo to Huila...")
             output['cities']['41'].append({'code': '41518', 'name': 'Palermo'}) # DANE code for Palermo, Huila is 41518
             output['cities']['41'].sort(key=lambda x: x['name'])
        else:
            print("Palermo already exists in Huila list.")

        with open('colombia_locations.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print('Success: colombia_locations.json created')
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
