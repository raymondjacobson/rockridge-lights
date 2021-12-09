# RockridgeLights

## Run

```bash
nohup python index.py
```

## Run a sequence

```bash
nohup python index.py lib/sequences/candycanes.py &
```

## Run a song

1. Connect bluetooth speaker (power on, should automatically connect. If not, ssh into raspberry pi and use bluetoothctl to connect)

```bash
nohup python index.py https://youtube.com?v=XYZ
```

