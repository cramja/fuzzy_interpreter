import requests
import zipfile
import io

datasets = {
    "gobike": 'https://s3.amazonaws.com/baywheels-data/202001-baywheels-tripdata.csv.zip'
}


def fetch():
    for name, url in datasets.items():
        r = requests.get(url)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(name)


if __name__ == '__main__':
    fetch()
