import sys
import os
import os.path
import shutil
import pandas as pd
import numpy as np
import requests

def download(url, file_name):
    with open(file_name, "wb") as file:
        response = requests.get(url)
        file.write(response.content)

    if response.status_code != 200:
        sys.exit('Downlaod Error: StatusCode '+str(response.status_code)+' URL:'+url)


def getDataFromInternet():
    downloads = {
        'ch.swisstopo.amtliches-gebaeudeadressverzeichnis': 'https://data.geo.admin.ch/ch.swisstopo.amtliches-gebaeudeadressverzeichnis/csv/2056/',
        'PLZO_CSV_LV95': 'https://data.geo.admin.ch/ch.swisstopo-vd.ortschaftenverzeichnis_plz/'
    }
    for file, url_path in downloads.items():
        file_name = file+'.zip'
        extract_folder = './'+file
        download(url=url_path+file_name, file_name=file_name)

        if os.path.exists(file_name):
            if os.path.isdir(extract_folder): 
                shutil.rmtree(extract_folder, ignore_errors=True)
            shutil.unpack_archive(file_name, extract_folder)
            os.remove(file_name)
        else:
            sys.exit('File does not exist: '+file_name)


    

def getGemeindeverzeichnis():
    file_name = r'./PLZO_CSV_LV95/PLZO_CSV_LV95/PLZO_CSV_LV95.csv'
    if os.path.exists(file_name):
        dfTown = pd.read_csv(file_name, sep=';', dtype='unicode')
    else:
        sys.exit('File does not exist '+file_name)

    dfTown = dfTown.reset_index(drop=True)
    dfTown = dfTown.drop(['Zusatzziffer', 'Ortschaftsname', 'Kantonskürzel', 'E', 'N'], axis=1)
    dfTown = dfTown.rename(columns={'PLZ': 'zipTown', 'BFS-Nr': 'bfs', 'Gemeindename': 'village', 'Kantonskürzel': 'canton', 'Sprache': 'locale'})
    dfTown['zipTown'] = dfTown['zipTown'].astype(int)
    dfTown['bfs'] = dfTown['bfs'].astype(int)
    dfTown = dfTown.drop(['zipTown'], axis=1)
    return dfTown

def getGebaeudeverzeichnis():
    dfStreet = pd.read_csv(r'./ch.swisstopo.amtliches-gebaeudeadressverzeichnis/pure_adr.csv', sep=';', dtype='unicode')
    dfStreet = dfStreet.reset_index(drop=True)
    dfStreet[['zip','streetVillage']] = dfStreet['ZIP_LABEL'].str.split(' ', n=1, expand=True)
    dfStreet['zip'] = dfStreet['zip'].astype(int)
    dfStreet['streetVillage'] = dfStreet['streetVillage'].str.strip()
    
    dfStreet = dfStreet.rename(columns={'COM_FOSNR': 'bfs'})
    dfStreet['bfs'] = dfStreet['bfs'].astype(int)
    dfStreet = dfStreet.drop(['ZIP_LABEL','ADR_EGAID', 'STR_ESID', 'BDG_EGID', 'COM_CANTON','ADR_EDID', 'STN_LABEL','ADR_NUMBER', 'BDG_CATEGORY', 'BDG_NAME', 'ADR_STATUS', 'ADR_OFFICIAL', 'ADR_VALID', 'ADR_MODIFIED','ADR_EASTING', 'ADR_NORTHING'], axis=1)
    dfStreet = dfStreet.drop(['streetVillage'], axis=1)
    return dfStreet

def sanatizeVillagesWithNumberAtEnd(df):
    #sanatize Villages with number at end
    #df = df[df['village'].str.contains('\d', regex= True)]
    villageCleanup = {
        "Lausanne 27": "Lausanne",
        "Lausanne 26": "Lausanne",
        "Lausanne 25": "Lausanne",
        "Laax GR 2": "Laax GR"
    }
    for old, new in villageCleanup.items():
        df['village'] = df['village'].replace([old], new)
    return df

def calculateZipShare(df):
    #calculate percentage of zip-share
    df['count_zip'] = df.groupby(['zip'])['zip'].transform('count')
    df['count_bfs'] = df.groupby(['zip','village'])['village'].transform('count')
    df['zip-share'] = df['count_bfs'] / df['count_zip'] * 100
    df['zip-share'] = df['zip-share'].round(decimals=2)
    df['zip-share'].values[df['zip-share'].values > 100] = 100
    return df

def main():
    getDataFromInternet()
    dfTown = getGemeindeverzeichnis()
    dfStreet = getGebaeudeverzeichnis()
    df = pd.merge(dfStreet, dfTown, on='bfs', how='left')

    df = sanatizeVillagesWithNumberAtEnd(df)
    df = calculateZipShare(df)
    
    #cleanup
    #df = df.drop(['count_bfs', 'count_zip', 'zipTown', 'streetVillage'], axis=1)
    df = df.dropna().drop_duplicates()
    
    #save
    df = df.sort_values(by=[ 'zip-share', 'zip'], ascending=[False, True])
    df.to_json(r'zip.json', orient='records');
    
    print( df[df['zip']==3053] )
    print(df)


if __name__ == "__main__":
    main()