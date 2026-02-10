import requests

def probe():
    for p in range(8000,8011):
        try:
            r = requests.get(f'http://127.0.0.1:{p}/get_signal_logs', timeout=1)
            print(p, r.status_code)
            print(r.text[:400])
            return
        except Exception as e:
            print(p, 'no')

if __name__ == '__main__':
    probe()
