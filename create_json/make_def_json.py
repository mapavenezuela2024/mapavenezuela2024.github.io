#%%
import pandas as pd
import json
from copy import deepcopy
from unidecode import unidecode
from tqdm import tqdm
from itertools import product
from names_map import states_mapping, municipalities_mapping, parroquias_mapping

#monkey patch JSONEncoder to limit the number of decimal places
class RoundingFloat(float):
    __repr__ = staticmethod(lambda x: format(x, '.6f'))

json.encoder.c_make_encoder = None
json.encoder.float = RoundingFloat
#%%
results_csv = './Filtered_Election_Results.csv'
geojson_file = './ven_admbnda_adm3_ine_20210223.json'

# Load the CSV file
filtered_data = pd.read_csv(results_csv)
# Load the GeoJSON file
with open(geojson_file) as f:
    venezuela_geojson = json.load(f)

#%%
def n(s):
    return unidecode(s.lower().strip())

def n_json(s):
    if s.startswith('Capital '):
        return n(s[8:])
    elif s.startswith('Urbana '):
        return n(s[7:])
    elif s.startswith('No Urbana '):
        return n(s[10:])
    else:
        return n(s)

def search_feature(estado, municipio, parroquia):
    for i, f in enumerate(venezuela_geojson['features']):
        if n(f['properties']['ADM1_ES']) == n(estado) and \
           n(f['properties']['ADM2_ES']) == n(municipio) and \
           n_json(f['properties']['ADM3_ES']) == n(parroquia):
            return i
    raise ValueError(f'Feature not found for {estado}, {municipio}, {parroquia}')
new_json = deepcopy(venezuela_geojson)
error_count = 0
dict_mapping = {}
for index, row in tqdm(filtered_data.iterrows(), total=filtered_data.shape[0]):
    estado = row['EDO']
    municipio = row['MUN']
    parroquia = row['PAR']
    m_estado = states_mapping[estado]
    m_municipio = municipalities_mapping[municipio]
    m_parroquia = parroquias_mapping[parroquia]
    row['URL'] = row['URL'].replace('https://static.resultadosconvzla.com/', '')
    row['URL'] = row['URL'].replace('.jpg', '')
    
    if estado == 'EDO. MERIDA' and municipio == 'MP.JULIO CESAR SALAS' and parroquia == 'CM. ARAPUEY':
        m_estado = 'Zulia'
        m_municipio = 'Sucre'
        m_parroquia = 'Rómulo Gallegos'
    if estado == 'EDO. LARA' and municipio == 'MP. TORRES' and parroquia == 'PQ. HERIBERTO ARROYO':
        m_estado = 'Trujillo'
        m_municipio = 'José Felipe Márquez Cañizal'
        m_parroquia = 'El Socorro'
    if not isinstance(m_parroquia, list):
        m_parroquia = [m_parroquia]
    if not isinstance(m_municipio, list):
        m_municipio = [m_municipio]
    json_index = None
    for mun, parr in product(m_municipio, m_parroquia):
        try:
            json_index = search_feature(m_estado, mun, parr)
        except:
            pass
    if json_index is None:
        error_count += 1
        print(f'Estado: {estado}, Municipio: {municipio}, Parroquia: {parroquia}, not found with {m_estado}, {m_municipio}, {m_parroquia}')
    dict_mapping[(estado, municipio, parroquia)] = json_index
    if 'EDO' not in new_json['features'][json_index]['properties']:
        new_json['features'][json_index]['properties'] = deepcopy(row).to_dict()
        total_votes = row['Nicolás Maduro Moros'] + row['Edmundo González'] + row['OTROS']
        new_json['features'][json_index]['properties']['mesas'] = []
        new_json['features'][json_index]['properties']['mesas'].append({'N. Maduro': row['Nicolás Maduro Moros'], 'E. González': row['Edmundo González'], 'OTROS': row['OTROS'], 'URL': row['URL']})
        del new_json['features'][json_index]['properties']['Nicolás Maduro Moros']
        del new_json['features'][json_index]['properties']['Edmundo González']
        del new_json['features'][json_index]['properties']['OTROS']
        del new_json['features'][json_index]['properties']['URL']
        #1.0 if González won, -1.0 if Maduro won, 0.0 if tie
        #formula: (votes for González - votes for Maduro) / total votes
        color = (row['Edmundo González'] - row['Nicolás Maduro Moros']) / total_votes
        new_json['features'][json_index]['properties']['color'] = color
    else: #update with a new electoral table
        new_json['features'][json_index]['properties']['mesas'].append({'N. Maduro': row['Nicolás Maduro Moros'], 'E. González': row['Edmundo González'], 'OTROS': row['OTROS'], 'URL': row['URL']})
        total_votes = sum([m['N. Maduro'] + m['E. González'] + m['OTROS'] for m in new_json['features'][json_index]['properties']['mesas']])
        votos_gonzalez = sum([m['E. González'] for m in new_json['features'][json_index]['properties']['mesas']])
        votos_maduro = sum([m['N. Maduro'] for m in new_json['features'][json_index]['properties']['mesas']])
        color = (votos_gonzalez - votos_maduro) / total_votes
        new_json['features'][json_index]['properties']['color'] = color

json.dump(new_json, open('votes_geojson_n.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print(f'Done! Dumped to votes_geojson_n.json with {error_count} errors')
# %%
# check if there are duplicates (repeated indexes in the dict values) and print the keys:val
print('The following parroquias from the vectorial map have being assigned to multiple electoral parroquias:')
d = {}
for k, v in dict_mapping.items():
    if v in d:
        print(f'{k}: {v}')
        for k2, v2 in dict_mapping.items():
            if v2 == v and k2 != k:
                print(f'    Also assigned to {k2}: {v2}')
    d[v] = k
        

