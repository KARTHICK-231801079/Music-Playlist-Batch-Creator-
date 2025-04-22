import gdown

url = 'https://drive.google.com/uc?id=1e8CtNMNCGfcFKiH4amW3NyliIn5Cf4P3'
output = 'music_df.pkl'
gdown.download(url, output, quiet=False)
